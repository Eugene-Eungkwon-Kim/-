import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { buildServer } from '@/server/app';
import type { FastifyInstance } from 'fastify';

describe('Fastify app (프론트엔드 연동용 최소 HTTP 서버)', () => {
  let db: Database.Database;
  let app: FastifyInstance;

  beforeEach(() => {
    db = createDatabase(':memory:');
    app = buildServer(db);
  });

  afterEach(() => {
    db.close();
  });

  it('POST /api/users - 정상 등록 시 200과 사용자 정보를 반환한다', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/users',
      payload: { email: 'demo@example.com', name: 'Demo User', creditProfile: { score: 750 } }
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.success).toBe(true);
    expect(body.data.email).toBe('demo@example.com');
  });

  it('POST /api/users - 중복 이메일은 409를 반환한다', async () => {
    await app.inject({ method: 'POST', url: '/api/users', payload: { email: 'dup@example.com', name: 'A' } });
    const res = await app.inject({ method: 'POST', url: '/api/users', payload: { email: 'dup@example.com', name: 'B' } });

    expect(res.statusCode).toBe(409);
    expect(res.json().error.code).toBe('DUPLICATE_EMAIL');
  });

  it('GET /api/users/:userId - 존재하지 않는 사용자는 404를 반환한다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/users/no-such-user' });
    expect(res.statusCode).toBe(404);
    expect(res.json().error.code).toBe('USER_NOT_FOUND');
  });

  it('POST /api/loans → GET /api/users/:userId/loans - 등록한 대출이 포트폴리오에 나타난다', async () => {
    const userRes = await app.inject({ method: 'POST', url: '/api/users', payload: { email: 'loan@example.com', name: 'Loan User' } });
    const userId = userRes.json().data.id;

    const loanRes = await app.inject({
      method: 'POST',
      url: '/api/loans',
      payload: { userId, productId: 'standard-loan-1', originalAmount: 300000000, interestRate: 3.2, termMonths: 240, startDate: '2026-01-01' }
    });
    expect(loanRes.statusCode).toBe(200);

    const portfolioRes = await app.inject({ method: 'GET', url: `/api/users/${userId}/loans` });
    expect(portfolioRes.statusCode).toBe(200);
    const portfolio = portfolioRes.json();
    expect(portfolio.data.length).toBe(1);
    expect(portfolio.data[0].currentBalance).toBe(300000000);
  });

  it('GET /api/users/:userId/loans/summary - 포트폴리오 요약을 반환한다', async () => {
    const userRes = await app.inject({ method: 'POST', url: '/api/users', payload: { email: 'summary@example.com', name: 'Summary User' } });
    const userId = userRes.json().data.id;
    await app.inject({
      method: 'POST',
      url: '/api/loans',
      payload: { userId, productId: 'p1', originalAmount: 100000000, interestRate: 3.2, termMonths: 120, startDate: '2026-01-01' }
    });

    const res = await app.inject({ method: 'GET', url: `/api/users/${userId}/loans/summary` });
    expect(res.statusCode).toBe(200);
    expect(res.json().data.loanCount).toBe(1);
  });

  it('POST /api/loans - 존재하지 않는 사용자는 404를 반환한다', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/loans',
      payload: { userId: 'no-such-user', productId: 'p1', originalAmount: 100000000, interestRate: 3.2, termMonths: 120, startDate: '2026-01-01' }
    });
    expect(res.statusCode).toBe(404);
    expect(res.json().error.code).toBe('USER_NOT_FOUND');
  });

  describe('POST /api/auth/login (Day 8 - Task 2, δ=1535)', () => {
    it('올바른 자격증명으로 로그인하면 JWT와 사용자 정보를 반환한다', async () => {
      await app.inject({
        method: 'POST',
        url: '/api/users',
        payload: { email: 'login@example.com', name: 'Login User', password: 'correct-horse' }
      });

      const res = await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        payload: { email: 'login@example.com', password: 'correct-horse' }
      });

      expect(res.statusCode).toBe(200);
      const body = res.json();
      expect(body.success).toBe(true);
      expect(typeof body.data.token).toBe('string');
      expect(body.data.user.email).toBe('login@example.com');
    });

    it('잘못된 비밀번호는 401을 반환한다', async () => {
      await app.inject({
        method: 'POST',
        url: '/api/users',
        payload: { email: 'wrong-pw@example.com', name: 'Wrong PW', password: 'correct-horse' }
      });

      const res = await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        payload: { email: 'wrong-pw@example.com', password: 'incorrect' }
      });

      expect(res.statusCode).toBe(401);
      expect(res.json().error.code).toBe('INVALID_CREDENTIALS');
    });

    it('발급된 토큰은 서버가 검증 가능한 형태다', async () => {
      await app.inject({
        method: 'POST',
        url: '/api/users',
        payload: { email: 'verify-token@example.com', name: 'Verify Token', password: 'correct-horse' }
      });
      const loginRes = await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        payload: { email: 'verify-token@example.com', password: 'correct-horse' }
      });
      const { token } = loginRes.json().data;

      const decoded = app.jwt.verify(token) as { userId: string };
      expect(typeof decoded.userId).toBe('string');
    });
  });
});
