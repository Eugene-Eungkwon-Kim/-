import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import Database from 'better-sqlite3';
import {
  applyMigrations,
  dryRunMigrations,
  getAppliedVersions,
  loadMigrations,
  rollbackLastMigration,
  validateMigrationsIntegrity
} from '@db/migrationRunner';
import { MIGRATIONS_DIR } from '@db/connection';
import { UserRepository } from '@repositories/UserRepository';
import { LoanRepository } from '@repositories/LoanRepository';
import { IntegrityChecker } from '@repositories/IntegrityChecker';

const REPO_ROOT = path.resolve(__dirname, '../../..');

function writeTempMigrations(files: Record<string, string>): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'maars-migrations-'));
  for (const [filename, content] of Object.entries(files)) {
    fs.writeFileSync(path.join(dir, filename), content);
  }
  return dir;
}

describe('Migration Framework (Day 5 - Task 8: 데이터 마이그레이션 프레임워크, δ=1405)', () => {
  let db: Database.Database;

  beforeEach(() => {
    db = new Database(':memory:');
    db.pragma('foreign_keys = ON');
  });

  afterEach(() => {
    db.close();
  });

  describe('[T-API-A43~A48] 마이그레이션 프레임워크', () => {
    it('[T-API-A43] 마이그레이션 파일 무결성 검증', () => {
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

    it('[T-API-A44] Dry-run은 실제 반영 없이 대기 중인 마이그레이션만 보고한다', () => {
      const allMigrations = loadMigrations(MIGRATIONS_DIR);
      const firstTwo = allMigrations.slice(0, 2).map((m) => m.version);
      const remaining = allMigrations.slice(2).map((m) => m.version);

      applyMigrations(db, MIGRATIONS_DIR); // 전부 적용
      // 일부만 적용된 상태를 재현하기 위해 뒷부분을 롤백
      for (let i = 0; i < remaining.length; i++) {
        rollbackLastMigration(db, MIGRATIONS_DIR);
      }
      expect([...getAppliedVersions(db)].sort()).toEqual(firstTwo.sort());

      const beforeTables = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all();

      const result = dryRunMigrations(db, MIGRATIONS_DIR);
      expect(result.wouldApply).toEqual(remaining);
      expect(result.errors).toEqual([]);

      // dry-run 이후에도 실제 적용 상태와 테이블 목록은 그대로여야 한다
      expect([...getAppliedVersions(db)].sort()).toEqual(firstTwo.sort());
      const afterTables = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all();
      expect(afterTables).toEqual(beforeTables);
    });

    it('[T-API-A45] Dry-run은 SQL 오류가 있는 마이그레이션을 사전에 감지한다', () => {
      const brokenDir = writeTempMigrations({
        '001_ok.sql': '-- UP\nCREATE TABLE ok_table (id TEXT PRIMARY KEY);\n-- DOWN\nDROP TABLE ok_table;',
        '002_broken.sql': '-- UP\nCREATE TABEL typo_syntax (id TEXT);\n-- DOWN\nDROP TABLE typo_syntax;'
      });

      const result = dryRunMigrations(db, brokenDir);
      expect(result.wouldApply).toEqual(['001']); // 001은 성공, 002에서 중단
      expect(result.errors.length).toBe(1);
      expect(result.errors[0].version).toBe('002');

      // 롤백되어 DB에는 아무 것도 남지 않는다
      const tables = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all();
      expect(tables).toEqual([]);

      fs.rmSync(brokenDir, { recursive: true, force: true });
    });

    it('[T-API-A46] 여러 차례 순차 롤백 및 빈 상태에서의 안전성', () => {
      const allMigrations = loadMigrations(MIGRATIONS_DIR);
      applyMigrations(db, MIGRATIONS_DIR);

      const rolledBackOrder: string[] = [];
      for (let i = 0; i < allMigrations.length; i++) {
        const version = rollbackLastMigration(db, MIGRATIONS_DIR);
        if (version) rolledBackOrder.push(version);
      }

      // 역순으로 하나씩 정확히 롤백되어야 한다
      expect(rolledBackOrder).toEqual([...allMigrations].reverse().map((m) => m.version));
      expect(getAppliedVersions(db).size).toBe(0);

      // 더 이상 롤백할 것이 없으면 안전하게 null을 반환한다 (예외 없이)
      expect(rollbackLastMigration(db, MIGRATIONS_DIR)).toBeNull();
    });

    it('[T-API-A47] 마이그레이션 파이프라인 이후 무결성 체크 정상 동작', async () => {
      applyMigrations(db, MIGRATIONS_DIR);

      const users = new UserRepository(db);
      const loans = new LoanRepository(db);
      const checker = new IntegrityChecker(db);

      const userId = users.register({ email: 'pipeline@example.com', name: 'Pipeline User' }).id;
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

    it(
      '[T-API-A48] CLI가 실제 파일 기반 DB에 대해 동작한다',
      () => {
        const dbPath = path.join(os.tmpdir(), `maars-cli-test-${process.pid}.sqlite`);
        fs.rmSync(dbPath, { force: true });

        // vite-node를 npx 없이 직접 호출해 프로세스 스폰 오버헤드를 줄인다
        const viteNodeBin = path.join(REPO_ROOT, 'node_modules', '.bin', 'vite-node');
        const runCli = (command: string): string =>
          execFileSync(viteNodeBin, ['src/db/migrate-cli.ts', command], {
            cwd: REPO_ROOT,
            env: { ...process.env, DATABASE_PATH: dbPath },
            encoding: 'utf-8'
          });

        // CLI 서브프로세스는 두 번만 실행하고, 상태 확인은 직접 DB를 열어 빠르게 검증한다
        const upOutput = runCli('up');
        expect(upOutput).toContain('Applied:');

        const afterUp = new Database(dbPath);
        expect(getAppliedVersions(afterUp).size).toBe(loadMigrations(MIGRATIONS_DIR).length);
        afterUp.close();

        const rollbackOutput = runCli('down');
        expect(rollbackOutput).toContain('Rolled back: 008');

        const afterRollback = new Database(dbPath);
        expect(getAppliedVersions(afterRollback).has('008')).toBe(false);
        afterRollback.close();

        fs.rmSync(dbPath, { force: true });
      },
      15000
    );
  });
});
