import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '../connection';

/**
 * Day 15 - Task J: 인덱스 최적화 검증
 *
 * 마이그레이션 017이 만든 인덱스가 존재하고, 실제 쿼리가
 * 그 인덱스를 사용하는지 EXPLAIN QUERY PLAN으로 검증한다.
 */
describe('인덱스 최적화 (마이그레이션 017)', () => {
  let db: Database.Database;

  beforeEach(() => {
    db = createDatabase(':memory:');
  });

  afterEach(() => {
    db.close();
  });

  function indexNames(table: string): string[] {
    return (db.prepare(`PRAGMA index_list(${table})`).all() as { name: string }[]).map((r) => r.name);
  }

  function queryPlan(sql: string, params: unknown[] = []): string {
    const rows = db.prepare(`EXPLAIN QUERY PLAN ${sql}`).all(...params) as { detail: string }[];
    return rows.map((r) => r.detail).join(' | ');
  }

  describe('인덱스 존재 검증', () => {
    it('audit_logs에 복합 인덱스가 존재하고 단일 인덱스는 제거되었다', () => {
      const names = indexNames('audit_logs');
      expect(names).toContain('idx_audit_logs_user_created');
      expect(names).toContain('idx_audit_logs_resource_created');
      expect(names).not.toContain('idx_audit_logs_user_id');
      expect(names).not.toContain('idx_audit_logs_resource_id');
    });

    it('transactions에 이상탐지용 복합 인덱스가 존재한다', () => {
      const names = indexNames('transactions');
      expect(names).toContain('idx_transactions_user_status_amount');
    });

    it('기존 핵심 인덱스는 유지된다', () => {
      expect(indexNames('audit_logs')).toContain('idx_audit_logs_action');
      expect(indexNames('transactions')).toContain('idx_transactions_user_time');
      expect(indexNames('loans')).toContain('idx_loans_status_next_payment');
    });
  });

  describe('쿼리 플랜 검증 (EXPLAIN QUERY PLAN)', () => {
    it('audit_logs 사용자별 조회는 복합 인덱스를 사용하며 별도 정렬이 없다', () => {
      const plan = queryPlan(
        'SELECT * FROM audit_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 100',
        ['user-1']
      );
      expect(plan).toContain('idx_audit_logs_user_created');
      // 복합 인덱스가 정렬까지 커버하므로 TEMP B-TREE 정렬이 없어야 한다
      expect(plan).not.toContain('USE TEMP B-TREE');
    });

    it('audit_logs 리소스별 조회는 복합 인덱스를 사용한다', () => {
      const plan = queryPlan(
        'SELECT * FROM audit_logs WHERE resource_id = ? ORDER BY created_at DESC',
        ['loan-1']
      );
      expect(plan).toContain('idx_audit_logs_resource_created');
      expect(plan).not.toContain('USE TEMP B-TREE');
    });

    it('transactions 이상탐지 조회는 복합 인덱스를 사용한다', () => {
      const plan = queryPlan(
        "SELECT * FROM transactions WHERE user_id = ? AND status = 'completed' AND amount > ?",
        ['user-1', 1000000]
      );
      expect(plan).toContain('idx_transactions_user_status_amount');
    });

    it('연체 감지 조회는 기존 status+next_payment 인덱스를 계속 사용한다', () => {
      const plan = queryPlan(
        "SELECT * FROM loans WHERE status = 'active' AND next_payment_date < ? ORDER BY next_payment_date ASC",
        ['2026-07-01']
      );
      expect(plan).toContain('idx_loans_status_next_payment');
    });
  });

  describe('마이그레이션 무결성', () => {
    it('017 마이그레이션이 적용 목록에 기록되어 있다', () => {
      const row = db
        .prepare("SELECT version FROM schema_migrations WHERE version = '017'")
        .get() as { version: string } | undefined;
      expect(row?.version).toBe('017');
    });
  });
});
