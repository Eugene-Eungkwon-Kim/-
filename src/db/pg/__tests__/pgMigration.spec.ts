import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool } from 'pg';
import { MIGRATIONS_DIR } from '../../connection';
import { initializeTestDatabase, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import {
  translateSqliteDdlToPostgres,
  findSqliteArtifacts,
  generatePostgresSchema
} from '../pgSchemaGenerator';
import {
  escapePgLiteral,
  listUserTables,
  sortTablesByForeignKeys,
  exportTableInserts,
  exportDatabaseInserts
} from '../pgDataExporter';
import { UserRepository } from '../../../repositories/UserRepository';

/**
 * Day 15 - Task K: PostgreSQL 마이그레이션 준비 테스트
 */
describe('PostgreSQL 스키마 변환 (pgSchemaGenerator)', () => {
  describe('translateSqliteDdlToPostgres', () => {
    it("datetime('now') 기본값을 PostgreSQL to_char 표현식으로 변환한다", () => {
      const sql = "created_at TEXT NOT NULL DEFAULT (datetime('now'))";
      const out = translateSqliteDdlToPostgres(sql);
      expect(out).toContain("to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')");
      expect(out).not.toContain('datetime(');
    });

    it('REAL 타입을 DOUBLE PRECISION으로 변환한다', () => {
      const sql = 'interest_rate REAL NOT NULL CHECK (interest_rate > 0)';
      const out = translateSqliteDdlToPostgres(sql);
      expect(out).toContain('interest_rate DOUBLE PRECISION NOT NULL');
      expect(out).not.toMatch(/\bREAL\b/);
    });

    it('PostgreSQL 호환 구문(TEXT/INTEGER/CHECK/REFERENCES)은 건드리지 않는다', () => {
      const sql = [
        'CREATE TABLE t (',
        '  id TEXT PRIMARY KEY,',
        '  user_id TEXT NOT NULL REFERENCES users(id),',
        "  status TEXT NOT NULL CHECK (status IN ('a', 'b')),",
        '  amount INTEGER',
        ');'
      ].join('\n');
      expect(translateSqliteDdlToPostgres(sql)).toBe(sql);
    });
  });

  describe('findSqliteArtifacts', () => {
    it('SQLite 전용 구문을 감지한다', () => {
      expect(findSqliteArtifacts("DEFAULT (datetime('now'))")).toContain("datetime('now')");
      expect(findSqliteArtifacts('rate REAL')).toContain('REAL');
      expect(findSqliteArtifacts('id INTEGER PRIMARY KEY AUTOINCREMENT')).toContain('AUTOINCREMENT');
    });

    it('호환 구문에서는 빈 배열을 반환한다', () => {
      expect(findSqliteArtifacts('CREATE TABLE t (id TEXT PRIMARY KEY);')).toEqual([]);
    });
  });

  describe('generatePostgresSchema (실제 마이그레이션 기준)', () => {
    it('생성된 스키마에 SQLite 전용 구문이 남지 않는다', () => {
      const schema = generatePostgresSchema(MIGRATIONS_DIR);
      expect(findSqliteArtifacts(schema)).toEqual([]);
    });

    it('핵심 테이블이 모두 포함된다', () => {
      const schema = generatePostgresSchema(MIGRATIONS_DIR);
      for (const table of ['users', 'loans', 'loan_payments', 'transactions', 'financial_snapshots', 'refresh_tokens', 'audit_logs']) {
        expect(schema, `${table} 테이블이 스키마에 있어야 함`).toContain(`CREATE TABLE ${table}`);
      }
    });

    it('schema_migrations 상태 테이블과 적용 기록을 포함한다', () => {
      const schema = generatePostgresSchema(MIGRATIONS_DIR);
      expect(schema).toContain('CREATE TABLE schema_migrations');
      expect(schema).toContain("VALUES ('001'");
      expect(schema).toContain("VALUES ('017'");
    });

    it('마이그레이션 파일 순서(버전 순)를 유지한다', () => {
      const schema = generatePostgresSchema(MIGRATIONS_DIR);
      const idx001 = schema.indexOf('===== 001');
      const idx010 = schema.indexOf('===== 010');
      const idx017 = schema.indexOf('===== 017');
      expect(idx001).toBeGreaterThan(-1);
      expect(idx001).toBeLessThan(idx010);
      expect(idx010).toBeLessThan(idx017);
    });
  });
});

describe('PostgreSQL 데이터 내보내기 (pgDataExporter)', () => {
  let pool: Pool;

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY =
      '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef';
    pool = await initializeTestDatabase();
  });

  afterEach(async () => {
    await cleanupTestDatabase();
    delete process.env.ENCRYPTION_KEY;
  });

  describe('escapePgLiteral', () => {
    it('null/undefined는 NULL이 된다', () => {
      expect(escapePgLiteral(null)).toBe('NULL');
      expect(escapePgLiteral(undefined)).toBe('NULL');
    });

    it('숫자는 그대로 출력한다', () => {
      expect(escapePgLiteral(42)).toBe('42');
      expect(escapePgLiteral(3.14)).toBe('3.14');
      expect(escapePgLiteral(-0.5)).toBe('-0.5');
    });

    it('문자열의 작은따옴표를 이중화한다', () => {
      expect(escapePgLiteral("O'Brien")).toBe("'O''Brien'");
      expect(escapePgLiteral('plain')).toBe("'plain'");
    });

    it('SQL 인젝션 페이로드도 안전한 리터럴로 감싼다', () => {
      const payload = "'; DROP TABLE users; --";
      expect(escapePgLiteral(payload)).toBe("'''; DROP TABLE users; --'");
    });

    it('무한대/NaN은 에러를 던진다', () => {
      expect(() => escapePgLiteral(Infinity)).toThrow();
      expect(() => escapePgLiteral(NaN)).toThrow();
    });
  });

  describe('sortTablesByForeignKeys', () => {
    it('참조되는 테이블(users)이 참조하는 테이블(loans 등)보다 먼저 온다', async () => {
      const sorted = await sortTablesByForeignKeys(pool, await listUserTables(pool));
      const pos = (t: string) => sorted.indexOf(t);
      expect(pos('users')).toBeGreaterThan(-1);
      expect(pos('users')).toBeLessThan(pos('loans'));
      expect(pos('users')).toBeLessThan(pos('refresh_tokens'));
      expect(pos('users')).toBeLessThan(pos('audit_logs'));
      expect(pos('loans')).toBeLessThan(pos('loan_payments'));
    });

    it('모든 사용자 테이블을 누락 없이 포함한다', async () => {
      const tables = await listUserTables(pool);
      const sorted = await sortTablesByForeignKeys(pool, tables);
      expect(sorted.length).toBe(tables.length);
      expect(new Set(sorted)).toEqual(new Set(tables));
    });
  });

  describe('exportTableInserts / exportDatabaseInserts', () => {
    it('등록된 사용자가 INSERT 문으로 내보내진다', async () => {
      const repo = new UserRepository(pool);
      await repo.register({
        email: "o'brien@example.com",
        name: "O'Brien",
        password: 'test-password-123',
        contact: { address: {} }
      });

      const inserts = await exportTableInserts(pool, 'users');
      expect(inserts.length).toBe(1);
      expect(inserts[0]).toMatch(/^INSERT INTO users \(/);
      // 작은따옴표가 이중화되어야 한다
      expect(inserts[0]).toContain("O''Brien");
    });

    it('빈 테이블은 INSERT 문을 생성하지 않는다', async () => {
      expect(await exportTableInserts(pool, 'loans')).toEqual([]);
    });

    it('전체 내보내기는 트랜잭션으로 감싸고 FK 순서를 지킨다', async () => {
      const repo = new UserRepository(pool);
      await repo.register({
        email: 'export@example.com',
        name: 'Export User',
        password: 'test-password-123',
        contact: { address: {} }
      });

      const script = await exportDatabaseInserts(pool);
      expect(script.startsWith('BEGIN;')).toBe(true);
      expect(script.trimEnd().endsWith('COMMIT;')).toBe(true);
      // users 섹션이 loans 섹션보다 먼저
      expect(script.indexOf('-- users')).toBeLessThan(script.indexOf('-- loans'));
      expect(script).toContain("'export@example.com'");
    });
  });
});
