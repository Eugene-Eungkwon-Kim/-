import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool, PoolClient } from 'pg';
import { createTestPool } from '@db/__tests__/testDatabase';
import {
  applyMigrationsAsync,
  getMigrationStatusAsync,
  loadMigrations,
  rollbackLastMigrationAsync
} from '@db/migrationRunner';
import { MIGRATIONS_DIR } from '@db/connection';

describe('Migration Runner (Day 5 - 기초: 스키마 버전 관리)', () => {
  let pool: Pool;
  let client: PoolClient;

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
    pool = createTestPool();
    client = await pool.connect();
    // 각 테스트마다 비어 있는 전용 스키마를 사용해 고립성을 보장한다 (SQLite의 :memory: 대체)
    await client.query('DROP SCHEMA IF EXISTS mig_test CASCADE');
    await client.query('CREATE SCHEMA mig_test');
    await client.query('SET search_path TO mig_test');
  });

  afterEach(async () => {
    await client.query('DROP SCHEMA IF EXISTS mig_test CASCADE').catch(() => {});
    await client.query('SET search_path TO public').catch(() => {});
    client.release();
    await pool.end();
    delete process.env.ENCRYPTION_KEY;
  });

  it('모든 마이그레이션을 순서대로 적용한다', async () => {
    const expectedVersions = loadMigrations(MIGRATIONS_DIR).map((m) => m.version);
    const applied = await applyMigrationsAsync(client, MIGRATIONS_DIR);
    expect(applied).toEqual(expectedVersions);

    const tables = await client.query(
      "SELECT tablename AS name FROM pg_tables WHERE schemaname = 'mig_test' ORDER BY tablename"
    );
    const tableNames = tables.rows.map((t) => t.name);
    expect(tableNames).toContain('users');
    expect(tableNames).toContain('users_audit');
  });

  it('이미 적용된 마이그레이션은 재실행하지 않는다 (idempotent)', async () => {
    await applyMigrationsAsync(client, MIGRATIONS_DIR);
    const secondRun = await applyMigrationsAsync(client, MIGRATIONS_DIR);
    expect(secondRun).toEqual([]);
  });

  it('DB 제약조건이 실제로 강제된다 (CHECK/UNIQUE)', async () => {
    await applyMigrationsAsync(client, MIGRATIONS_DIR);

    // credit_score 범위 초과 → CHECK 제약 위반
    await expect(
      client.query('INSERT INTO users (id, email, name, credit_score) VALUES ($1, $2, $3, $4)', [
        'u1',
        'a@example.com',
        'A',
        1500
      ])
    ).rejects.toThrow(/violates check constraint/);

    // 정상 삽입 후 이메일 중복 → UNIQUE 제약 위반
    await client.query('INSERT INTO users (id, email, name) VALUES ($1, $2, $3)', [
      'u2',
      'dup@example.com',
      'B'
    ]);
    await expect(
      client.query('INSERT INTO users (id, email, name) VALUES ($1, $2, $3)', ['u3', 'dup@example.com', 'C'])
    ).rejects.toThrow(/duplicate key value violates unique constraint/);
  });

  it('마이그레이션 상태를 조회할 수 있다', async () => {
    const beforeStatus = await getMigrationStatusAsync(client, MIGRATIONS_DIR);
    expect(beforeStatus.every((m) => !m.applied)).toBe(true);

    await applyMigrationsAsync(client, MIGRATIONS_DIR);
    const afterStatus = await getMigrationStatusAsync(client, MIGRATIONS_DIR);
    expect(afterStatus.every((m) => m.applied)).toBe(true);
  });

  it('마지막 마이그레이션을 롤백할 수 있다', async () => {
    const allMigrations = loadMigrations(MIGRATIONS_DIR);
    const lastMigration = allMigrations[allMigrations.length - 1];
    const secondLastMigration = allMigrations[allMigrations.length - 2];

    await applyMigrationsAsync(client, MIGRATIONS_DIR);
    const rolledBack = await rollbackLastMigrationAsync(client, MIGRATIONS_DIR);
    expect(rolledBack).toBe(lastMigration.version);

    const status = await getMigrationStatusAsync(client, MIGRATIONS_DIR);
    expect(status.find((m) => m.version === secondLastMigration.version)?.applied).toBe(true);
    expect(status.find((m) => m.version === lastMigration.version)?.applied).toBe(false);
  });
});
