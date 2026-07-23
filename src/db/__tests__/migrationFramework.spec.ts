import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { Pool } from 'pg';
import type { PoolClient } from 'pg';
import {
  applyMigrationsAsync,
  dryRunMigrationsAsync,
  getAppliedVersionsAsync,
  loadMigrations,
  rollbackLastMigrationAsync,
  validateMigrationsIntegrity
} from '@db/migrationRunner';
import { MIGRATIONS_DIR } from '@db/connection';
import { UserRepository } from '@repositories/UserRepository';
import { LoanRepository } from '@repositories/LoanRepository';
import { IntegrityChecker } from '@repositories/IntegrityChecker';

const TEST_SCHEMA = 'mig_test';

function writeTempMigrations(files: Record<string, string>): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'maars-migrations-'));
  for (const [filename, content] of Object.entries(files)) {
    fs.writeFileSync(path.join(dir, filename), content);
  }
  return dir;
}

/**
 * search_path를 전용 스키마로 고정한 커넥션 풀을 생성한다.
 * 풀에서 꺼내는 모든 커넥션이 동일 스키마를 바라보므로,
 * 내부적으로 pool.query를 사용하는 리포지토리도 고립된 스키마에서 동작한다.
 */
function createSchemaPool(schema: string): Pool {
  const password = process.env.PG_PASSWORD;
  return new Pool({
    host: process.env.PG_HOST || 'localhost',
    port: parseInt(process.env.PG_PORT || '5432'),
    database: process.env.PG_TEST_DATABASE || 'maars_test',
    user: process.env.PG_USER || 'postgres',
    ...(password ? { password } : {}),
    options: `-c search_path=${schema}`,
    max: 5
  });
}

async function listTables(client: PoolClient): Promise<{ name: string }[]> {
  const result = await client.query(
    'SELECT tablename AS name FROM pg_tables WHERE schemaname = $1 ORDER BY tablename',
    [TEST_SCHEMA]
  );
  return result.rows;
}

