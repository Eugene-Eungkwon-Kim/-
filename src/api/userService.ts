import type { Pool } from 'pg';
import { UserRepository } from '../repositories/UserRepository';
import { UserNotFoundError } from '../repositories/errors';
import { CreditHistoryEntry, RegisterUserInput, UpdateUserInput, UserProfile } from '../types/user';
import { ServiceResult, toServiceResultAsync } from './errorMapping';
import { validateUserRegistration } from '../validation/requestValidation';

export type { ServiceResult };

export async function registerUser(pool: Pool, input: RegisterUserInput): Promise<ServiceResult<UserProfile>> {
  return toServiceResultAsync(async () => {
    validateUserRegistration(input);
    return new UserRepository(pool).register(input);
  });
}

export async function getUserProfile(pool: Pool, userId: string): Promise<ServiceResult<UserProfile>> {
  return toServiceResultAsync(async () => {
    const profile = await new UserRepository(pool).getProfile(userId);
    if (!profile) throw new UserNotFoundError(userId);
    return profile;
  });
}

export async function updateUserProfile(
  pool: Pool,
  userId: string,
  updates: UpdateUserInput,
  expectedVersion: number
): Promise<ServiceResult<UserProfile>> {
  return toServiceResultAsync(async () => new UserRepository(pool).updateProfile(userId, updates, expectedVersion));
}

export async function getCreditHistory(pool: Pool, userId: string): Promise<ServiceResult<CreditHistoryEntry[]>> {
  return toServiceResultAsync(async () => new UserRepository(pool).getCreditHistory(userId));
}
