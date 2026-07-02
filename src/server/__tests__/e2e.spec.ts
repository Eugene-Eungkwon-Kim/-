import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { buildServer } from '@/server/app';
import type { FastifyInstance } from 'fastify';

/**
 * 종단 통합 테스트 (Day 8 - Task 6, δ=1085)
 *
 * Task1~5에서 개별적으로 검증한 조각들(비밀번호 해싱, 로그인, 인증 훅, 권한
 * 검사)을 하나의 연속된 사용자 여정으로 이어붙여, 실제 운영 흐름을 재현한다.
 */
describe('인증 & 권한 종단 시나리오 (Day 8 - Task 6)', () => {
  let db: Database.Database;
  let app: FastifyInstance;

  beforeEach(async () => {
    db = createDatabase(':memory:');
    app = await buildServer(db, { jwtSecret: 'test-secret' });
  });

  afterEach(() => {
    db.close();
  });

  it('회원가입 → 로그인 → 본인 리소스 접근 → 타인 리소스 차단 → 무효 토큰 차단', async () => {
    // 1. 회원가입
    const registerRes = await app.inject({
      method: 'POST',
      url: '/api/users',
      payload: { email: 'e2e-alice@example.com', name: 'E2E Alice', password: 'alice-secret-1234', creditProfile: { score: 780 } }
    });
    expect(registerRes.statusCode).toBe(200);
    const aliceId = registerRes.json().data.id;

    // 2. 로그인 → 토큰 발급
    const loginRes = await app.inject({
      method: 'POST',
      url: '/api/auth/login',
      payload: { email: 'e2e-alice@example.com', password: 'alice-secret-1234' }
    });
    expect(loginRes.statusCode).toBe(200);
    const aliceToken = loginRes.json().data.token;

    // 3. 본인 프로필 조회
    const profileRes = await app.inject({ method: 'GET', url: `/api/users/${aliceId}`, headers: { authorization: `Bearer ${aliceToken}` } });
    expect(profileRes.statusCode).toBe(200);
    expect(profileRes.json().data.email).toBe('e2e-alice@example.com');

    // 4. 대출 신청
    const loanRes = await app.inject({
      method: 'POST',
      url: '/api/loans',
      headers: { authorization: `Bearer ${aliceToken}` },
      payload: { userId: aliceId, productId: 'standard-loan-1', originalAmount: 300000000, interestRate: 3.2, termMonths: 240, startDate: '2026-01-01' }
    });
    expect(loanRes.statusCode).toBe(200);

    // 5. 본인 포트폴리오 조회 — 방금 신청한 대출이 보여야 함
    const portfolioRes = await app.inject({ method: 'GET', url: `/api/users/${aliceId}/loans`, headers: { authorization: `Bearer ${aliceToken}` } });
    expect(portfolioRes.statusCode).toBe(200);
    expect(portfolioRes.json().data.length).toBe(1);

    // 6. 두 번째 사용자(Bob) 등록 & 로그인
    await app.inject({ method: 'POST', url: '/api/users', payload: { email: 'e2e-bob@example.com', name: 'E2E Bob', password: 'bob-secret-1234' } });
    const bobLoginRes = await app.inject({ method: 'POST', url: '/api/auth/login', payload: { email: 'e2e-bob@example.com', password: 'bob-secret-1234' } });
    const bobToken = bobLoginRes.json().data.token;

    // 7. Bob이 Alice의 프로필에 접근 시도 → 403
    const crossAccessProfile = await app.inject({ method: 'GET', url: `/api/users/${aliceId}`, headers: { authorization: `Bearer ${bobToken}` } });
    expect(crossAccessProfile.statusCode).toBe(403);

    // 8. Bob이 Alice의 포트폴리오에 접근 시도 → 403
    const crossAccessPortfolio = await app.inject({ method: 'GET', url: `/api/users/${aliceId}/loans`, headers: { authorization: `Bearer ${bobToken}` } });
    expect(crossAccessPortfolio.statusCode).toBe(403);

    // 9. Bob이 Alice 명의로 대출 신청 시도 → 403
    const crossLoanApply = await app.inject({
      method: 'POST',
      url: '/api/loans',
      headers: { authorization: `Bearer ${bobToken}` },
      payload: { userId: aliceId, productId: 'p1', originalAmount: 50000000, interestRate: 3.0, termMonths: 60, startDate: '2026-01-01' }
    });
    expect(crossLoanApply.statusCode).toBe(403);

    // 10. 토큰 없이 접근 → 401
    const noTokenRes = await app.inject({ method: 'GET', url: `/api/users/${aliceId}` });
    expect(noTokenRes.statusCode).toBe(401);

    // 11. 무효한 토큰으로 접근 → 401
    const invalidTokenRes = await app.inject({ method: 'GET', url: `/api/users/${aliceId}`, headers: { authorization: 'Bearer garbage-token' } });
    expect(invalidTokenRes.statusCode).toBe(401);

    // 12. Alice의 토큰은 여전히 유효 (다른 사용자 검증이 Alice 세션에 영향 없음)
    const aliceStillWorksRes = await app.inject({ method: 'GET', url: `/api/users/${aliceId}`, headers: { authorization: `Bearer ${aliceToken}` } });
    expect(aliceStillWorksRes.statusCode).toBe(200);
  });
});
