/**
 * 대출 포트폴리오 관리 관련 타입 정의
 * Day 5 - Task 2: Loan Portfolio Management (δ=1570)
 *
 * 기존 src/types/loan.ts 의 Loan/LoanProduct 는 "계산 입력/출력" 모델이며,
 * 여기서는 DB에 영속화되는 실제 대출 레코드(잔액, 상환이력 등)를 다룬다.
 */

export type LoanStatus = 'active' | 'closed' | 'delinquent' | 'defaulted';
export type PaymentStatus = 'completed' | 'failed' | 'pending';
export type LoanHistoryAction = 'CREATED' | 'PAYMENT' | 'STATUS_CHANGE' | 'CLOSED';

export interface LoanRecord {
  id: string;
  userId: string;
  productId: string;
  status: LoanStatus;
  originalAmount: number;
  currentBalance: number;
  interestRate: number;
  termMonths: number;
  startDate: string; // YYYY-MM-DD
  maturityDate: string; // YYYY-MM-DD
  monthlyPayment: number;
  nextPaymentDate: string | null;
  totalPaid: number;
  totalInterestPaid: number;
  createdAt: string;
  updatedAt: string;
  closedAt: string | null;
}

export interface RegisterLoanInput {
  userId: string;
  productId: string;
  originalAmount: number;
  interestRate: number; // annual %
  termMonths: number;
  startDate: string; // YYYY-MM-DD
}

export interface LoanPayment {
  id: string;
  loanId: string;
  paymentDate: string;
  principal: number;
  interest: number;
  fees: number;
  status: PaymentStatus;
}

export interface RecordPaymentInput {
  paymentDate: string;
  principal: number;
  interest: number;
  fees?: number;
  status?: PaymentStatus;
}

export interface LoanHistoryEntry {
  id: string;
  loanId: string;
  action: LoanHistoryAction;
  previousBalance: number;
  newBalance: number;
  actionDate: string;
}

export interface PortfolioSummary {
  userId: string;
  loanCount: number;
  activeLoanCount: number;
  delinquentLoanCount: number;
  totalOriginalAmount: number;
  totalCurrentBalance: number;
  totalMonthlyPayment: number;
  averageInterestRate: number;
}
