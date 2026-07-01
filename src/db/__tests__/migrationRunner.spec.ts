import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { applyMigrations, getMigrationStatus, loadMigrations, rollbackLastMigration } from '@db/migrationRunner';
import { MIGRATIONS_DIR } from '@db/connection';

describe('Migration Runner (Day 5 - 기초: 스키마 버전 관리)', () => {
  let db: Database.Database;

  beforeEach(() => {
    db = new Database(':memory:');
    db.pragma('foreign_keys = ON');
  });

  afterEach(() => {
    db.close();
  });

  it('모든 마이그레이션을 순서대로 적용한다', () => {
    const expectedVersions = loadMigrations(MIGRATIONS_DIR).map((m) => m.version);
    const applied = applyMigrations(db, MIGRATIONS_DIR);
    expect(applied).toEqual(expectedVersions);

    const tables = db
      .prepare("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
      .all() as { name: string }[];
    const tableNames = tables.map((t) => t.name);
    expect(tableNames).toContain('users');
    expect(tableNames).toContain('users_audit');
  });

  it('이미 적용된 마이그레이션은 재실행하지 않는다 (idempotent)', () => {
    applyMigrations(db, MIGRATIONS_DIR);
    const secondRun = applyMigrations(db, MIGRATIONS_DIR);
    expect(secondRun).toEqual([]);
  });

  it('DB 제약조건이 실제로 강제된다 (CHECK/UNIQUE)', () => {
    applyMigrations(db, MIGRATIONS_DIR);

    // credit_score 범위 초과 → CHECK 제약 위반
    expect(() =>
      db
        .prepare('INSERT INTO users (id, email, name, credit_score) VALUES (?, ?, ?, ?)')
        .run('u1', 'a@example.com', 'A', 1500)
    ).toThrow(/CHECK constraint failed/);

    // 정상 삽입 후 이메일 중복 → UNIQUE 제약 위반
    db.prepare('INSERT INTO users (id, email, name) VALUES (?, ?, ?)').run('u2', 'dup@example.com', 'B');
    expect(() =>
      db.prepare('INSERT INTO users (id, email, name) VALUES (?, ?, ?)').run('u3', 'dup@example.com', 'C')
    ).toThrow(/UNIQUE constraint failed/);
  });

  it('마이그레이션 상태를 조회할 수 있다', () => {
    const beforeStatus = getMigrationStatus(db, MIGRATIONS_DIR);
    expect(beforeStatus.every((m) => !m.applied)).toBe(true);

    applyMigrations(db, MIGRATIONS_DIR);
    const afterStatus = getMigrationStatus(db, MIGRATIONS_DIR);
    expect(afterStatus.every((m) => m.applied)).toBe(true);
  });

  it('마지막 마이그레이션을 롤백할 수 있다', () => {
    const allMigrations = loadMigrations(MIGRATIONS_DIR);
    const lastMigration = allMigrations[allMigrations.length - 1];
    const secondLastMigration = allMigrations[allMigrations.length - 2];

    applyMigrations(db, MIGRATIONS_DIR);
    const rolledBack = rollbackLastMigration(db, MIGRATIONS_DIR);
    expect(rolledBack).toBe(lastMigration.version);

    const status = getMigrationStatus(db, MIGRATIONS_DIR);
    expect(status.find((m) => m.version === secondLastMigration.version)?.applied).toBe(true);
    expect(status.find((m) => m.version === lastMigration.version)?.applied).toBe(false);
  });
});
