import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool } from 'pg';
import type { FastifyInstance } from 'fastify';
import { cleanupTestDatabase, initializeTestDatabase } from '@db/__tests__/testDatabase';
import { buildServer } from '@/server/app';
import { MemoryNotificationHub } from '@/notifications/notificationHub';
import { FinancialSnapshotRepository } from '@repositories/FinancialSnapshotRepository';

/**
 * Phase 15 - Section 3 (A-3, A-4): 이미 구현됐지만 라우트가 없던 서비스의 HTTP 노출.
 */
describe('분석 API 노출 (Section 3)', () => {
  let pool: Pool;
  let app: FastifyInstance;

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
    pool = await initializeTestDatabase();
    app = await buildServer(pool, { jwtSecret: 'test-secret', notificationHub: new MemoryNotificationHub() });
  });

  afterEach(async () => {
    await app.close();
    await cleanupTestDatabase();
    delete process.env.ENCRYPTION_KEY;
  });

  async function registerAndLogin(email: string): Promise<{ userId: string; token: string }> {
    const registerRes = await app.inject({
      method: 'POST',
      url: '/api/users',
      payload: { email, name: 'Analytics User', password: 'correct-horse' }
    });
    const userId = registerRes.json().data.id;

    const loginRes = await app.inject({ method: 'POST', url: '/api/auth/login', payload: { email, password: 'correct-horse' } });
    return { userId, token: loginRes.json().data.token };
  }

  function auth(token: string) {
    return { authorization: `Bearer ${token}` };
  }

  async function recordTransaction(userId: string, token: string, amount: number, occurredAt: string): Promise<void> {
    const res = await app.inject({
      method: 'POST',
      url: '/api/transactions',
      headers: auth(token),
      payload: { userId, transactionType: 'deposit', amount, occurredAt }
    });
    expect(res.statusCode).toBe(200);
  }

  async function recordSnapshot(userId: string, creditScore: number, snapshotDate: string): Promise<void> {
    await new FinancialSnapshotRepository(pool).recordSnapshot({
      userId,
      snapshotDate,
      creditScore,
      financialHealthScore: 70,
      healthGrade: 'B',
      debtToIncomeRatio: 0.3,
      assetToDebtRatio: 2,
      monthlySurplus: 500_000,
      riskScore: 30,
      riskLevel: 'low',
      probabilityOfDefault: 0.05
    });
  }

  describe('GET /api/users/:userId/transactions/trend', () => {
    it('월별 집계를 오름차순으로 반환한다', async () => {
      const { userId, token } = await registerAndLogin('trend@example.com');
      await recordTransaction(userId, token, 1000, '2026-01-15');
      await recordTransaction(userId, token, 2000, '2026-01-20');
      await recordTransaction(userId, token, 3000, '2026-02-10');

      const res = await app.inject({ method: 'GET', url: `/api/users/${userId}/transactions/trend`, headers: auth(token) });

      expect(res.statusCode).toBe(200);
      const points = res.json().data;
      expect(points.map((p: { month: string }) => p.month)).toEqual(['2026-01', '2026-02']);
      expect(points[0].transactionCount).toBe(2);
      expect(points[0].totalAmount).toBe(3000);
    });

    it('타인의 추이 조회는 403이다', async () => {
      const owner = await registerAndLogin('t-owner@example.com');
      const other = await registerAndLogin('t-other@example.com');

      const res = await app.inject({
        method: 'GET',
        url: `/api/users/${owner.userId}/transactions/trend`,
        headers: auth(other.token)
      });
      expect(res.statusCode).toBe(403);
    });
  });

  describe('POST /api/users/:userId/snapshots/compare', () => {
    it('두 시점의 지표 변화를 반환한다', async () => {
      const { userId, token } = await registerAndLogin('compare@example.com');
      await recordSnapshot(userId, 600, '2026-01-01');
      await recordSnapshot(userId, 700, '2026-02-01');

      const res = await app.inject({
        method: 'POST',
        url: `/api/users/${userId}/snapshots/compare`,
        headers: auth(token),
        payload: { fromDate: '2026-01-01', toDate: '2026-02-01' }
      });

      expect(res.statusCode).toBe(200);
      const comparisons = res.json().data;
      const credit = comparisons.find((c: { metric: string }) => c.metric === 'creditScore');
      expect(credit.change).toBe(100);
      expect(credit.from.value).toBe(600);
      expect(credit.to.value).toBe(700);
    });

    it('없는 날짜를 지정하면 404와 SNAPSHOT_NOT_FOUND를 반환한다', async () => {
      const { userId, token } = await registerAndLogin('compare404@example.com');
      await recordSnapshot(userId, 600, '2026-01-01');

      const res = await app.inject({
        method: 'POST',
        url: `/api/users/${userId}/snapshots/compare`,
        headers: auth(token),
        payload: { fromDate: '2026-01-01', toDate: '2099-12-31' }
      });

      expect(res.statusCode).toBe(404);
      expect(res.json().error.code).toBe('SNAPSHOT_NOT_FOUND');
    });

    it('타인의 스냅샷 비교는 403이다', async () => {
      const owner = await registerAndLogin('c-owner@example.com');
      const other = await registerAndLogin('c-other@example.com');

      const res = await app.inject({
        method: 'POST',
        url: `/api/users/${owner.userId}/snapshots/compare`,
        headers: auth(other.token),
        payload: { fromDate: '2026-01-01', toDate: '2026-02-01' }
      });
      expect(res.statusCode).toBe(403);
    });
  });

  describe('GET /api/admin/transactions/audit-log', () => {
    it('비관리자는 403이다', async () => {
      const { token } = await registerAndLogin('audit-user@example.com');

      const res = await app.inject({ method: 'GET', url: '/api/admin/transactions/audit-log', headers: auth(token) });
      expect(res.statusCode).toBe(403);
    });

    it('관리자는 거래 감사 로그를 조회한다', async () => {
      const { userId, token } = await registerAndLogin('audit-admin@example.com');
      await recordTransaction(userId, token, 5000, '2026-01-15');

      await pool.query('UPDATE users SET role = $1 WHERE id = $2', ['admin', userId]);
      const loginRes = await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        payload: { email: 'audit-admin@example.com', password: 'correct-horse' }
      });
      const adminToken = loginRes.json().data.token;

      const res = await app.inject({ method: 'GET', url: '/api/admin/transactions/audit-log', headers: auth(adminToken) });

      expect(res.statusCode).toBe(200);
      expect(Array.isArray(res.json().data)).toBe(true);
    });
  });

  describe('GET /api/users/:userId/dashboard', () => {
    it('요약·추이·최신 스냅샷·활성 경고를 한 번에 반환한다', async () => {
      const { userId, token } = await registerAndLogin('dash@example.com');
      await recordTransaction(userId, token, 1000, '2026-01-15');
      await recordSnapshot(userId, 480, '2026-01-01'); // creditScore critical

      const res = await app.inject({ method: 'GET', url: `/api/users/${userId}/dashboard`, headers: auth(token) });

      expect(res.statusCode).toBe(200);
      const view = res.json().data;
      expect(view.summary.transactionCount).toBe(1);
      expect(view.monthlyTrend).toHaveLength(1);
      expect(view.latestSnapshot.creditScore).toBe(480);
      expect(view.activeAlerts.some((a: { metric: string }) => a.metric === 'creditScore')).toBe(true);
      expect(view.degraded).toEqual([]);
    });

    it('데이터가 없는 신규 사용자도 빈 뷰를 받는다', async () => {
      const { userId, token } = await registerAndLogin('dash-empty@example.com');

      const res = await app.inject({ method: 'GET', url: `/api/users/${userId}/dashboard`, headers: auth(token) });

      expect(res.statusCode).toBe(200);
      const view = res.json().data;
      expect(view.latestSnapshot).toBeNull();
      expect(view.activeAlerts).toEqual([]);
      expect(view.degraded).toEqual([]);
    });

    it('타인의 대시보드는 403이다', async () => {
      const owner = await registerAndLogin('d-owner@example.com');
      const other = await registerAndLogin('d-other@example.com');

      const res = await app.inject({
        method: 'GET',
        url: `/api/users/${owner.userId}/dashboard`,
        headers: auth(other.token)
      });
      expect(res.statusCode).toBe(403);
    });
  });
});
