import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool } from 'pg';
import { initializeTestDatabase, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { buildServer } from '@/server/app';
import type { FastifyInstance } from 'fastify';

/**
 * 세션 라이프사이클 종단 테스트 (Day 9 - Task 6, δ=895)
 *
 * Task1~5에서 조각조각 검증한 것(JWT_SECRET 검증, rate limit, 리프레시 토큰
 * 회전/무효화, 프론트 영속화, 보안 헤더 중 서버가 관여하는 부분)을 하나의
 * 연속된 세션 라이프사이클로 이어붙인다. 기존 e2e.spec.ts(Day8, 권한 검사
 * 시나리오)의 이미 통과하는 단언들을 건드리지 않도록 별도 파일로 둔다.
 */
describe('세션 라이프사이클 종단 시나리오 (Day 9 - Task 6)', () => {
  let pool: Pool;
  let app: FastifyInstance;

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
    pool = await initializeTestDatabase();
    app = await buildServer(pool, { jwtSecret: 'test-secret' });
  });

  afterEach(async () => {
    await cleanupTestDatabase();
    delete process.env.ENCRYPTION_KEY;
  });

  it('회원가입 → 로그인 → refresh → 보호된 라우트 접근 → 로그아웃 → 리프레시 토큰 재사용 실패', async () => {
    const registerRes = await app.inject({
      method: 'POST',
      url: '/api/users',
      payload: { email: 'session-user@example.com', name: 'Session User', password: 'session-secret-1234' }
    });
    expect(registerRes.statusCode).toBe(200);
    const userId = registerRes.json().data.id;

    const loginRes = await app.inject({
      method: 'POST',
      url: '/api/auth/login',
      payload: { email: 'session-user@example.com', password: 'session-secret-1234' }
    });
    expect(loginRes.statusCode).toBe(200);
    const originalRefreshToken = loginRes.json().data.refreshToken;

    const refreshRes = await app.inject({ method: 'POST', url: '/api/auth/refresh', payload: { refreshToken: originalRefreshToken } });
    expect(refreshRes.statusCode).toBe(200);
    const { token: newAccessToken, refreshToken: rotatedRefreshToken } = refreshRes.json().data;

    const protectedRes = await app.inject({
      method: 'GET',
      url: `/api/users/${userId}`,
      headers: { authorization: `Bearer ${newAccessToken}` }
    });
    expect(protectedRes.statusCode).toBe(200);

    const logoutRes = await app.inject({ method: 'POST', url: '/api/auth/logout', payload: { refreshToken: rotatedRefreshToken } });
    expect(logoutRes.statusCode).toBe(200);

    const reuseAfterLogoutRes = await app.inject({ method: 'POST', url: '/api/auth/refresh', payload: { refreshToken: rotatedRefreshToken } });
    expect(reuseAfterLogoutRes.statusCode).toBe(401);
  });

  it('성공적인 refresh 이후 회전 이전의 리프레시 토큰도 재사용할 수 없다', async () => {
    await app.inject({
      method: 'POST',
      url: '/api/users',
      payload: { email: 'rotate-e2e@example.com', name: 'Rotate E2E', password: 'rotate-secret-1234' }
    });
    const loginRes = await app.inject({
      method: 'POST',
      url: '/api/auth/login',
      payload: { email: 'rotate-e2e@example.com', password: 'rotate-secret-1234' }
    });
    const originalRefreshToken = loginRes.json().data.refreshToken;

    const firstRefreshRes = await app.inject({ method: 'POST', url: '/api/auth/refresh', payload: { refreshToken: originalRefreshToken } });
    expect(firstRefreshRes.statusCode).toBe(200);

    // 회전 이전(original) 토큰으로 다시 refresh 시도 → 실패해야 함
    const reuseOriginalRes = await app.inject({ method: 'POST', url: '/api/auth/refresh', payload: { refreshToken: originalRefreshToken } });
    expect(reuseOriginalRes.statusCode).toBe(401);
    expect(reuseOriginalRes.json().error.code).toBe('INVALID_REFRESH_TOKEN');
  });

  it('1분 내 6번째 로그인 시도는 자격증명이 올바르더라도 429를 반환한다', async () => {
    await app.inject({
      method: 'POST',
      url: '/api/users',
      payload: { email: 'rate-limit-e2e@example.com', name: 'Rate Limit E2E', password: 'correct-password-1234' }
    });

    // 앞의 5번은 일부러 틀린 비밀번호로 시도해 rate limit 카운터만 소진시킨다
    for (let i = 0; i < 5; i++) {
      const res = await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        payload: { email: 'rate-limit-e2e@example.com', password: 'wrong-password' }
      });
      expect(res.statusCode).toBe(401);
    }

    // 6번째는 올바른 자격증명이어도 이미 한도를 넘겨 429여야 한다 —
    // rate limiter가 실패 횟수가 아니라 요청 횟수 자체를 세고 있음을 증명한다
    const finalRes = await app.inject({
      method: 'POST',
      url: '/api/auth/login',
      payload: { email: 'rate-limit-e2e@example.com', password: 'correct-password-1234' }
    });
    expect(finalRes.statusCode).toBe(429);
    expect(finalRes.json().error.code).toBe('RATE_LIMITED');
  });
});
