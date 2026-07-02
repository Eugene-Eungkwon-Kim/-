import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { buildServer } from '@/server/app';
import type { FastifyInstance } from 'fastify';

/**
 * API 서프리스 종단 시나리오 (Day 10 - Task 5, δ=880)
 *
 * Task1~4에서 노출한 거래/금융분석/관리자 라우트를 하나의 연속된 흐름으로
 * 이어붙인다. Day8/9의 기존 e2e 파일들이 이미 통과하는 단언을 건드리지
 * 않도록 별도 파일로 둔다.
 */
describe('API 서프리스 종단 시나리오 (Day 10 - Task 5)', () => {
  let db: Database.Database;
  let app: FastifyInstance;
  let backupDir: string;

  beforeEach(async () => {
    db = createDatabase(':memory:');
    backupDir = fs.mkdtempSync(path.join(os.tmpdir(), 'maars-api-surface-e2e-'));
    app = await buildServer(db, { jwtSecret: 'test-secret', backupDir });
  });

  afterEach(() => {
    db.close();
    fs.rmSync(backupDir, { recursive: true, force: true });
  });

  async function registerAndLogin(email: string, name: string): Promise<{ userId: string; token: string }> {
    const registerRes = await app.inject({ method: 'POST', url: '/api/users', payload: { email, name, password: 'correct-horse' } });
    const userId = registerRes.json().data.id;
    const loginRes = await app.inject({ method: 'POST', url: '/api/auth/login', payload: { email, password: 'correct-horse' } });
    return { userId, token: loginRes.json().data.token };
  }

  function authHeader(token: string) {
    return { authorization: `Bearer ${token}` };
  }

  it('등록 → 거래 기록 → 신용시뮬레이션(스냅샷 자동저장) → 추세 조회', async () => {
    const { userId, token } = await registerAndLogin('surface-user@example.com', 'Surface User');

    const txnRes = await app.inject({
      method: 'POST',
      url: '/api/transactions',
      headers: authHeader(token),
      payload: { userId, transactionType: 'deposit', amount: 500000, occurredAt: '2026-01-01' }
    });
    expect(txnRes.statusCode).toBe(200);

    const riskRes = await app.inject({
      method: 'POST',
      url: '/api/analytics/risk-assessment',
      headers: authHeader(token),
      payload: { userId, snapshotDate: '2026-01-01' }
    });
    expect(riskRes.statusCode).toBe(200);

    const trendRes = await app.inject({
      method: 'GET',
      url: `/api/users/${userId}/snapshots/trend/riskScore`,
      headers: authHeader(token)
    });
    expect(trendRes.statusCode).toBe(200);
    expect(trendRes.json().data.points.length).toBe(1);

    const summaryRes = await app.inject({ method: 'GET', url: `/api/users/${userId}/transactions/summary`, headers: authHeader(token) });
    expect(summaryRes.statusCode).toBe(200);
    expect(summaryRes.json().data.transactionCount).toBe(1);
  });

  it('일반 사용자는 관리자 라우트에서 403, admin 승격 후에는 통과한다', async () => {
    const { userId, token: userToken } = await registerAndLogin('surface-promote@example.com', 'Surface Promote');

    const beforeRes = await app.inject({ method: 'GET', url: '/api/admin/backups', headers: authHeader(userToken) });
    expect(beforeRes.statusCode).toBe(403);

    db.prepare("UPDATE users SET role = 'admin' WHERE id = ?").run(userId);
    const reloginRes = await app.inject({
      method: 'POST',
      url: '/api/auth/login',
      payload: { email: 'surface-promote@example.com', password: 'correct-horse' }
    });
    const adminToken = reloginRes.json().data.token;

    const afterRes = await app.inject({ method: 'GET', url: '/api/admin/backups', headers: authHeader(adminToken) });
    expect(afterRes.statusCode).toBe(200);
  });
});