describe('Migration Framework (Day 5 - Task 8: 데이터 마이그레이션 프레임워크, δ=1405)', () => {
  let pool: Pool;
  let client: PoolClient;

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
    pool = createSchemaPool(TEST_SCHEMA);
    client = await pool.connect();
    // 각 테스트마다 비어 있는 전용 스키마를 사용해 고립성을 보장한다 (SQLite의 :memory: 대체)
    await client.query(`DROP SCHEMA IF EXISTS ${TEST_SCHEMA} CASCADE`);
    await client.query(`CREATE SCHEMA ${TEST_SCHEMA}`);
    await client.query(`SET search_path TO ${TEST_SCHEMA}`);
  });

  afterEach(async () => {
    await client.query(`DROP SCHEMA IF EXISTS ${TEST_SCHEMA} CASCADE`).catch(() => {});
    await client.query('SET search_path TO public').catch(() => {});
    client.release();
    await pool.end();
    delete process.env.ENCRYPTION_KEY;
  });

  describe('[T-API-A43~A48] 마이그레이션 프레임워크', () => {
    it('[T-API-A43] 마이그레이션 파일 무결성 검증', async () => {
      // 실제 프로젝트의 마이그레이션 파일들은 이상이 없어야 한다
      expect(validateMigrationsIntegrity(MIGRATIONS_DIR)).toEqual([]);

      // 중복 버전 + 빈 DOWN 섹션을 가진 결함 있는 마이그레이션을 시뮬레이션
      const brokenDir = writeTempMigrations({
        '001_a.sql': '-- UP\nCREATE TABLE a (id TEXT PRIMARY KEY);\n-- DOWN\nDROP TABLE a;',
        '001_b.sql': '-- UP\nCREATE TABLE b (id TEXT PRIMARY KEY);\n-- DOWN\n'
      });

      const issues = validateMigrationsIntegrity(brokenDir);
      expect(issues.some((i) => i.message.includes('Duplicate migration version'))).toBe(true);
      expect(issues.some((i) => i.message.includes('empty DOWN section'))).toBe(true);

      fs.rmSync(brokenDir, { recursive: true, force: true });
    });

    it('[T-API-A44] Dry-run은 실제 반영 없이 대기 중인 마이그레이션만 보고한다', async () => {
      const allMigrations = loadMigrations(MIGRATIONS_DIR);
      const firstTwo = allMigrations.slice(0, 2).map((m) => m.version);
      const remaining = allMigrations.slice(2).map((m) => m.version);

      await applyMigrationsAsync(client, MIGRATIONS_DIR); // 전부 적용
      // 일부만 적용된 상태를 재현하기 위해 뒷부분을 롤백
      for (let i = 0; i < remaining.length; i++) {
        await rollbackLastMigrationAsync(client, MIGRATIONS_DIR);
      }
      expect([...(await getAppliedVersionsAsync(client))].sort()).toEqual([...firstTwo].sort());

      const beforeTables = await listTables(client);

      const result = await dryRunMigrationsAsync(client, MIGRATIONS_DIR);
      expect(result.wouldApply).toEqual(remaining);
      expect(result.errors).toEqual([]);

      // dry-run 이후에도 실제 적용 상태와 테이블 목록은 그대로여야 한다
      expect([...(await getAppliedVersionsAsync(client))].sort()).toEqual([...firstTwo].sort());
      const afterTables = await listTables(client);
      expect(afterTables).toEqual(beforeTables);
    });

    it('[T-API-A45] Dry-run은 SQL 오류가 있는 마이그레이션을 사전에 감지한다', async () => {
      const brokenDir = writeTempMigrations({
        '001_ok.sql': '-- UP\nCREATE TABLE ok_table (id TEXT PRIMARY KEY);\n-- DOWN\nDROP TABLE ok_table;',
        '002_broken.sql': '-- UP\nCREATE TABEL typo_syntax (id TEXT);\n-- DOWN\nDROP TABLE typo_syntax;'
      });

      const result = await dryRunMigrationsAsync(client, brokenDir);
      expect(result.wouldApply).toEqual(['001']); // 001은 성공, 002에서 중단
      expect(result.errors.length).toBe(1);
      expect(result.errors[0].version).toBe('002');

      // 롤백되어 DB에는 아무 것도 남지 않는다
      const tables = await listTables(client);
      expect(tables).toEqual([]);

      fs.rmSync(brokenDir, { recursive: true, force: true });
    });

    it('[T-API-A46] 여러 차례 순차 롤백 및 빈 상태에서의 안전성', async () => {
      const allMigrations = loadMigrations(MIGRATIONS_DIR);
      await applyMigrationsAsync(client, MIGRATIONS_DIR);

      const rolledBackOrder: string[] = [];
      for (let i = 0; i < allMigrations.length; i++) {
        const version = await rollbackLastMigrationAsync(client, MIGRATIONS_DIR);
        if (version) rolledBackOrder.push(version);
      }

      // 역순으로 하나씩 정확히 롤백되어야 한다
      expect(rolledBackOrder).toEqual([...allMigrations].reverse().map((m) => m.version));
      expect((await getAppliedVersionsAsync(client)).size).toBe(0);

      // 더 이상 롤백할 것이 없으면 안전하게 null을 반환한다 (예외 없이)
      expect(await rollbackLastMigrationAsync(client, MIGRATIONS_DIR)).toBeNull();
    });

    it('[T-API-A47] 마이그레이션 파이프라인 이후 무결성 체크 정상 동작', async () => {
      await applyMigrationsAsync(client, MIGRATIONS_DIR);

      // 리포지토리는 pool.query를 사용하므로, search_path가 고정된 풀을 통해
      // 동일한 고립 스키마(mig_test)에서 동작한다.
      const users = new UserRepository(pool);
      const loans = new LoanRepository(pool);
      const checker = new IntegrityChecker(pool);

      const registered = await users.register({ email: 'pipeline@example.com', name: 'Pipeline User' });
      const userId = registered.id;
      await loans.registerLoan({
        userId,
        productId: 'prod-1',
        originalAmount: 100000000,
        interestRate: 3.2,
        termMonths: 120,
        startDate: '2026-01-01'
      });

      const results = await checker.runFullCheck('2026-07-01');
      expect(results.every((r) => r.status === 'ok')).toBe(true);
    });
  });
});
