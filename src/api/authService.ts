import type Database from 'better-sqlite3';
import { UserRepository } from '../repositories/UserRepository';
import { InvalidCredentialsError } from '../repositories/errors';
import { UserProfile } from '../types/user';
import { ServiceResult, toServiceResult } from './errorMapping';

/**
 * 인증 서비스 계층 (Day 8 - Task 2, δ=1535)
 *
 * JWT 발급은 HTTP 전송 계층의 관심사이므로 여기서 다루지 않는다 (src/server/app.ts가
 * @fastify/jwt로 처리). 이 서비스는 "자격증명이 유효한가"만 판단해 다른 서비스들과
 * 동일하게 프레임워크에 종속되지 않는 ServiceResult<T>를 반환한다.
 */
export function verifyCredentials(db: Database.Database, email: string, password: string): ServiceResult<UserProfile> {
  return toServiceResult(() => {
    const profile = new UserRepository(db).verifyPassword(email, password);
    if (!profile) throw new InvalidCredentialsError();
    return profile;
  });
}
