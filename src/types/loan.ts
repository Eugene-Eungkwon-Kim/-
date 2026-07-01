/**
 * 대출 상품 및 신청 관련 타입 정의
 * Phase 2 D09: 금융로직 단위테스트
 */

export interface LoanProduct {
  id: string;
  name: string;
  type: 'premium' | 'standard' | 'conditional' | 'commercial';
  minCreditScore: number;
  rate: number; // annual %
  maxAmount: number; // KRW
  term: number[]; // months
  propertyTypes: string[];
  requirements: {
    minIncome: number;
    maxDebtRatio: number;
    commercialLicense?: boolean;
    additionalReview?: boolean;
  };
}

export interface LoanFilter {
  creditScore: number; // 0-999
  propertyType?: string;
  amountRange?: [min: number, max: number];
  priceMin?: number;
  priceMax?: number;
}

export interface LoanCalculationInput {
  principal: number; // KRW
  rate: number; // annual %
  term: number; // months
}

export interface LoanCalculationResult {
  monthlyPayment: number; // KRW
  totalPayment: number; // KRW
  totalInterest: number; // KRW
}

export interface Loan {
  id: string;
  principal: number; // KRW
  rate: number; // annual %
  term: number; // months
  status: 'approved' | 'pending' | 'rejected' | 'completed';
  startDate: Date;
  endDate: Date;
  product: LoanProduct;
}
