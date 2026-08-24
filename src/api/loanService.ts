import type { Pool } from 'pg';
import { LoanRepository } from '../repositories/LoanRepository';
import { LoanRecord, PortfolioSummary, RecordPaymentInput, RegisterLoanInput } from '../types/loanPortfolio';
import { ServiceResult, toServiceResultAsync } from './errorMapping';
import { validateLoanApplication, validateLoanPayment } from '../validation/requestValidation';

export async function applyForLoan(pool: Pool, input: RegisterLoanInput): Promise<ServiceResult<LoanRecord>> {
  return toServiceResultAsync(async () => {
    validateLoanApplication(input);
    return new LoanRepository(pool).registerLoan(input);
  });
}

export async function getLoanPortfolio(pool: Pool, userId: string): Promise<ServiceResult<LoanRecord[]>> {
  return toServiceResultAsync(async () => new LoanRepository(pool).getPortfolio(userId));
}

export async function recordLoanPayment(
  pool: Pool,
  loanId: string,
  input: RecordPaymentInput
): Promise<ServiceResult<LoanRecord>> {
  return toServiceResultAsync(async () => {
    validateLoanPayment(input);
    return new LoanRepository(pool).recordPayment(loanId, input);
  });
}

export async function getLoanPortfolioSummary(pool: Pool, userId: string): Promise<ServiceResult<PortfolioSummary>> {
  return toServiceResultAsync(async () => new LoanRepository(pool).getPortfolioSummary(userId));
}

export async function detectDelinquentLoans(pool: Pool, asOfDate: string): Promise<ServiceResult<LoanRecord[]>> {
  return toServiceResultAsync(async () => new LoanRepository(pool).detectDelinquentLoans(asOfDate));
}
