import { describe, it, expect } from 'vitest';
import type { Pool } from 'pg';
import { initializeTestDatabase, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { DuplicateEmailError, OptimisticLockError, UserNotFoundError, ValidationError } from '@repositories/errors';
import { LoanNotFoundError, OverpaymentError } from '@repositories/LoanRepository';
import { mapErrorToCode, toServiceResult, toServiceResultAsync } from '@api/errorMapping';
import { registerUser } from '@api/userService';
import { applyForLoan } from '@api/loanService';

describe('errorMapping (Day 6 - Task 3: 응답 표준화 & 에러 처리, δ=1440)', () => {
  describe('[T-SVC-301~306] 에러 매핑 & 서비스 결과 표준화', () => {
    it('[T-SVC-301] 알려진 에러가 정확한 code로 매핑된다', () => {
      expect(mapErrorToCode(new DuplicateEmailError('a@b.com')).code).toBe('DUPLICATE_EMAIL');
      expect(mapErrorToCode(new ValidationError('bad input')).code).toBe('VALIDATION_ERROR');
      expect(mapErrorToCode(new OptimisticLockError('u1', 1, 2)).code).toBe('VERSION_CONFLICT');
      expect(mapErrorToCode(new UserNotFoundError('u1')).code).toBe('USER_NOT_FOUND');
      expect(mapErrorToCode(new LoanNotFoundError('l1')).code).toBe('LOAN_NOT_FOUND');
      expect(mapErrorToCode(new OverpaymentError('l1', 100, 50)).code).toBe('OVERPAYMENT');
    });

    it('[T-SVC-302] 알 수 없는 에러는 INTERNAL_ERROR로 폴백하고 내부 메시지를 유출하지 않는다', () => {
      expect(mapErrorToCode(new Error('boom')).code).toBe('INTERNAL_ERROR');
      expect(mapErrorToCode('a plain string throw').code).toBe('INTERNAL_ERROR');
      // 미매핑 예외의 원본 메시지(SQL 오류, 암호화 키 상태 등)는 서버 로그에만
      // 남기고 클라이언트에는 일반화된 메시지만 내보낸다 (정보 노출 방지)
      const leaked = mapErrorToCode(new Error('ENCRYPTION_KEY environment variable is not set'));
      expect(leaked.message).toBe('An unexpected internal error occurred');
      expect(leaked.message).not.toContain('ENCRYPTION_KEY');
    });

    it('[T-SVC-303] 성공 값은 그대로 통과한다', () => {
      const result = toServiceResult(() => 42);
      expect(result).toEqual({ success: true, data: 42 });
    });

    it('[T-SVC-304] 비동기 버전이 정상 동작한다', async () => {
      const result = await toServiceResultAsync(async () => 'ok');
      expect(result).toEqual({ success: true, data: 'ok' });
    });

    it('[T-SVC-305] 비동기 버전이 에러를 매핑한다', async () => {
      const result = await toServiceResultAsync(async () => {
        throw new UserNotFoundError('missing-user');
      });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.code).toBe('USER_NOT_FOUND');
      }
    });

    it('[T-SVC-306] 공용 유틸 도입 후에도 Task1/2 서비스 동작에 회귀가 없다', async () => {
      process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
      const pool: Pool = await initializeTestDatabase();
      try {
        const dup1 = await registerUser(pool, { email: 'regress@example.com', name: 'A', password: 'test-password-123', contact: { address: {} } });
        expect(dup1.success).toBe(true);
        const dup2 = await registerUser(pool, { email: 'regress@example.com', name: 'B', password: 'test-password-123', contact: { address: {} } });
        expect(dup2.success).toBe(false);
        if (!dup2.success) expect(dup2.error.code).toBe('DUPLICATE_EMAIL');

        const loanResult = await applyForLoan(pool, {
          userId: 'ffffffff-ffff-ffff-ffff-ffffffffffff',
          productId: 'p1',
          originalAmount: 1000000,
          interestRate: 3.2,
          termMonths: 12,
          startDate: '2026-01-01'
        });
        expect(loanResult.success).toBe(false);
        if (!loanResult.success) expect(loanResult.error.code).toBe('USER_NOT_FOUND');
      } finally {
        await cleanupTestDatabase();
        delete process.env.ENCRYPTION_KEY;
      }
    });
  });
});
