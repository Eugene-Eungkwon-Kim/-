/**
 * 이자 계산 서비스
 * D09: 금융로직 단위테스트
 * 월정액 이자 계산 (compound interest formula)
 */

import { LoanCalculationInput, LoanCalculationResult } from '../types/loan';

export async function calculateLoanPayment(input: LoanCalculationInput): Promise<LoanCalculationResult> {
  // 입력 검증
  if (input.principal <= 0) {
    throw new Error('Principal must be greater than 0');
  }
  if (input.rate < 0 || input.rate > 100) {
    throw new Error('Interest rate must be between 0 and 100');
  }
  if (input.term <= 0 || input.term > 600) {
    throw new Error('Term must be between 1 and 600 months');
  }

  // 0% 이율 특수 처리
  if (input.rate === 0) {
    const monthlyPayment = Math.round(input.principal / input.term);
    return {
      monthlyPayment,
      totalPayment: input.principal,
      totalInterest: 0
    };
  }

  // 월이율 계산
  const monthlyRate = input.rate / 12 / 100;

  // 월 상환액 계산 (원금균등상환)
  // 공식: P * [r(1+r)^n] / [(1+r)^n - 1]
  const numerator = monthlyRate * Math.pow(1 + monthlyRate, input.term);
  const denominator = Math.pow(1 + monthlyRate, input.term) - 1;
  const monthlyPayment = Math.round(input.principal * (numerator / denominator));

  const totalPayment = monthlyPayment * input.term;
  const totalInterest = totalPayment - input.principal;

  return {
    monthlyPayment,
    totalPayment,
    totalInterest
  };
}
