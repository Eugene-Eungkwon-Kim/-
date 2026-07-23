import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool } from 'pg';
import { initializeTestDatabase, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { UserRepository } from '@repositories/UserRepository';
import { LoanRepository } from '@repositories/LoanRepository';
import { TransactionRepository } from '@repositories/TransactionRepository';

/**
 * EXPLAIN 결과에서 인덱스 스캔(Seq Scan 아님)이 쓰이는지 확인한다.
 *
 * PostgreSQL 플래너는 소량 데이터에서 Seq Scan을 선호하므로, 인덱스의
 * "사용 가능성"을 결정적으로 검증하려면 seqscan을 끈 뒤 EXPLAIN을 봐야 한다.
 * (SQLite의 EXPLAIN QUERY PLAN + "USING INDEX" 검사에 대응하는 PG 등가물)
 */
async function usesIndexScan(pool: Pool, sql: string, params: unknown[] = []): Promise<boolean> {
  const client = await pool.connect();
  try {
    await client.query('SET enable_seqscan = off');
    const result = await client.query(`EXPLAIN ${sql}`, params);
    const plan = result.rows.map((r: Record<string, string>) => r['QUERY PLAN']).join('\n');
    return /Index (Only )?Scan/.test(plan);
  } finally {
    client.release();
  }
}

/** EXPLAIN 계획 텍스트 전체를 반환한다 (특정 인덱스 이름 확인용). */
async function queryPlanText(pool: Pool, sql: string, params: unknown[] = []): Promise<string> {
  const client = await pool.connect();
  try {
    await client.query('SET enable_seqscan = off');
    const result = await client.query(`EXPLAIN ${sql}`, params);
    return result.rows.map((r: Record<string, string>) => r['QUERY PLAN']).join('\n');
  } finally {
    client.release();
  }
}

describe('Query Optimization & Indexing (Day 5 - Task 6: 쿼리 최적화 & 인덱싱, δ=1025)', () => {
  let pool: Pool;
  let users: UserRepository;
  let loans: LoanRepository;
  let transactions: TransactionRepository;

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
    pool = await initializeTestDatabase();
    users = new UserRepository(pool);
    loans = new LoanRepository(pool);
    transactions = new TransactionRepository(pool);
  });

  afterEach(async () => {
    await cleanupTestDatabase();
    delete process.env.ENCRYPTION_KEY;
  });

  describe('[T-API-A31~A36] 쿼리 최적화 & 인덱싱', () => {
    it('[T-API-A31] 모든 예상 인덱스가 존재한다', async () => {
      const result = await pool.query(
        "SELECT indexname AS name, tablename AS tbl_name FROM pg_indexes WHERE schemaname = 'public'"
      );
      const indexes = result.rows.map((r: { name: string }) => r.name);

      const expected = [
        'idx_users_email',
        'idx_users_credit_score',
        'idx_users_status',
        'idx_users_audit_user_id',
        'idx_loans_user_status',
        'idx_loans_maturity',
        'idx_loans_status_next_payment',
        'idx_loan_payments_loan_date',
        'idx_loan_history_loan_date',
        'idx_data_integrity_log_check_type',
        'idx_transactions_user_time',
        'idx_transactions_status',
        'idx_audit_log_entity',
        'idx_financial_snapshots_user_date'
      ];

      for (const name of expected) {
        expect(indexes).toContain(name);
      }
    });

    it('[T-API-A32] 대용량 포트폴리오 조회가 인덱스를 사용하며 빠르다', async () => {
      const userId = (await users.register({ email: 'perf-user@example.com', name: 'Perf User' })).id;
      const otherUserId = (await users.register({ email: 'other-user@example.com', name: 'Other User' })).id;

      // 다른 사용자에 대출을 대량으로 흩뿌려 조회 대상 테이블을 키운다
      for (let i = 0; i < 300; i++) {
        await loans.registerLoan({
          userId: otherUserId,
          productId: `noise-${i}`,
          originalAmount: 100000000,
          interestRate: 3.0,
          termMonths: 120,
          startDate: '2026-01-01'
        });
      }
      await loans.registerLoan({
        userId,
        productId: 'target-loan',
        originalAmount: 200000000,
        interestRate: 3.2,
        termMonths: 240,
        startDate: '2026-01-01'
      });

      expect(await usesIndexScan(pool, 'SELECT * FROM loans WHERE user_id = $1', [userId])).toBe(true);

      // PostgreSQL은 커넥션 풀 왕복이 있어 SQLite in-memory보다 느리므로,
      // "인덱스 덕분에 규모와 무관하게 빠르다"는 의도를 유지하되 임계값은 넉넉히 잡는다.
      const start = performance.now();
      const portfolio = await loans.getPortfolio(userId);
      const elapsedMs = performance.now() - start;

      expect(portfolio.length).toBe(1);
      expect(elapsedMs).toBeLessThan(500);
    });

    it('[T-API-A33] 배치 작업은 트랜잭션으로 원자성을 보장한다', async () => {
      const userId = (await users.register({ email: 'atomic-user@example.com', name: 'Atomic User' })).id;

      const loan1 = await loans.registerLoan({ userId, productId: 'p1', originalAmount: 50000000, interestRate: 3.2, termMonths: 60, startDate: '2020-01-01' });
      const loan2 = await loans.registerLoan({ userId, productId: 'p2', originalAmount: 50000000, interestRate: 3.2, termMonths: 60, startDate: '2020-02-01' });

      // 정상 케이스: detectDelinquentLoans는 배치 전체가 하나의 트랜잭션이므로 둘 다 반영된다
      const delinquent = await loans.detectDelinquentLoans('2026-07-01');
      expect(delinquent.length).toBe(2);
      expect((await loans.getLoan(loan1.id))?.status).toBe('delinquent');
      expect((await loans.getLoan(loan2.id))?.status).toBe('delinquent');

      // 실패 케이스: 배치 도중 CHECK 제약 위반이 발생하면 이미 처리된 항목도 롤백되어야 한다
      const loan3 = await loans.registerLoan({ userId, productId: 'p3', originalAmount: 50000000, interestRate: 3.2, termMonths: 60, startDate: '2026-01-01' });

      const client = await pool.connect();
      let threw = false;
      try {
        await client.query('BEGIN');
        await client.query("UPDATE loans SET status = 'delinquent' WHERE id = $1", [loan3.id]); // 유효한 변경
        await client.query('UPDATE loans SET status = $1 WHERE id = $2', ['not-a-real-status', loan3.id]); // CHECK 위반
        await client.query('COMMIT');
      } catch (error) {
        threw = true;
        expect((error as Error).message).toMatch(/violates check constraint/);
        await client.query('ROLLBACK').catch(() => {});
      } finally {
        client.release();
      }
      expect(threw).toBe(true);

      // 트랜잭션 전체가 롤백되어 loan3은 애초 상태(active)로 남아야 한다
      expect((await loans.getLoan(loan3.id))?.status).toBe('active');
    });

    it('[T-API-A34] 대용량 데이터에서도 요약 집계가 빠르게 동작한다', async () => {
      const userId = (await users.register({ email: 'summary-user@example.com', name: 'Summary User', financialSnapshot: { monthlyIncome: 50000000 } })).id;

      for (let i = 0; i < 500; i++) {
        await transactions.recordTransaction({
          userId,
          transactionType: i % 2 === 0 ? 'deposit' : 'withdrawal',
          amount: 100000 + i,
          occurredAt: '2026-01-01'
        });
      }

      expect(await usesIndexScan(pool, 'SELECT * FROM transactions WHERE user_id = $1', [userId])).toBe(true);

      // PG 왕복 오버헤드를 감안해 임계값을 넉넉히 잡되, 집계가 규모와 무관하게
      // 빠르게 완료된다는 의도는 유지한다.
      const start = performance.now();
      const summary = await transactions.getSummary(userId);
      const elapsedMs = performance.now() - start;

      expect(summary.transactionCount).toBe(500);
      expect(elapsedMs).toBeLessThan(500);
    });

    it('[T-API-A35] 반복 조회에서도 일관되게 인덱스를 사용한다', async () => {
      const userId = (await users.register({ email: 'repeat-user@example.com', name: 'Repeat User' })).id;

      for (let i = 0; i < 10; i++) {
        const usesIndex = await usesIndexScan(pool, 'SELECT * FROM users WHERE email = $1', ['repeat-user@example.com']);
        expect(usesIndex).toBe(true);
      }

      // 실제 조회 결과도 매번 동일해야 한다 (쿼리 플랜이 안정적이라는 방증)
      for (let i = 0; i < 5; i++) {
        expect((await users.getProfile(userId))?.email).toBe('repeat-user@example.com');
      }
    });

    it('[T-API-A36] 연체 감지 쿼리가 복합 인덱스(status, next_payment_date)를 사용한다', async () => {
      const userId = (await users.register({ email: 'delinquent-index@example.com', name: 'Delinquent Index User' })).id;
      await loans.registerLoan({ userId, productId: 'p1', originalAmount: 50000000, interestRate: 3.2, termMonths: 60, startDate: '2020-01-01' });

      const plan = await queryPlanText(
        pool,
        "SELECT * FROM loans WHERE status = 'active' AND next_payment_date < $1",
        ['2026-07-01']
      );

      expect(plan).toContain('idx_loans_status_next_payment');
      expect(plan).not.toMatch(/Seq Scan/);
    });
  });
});
