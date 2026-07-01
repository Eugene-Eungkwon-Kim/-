import type Database from 'better-sqlite3';
import { LoanNotFoundError, LoanRepository, OverpaymentError } from '../repositories/LoanRepository';
import { UserNotFoundError, ValidationError } from '../repositories/errors';
import { LoanRecord, PortfolioSummary, RecordPaymentInput, RegisterLoanInput } from '../types/loanPortfolio';
import { ServiceResult } from './userService';

/** 서비스 계층 (Day 6 - Task 2: 대출 서비스, δ=1600) */
function mapLoanError(error: unknown): { code: string; message: string } {
  if (error instanceof UserNotFoundError) return { code: 'USER_NOT_FOUND', message: error.message };
  if (error instanceof ValidationError) return { code: 'VALIDATION_ERROR', message: error.message };
  if (error instanceof LoanNotFoundError) return { code: 'LOAN_NOT_FOUND', message: error.message };
  if (error instanceof OverpaymentError) return { code: 'OVERPAYMENT', message: error.message };
  return { code: 'INTERNAL_ERROR', message: error instanceof Error ? error.message : String(error) };
}

export async function applyForLoan(db: Database.Database, input: RegisterLoanInput): Promise<ServiceResult<LoanRecord>> {
  try {
    const repo = new LoanRepository(db);
    return { success: true, data: await repo.registerLoan(input) };
  } catch (error) {
    return { success: false, error: mapLoanError(error) };
  }
}

export function getLoanPortfolio(db: Database.Database, userId: string): ServiceResult<LoanRecord[]> {
  try {
    const repo = new LoanRepository(db);
    return { success: true, data: repo.getPortfolio(userId) };
  } catch (error) {
    return { success: false, error: mapLoanError(error) };
  }
}

export function recordLoanPayment(
  db: Database.Database,
  loanId: string,
  input: RecordPaymentInput
): ServiceResult<LoanRecord> {
  try {
    const repo = new LoanRepository(db);
    return { success: true, data: repo.recordPayment(loanId, input) };
  } catch (error) {
    return { success: false, error: mapLoanError(error) };
  }
}

export function getLoanPortfolioSummary(db: Database.Database, userId: string): ServiceResult<PortfolioSummary> {
  try {
    const repo = new LoanRepository(db);
    return { success: true, data: repo.getPortfolioSummary(userId) };
  } catch (error) {
    return { success: false, error: mapLoanError(error) };
  }
}
