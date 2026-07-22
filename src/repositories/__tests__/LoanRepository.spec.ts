import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool } from 'pg';
import { getTestPool, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { UserRepository } from '@repositories/UserRepository';
import { LoanRepository, OverpaymentError } from '@repositories/LoanRepository';
import { UserNotFoundError } from '@repositories/errors';
import { calculateLoanPayment } from '@services/interest-calculator';

describe('LoanRepository (Day 5 - Task 2: 대출 포트폴리오 관리, δ=1570)', () => {
  let pool: Pool;
  let users: UserRepository;
  let loans: LoanRepository;
  let userId: string;

  beforeEach(async () => {
    pool = getTestPool();
    users = new UserRepository(pool);
    loans = new LoanRepository(pool);
    const user = await users.register({ email: 'borrower@example.com', name: 'Borrower' });
    userId = user.id;
  });

  afterEach(async () => {
    await cleanupTestDatabase();
  });

  describe('[T-API-A07~A12] 대출 포트폴리오 관리', () => {
    it('[T-API-A07] 대출 등록', async () => {
      const expected = await calculateLoanPayment({ principal: 300000000, rate: 3.2, term: 240 });

      const loan = await loans.registerLoan({
        userId,
        productId: 'standard-loan-1',
        originalAmount: 300000000,
        interestRate: 3.2,
        termMonths: 240,
        startDate: '2026-01-01'
      });

      expect(loan.monthlyPayment).toBe(expected.monthlyPayment);
      expect(loan.currentBalance).toBe(300000000);
      expect(loan.maturityDate).toBe('2046-01-01');
      expect(loan.status).toBe('active');
      expect(loan.nextPaymentDate).toBe('2026-02-01');

      await expect(
        loans.registerLoan({
          userId: 'non-existent-user',
          productId: 'standard-loan-1',
          originalAmount: 100000000,
          interestRate: 3.2,
          termMonths: 120,
          startDate: '2026-01-01'
        })
      ).rejects.toThrow(UserNotFoundError);
    });

    it('[T-API-A08] 포트폴리오 조회 (다중 대출)', async () => {
      await loans.registerLoan({ userId, productId: 'prod-1', originalAmount: 300000000, interestRate: 3.2, termMonths: 240, startDate: '2026-01-01' });
      await loans.registerLoan({ userId, productId: 'prod-2', originalAmount: 100000000, interestRate: 2.8, termMonths: 120, startDate: '2026-02-01' });

      const portfolio = await loans.getPortfolio(userId);
      expect(portfolio.length).toBe(2);
      expect(portfolio.map((l) => l.productId)).toEqual(['prod-1', 'prod-2']);
    });

    it('[T-API-A09] 상환 기록 추가', async () => {
      const loan = await loans.registerLoan({ userId, productId: 'prod-1', originalAmount: 300000000, interestRate: 3.2, termMonths: 240, startDate: '2026-01-01' });

      const updated = await loans.recordPayment(loan.id, { paymentDate: '2026-02-01', principal: 1000000, interest: 800000 });

      expect(updated.currentBalance).toBe(299000000);
      expect(updated.totalPaid).toBe(1800000);
      expect(updated.totalInterestPaid).toBe(800000);
      expect(updated.nextPaymentDate).toBe('2026-03-01');
      expect(updated.status).toBe('active');

      const history = await loans.getLoanHistory(loan.id);
      expect(history.length).toBe(2); // CREATED + PAYMENT
      expect(history[1].action).toBe('PAYMENT');
      expect(history[1].previousBalance).toBe(300000000);
      expect(history[1].newBalance).toBe(299000000);
    });

    it('[T-API-A10] 잔액 일관성 검증', async () => {
      const loan = await loans.registerLoan({ userId, productId: 'prod-1', originalAmount: 10000000, interestRate: 3.2, termMonths: 12, startDate: '2026-01-01' });

      // 잔액보다 큰 원금 상환 시도 → 애플리케이션 레벨에서 차단
      await expect(loans.recordPayment(loan.id, { paymentDate: '2026-02-01', principal: 20000000, interest: 100000 })).rejects.toThrow(OverpaymentError);

      // 완납 처리: 정확히 잔액만큼 상환하면 대출이 종료된다
      const paidOff = await loans.recordPayment(loan.id, { paymentDate: '2026-02-01', principal: 10000000, interest: 50000 });
      expect(paidOff.currentBalance).toBe(0);
      expect(paidOff.status).toBe('closed');
      expect(paidOff.nextPaymentDate).toBeNull();
      expect(paidOff.closedAt).not.toBeNull();

      // DB 제약조건도 최후 방어선으로 잔액 초과를 직접 차단한다
      await expect(pool.query('UPDATE loans SET current_balance = original_amount + 1 WHERE id = $1', [loan.id])).rejects.toThrow();
    });

    it('[T-API-A11] 연체 자동 감지', async () => {
      const loan = await loans.registerLoan({ userId, productId: 'prod-1', originalAmount: 50000000, interestRate: 3.5, termMonths: 60, startDate: '2020-01-01' });
      expect(loan.status).toBe('active');
      expect(loan.nextPaymentDate).toBe('2020-02-01'); // 오래 전에 지난 상환일

      const delinquent = await loans.detectDelinquentLoans('2026-07-01');
      expect(delinquent.length).toBe(1);
      expect(delinquent[0].id).toBe(loan.id);
      expect(delinquent[0].status).toBe('delinquent');

      // 재조회 시에도 반영 확인
<<<<<<< HEAD
      expect((await loans.getLoan(loan.id))?.status).toBe('delinquent');
=======
      const refreshed = await loans.getLoan(loan.id);
      expect(refreshed?.status).toBe('delinquent');
>>>>>>> defc7bb5 (Tier 1: 핵심 Repository 테스트 3개 파일 async/PostgreSQL 변환)
    });

    it('[T-API-A12] 포트폴리오 요약', async () => {
      const loan1 = await loans.registerLoan({ userId, productId: 'prod-1', originalAmount: 300000000, interestRate: 3.2, termMonths: 240, startDate: '2026-01-01' });
      await loans.registerLoan({ userId, productId: 'prod-2', originalAmount: 100000000, interestRate: 2.8, termMonths: 120, startDate: '2026-01-01' });
      await loans.recordPayment(loan1.id, { paymentDate: '2026-02-01', principal: 1000000, interest: 800000 });

      const summary = await loans.getPortfolioSummary(userId);
      expect(summary.loanCount).toBe(2);
      expect(summary.activeLoanCount).toBe(2);
      expect(summary.delinquentLoanCount).toBe(0);
      expect(summary.totalOriginalAmount).toBe(400000000);
      expect(summary.totalCurrentBalance).toBe(399000000);
      expect(summary.averageInterestRate).toBe(3);
    });
  });
});
