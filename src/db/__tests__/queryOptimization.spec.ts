import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { UserRepository } from '@repositories/UserRepository';
import { LoanRepository } from '@repositories/LoanRepository';
import { TransactionRepository } from '@repositories/TransactionRepository';

/** EXPLAIN QUERY PLAN 결과에서 인덱스 SEARCH(풀스캔 아님)가 쓰였는지 확인한다 */
function usesIndexSearch(db: Database.Database, sql: string, params: unknown[] = []): boolean {
  const plan = db.prepare(`EXPLAIN QUERY PLAN ${sql}`).all(...params) as { detail: string }[];
  return plan.every((row) => /SEARCH/.test(row.detail)) && plan.some((row) => /USING (COVERING )?INDEX/.test(row.detail));
}

describe('Query Optimization & Indexing (Day 5 - Task 6: 쿼리 최적화 & 인덱싱, δ=1025)', () => {
  let db: Database.Database;
  let users: UserRepository;
  let loans: LoanRepository;
  let transactions: TransactionRepository;

  beforeEach(() => {
    db = createDatabase(':memory:');
    users = new UserRepository(db);
    loans = new LoanRepository(db);
    transactions = new TransactionRepository(db);
  });

  afterEach(() => {
    db.close();
  });

  describe('[T-API-A31~A36] 쿼리 최적화 & 인덱싱', () => {
    it('[T-API-A31] 모든 예상 인덱스가 존재한다', () => {
      const indexes = (
        db.prepare("SELECT name, tbl_name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'").all() as {
          name: string;
          tbl_name: string;
        }[]
      ).map((r) => r.name);

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
      const userId = users.register({ email: 'perf-user@example.com', name: 'Perf User' }).id;
      const otherUserId = users.register({ email: 'other-user@example.com', name: 'Other User' }).id;

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

      expect(usesIndexSearch(db, 'SELECT * FROM loans WHERE user_id = ?', [userId])).toBe(true);

      const start = performance.now();
      const portfolio = loans.getPortfolio(userId);
      const elapsedMs = performance.now() - start;

      expect(portfolio.length).toBe(1);
      expect(elapsedMs).toBeLessThan(50);
    });

    it('[T-API-A33] 배치 작업은 트랜잭션으로 원자성을 보장한다', async () => {
      const userId = users.register({ email: 'atomic-user@example.com', name: 'Atomic User' }).id;

      const loan1 = await loans.registerLoan({ userId, productId: 'p1', originalAmount: 50000000, interestRate: 3.2, termMonths: 60, startDate: '2020-01-01' });
      const loan2 = await loans.registerLoan({ userId, productId: 'p2', originalAmount: 50000000, interestRate: 3.2, termMonths: 60, startDate: '2020-02-01' });

      // 정상 케이스: detectDelinquentLoans는 배치 전체가 하나의 트랜잭션이므로 둘 다 반영된다
      const delinquent = loans.detectDelinquentLoans('2026-07-01');
      expect(delinquent.length).toBe(2);
      expect(loans.getLoan(loan1.id)?.status).toBe('delinquent');
      expect(loans.getLoan(loan2.id)?.status).toBe('delinquent');

      // 실패 케이스: 배치 도중 CHECK 제약 위반이 발생하면 이미 처리된 항목도 롤백되어야 한다
      const loan3 = await loans.registerLoan({ userId, productId: 'p3', originalAmount: 50000000, interestRate: 3.2, termMonths: 60, startDate: '2026-01-01' });
      expect(() => {
        db.transaction(() => {
          db.prepare("UPDATE loans SET status = 'delinquent' WHERE id = ?").run(loan3.id); // 유효한 변경
          db.prepare('UPDATE loans SET status = ? WHERE id = ?').run('not-a-real-status', loan3.id); // CHECK 위반
        })();
      }).toThrow(/CHECK constraint failed/);

      // 트랜잭션 전체가 롤백되어 loan3은 애초 상태(active)로 남아야 한다
      expect(loans.getLoan(loan3.id)?.status).toBe('active');
    });

    it('[T-API-A34] 대용량 데이터에서도 요약 집계가 빠르게 동작한다', () => {
      const userId = users.register({ email: 'summary-user@example.com', name: 'Summary User', financialSnapshot: { monthlyIncome: 50000000 } }).id;

      for (let i = 0; i < 500; i++) {
        transactions.recordTransaction({
          userId,
          transactionType: i % 2 === 0 ? 'deposit' : 'withdrawal',
          amount: 100000 + i,
          occurredAt: '2026-01-01'
        });
      }

      expect(usesIndexSearch(db, 'SELECT * FROM transactions WHERE user_id = ?', [userId])).toBe(true);

      const start = performance.now();
      const summary = transactions.getSummary(userId);
      const elapsedMs = performance.now() - start;

      expect(summary.transactionCount).toBe(500);
      expect(elapsedMs).toBeLessThan(100);
    });

    it('[T-API-A35] 반복 조회에서도 일관되게 인덱스를 사용한다', () => {
      const userId = users.register({ email: 'repeat-user@example.com', name: 'Repeat User' }).id;

      for (let i = 0; i < 10; i++) {
        const plan = usesIndexSearch(db, 'SELECT * FROM users WHERE email = ?', [`repeat-user@example.com`]);
        expect(plan).toBe(true);
      }

      // 실제 조회 결과도 매번 동일해야 한다 (쿼리 플랜이 안정적이라는 방증)
      for (let i = 0; i < 5; i++) {
        expect(users.getProfile(userId)?.email).toBe('repeat-user@example.com');
      }
    });

    it('[T-API-A36] 연체 감지 쿼리가 복합 인덱스(status, next_payment_date)를 사용한다', async () => {
      const userId = users.register({ email: 'delinquent-index@example.com', name: 'Delinquent Index User' }).id;
      await loans.registerLoan({ userId, productId: 'p1', originalAmount: 50000000, interestRate: 3.2, termMonths: 60, startDate: '2020-01-01' });

      const plan = db
        .prepare("EXPLAIN QUERY PLAN SELECT * FROM loans WHERE status = 'active' AND next_payment_date < ?")
        .all('2026-07-01') as { detail: string }[];

      expect(plan.some((row) => row.detail.includes('idx_loans_status_next_payment'))).toBe(true);
      expect(plan.every((row) => !/^SCAN/.test(row.detail))).toBe(true);
    });
  });
});
