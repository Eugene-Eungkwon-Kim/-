import type Database from 'better-sqlite3';
import { LoanRepository } from '../repositories/LoanRepository';
import { LoanRecord, PortfolioSummary, RecordPaymentInput, RegisterLoanInput } from '../types/loanPortfolio';
import { ServiceResult, toServiceResult, toServiceResultAsync } from './errorMapping';
import { validateLoanApplication, validateLoanPayment } from '../validation/requestValidation';

/** 대출 서비스 계층 (Day 6 - Task 2, δ=1600) */
export function applyForLoan(db: Database.Database, input: RegisterLoanInput): Promise<ServiceResult<LoanRecord>> {
  return toServiceResultAsync(() => {
    validateLoanApplication(input);
    return new LoanRepository(db).registerLoan(input);
  });
}

export function getLoanPortfolio(db: Database.Database, userId: string): ServiceResult<LoanRecord[]> {
  return toServiceResult(() => new LoanRepository(db).getPortfolio(userId));
}

export function recordLoanPayment(
  db: Database.Database,
  loanId: string,
  input: RecordPaymentInput
): ServiceResult<LoanRecord> {
  return toServiceResult(() => {
    validateLoanPayment(input);
    return new LoanRepository(db).recordPayment(loanId, input);
  });
}

export function getLoanPortfolioSummary(db: Database.Database, userId: string): ServiceResult<PortfolioSummary> {
  return toServiceResult(() => new LoanRepository(db).getPortfolioSummary(userId));
}

/** 연체 감지 배치 진입점 (Day 7 - Task 2, δ=1010). 운영에서는 스케줄러가 이 함수를 주기 호출한다 */
export function detectDelinquentLoans(db: Database.Database, asOfDate: string): ServiceResult<LoanRecord[]> {
  return toServiceResult(() => new LoanRepository(db).detectDelinquentLoans(asOfDate));
}
