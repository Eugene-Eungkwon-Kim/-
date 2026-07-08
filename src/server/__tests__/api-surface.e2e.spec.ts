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

  it('헬스체크 — 인증 불필요, DB 연결 상태 반환', async () => {
    const res = await app.inject({ method: 'GET', url: '/health' });
    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.status).toBe('ok');
    expect(body.db).toBe('connected');
  });

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

  it('대출금 상환 기록 — 소유자만 가능, 잘못된 대출 ID는 404', async () => {
    const { userId: userId1, token: token1 } = await registerAndLogin('payment-user1@example.com', 'User 1');
    const { token: token2 } = await registerAndLogin('payment-user2@example.com', 'User 2');

    // User 1이 대출 신청
    const loanRes = await app.inject({
      method: 'POST',
      url: '/api/loans',
      headers: authHeader(token1),
      payload: {
        userId: userId1,
        productId: 'standard-loan-1',
        originalAmount: 1000000,
        interestRate: 5,
        termMonths: 60,
        startDate: '2026-01-01'
      }
    });
    const loanId = loanRes.json().data.id;

    // User 1이 자신의 대출에 상환 기록 — 성공
    const paymentRes = await app.inject({
      method: 'POST',
      url: `/api/loans/${loanId}/payments`,
      headers: authHeader(token1),
      payload: { paymentDate: '2026-06-01', principal: 10000, interest: 5000 }
    });
    expect(paymentRes.statusCode).toBe(200);
    expect(paymentRes.json().data.currentBalance).toBeLessThan(1000000);

    // User 2가 User 1의 대출에 상환 기록 시도 — 403
    const unauthorizedRes = await app.inject({
      method: 'POST',
      url: `/api/loans/${loanId}/payments`,
      headers: authHeader(token2),
      payload: { paymentDate: '2026-06-01', principal: 10000, interest: 5000 }
    });
    expect(unauthorizedRes.statusCode).toBe(403);

    // 잘못된 대출 ID — 404
    const notFoundRes = await app.inject({
      method: 'POST',
      url: '/api/loans/nonexistent-loan/payments',
      headers: authHeader(token1),
      payload: { paymentDate: '2026-06-01', principal: 10000, interest: 5000 }
    });
    expect(notFoundRes.statusCode).toBe(404);
  });

  it('연체 감지 — 관리자만 가능', async () => {
    const { userId: adminId, token: adminToken } = await registerAndLogin('delinquency-admin@example.com', 'Admin');
    const { token: userToken } = await registerAndLogin('delinquency-user@example.com', 'User');

    // 일반 사용자 시도 — 403
    const userRes = await app.inject({
      method: 'POST',
      url: '/api/admin/delinquency-check',
      headers: authHeader(userToken),
      payload: { asOfDate: '2026-07-01' }
    });
    expect(userRes.statusCode).toBe(403);

    // 관리자로 승격
    db.prepare("UPDATE users SET role = 'admin' WHERE id = ?").run(adminId);
    const reloginRes = await app.inject({
      method: 'POST',
      url: '/api/auth/login',
      payload: { email: 'delinquency-admin@example.com', password: 'correct-horse' }
    });
    const newAdminToken = reloginRes.json().data.token;

    // 관리자 시도 — 성공 (빈 배열 반환)
    const adminCheckRes = await app.inject({
      method: 'POST',
      url: '/api/admin/delinquency-check',
      headers: authHeader(newAdminToken),
      payload: { asOfDate: '2026-07-01' }
    });
    expect(adminCheckRes.statusCode).toBe(200);
    expect(Array.isArray(adminCheckRes.json().data)).toBe(true);
  });

  it('백업 관련 엔드포인트 — 관리자 전용', async () => {
    const { userId: adminId, token: adminToken } = await registerAndLogin('backup-admin@example.com', 'Admin');
    const { token: userToken } = await registerAndLogin('backup-user@example.com', 'User');

    // 일반 사용자의 시도 — 403
    const userDueRes = await app.inject({
      method: 'GET',
      url: '/api/admin/backups/due?intervalHours=24&now=2026-07-01',
      headers: authHeader(userToken)
    });
    expect(userDueRes.statusCode).toBe(403);

    const userPruneRes = await app.inject({
      method: 'POST',
      url: '/api/admin/backups/prune',
      headers: authHeader(userToken),
      payload: { retentionDays: 30, now: '2026-07-01' }
    });
    expect(userPruneRes.statusCode).toBe(403);

    // 관리자로 승격
    db.prepare("UPDATE users SET role = 'admin' WHERE id = ?").run(adminId);
    const reloginRes = await app.inject({
      method: 'POST',
      url: '/api/auth/login',
      payload: { email: 'backup-admin@example.com', password: 'correct-horse' }
    });
    const newAdminToken = reloginRes.json().data.token;

    // 관리자의 시도 — 성공
    const adminDueRes = await app.inject({
      method: 'GET',
      url: '/api/admin/backups/due?intervalHours=24&now=2026-07-01',
      headers: authHeader(newAdminToken)
    });
    expect(adminDueRes.statusCode).toBe(200);
    expect(typeof adminDueRes.json().data).toBe('boolean');

    const adminPruneRes = await app.inject({
      method: 'POST',
      url: '/api/admin/backups/prune',
      headers: authHeader(newAdminToken),
      payload: { retentionDays: 30, now: '2026-07-01' }
    });
    expect(adminPruneRes.statusCode).toBe(200);
  });

  it('종단 통합 시나리오: 헬스체크 → 대출/상환 → 관리자 배치', async () => {
    // 1. 헬스체크 (인증 불필요)
    const healthRes = await app.inject({ method: 'GET', url: '/health' });
    expect(healthRes.statusCode).toBe(200);
    expect(healthRes.json().status).toBe('ok');

    // 2. 사용자 가입 및 로그인
    const { userId, token } = await registerAndLogin('e2e-user@example.com', 'E2E User');

    // 3. 대출 신청
    const loanRes = await app.inject({
      method: 'POST',
      url: '/api/loans',
      headers: authHeader(token),
      payload: {
        userId,
        productId: 'standard-loan-1',
        originalAmount: 5000000,
        interestRate: 4.5,
        termMonths: 120,
        startDate: '2026-01-01'
      }
    });
    expect(loanRes.statusCode).toBe(200);
    const loanId = loanRes.json().data.id;

    // 4. 상환 기록
    const paymentRes = await app.inject({
      method: 'POST',
      url: `/api/loans/${loanId}/payments`,
      headers: authHeader(token),
      payload: { paymentDate: '2026-02-01', principal: 50000, interest: 18000 }
    });
    expect(paymentRes.statusCode).toBe(200);
    expect(paymentRes.json().data.currentBalance).toBeLessThan(5000000);

    // 5. 관리자 승격 및 배치 작업 실행
    db.prepare("UPDATE users SET role = 'admin' WHERE id = ?").run(userId);
    const adminLoginRes = await app.inject({
      method: 'POST',
      url: '/api/auth/login',
      payload: { email: 'e2e-user@example.com', password: 'correct-horse' }
    });
    const adminToken = adminLoginRes.json().data.token;

    // 6. 연체 감지 배치 (현재 상환 상태는 양호)
    const delinquencyRes = await app.inject({
      method: 'POST',
      url: '/api/admin/delinquency-check',
      headers: authHeader(adminToken),
      payload: { asOfDate: '2026-02-15' }
    });
    expect(delinquencyRes.statusCode).toBe(200);
    expect(Array.isArray(delinquencyRes.json().data)).toBe(true);

    // 7. 백업 스케줄 확인 및 정리
    const backupDueRes = await app.inject({
      method: 'GET',
      url: '/api/admin/backups/due?intervalHours=24&now=2026-02-15',
      headers: authHeader(adminToken)
    });
    expect(backupDueRes.statusCode).toBe(200);

    const pruneRes = await app.inject({
      method: 'POST',
      url: '/api/admin/backups/prune',
      headers: authHeader(adminToken),
      payload: { retentionDays: 30, now: '2026-02-15' }
    });
    expect(pruneRes.statusCode).toBe(200);
  });
});
