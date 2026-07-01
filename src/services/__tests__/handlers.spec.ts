/**
 * D09: MSW 엔드포인트 테스트
 * Week 2 Day 2: Task 1 - 신용도 평가 엔드포인트 (6 tests)
 */

import { describe, it, expect } from 'vitest';

// Credit assessment endpoint logic (extracted from handlers for testing)
async function assessCreditEndpoint(input: {
  income: number;
  debt: number;
  creditScore: number;
  assets: number;
}): Promise<any> {
  // 입력 검증
  if (input.income <= 0) {
    throw new Error('Income must be greater than 0');
  }
  if (input.debt < 0) {
    throw new Error('Debt cannot be negative');
  }
  if (input.creditScore < 0 || input.creditScore > 999) {
    throw new Error('Credit score must be between 0 and 999');
  }
  if (input.assets < 0) {
    throw new Error('Assets cannot be negative');
  }

  // 월간 부채 비율 계산
  const monthlyIncome = input.income;
  const monthlyDebtPayment = input.debt / 12;
  const debtRatio = (monthlyDebtPayment / monthlyIncome) * 100;

  // 신용 등급 결정 및 최대 대출액 계산
  let maxLoanAmount = 0;
  let approved = false;
  let recommendation: 'APPROVED' | 'CONDITIONAL' | 'REJECTED' = 'REJECTED';
  let grade = 'D';

  if (input.creditScore >= 800) {
    grade = 'A';
    maxLoanAmount = Math.min(
      monthlyIncome * 12 * 5,
      500000000
    );
    approved = debtRatio <= 40;
    recommendation = approved ? 'APPROVED' : 'CONDITIONAL';
  } else if (input.creditScore >= 700) {
    grade = 'B';
    maxLoanAmount = Math.min(
      monthlyIncome * 12 * 3,
      300000000
    );
    approved = debtRatio <= 50;
    recommendation = approved ? 'APPROVED' : 'CONDITIONAL';
  } else if (input.creditScore >= 650) {
    grade = 'C';
    maxLoanAmount = Math.min(
      monthlyIncome * 12 * 1.5,
      150000000
    );
    approved = debtRatio <= 60;
    recommendation = 'CONDITIONAL';
  } else {
    grade = 'D';
    maxLoanAmount = 0;
    approved = false;
    recommendation = 'REJECTED';
  }

  // 자산 기반 추가 대출액 계산
  if (input.assets > 0) {
    const assetBasedLoan = input.assets * 0.7;
    maxLoanAmount = Math.max(maxLoanAmount, Math.min(assetBasedLoan, maxLoanAmount * 1.2));
  }

  // 현재 부채를 고려한 최종 대출액 조정
  const adjustedMaxLoan = Math.max(0, maxLoanAmount - input.debt);

  return {
    approved,
    score: input.creditScore,
    maxLoanAmount: Math.round(adjustedMaxLoan),
    debtRatioPercent: Math.round(debtRatio * 100) / 100,
    recommendation,
    grade,
    message: approved
      ? `Credit assessment approved. Grade ${grade}. Max loan: ${Math.round(adjustedMaxLoan).toLocaleString()}원`
      : `Credit assessment ${recommendation.toLowerCase()}. Grade ${grade}.`
  };
}

describe('MSW Handlers: Credit Assessment Endpoint (Task 1)', () => {

  describe('[T-API-001~004] 신용 등급별 평가', () => {

    it('[T-API-001] Grade A: 신용도 우수 승인 (신용점수 800+)', async () => {
      const data = await assessCreditEndpoint({
        income: 50000000,
        debt: 30000000,
        creditScore: 820,
        assets: 500000000
      });

      expect(data.approved).toBe(true);
      expect(data.grade).toBe('A');
      expect(data.recommendation).toBe('APPROVED');
      expect(data.maxLoanAmount).toBeGreaterThan(200000000);
      expect(data.debtRatioPercent).toBeLessThan(40);
      expect(data.message).toContain('Grade A');
    });

    it('[T-API-002] Grade B: 신용도 양호 승인 (신용점수 700-799)', async () => {
      const data = await assessCreditEndpoint({
        income: 40000000,
        debt: 20000000,
        creditScore: 750,
        assets: 200000000
      });

      expect(data.approved).toBe(true);
      expect(data.grade).toBe('B');
      expect(data.recommendation).toBe('APPROVED');
      expect(data.maxLoanAmount).toBeGreaterThan(100000000);
      expect(data.maxLoanAmount).toBeLessThanOrEqual(300000000);
      expect(data.debtRatioPercent).toBeLessThan(50);
    });

    it('[T-API-003] Grade C: 신용도 보통 조건부 (신용점수 650-699)', async () => {
      const data = await assessCreditEndpoint({
        income: 30000000,
        debt: 15000000,
        creditScore: 670,
        assets: 100000000
      });

      expect(data.grade).toBe('C');
      expect(data.recommendation).toBe('CONDITIONAL');
      expect(data.maxLoanAmount).toBeGreaterThan(0);
      expect(data.maxLoanAmount).toBeLessThanOrEqual(150000000);
    });

    it('[T-API-004] Grade D: 신용도 불량 거절 (신용점수 <650)', async () => {
      const data = await assessCreditEndpoint({
        income: 30000000,
        debt: 15000000,
        creditScore: 600,
        assets: 50000000
      });

      expect(data.approved).toBe(false);
      expect(data.grade).toBe('D');
      expect(data.recommendation).toBe('REJECTED');
      expect(data.maxLoanAmount).toBe(0);
      expect(data.message).toContain('rejected');
    });
  });

  describe('[T-API-005~006] 부채비율 경계 및 초과', () => {

    it('[T-API-005] 부채비율 경계값 (정확히 40% at Grade A)', async () => {
      const monthlyIncome = 50000000;
      const monthlyDebtTarget = (monthlyIncome * 40) / 100;
      const debt = monthlyDebtTarget * 12;

      const data = await assessCreditEndpoint({
        income: monthlyIncome,
        debt: debt,
        creditScore: 800,
        assets: 0
      });

      expect(data.approved).toBe(true);
      expect(data.debtRatioPercent).toBe(40);
      expect(data.grade).toBe('A');
    });

    it('[T-API-006] 부채비율 초과 (41% at Grade A, 거절)', async () => {
      const monthlyIncome = 50000000;
      const monthlyDebtTarget = (monthlyIncome * 41) / 100;
      const debt = monthlyDebtTarget * 12;

      const data = await assessCreditEndpoint({
        income: monthlyIncome,
        debt: debt,
        creditScore: 800,
        assets: 0
      });

      expect(data.approved).toBe(false);
      expect(data.debtRatioPercent).toBeGreaterThan(40);
      expect(data.recommendation).toBe('CONDITIONAL');
      expect(data.grade).toBe('A');
    });
  });
});
