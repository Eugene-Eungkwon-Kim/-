import type Database from 'better-sqlite3';
import { UserRepository } from '../repositories/UserRepository';
import { InvalidCredentialsError, InvalidRefreshTokenError } from '../repositories/errors';
import { IssuedRefreshToken, RefreshTokenRepository, VerifiedRefreshToken } from '../repositories/RefreshTokenRepository';
import { UserProfile } from '../types/user';
import { ServiceResult, toServiceResult } from './errorMapping';
import { validateLogin } from '../validation/requestValidation';

/**
 * 인증 서비스 계층 (Day 8 - Task 2, δ=1535 / Day 9 - Task 3, δ=1155)
 *
 * JWT *서명*은 HTTP 전송 계층의 관심사이므로 여기서 다루지 않는다 (src/server/app.ts가
 * @fastify/jwt로 처리). 반면 "이 자격증명/리프레시 토큰이 유효한가, 누구의 것인가"는
 * 프레임워크에 독립적인 판단이라 여기서 다루며, 다른 서비스들과 동일하게 ServiceResult<T>를 반환한다.
 */
export function verifyCredentials(db: Database.Database, email: string, password: string): ServiceResult<UserProfile> {
  return toServiceResult(() => {
    validateLogin({ email, password });
    const profile = new UserRepository(db).verifyPassword(email, password);
    if (!profile) throw new InvalidCredentialsError();
    return profile;
  });
}

export function issueRefreshToken(db: Database.Database, userId: string): ServiceResult<IssuedRefreshToken> {
  return toServiceResult(() => new RefreshTokenRepository(db).issue(userId));
}

export function verifyRefreshToken(db: Database.Database, token: string): ServiceResult<VerifiedRefreshToken> {
  return toServiceResult(() => {
    const result = new RefreshTokenRepository(db).verify(token);
    if (!result) throw new InvalidRefreshTokenError();
    return result;
  });
}

export function revokeRefreshToken(db: Database.Database, token: string): ServiceResult<void> {
  return toServiceResult(() => {
    new RefreshTokenRepository(db).revoke(token);
  });
}
