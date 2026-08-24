/**
 * D09: 신용도 평가 서비스 테스트
 * Week 1 Wednesday: 6개 테스트 케이스
 */

import { describe, it, expect } from 'vitest';
import { assessCredit } from './credit-assessment';

describe('CreditAssessment.assessCredit()', () => {

  describe('[T-C001~C002] 기본 신용도 평가', () => {

    it('[T-C001] Grade A: 신용도 우수, 낮은 부채비율 승인', async () => {
      const result = await assessCredit({
        income: 50000000,
        debt: 50000000,
        creditScore: 820,
        assets: 100000000
      });

      expect(result.approved).toBe(true);
      expect(result.recommendation).toBe('APPROVED');
      expect(result.maxLoanAmount).toBeGreaterThan(0);
      expect(result.debtRatioPercent).toBeLessThan(50);
    });

    it('[T-C002] 자산 기반 대출액 산정', async () => {
      const result = await assessCredit({
        income: 30000000,
        debt: 30000000,
        creditScore: 750,
        assets: 200000000
      });

      expect(result.maxLoanAmount).toBeGreaterThan(0);
      expect(result.recommendation).toBe('APPROVED');
    });
  });

  describe('[T-C003~C004] 조건부 및 거절 판정', () => {

    it('[T-C003] Grade B: 조건부 승인 (부채비율 경계)', async () => {
      const result = await assessCredit({
        income: 30000000,
        debt: 150000000,
        creditScore: 750,
        assets: 50000000
      });

      expect(result.debtRatioPercent).toBeGreaterThan(40);
      expect(result.debtRatioPercent).toBeLessThanOrEqual(50);
      expect(result.recommendation).toBe('APPROVED');
    });

    it('[T-C004] Grade D: 신용도 불량 거절', async () => {
      const result = await assessCredit({
        income: 30000000,
        debt: 100000000,
        creditScore: 600,
        assets: 50000000
      });

      expect(result.approved).toBe(false);
      expect(result.recommendation).toBe('REJECTED');
      expect(result.maxLoanAmount).toBe(0);
    });
  });

  describe('[T-C005~C006] 등급별 한도 및 에러 처리', () => {

    it('[T-C005] 등급별 대출 한도 차등 적용', async () => {
      const gradeA = await assessCredit({
        income: 50000000,
        debt: 0,
        creditScore: 850,
        assets: 0
      });

      const gradeB = await assessCredit({
        income: 50000000,
        debt: 0,
        creditScore: 750,
        assets: 0
      });

      const gradeC = await assessCredit({
        income: 50000000,
        debt: 0,
        creditScore: 670,
        assets: 0
      });

      expect(gradeA.maxLoanAmount).toBeGreaterThan(gradeB.maxLoanAmount);
      expect(gradeB.maxLoanAmount).toBeGreaterThan(gradeC.maxLoanAmount);
    });

    it('[T-C006] 음수 소득 입력 거부', () => {
      expect(async () => {
        await assessCredit({
          income: -10000000,
          debt: 0,
          creditScore: 750,
          assets: 0
        });
      }).rejects.toThrow('Income must be greater than 0');
    });
  });

});
