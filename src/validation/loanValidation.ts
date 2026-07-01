/**
 * 대출 입력 검증 (Day 5 - Task 5: 데이터 검증 & 무결성, δ=1605)
 */

import { RegisterLoanInput } from '../types/loanPortfolio';
import { ValidationError } from '../repositories/errors';

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export function validateRegisterLoanInput(input: RegisterLoanInput): void {
  if (input.originalAmount <= 0) {
    throw new ValidationError('originalAmount must be greater than 0');
  }
  if (input.interestRate <= 0 || input.interestRate > 100) {
    throw new ValidationError('interestRate must be between 0 and 100');
  }
  if (input.termMonths <= 0 || input.termMonths > 600) {
    throw new ValidationError('termMonths must be between 1 and 600');
  }
  if (!DATE_PATTERN.test(input.startDate)) {
    throw new ValidationError('startDate must be formatted as YYYY-MM-DD');
  }
}
