/**
 * 신용도 평가 서비스
 * D09: 금융로직 단위테스트
 * 소득, 부채, 신용점수, 자산을 기반으로 신용도 판단
 */

import { CreditAssessmentInput, CreditAssessment } from '@types/credit';

export async function assessCredit(input: CreditAssessmentInput): Promise<CreditAssessment> {
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

  if (input.creditScore >= 800) {
    // Grade A: 신용점수 우수
    maxLoanAmount = Math.min(
      monthlyIncome * 12 * 5, // 연소득의 5배
      500000000 // 최대 5억
    );
    approved = debtRatio <= 40;
    recommendation = approved ? 'APPROVED' : 'CONDITIONAL';
  } else if (input.creditScore >= 700) {
    // Grade B: 신용점수 양호
    maxLoanAmount = Math.min(
      monthlyIncome * 12 * 3, // 연소득의 3배
      300000000 // 최대 3억
    );
    approved = debtRatio <= 50;
    recommendation = approved ? 'APPROVED' : 'CONDITIONAL';
  } else if (input.creditScore >= 650) {
    // Grade C: 신용점수 보통
    maxLoanAmount = Math.min(
      monthlyIncome * 12 * 1.5, // 연소득의 1.5배
      150000000 // 최대 1.5억
    );
    approved = debtRatio <= 60;
    recommendation = 'CONDITIONAL';
  } else {
    // Grade D: 신용점수 불량
    maxLoanAmount = 0;
    approved = false;
    recommendation = 'REJECTED';
  }

  // 자산 기반 추가 대출액 계산
  if (input.assets > 0) {
    const assetBasedLoan = input.assets * 0.7; // 자산의 70%까지
    maxLoanAmount = Math.max(maxLoanAmount, Math.min(assetBasedLoan, maxLoanAmount * 1.2));
  }

  // 현재 부채를 고려한 최종 대출액 조정
  const adjustedMaxLoan = Math.max(0, maxLoanAmount - input.debt);

  return {
    approved,
    score: input.creditScore,
    maxLoanAmount: Math.round(adjustedMaxLoan),
    debtRatioPercent: Math.round(debtRatio * 100) / 100,
    recommendation
  };
}
