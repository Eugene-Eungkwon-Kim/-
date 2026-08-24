import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { randomUUID } from 'node:crypto';
import type { Pool } from 'pg';
import { initializeTestDatabase, cleanupTestDatabase } from './testDatabase';
import { UserRepository } from '@repositories/UserRepository';
import { LoanRepository } from '@repositories/LoanRepository';
import { TransactionRepository } from '@repositories/TransactionRepository';

/**
 * Day 15 - Task J: 인덱스 최적화 검증
 *
 * 마이그레이션 017이 만든 인덱스가 존재하고, 실제 쿼리가
 * 그 인덱스를 사용하는지 EXPLAIN으로 검증한다 (PostgreSQL).
 */
describe('인덱스 최적화 (마이그레이션 017)', () => {
  let pool: Pool;
  let users: UserRepository;
  let loans: LoanRepository;
  let transactions: TransactionRepository;
  let userId: string;

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
    pool = await initializeTestDatabase();
    users = new UserRepository(pool);
    loans = new LoanRepository(pool);
    transactions = new TransactionRepository(pool);

    // 플래너가 의미 있는(그리고 결정론적인) 계획을 세우도록 대표 데이터를 삽입한다.
    // 선행 필터 컬럼(user_id / resource_id)이 선택도를 갖도록 노이즈 사용자를 함께 넣는다.
    userId = (await users.register({ email: 'idx-user@example.com', name: 'Index User' })).id;
    const noiseUserId = (await users.register({ email: 'idx-noise@example.com', name: 'Noise User' })).id;

    // transactions: user_id / status / amount 조회용 (income이 없으므로 status는 completed)
    for (let i = 0; i < 15; i++) {
      await transactions.recordTransaction({
        userId,
        transactionType: i % 2 === 0 ? 'deposit' : 'withdrawal',
        amount: 100000 + i * 1000,
        occurredAt: '2026-01-01'
      });
      await transactions.recordTransaction({
        userId: noiseUserId,
        transactionType: 'deposit',
        amount: 50000 + i * 500,
        occurredAt: '2026-01-01'
      });
    }

    // loans: status / next_payment_date 조회용
    for (let i = 0; i < 8; i++) {
      await loans.registerLoan({
        userId,
        productId: `p-${i}`,
        originalAmount: 50000000,
        interestRate: 3.2,
        termMonths: 60,
        startDate: '2020-01-01'
      });
      await loans.registerLoan({
        userId: noiseUserId,
        productId: `noise-${i}`,
        originalAmount: 50000000,
        interestRate: 3.2,
        termMonths: 60,
        startDate: '2020-01-01'
      });
    }

    // audit_logs: user_id / resource_id + created_at 조회용
    const insertAuditLog = (uid: string, resourceId: string, seq: number): Promise<unknown> =>
      pool.query(
        `INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, status, created_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [randomUUID(), uid, 'READ', 'loan', resourceId, 'success', `2026-01-01 00:00:${String(seq % 60).padStart(2, '0')}`]
      );

    for (let i = 0; i < 8; i++) {
      await insertAuditLog(userId, i < 4 ? 'loan-1' : `loan-${i}`, i);
    }
    for (let i = 0; i < 40; i++) {
      await insertAuditLog(noiseUserId, `loan-noise-${i}`, i);
    }

    // 통계를 갱신해 인덱스 선택을 결정론적으로 만든다.
    await pool.query('ANALYZE');
  });

  afterEach(async () => {
    await cleanupTestDatabase();
    delete process.env.ENCRYPTION_KEY;
  });

  async function indexNames(table: string): Promise<string[]> {
    const result = await pool.query(
      "SELECT indexname FROM pg_indexes WHERE tablename = $1 AND schemaname = 'public'",
      [table]
    );
    return (result.rows as { indexname: string }[]).map((r) => r.indexname);
  }

  /**
   * EXPLAIN 계획을 문자열로 반환한다. 작은 테스트 테이블에서 PG 플래너가 Seq Scan을
   * 선호하는 것을 막아 인덱스 사용 여부를 결정론적으로 확인하기 위해, 동일 커넥션에서
   * enable_seqscan을 끈 뒤 EXPLAIN을 실행한다 (세션 스코프 GUC).
   */
  async function queryPlan(sql: string, params: unknown[] = []): Promise<string> {
    const client = await pool.connect();
    try {
      await client.query('SET enable_seqscan = off');
      const result = await client.query(`EXPLAIN ${sql}`, params);
      return (result.rows as Record<string, string>[]).map((r) => r['QUERY PLAN']).join('\n');
    } finally {
      client.release();
    }
  }

  describe('인덱스 존재 검증', () => {
    it('audit_logs에 복합 인덱스가 존재하고 단일 인덱스는 제거되었다', async () => {
      const names = await indexNames('audit_logs');
      expect(names).toContain('idx_audit_logs_user_created');
      expect(names).toContain('idx_audit_logs_resource_created');
      expect(names).not.toContain('idx_audit_logs_user_id');
      expect(names).not.toContain('idx_audit_logs_resource_id');
    });

    it('transactions에 이상탐지용 복합 인덱스가 존재한다', async () => {
      const names = await indexNames('transactions');
      expect(names).toContain('idx_transactions_user_status_amount');
    });

    it('기존 핵심 인덱스는 유지된다', async () => {
      expect(await indexNames('audit_logs')).toContain('idx_audit_logs_action');
      expect(await indexNames('transactions')).toContain('idx_transactions_user_time');
      expect(await indexNames('loans')).toContain('idx_loans_status_next_payment');
    });
  });

  describe('쿼리 플랜 검증 (EXPLAIN)', () => {
    it('audit_logs 사용자별 조회는 복합 인덱스를 사용하며 별도 정렬이 없다', async () => {
      const plan = await queryPlan(
        'SELECT * FROM audit_logs WHERE user_id = $1 ORDER BY created_at DESC LIMIT 100',
        [userId]
      );
      expect(plan).toContain('idx_audit_logs_user_created');
      // 복합 인덱스가 정렬까지 커버하므로 별도 Sort 노드가 없어야 한다
      expect(plan).not.toContain('Sort');
    });

    it('audit_logs 리소스별 조회는 복합 인덱스를 사용한다', async () => {
      const plan = await queryPlan(
        'SELECT * FROM audit_logs WHERE resource_id = $1 ORDER BY created_at DESC',
        ['loan-1']
      );
      expect(plan).toContain('idx_audit_logs_resource_created');
      expect(plan).not.toContain('Sort');
    });

    it('transactions 이상탐지 조회는 복합 인덱스를 사용한다', async () => {
      const plan = await queryPlan(
        "SELECT * FROM transactions WHERE user_id = $1 AND status = 'completed' AND amount > $2",
        [userId, 1000000]
      );
      expect(plan).toContain('idx_transactions_user_status_amount');
    });

    it('연체 감지 조회는 기존 status+next_payment 인덱스를 계속 사용한다', async () => {
      const plan = await queryPlan(
        "SELECT * FROM loans WHERE status = 'active' AND next_payment_date < $1 ORDER BY next_payment_date ASC",
        ['2026-07-01']
      );
      expect(plan).toContain('idx_loans_status_next_payment');
    });
  });

  describe('마이그레이션 무결성', () => {
    it('017 마이그레이션이 적용 목록에 기록되어 있다', async () => {
      const result = await pool.query("SELECT version FROM schema_migrations WHERE version = $1", ['017']);
      const row = result.rows[0] as { version: string } | undefined;
      expect(row?.version).toBe('017');
    });
  });
});
