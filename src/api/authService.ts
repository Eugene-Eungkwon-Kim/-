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

/**
 * 취소된 토큰의 소유자를 함께 돌려준다 — 호출자가 그 사용자의 SSE 스트림을
 * 끊는 데 쓴다. 이미 취소됐거나 없는 토큰이면 userId는 null이다(로그아웃은
 * 멱등해야 하므로 실패로 보지 않는다).
 */
export async function revokeRefreshToken(
  pool: Pool,
  token: string
): Promise<ServiceResult<{ userId: string | null }>> {
  return toServiceResultAsync(async () => {
    const revoked = await new RefreshTokenRepository(pool).revoke(token);
    return { userId: revoked?.userId ?? null };
  });
}
