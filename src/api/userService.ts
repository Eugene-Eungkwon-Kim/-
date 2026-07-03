import type Database from 'better-sqlite3';
import { UserRepository } from '../repositories/UserRepository';
import { UserNotFoundError } from '../repositories/errors';
import { CreditHistoryEntry, RegisterUserInput, UpdateUserInput, UserProfile } from '../types/user';
import { ServiceResult, toServiceResult } from './errorMapping';
import { validateUserRegistration } from '../validation/requestValidation';

export type { ServiceResult };

/**
 * 사용자 서비스 계층 (Day 6 - Task 1, δ=1615)
 *
 * Day5의 UserRepository는 실패를 예외로 표현하지만, API 경계에서는 예외가
 * 호출자까지 전파되지 않고 값으로 나타나야 한다. 에러 매핑은 errorMapping.ts의
 * 공용 유틸(Task3)에 위임한다.
 */
export function registerUser(db: Database.Database, input: RegisterUserInput): ServiceResult<UserProfile> {
  return toServiceResult(() => {
    validateUserRegistration(input);
    return new UserRepository(db).register(input);
  });
}

export function getUserProfile(db: Database.Database, userId: string): ServiceResult<UserProfile> {
  return toServiceResult(() => {
    const profile = new UserRepository(db).getProfile(userId);
    if (!profile) throw new UserNotFoundError(userId);
    return profile;
  });
}

export function updateUserProfile(
  db: Database.Database,
  userId: string,
  updates: UpdateUserInput,
  expectedVersion: number
): ServiceResult<UserProfile> {
  return toServiceResult(() => new UserRepository(db).updateProfile(userId, updates, expectedVersion));
}

export function getCreditHistory(db: Database.Database, userId: string): ServiceResult<CreditHistoryEntry[]> {
  return toServiceResult(() => new UserRepository(db).getCreditHistory(userId));
}
