/**
 * Day 12 - Task A (δ=1200): 입력 데이터 검증 강화
 *
 * 모든 API 엔드포인트의 요청 데이터에 대해 명시적 유효성 검사를 수행한다.
 * 검증 실패 시 ValidationError를 던져 에러 매핑(400)으로 변환된다.
 */

import { ValidationError } from '../repositories/errors';

export { ValidationError };

/**
 * UUID v4 형식 검증
 */
function isValidUUID(value: unknown): boolean {
  if (typeof value !== 'string') return false;
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(value);
}

/**
 * 이메일 형식 검증 (간단한 패턴)
 */
function isValidEmail(value: unknown): boolean {
  if (typeof value !== 'string') return false;
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

/**
 * ISO 8601 날짜 형식 검증
 */
function isValidISODate(value: unknown): boolean {
  if (typeof value !== 'string') return false;
  const date = new Date(value);
  return !isNaN(date.getTime()) && value.match(/^\d{4}-\d{2}-\d{2}/);
}

/**
 * POST /api/users — 회원가입 입력 검증
 */
export function validateUserRegistration(input: unknown): void {
  if (!input || typeof input !== 'object') {
    throw new ValidationError('Request body must be an object');
  }

  const data = input as Record<string, unknown>;

  // name: 1-100자
  if (typeof data.name !== 'string' || data.name.length < 1 || data.name.length > 100) {
    throw new ValidationError('name must be a string between 1 and 100 characters');
  }

  // email: 유효한 형식
  if (!isValidEmail(data.email)) {
    throw new ValidationError('email must be a valid email format');
  }

  // password: 최소 8자
  if (typeof data.password !== 'string' || data.password.length < 8) {
    throw new ValidationError('password must be at least 8 characters');
  }

  // creditProfile.score (optional): 300-850
  if (data.creditProfile !== undefined) {
    if (typeof data.creditProfile !== 'object' || data.creditProfile === null) {
      throw new ValidationError('creditProfile must be an object');
    }
    const cp = data.creditProfile as Record<string, unknown>;
    if (cp.score !== undefined && cp.score !== null) {
      const score = Number(cp.score);
      if (!Number.isInteger(score) || score < 300 || score > 850) {
        throw new ValidationError('creditProfile.score must be between 300 and 850');
      }
    }
  }
}

/**
 * POST /api/auth/login — 로그인 입력 검증
 */
export function validateLogin(input: unknown): void {
  if (!input || typeof input !== 'object') {
    throw new ValidationError('Request body must be an object');
  }

  const data = input as Record<string, unknown>;

  // email: 유효한 형식
  if (!isValidEmail(data.email)) {
    throw new ValidationError('email must be a valid email format');
  }

  // password: 최소 8자
  if (typeof data.password !== 'string' || data.password.length < 8) {
    throw new ValidationError('password must be at least 8 characters');
  }
}

/**
 * POST /api/loans — 대출 신청 입력 검증
 */
export function validateLoanApplication(input: unknown): void {
  if (!input || typeof input !== 'object') {
    throw new ValidationError('Request body must be an object');
  }

  const data = input as Record<string, unknown>;

  // userId: UUID 형식
  if (!isValidUUID(data.userId)) {
    throw new ValidationError('userId must be a valid UUID');
  }

  // originalAmount: 양수, 1,000 ~ 1,000,000,000
  const originalAmount = Number(data.originalAmount);
  if (!Number.isInteger(originalAmount) || originalAmount < 1000 || originalAmount > 1000000000) {
    throw new ValidationError('originalAmount must be an integer between 1000 and 1000000000');
  }

  // interestRate: 0.5 ~ 20.0
  const interestRate = Number(data.interestRate);
  if (typeof data.interestRate !== 'number' || interestRate < 0.5 || interestRate > 20.0) {
    throw new ValidationError('interestRate must be between 0.5 and 20.0');
  }

  // termMonths: 12 ~ 600
  const termMonths = Number(data.termMonths);
  if (!Number.isInteger(termMonths) || termMonths < 12 || termMonths > 600) {
    throw new ValidationError('termMonths must be an integer between 12 and 600');
  }

  // productId: required
  if (typeof data.productId !== 'string' || data.productId.length === 0) {
    throw new ValidationError('productId must be a non-empty string');
  }

  // startDate: ISO 8601 형식
  if (!isValidISODate(data.startDate)) {
    throw new ValidationError('startDate must be a valid ISO 8601 date');
  }
}

/**
 * POST /api/loans/:loanId/payments — 상환 기록 입력 검증
 */
export function validateLoanPayment(input: unknown): void {
  if (!input || typeof input !== 'object') {
    throw new ValidationError('Request body must be an object');
  }

  const data = input as Record<string, unknown>;

  // principal: 양수
  const principal = Number(data.principal);
  if (!Number.isFinite(principal) || principal <= 0) {
    throw new ValidationError('principal must be a positive number');
  }

  // interest: 0 이상
  const interest = Number(data.interest);
  if (!Number.isFinite(interest) || interest < 0) {
    throw new ValidationError('interest must be a non-negative number');
  }

  // fees (optional): 0 이상
  if (data.fees !== undefined && data.fees !== null) {
    const fees = Number(data.fees);
    if (!Number.isFinite(fees) || fees < 0) {
      throw new ValidationError('fees must be a non-negative number');
    }
  }

  // paymentDate: ISO 8601 형식, 미래 날짜 불가
  if (!isValidISODate(data.paymentDate)) {
    throw new ValidationError('paymentDate must be a valid ISO 8601 date');
  }

  const paymentDate = new Date(data.paymentDate as string);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (paymentDate > today) {
    throw new ValidationError('paymentDate cannot be in the future');
  }
}

/**
 * POST /api/transactions — 거래 기록 입력 검증
 */
export function validateTransaction(input: unknown): void {
  if (!input || typeof input !== 'object') {
    throw new ValidationError('Request body must be an object');
  }

  const data = input as Record<string, unknown>;

  // userId: UUID 형식
  if (!isValidUUID(data.userId)) {
    throw new ValidationError('userId must be a valid UUID');
  }

  // transactionType: enum
  const validTypes = ['deposit', 'withdrawal', 'loan_payment', 'fee', 'adjustment'];
  if (!validTypes.includes(data.transactionType as string)) {
    throw new ValidationError(`transactionType must be one of: ${validTypes.join(', ')}`);
  }

  // amount: 양수, 최대 10,000,000
  const amount = Number(data.amount);
  if (!Number.isFinite(amount) || amount <= 0 || amount > 10000000) {
    throw new ValidationError('amount must be a positive number not exceeding 10000000');
  }

  // occurredAt: ISO 8601 형식, 미래 날짜 불가
  if (!isValidISODate(data.occurredAt)) {
    throw new ValidationError('occurredAt must be a valid ISO 8601 date');
  }

  const occurredAt = new Date(data.occurredAt as string);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (occurredAt > today) {
    throw new ValidationError('occurredAt cannot be in the future');
  }
}
