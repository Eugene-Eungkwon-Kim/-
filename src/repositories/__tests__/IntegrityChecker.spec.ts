import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { UserRepository } from '@repositories/UserRepository';
import { LoanRepository } from '@repositories/LoanRepository';
import { IntegrityChecker } from '@repositories/IntegrityChecker';
import { ValidationError } from '@repositories/errors';

describe('IntegrityChecker (Day 5 - Task 5: 데이터 검증 & 무결성, δ=1605)', () => {
  let db: Database.Database;
  let users: UserRepository;
  let loans: LoanRepository;
  let checker: IntegrityChecker;
  let userId: string;

  beforeEach(() => {
    db = createDatabase(':memory:');
    users = new UserRepository(db);
    loans = new LoanRepository(db);
    checker = new IntegrityChecker(db);
    userId = users.register({ email: 'integrity@example.com', name: 'Integrity User' }).id;
  });

  afterEach(() => {
    db.close();
  });

  describe('[T-API-A25~A30] 데이터 검증 & 무결성', () => {
    it('[T-API-A25] DB 제약조건 검증 (loans/loan_payments)', async () => {
      const loan = await loans.registerLoan({
        userId,
        productId: 'prod-1',
        originalAmount: 100000000,
        interestRate: 3.2,
        termMonths: 120,
        startDate: '2026-01-01'
      });

      // 잔액이 원금을 초과하는 상태는 CHECK 제약으로 직접 차단된다
      expect(() =>
        db.prepare('UPDATE loans SET current_balance = original_amount + 1 WHERE id = ?').run(loan.id)
      ).toThrow(/CHECK constraint failed/);

      // 상환액 3요소가 모두 0인 결제 기록도 CHECK 제약으로 차단된다
      expect(() =>
        db
          .prepare('INSERT INTO loan_payments (id, loan_id, payment_date, principal, interest, fees) VALUES (?, ?, ?, 0, 0, 0)')
          .run('payment-zero', loan.id, '2026-02-01')
      ).toThrow(/CHECK constraint failed/);
    });

    it('[T-API-A26] 입력 검증 (타입, 범위)', async () => {
      expect(() => users.register({ email: 'not-an-email', name: 'Bad Email' })).toThrow(ValidationError);
      expect(() => users.register({ email: 'ok@example.com', name: 'X', financialSnapshot: { monthlyIncome: -1 } })).toThrow(
        ValidationError
      );

      await expect(
        loans.registerLoan({
          userId,
          productId: 'prod-1',
          originalAmount: -100,
          interestRate: 3.2,
          termMonths: 120,
          startDate: '2026-01-01'
        })
      ).rejects.toThrow(ValidationError);
    });

    it('[T-API-A27] 비즈니스 규칙 검증 (나이 18-99세)', () => {
      // 2020년생 → 명백히 18세 미만
      expect(() => users.register({ email: 'too-young@example.com', name: 'Too Young', dateOfBirth: '2020-01-01' })).toThrow(
        ValidationError
      );
      // 1900년생 → 명백히 99세 초과
      expect(() => users.register({ email: 'too-old@example.com', name: 'Too Old', dateOfBirth: '1900-01-01' })).toThrow(
        ValidationError
      );

      // 유효 범위는 정상 등록
      const valid = users.register({ email: 'valid-age@example.com', name: 'Valid Age', dateOfBirth: '1990-01-01' });
      expect(valid.dateOfBirth).toBe('1990-01-01');
    });

    it('[T-API-A28] 교차 엔티티 일관성', async () => {
      // 존재하지 않는 user_id 참조는 FK 제약으로 즉시 차단 (리포지토리 우회 경로 방어)
      expect(() =>
        db
          .prepare(
            'INSERT INTO loans (id, user_id, product_id, original_amount, current_balance, interest_rate, term_months, start_date, maturity_date, monthly_payment) VALUES (?, ?, ?, 1000000, 1000000, 3.2, 12, ?, ?, 100000)'
          )
          .run('orphan-loan', 'non-existent-user', 'prod-1', '2026-01-01', '2027-01-01')
      ).toThrow(/FOREIGN KEY constraint failed/);

      // 정상 등록 후 월상환액을 우회 경로로 오염시키면 재계산값과 불일치가 감지된다
      const loan = await loans.registerLoan({
        userId,
        productId: 'prod-1',
        originalAmount: 300000000,
        interestRate: 3.2,
        termMonths: 240,
        startDate: '2026-01-01'
      });
      db.prepare('UPDATE loans SET monthly_payment = monthly_payment + 12345 WHERE id = ?').run(loan.id);

      const result = await checker.checkMonthlyPaymentConsistency();
      expect(result.status).toBe('violation');
      expect(result.findings.some((f) => f.entityId === loan.id)).toBe(true);
    });

    it('[T-API-A29] 무결성 자동 검사', async () => {
      const clean = await checker.runFullCheck('2026-07-01');
      expect(clean.every((r) => r.status === 'ok')).toBe(true);

      // 검증을 우회한 레거시 데이터(리포지토리 밖에서 직접 삽입)를 시뮬레이션
      db.prepare('INSERT INTO users (id, email, name, date_of_birth) VALUES (?, ?, ?, ?)').run(
        'legacy-user',
        'legacy@example.com',
        'Legacy User',
        '2020-01-01'
      );

      const ageCheck = checker.checkAgeConsistency('2026-07-01');
      expect(ageCheck.status).toBe('violation');
      expect(ageCheck.findings.some((f) => f.entityId === 'legacy-user')).toBe(true);

      const log = checker.getIntegrityLog('age_out_of_range');
      expect(log.length).toBeGreaterThan(0);
      expect(log[log.length - 1].status).toBe('violation');
    });

    it('[T-API-A30] 위반 사항 복구', async () => {
      const loan = await loans.registerLoan({
        userId,
        productId: 'prod-1',
        originalAmount: 300000000,
        interestRate: 3.2,
        termMonths: 240,
        startDate: '2026-01-01'
      });
      const correctPayment = loan.monthlyPayment;

      db.prepare('UPDATE loans SET monthly_payment = monthly_payment + 99999 WHERE id = ?').run(loan.id);
      const violation = await checker.checkMonthlyPaymentConsistency();
      expect(violation.status).toBe('violation');

      const repairResult = await checker.repairMonthlyPaymentDrift(loan.id);
      expect(repairResult.status).toBe('repaired');

      const repaired = loans.getLoan(loan.id);
      expect(repaired?.monthlyPayment).toBe(correctPayment);

      const log = checker.getIntegrityLog('monthly_payment_drift');
      expect(log.some((entry) => entry.status === 'repaired')).toBe(true);

      const recheck = await checker.checkMonthlyPaymentConsistency();
      expect(recheck.status).toBe('ok');
    });
  });
});
