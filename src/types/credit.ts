/**
 * 신용도 평가 관련 타입 정의
 */

export interface CreditAssessmentInput {
  income: number; // KRW, monthly
  debt: number; // KRW, total
  creditScore: number; // 0-999
  assets: number; // KRW, total
}

export interface CreditAssessment {
  approved: boolean;
  score: number; // 0-999
  maxLoanAmount: number; // KRW
  debtRatioPercent: number; // %
  recommendation: 'APPROVED' | 'CONDITIONAL' | 'REJECTED';
}

export interface CreditScore {
  grade: 'A' | 'B' | 'C' | 'D';
  minScore: number;
  maxScore: number;
  description: string;
}
