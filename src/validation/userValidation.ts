/**
 * 사용자 입력 검증 (Day 5 - Task 5: 데이터 검증 & 무결성, δ=1605)
 *
 * DB에 닿기 전 시스템 경계에서 검증한다. UserRepository.register/updateProfile은
 * 이 함수들을 호출해 검증을 위임하며, DB CHECK 제약(range 등)은 최후 방어선으로
 * 별도 유지된다 (애플리케이션 검증 실패 시 더 read 가능한 에러 메시지를 주고,
 * 애플리케이션 검증을 우회하는 경로가 생기더라도 DB가 무결성을 보장한다).
 */

import { RegisterUserInput, UpdateUserInput } from '../types/user';
import { ValidationError } from '../repositories/errors';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const MIN_AGE = 18;
export const MAX_AGE = 99;

export function calculateAge(dateOfBirth: string, asOfDate: string): number {
  const [birthYear, birthMonth, birthDay] = dateOfBirth.split('-').map(Number);
  const [refYear, refMonth, refDay] = asOfDate.split('-').map(Number);

  let age = refYear - birthYear;
  if (refMonth < birthMonth || (refMonth === birthMonth && refDay < birthDay)) {
    age -= 1;
  }
  return age;
}

function assertAgeInRange(dateOfBirth: string, asOfDate: string): void {
  const age = calculateAge(dateOfBirth, asOfDate);
  if (age < MIN_AGE || age > MAX_AGE) {
    throw new ValidationError(`age must be between ${MIN_AGE} and ${MAX_AGE} (calculated: ${age})`);
  }
}

function assertCreditScoreInRange(score: number | undefined): void {
  if (score !== undefined && (score < 0 || score > 999)) {
    throw new ValidationError('creditProfile.score must be between 0 and 999');
  }
}

function assertNonNegative(fieldName: string, value: number | undefined): void {
  if (value !== undefined && value < 0) {
    throw new ValidationError(`${fieldName} cannot be negative`);
  }
}

export function validateRegisterUserInput(input: RegisterUserInput, asOfDate: string): void {
  if (!input.email || !EMAIL_PATTERN.test(input.email)) {
    throw new ValidationError('A valid email is required');
  }
  if (!input.name || input.name.trim().length === 0) {
    throw new ValidationError('name is required');
  }
  if (input.dateOfBirth) {
    assertAgeInRange(input.dateOfBirth, asOfDate);
  }
  assertCreditScoreInRange(input.creditProfile?.score);
  assertNonNegative('financialSnapshot.monthlyIncome', input.financialSnapshot?.monthlyIncome);
  assertNonNegative('financialSnapshot.monthlyExpenses', input.financialSnapshot?.monthlyExpenses);
  assertNonNegative('financialSnapshot.totalAssets', input.financialSnapshot?.totalAssets);
  assertNonNegative('financialSnapshot.totalDebt', input.financialSnapshot?.totalDebt);
}

export function validateUpdateUserInput(updates: UpdateUserInput, asOfDate: string): void {
  if (updates.name !== undefined && updates.name.trim().length === 0) {
    throw new ValidationError('name cannot be empty');
  }
  if (updates.dateOfBirth) {
    assertAgeInRange(updates.dateOfBirth, asOfDate);
  }
  assertCreditScoreInRange(updates.creditProfile?.score);
  assertNonNegative('financialSnapshot.monthlyIncome', updates.financialSnapshot?.monthlyIncome);
  assertNonNegative('financialSnapshot.monthlyExpenses', updates.financialSnapshot?.monthlyExpenses);
  assertNonNegative('financialSnapshot.totalAssets', updates.financialSnapshot?.totalAssets);
  assertNonNegative('financialSnapshot.totalDebt', updates.financialSnapshot?.totalDebt);
}
