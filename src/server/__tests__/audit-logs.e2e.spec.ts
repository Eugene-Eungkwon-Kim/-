import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type { Pool } from 'pg';
import { initializeTestDatabase, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { buildServer } from '@/server/app';
import { AuditLogger, AuditAction } from '../../audit/auditLogger';
import type { FastifyInstance } from 'fastify';

/**
 * Day 13 - Task G (δ=550): 감사 로그 API 종단 테스트
 *
 * 감사 로그 조회 엔드포인트의 권한 검증, 필터링, 페이지네이션을 테스트한다.
 */
describe('Audit Logs API (Day 13 - Task G)', () => {
  let pool: Pool;
  let app: FastifyInstance;
  let backupDir: string;
  let auditLogger: AuditLogger;

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
    pool = await initializeTestDatabase();
    backupDir = fs.mkdtempSync(path.join(os.tmpdir(), 'maars-audit-e2e-'));
    app = await buildServer(pool, { jwtSecret: 'test-secret', backupDir });
    auditLogger = new AuditLogger(pool);
  });

  afterEach(async () => {
    fs.rmSync(backupDir, { recursive: true, force: true });
    await cleanupTestDatabase();
    delete process.env.ENCRYPTION_KEY;
  });

  async function registerAndLogin(email: string, name: string): Promise<{ userId: string; token: string }> {
    const registerRes = await app.inject({ method: 'POST', url: '/api/users', payload: { email, name, password: 'test-password-123' } });
    const userId = registerRes.json().data.id;
    const loginRes = await app.inject({ method: 'POST', url: '/api/auth/login', payload: { email, password: 'test-password-123' } });
    return { userId, token: loginRes.json().data.token };
  }

  function authHeader(token: string) {
    return { authorization: `Bearer ${token}` };
  }

  describe('권한 검증', () => {
    it('일반 사용자는 감사 로그 조회 불가 (403)', async () => {
      const { token } = await registerAndLogin('user@example.com', 'Regular User');

      const res = await app.inject({
        method: 'GET',
        url: '/api/admin/audit-logs',
        headers: authHeader(token)
      });

      expect(res.statusCode).toBe(403);
    });

    it('관리자는 감사 로그를 조회할 수 있다', async () => {
      const { userId } = await registerAndLogin('admin@example.com', 'Admin User');
      await pool.query("UPDATE users SET role = $1 WHERE id = $2", ['admin', userId]);

      // 관리자로 재로그인
      const loginRes = await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        payload: { email: 'admin@example.com', password: 'test-password-123' }
      });
      const adminToken = loginRes.json().data.token;

      const res = await app.inject({
        method: 'GET',
        url: '/api/admin/audit-logs',
        headers: authHeader(adminToken)
      });

      expect(res.statusCode).toBe(200);
      expect(res.json().data).toHaveProperty('logs');
      expect(res.json().data).toHaveProperty('total');
    });
  });

  describe('감사 로그 조회', () => {
    beforeEach(async () => {
      // 테스트용 로그를 추가한다
      const testUserId = 'test-user-id';

      // 사용자가 없으므로 먼저 users 테이블에 삽입
      try {
        await pool.query(
          "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
          [testUserId, 'test@example.com', 'Test User']
        );
      } catch (err) {
        // Ignore duplicate key errors - user may already exist
        if (!(err instanceof Error) || !err.message.includes('duplicate')) throw err;
      }

      auditLogger.log({
        userId: testUserId,
        action: AuditAction.CREATE,
        resourceType: 'user',
        resourceId: 'user-1',
        changesBefore: null,
        changesAfter: { email: 'user1@example.com' },
        metadataIp: '192.168.1.1',
        status: 'success',
        errorMessage: null
      });

      auditLogger.log({
        userId: testUserId,
        action: AuditAction.UPDATE,
        resourceType: 'loan',
        resourceId: 'loan-1',
        changesBefore: { status: 'active' },
        changesAfter: { status: 'repaid' },
        metadataIp: '192.168.1.2',
        status: 'success',
        errorMessage: null
      });

      auditLogger.log({
        userId: testUserId,
        action: AuditAction.PAYMENT,
        resourceType: 'loan',
        resourceId: 'loan-1',
        changesBefore: { balance: 100000 },
        changesAfter: { balance: 90000 },
        metadataIp: null,
        status: 'success',
        errorMessage: null
      });
    });

    it('모든 감사 로그를 조회할 수 있다', async () => {
      const { userId } = await registerAndLogin('admin@example.com', 'Admin User');
      await pool.query("UPDATE users SET role = $1 WHERE id = $2", ['admin', userId]);

      const loginRes = await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        payload: { email: 'admin@example.com', password: 'test-password-123' }
      });
      const adminToken = loginRes.json().data.token;

      const res = await app.inject({
        method: 'GET',
        url: '/api/admin/audit-logs',
        headers: authHeader(adminToken)
      });

      expect(res.statusCode).toBe(200);
      expect(res.json().data.logs).toBeInstanceOf(Array);
      expect(res.json().data.total).toBeGreaterThan(0);
    });

    it('페이지네이션을 지원한다', async () => {
      const { userId } = await registerAndLogin('admin@example.com', 'Admin User');
      await pool.query("UPDATE users SET role = $1 WHERE id = $2", ['admin', userId]);

      const loginRes = await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        payload: { email: 'admin@example.com', password: 'test-password-123' }
      });
      const adminToken = loginRes.json().data.token;

      const page1 = await app.inject({
        method: 'GET',
        url: '/api/admin/audit-logs?limit=2&offset=0',
        headers: authHeader(adminToken)
      });

      const page2 = await app.inject({
        method: 'GET',
        url: '/api/admin/audit-logs?limit=2&offset=2',
        headers: authHeader(adminToken)
      });

      expect(page1.statusCode).toBe(200);
      expect(page2.statusCode).toBe(200);
      expect(page1.json().data.limit).toBe(2);
      expect(page1.json().data.offset).toBe(0);
      expect(page2.json().data.offset).toBe(2);
    });

    it('액션으로 필터링할 수 있다', async () => {
      const { userId } = await registerAndLogin('admin@example.com', 'Admin User');
      await pool.query("UPDATE users SET role = $1 WHERE id = $2", ['admin', userId]);

      const loginRes = await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        payload: { email: 'admin@example.com', password: 'test-password-123' }
      });
      const adminToken = loginRes.json().data.token;

      const res = await app.inject({
        method: 'GET',
        url: '/api/admin/audit-logs?action=PAYMENT',
        headers: authHeader(adminToken)
      });

      expect(res.statusCode).toBe(200);
      const logs = res.json().data.logs;
      expect(logs.every((log: any) => log.action === 'PAYMENT')).toBe(true);
    });

    it('리소스 타입으로 필터링할 수 있다', async () => {
      const { userId } = await registerAndLogin('admin@example.com', 'Admin User');
      await pool.query("UPDATE users SET role = $1 WHERE id = $2", ['admin', userId]);

      const loginRes = await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        payload: { email: 'admin@example.com', password: 'test-password-123' }
      });
      const adminToken = loginRes.json().data.token;

      const res = await app.inject({
        method: 'GET',
        url: '/api/admin/audit-logs?resourceType=loan',
        headers: authHeader(adminToken)
      });

      expect(res.statusCode).toBe(200);
      const logs = res.json().data.logs;
      expect(logs.every((log: any) => log.resourceType === 'loan')).toBe(true);
    });
  });

  describe('사용자별 감사 로그', () => {
    beforeEach(async () => {
      const testUserId = 'test-user-id';
      try {
        await pool.query(
          "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
          [testUserId, 'test@example.com', 'Test User']
        );
      } catch (err) {
        if (!(err instanceof Error) || !err.message.includes('duplicate')) throw err;
      }

      for (let i = 0; i < 3; i++) {
        auditLogger.log({
          userId: testUserId,
          action: AuditAction.CREATE,
          resourceType: 'loan',
          resourceId: `loan-${i}`,
          changesBefore: null,
          changesAfter: { amount: 1000000 * (i + 1) },
          metadataIp: null,
          status: 'success',
          errorMessage: null
        });
      }
    });

    it('특정 사용자의 감사 로그를 조회할 수 있다', async () => {
      const { userId } = await registerAndLogin('admin@example.com', 'Admin User');
      await pool.query("UPDATE users SET role = $1 WHERE id = $2", ['admin', userId]);

      const loginRes = await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        payload: { email: 'admin@example.com', password: 'test-password-123' }
      });
      const adminToken = loginRes.json().data.token;

      const res = await app.inject({
        method: 'GET',
        url: '/api/admin/audit-logs/user/test-user-id',
        headers: authHeader(adminToken)
      });

      expect(res.statusCode).toBe(200);
      const logs = res.json().data.logs;
      expect(logs.length).toBe(3);
      expect(logs.every((log: any) => log.userId === 'test-user-id')).toBe(true);
    });
  });

  describe('리소스 변경 이력', () => {
    beforeEach(async () => {
      const testUserId = 'test-user-id';
      try {
        await pool.query(
          "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
          [testUserId, 'test@example.com', 'Test User']
        );
      } catch (err) {
        if (!(err instanceof Error) || !err.message.includes('duplicate')) throw err;
      }

      auditLogger.log({
        userId: testUserId,
        action: AuditAction.CREATE,
        resourceType: 'loan',
        resourceId: 'loan-1',
        changesBefore: null,
        changesAfter: { amount: 1000000, status: 'active' },
        metadataIp: null,
        status: 'success',
        errorMessage: null
      });

      auditLogger.log({
        userId: testUserId,
        action: AuditAction.UPDATE,
        resourceType: 'loan',
        resourceId: 'loan-1',
        changesBefore: { status: 'active' },
        changesAfter: { status: 'repaid' },
        metadataIp: null,
        status: 'success',
        errorMessage: null
      });
    });

    it('특정 리소스의 모든 변경 이력을 조회할 수 있다', async () => {
      const { userId } = await registerAndLogin('admin@example.com', 'Admin User');
      await pool.query("UPDATE users SET role = $1 WHERE id = $2", ['admin', userId]);

      const loginRes = await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        payload: { email: 'admin@example.com', password: 'test-password-123' }
      });
      const adminToken = loginRes.json().data.token;

      const res = await app.inject({
        method: 'GET',
        url: '/api/admin/audit-logs/resource/loan-1',
        headers: authHeader(adminToken)
      });

      expect(res.statusCode).toBe(200);
      const logs = res.json().data;
      expect(logs).toBeInstanceOf(Array);
      expect(logs.length).toBe(2);
      expect(logs.every((log: any) => log.resourceId === 'loan-1')).toBe(true);
    });
  });
});
