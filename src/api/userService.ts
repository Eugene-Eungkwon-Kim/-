import type Database from 'better-sqlite3';
import { UserRepository } from '../repositories/UserRepository';
import { DuplicateEmailError, OptimisticLockError, UserNotFoundError, ValidationError } from '../repositories/errors';
import { CreditHistoryEntry, RegisterUserInput, UpdateUserInput, UserProfile } from '../types/user';

/**
 * 서비스 계층 (Day 6 - Task 1: 사용자 서비스, δ=1615)
 *
 * Day5의 UserRepository는 실패를 예외로 표현하지만, API 경계에서는 예외가
 * 호출자(테스트/향후 HTTP 핸들러)까지 전파되지 않고 값으로 나타나야 한다.
 * ServiceResult가 그 경계 역할을 한다. 에러 매핑 방식은 Task1/2에서 먼저
 * 각자 구현한 뒤 Task3에서 공용 유틸로 추출한다 (섣부른 추상화 방지).
 */
export type ServiceResult<T> = { success: true; data: T } | { success: false; error: { code: string; message: string } };

function mapUserError(error: unknown): { code: string; message: string } {
  if (error instanceof DuplicateEmailError) return { code: 'DUPLICATE_EMAIL', message: error.message };
  if (error instanceof ValidationError) return { code: 'VALIDATION_ERROR', message: error.message };
  if (error instanceof OptimisticLockError) return { code: 'VERSION_CONFLICT', message: error.message };
  if (error instanceof UserNotFoundError) return { code: 'USER_NOT_FOUND', message: error.message };
  return { code: 'INTERNAL_ERROR', message: error instanceof Error ? error.message : String(error) };
}

export function registerUser(db: Database.Database, input: RegisterUserInput): ServiceResult<UserProfile> {
  try {
    const repo = new UserRepository(db);
    return { success: true, data: repo.register(input) };
  } catch (error) {
    return { success: false, error: mapUserError(error) };
  }
}

export function getUserProfile(db: Database.Database, userId: string): ServiceResult<UserProfile> {
  try {
    const repo = new UserRepository(db);
    const profile = repo.getProfile(userId);
    if (!profile) {
      return { success: false, error: { code: 'USER_NOT_FOUND', message: `User not found: ${userId}` } };
    }
    return { success: true, data: profile };
  } catch (error) {
    return { success: false, error: mapUserError(error) };
  }
}

export function updateUserProfile(
  db: Database.Database,
  userId: string,
  updates: UpdateUserInput,
  expectedVersion: number
): ServiceResult<UserProfile> {
  try {
    const repo = new UserRepository(db);
    return { success: true, data: repo.updateProfile(userId, updates, expectedVersion) };
  } catch (error) {
    return { success: false, error: mapUserError(error) };
  }
}

export function getCreditHistory(db: Database.Database, userId: string): ServiceResult<CreditHistoryEntry[]> {
  try {
    const repo = new UserRepository(db);
    return { success: true, data: repo.getCreditHistory(userId) };
  } catch (error) {
    return { success: false, error: mapUserError(error) };
  }
}
