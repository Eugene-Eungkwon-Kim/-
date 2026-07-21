import type { Pool } from 'pg';
import { UserRepository } from '../repositories/UserRepository';
import { InvalidCredentialsError, InvalidRefreshTokenError } from '../repositories/errors';
import { IssuedRefreshToken, RefreshTokenRepository, VerifiedRefreshToken } from '../repositories/RefreshTokenRepository';
import { UserProfile } from '../types/user';
import { ServiceResult, toServiceResultAsync } from './errorMapping';
import { validateLogin } from '../validation/requestValidation';

export async function verifyCredentials(pool: Pool, email: string, password: string): Promise<ServiceResult<UserProfile>> {
  return toServiceResultAsync(async () => {
    validateLogin({ email, password });
    const profile = await new UserRepository(pool).verifyPassword(email, password);
    if (!profile) throw new InvalidCredentialsError();
    return profile;
  });
}

export async function issueRefreshToken(pool: Pool, userId: string): Promise<ServiceResult<IssuedRefreshToken>> {
  return toServiceResultAsync(async () => new RefreshTokenRepository(pool).issue(userId));
}

export async function verifyRefreshToken(pool: Pool, token: string): Promise<ServiceResult<VerifiedRefreshToken>> {
  return toServiceResultAsync(async () => {
    const result = await new RefreshTokenRepository(pool).verify(token);
    if (!result) throw new InvalidRefreshTokenError();
    return result;
  });
}

export async function revokeRefreshToken(pool: Pool, token: string): Promise<ServiceResult<void>> {
  return toServiceResultAsync(async () => {
    await new RefreshTokenRepository(pool).revoke(token);
  });
}
