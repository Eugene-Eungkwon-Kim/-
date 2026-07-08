import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { registerUser } from '@api/userService';
import { applyForLoan, detectDelinquentLoans, getLoanPortfolio, getLoanPortfolioSummary, recordLoanPayment } from '@api/loanService';

describe('loanService (Day 6 - Task 2: 대출 서비스 계층, δ=1600)', () => {
  let db: Database.Database;
  let userId: string;

  beforeEach(() => {
    db = createDatabase(':memory:');
    const created = registerUser(db, { email: 'loan-svc@example.com', name: 'Loan Service User', password: 'test-password-123' });
    userId = created.success ? created.data.id : '';
  });

  afterEach(() => {
    db.close();
  });

  describe('[T-SVC-201~206] 대출 서비스', () => {
    it('[T-SVC-201] 대출 신청 성공', async () => {
      const result = await applyForLoan(db, {
        userId,
        productId: 'standard-loan-1',
        originalAmount: 300000000,
        interestRate: 3.2,
        termMonths: 240,
        startDate: '2026-01-01'
      });

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.status).toBe('active');
        expect(result.data.currentBalance).toBe(300000000);
      }
    });

    it('[T-SVC-202] 존재하지 않는 사용자로 신청', async () => {
      const result = await applyForLoan(db, {
        userId: 'ffffffff-ffff-ffff-ffff-ffffffffffff',
        productId: 'standard-loan-1',
        originalAmount: 100000000,
        interestRate: 3.2,
        termMonths: 120,
        startDate: '2026-01-01'
      });

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.code).toBe('USER_NOT_FOUND');
      }
    });

    it('[T-SVC-203] 포트폴리오 조회', async () => {
      await applyForLoan(db, { userId, productId: 'p1', originalAmount: 100000000, interestRate: 3.2, termMonths: 120, startDate: '2026-01-01' });
      await applyForLoan(db, { userId, productId: 'p2', originalAmount: 50000000, interestRate: 2.8, termMonths: 60, startDate: '2026-02-01' });

      const result = getLoanPortfolio(db, userId);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.length).toBe(2);
      }
    });

    it('[T-SVC-204] 상환 기록 (정상)', async () => {
      const loanResult = await applyForLoan(db, { userId, productId: 'p1', originalAmount: 100000000, interestRate: 3.2, termMonths: 120, startDate: '2026-01-01' });
      const loanId = loanResult.success ? loanResult.data.id : '';

      const result = recordLoanPayment(db, loanId, { paymentDate: '2026-02-01', principal: 500000, interest: 300000 });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.currentBalance).toBe(99500000);
      }
    });

    it('[T-SVC-205] 초과 상환 시도', async () => {
      const loanResult = await applyForLoan(db, { userId, productId: 'p1', originalAmount: 10000000, interestRate: 3.2, termMonths: 12, startDate: '2026-01-01' });
      const loanId = loanResult.success ? loanResult.data.id : '';

      const result = recordLoanPayment(db, loanId, { paymentDate: '2026-02-01', principal: 20000000, interest: 100000 });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.code).toBe('OVERPAYMENT');
      }
    });

    it('[T-SVC-206] 포트폴리오 요약', async () => {
      await applyForLoan(db, { userId, productId: 'p1', originalAmount: 100000000, interestRate: 3.2, termMonths: 120, startDate: '2026-01-01' });
      await applyForLoan(db, { userId, productId: 'p2', originalAmount: 50000000, interestRate: 2.8, termMonths: 60, startDate: '2026-01-01' });

      const result = getLoanPortfolioSummary(db, userId);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.loanCount).toBe(2);
        expect(result.data.totalOriginalAmount).toBe(150000000);
      }
    });
  });

  describe('[T-SVC-811~813] 연체 감지 서비스 진입점 (Day 7 - Task 2, δ=1010)', () => {
    it('[T-SVC-811] 연체 대출을 감지해 delinquent로 전환한다', async () => {
      const loan = await applyForLoan(db, { userId, productId: 'p1', originalAmount: 50000000, interestRate: 3.2, termMonths: 60, startDate: '2020-01-01' });
      const loanId = loan.success ? loan.data.id : '';

      const result = detectDelinquentLoans(db, '2026-07-01');
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.some((l) => l.id === loanId)).toBe(true);
        expect(result.data.find((l) => l.id === loanId)?.status).toBe('delinquent');
      }
    });

    it('[T-SVC-812] 연체가 없으면 빈 배열을 반환한다', async () => {
      await applyForLoan(db, { userId, productId: 'p1', originalAmount: 50000000, interestRate: 3.2, termMonths: 60, startDate: '2026-01-01' });

      const result = detectDelinquentLoans(db, '2026-01-15'); // 아직 다음 상환일(2026-02-01) 이전
      expect(result.success).toBe(true);
      if (result.success) expect(result.data.length).toBe(0);
    });

    it('[T-SVC-813] 존재하지 않는 대출은 영향을 주지 않는다 (빈 포트폴리오)', () => {
      const result = detectDelinquentLoans(db, '2026-07-01');
      expect(result.success).toBe(true);
      if (result.success) expect(result.data).toEqual([]);
    });
  });
});
