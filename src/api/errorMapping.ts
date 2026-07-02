import {
  DuplicateEmailError,
  InvalidCredentialsError,
  OptimisticLockError,
  UserNotFoundError,
  ValidationError
} from '../repositories/errors';
import { LoanNotFoundError, OverpaymentError } from '../repositories/LoanRepository';
import { TransactionNotFoundError } from '../repositories/TransactionRepository';
import { BackupNotFoundError } from '../repositories/BackupManager';

/**
 * 응답 표준화 & 에러 처리 (Day 6 - Task 3, δ=1440)
 *
 * Task1(userService)/Task2(loanService)가 각자 인라인으로 구현했던 동일한
 * "예외 → {code,message}" 매핑 패턴을 여기로 추출한다. 새 리포지토리 에러가
 * 추가되면 ERROR_CODE_MAP 한 곳만 수정하면 모든 서비스에 반영된다.
 */
export type ServiceResult<T> = { success: true; data: T } | { success: false; error: { code: string; message: string } };

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ErrorConstructor = new (...args: any[]) => Error;

const ERROR_CODE_MAP: [ErrorConstructor, string][] = [
  [DuplicateEmailError, 'DUPLICATE_EMAIL'],
  [ValidationError, 'VALIDATION_ERROR'],
  [OptimisticLockError, 'VERSION_CONFLICT'],
  [UserNotFoundError, 'USER_NOT_FOUND'],
  [LoanNotFoundError, 'LOAN_NOT_FOUND'],
  [OverpaymentError, 'OVERPAYMENT'],
  [TransactionNotFoundError, 'TRANSACTION_NOT_FOUND'],
  [BackupNotFoundError, 'BACKUP_NOT_FOUND'],
  [InvalidCredentialsError, 'INVALID_CREDENTIALS']
];

export function mapErrorToCode(error: unknown): { code: string; message: string } {
  for (const [ctor, code] of ERROR_CODE_MAP) {
    if (error instanceof ctor) return { code, message: error.message };
  }
  return { code: 'INTERNAL_ERROR', message: error instanceof Error ? error.message : String(error) };
}

export function toServiceResult<T>(fn: () => T): ServiceResult<T> {
  try {
    return { success: true, data: fn() };
  } catch (error) {
    return { success: false, error: mapErrorToCode(error) };
  }
}

export async function toServiceResultAsync<T>(fn: () => Promise<T>): Promise<ServiceResult<T>> {
  try {
    return { success: true, data: await fn() };
  } catch (error) {
    return { success: false, error: mapErrorToCode(error) };
  }
}
