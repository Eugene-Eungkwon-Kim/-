import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { buildServer } from '@/server/app';
import type { FastifyInstance } from 'fastify';
import {
  calculateMetrics,
  simulateConcurrentLoad,
  formatMetricsTable,
  type LoadTestResult,
} from './utils/performanceUtils';

/**
 * Day 12 - Task E (δ=800): 성능 기준 설정 (Performance Benchmarking)
 *
 * Baseline performance measurement for critical API endpoints.
 * Tests measure response times under various load conditions.
 */
describe('Performance Benchmarks (Day 12 - Task E, δ=800)', () => {
  let db: Database.Database;
  let app: FastifyInstance;
  let backupDir: string;
  const results: LoadTestResult[] = [];

  beforeEach(async () => {
    db = createDatabase(':memory:');
    backupDir = fs.mkdtempSync(path.join(os.tmpdir(), 'maars-perf-spec-'));
    app = await buildServer(db, { jwtSecret: 'test-secret', backupDir });
  });

  afterEach(() => {
    db.close();
    fs.rmSync(backupDir, { recursive: true, force: true });
  });

  // Helper to register a user and get auth token
  async function registerAndLogin(email: string): Promise<{ userId: string; token: string }> {
    const registerRes = await app.inject({
      method: 'POST',
      url: '/api/users',
      payload: { email, name: 'Test User', password: 'test-password-123' },
    });
    const userId = registerRes.json().data.id;

    const loginRes = await app.inject({
      method: 'POST',
      url: '/api/auth/login',
      payload: { email, password: 'test-password-123' },
    });
    const token = loginRes.json().data.token;

    return { userId, token };
  }

  describe('E1: User Registration Performance', () => {
    it('should register single user in acceptable time', async () => {
      const startTime = performance.now();
      const res = await app.inject({
        method: 'POST',
        url: '/api/users',
        payload: { email: 'single-user@example.com', name: 'Single User', password: 'test-password-123' },
      });
      const latency = performance.now() - startTime;

      expect(res.statusCode).toBe(200);
      expect(latency).toBeLessThan(300); // Single request should be < 300ms (includes bcrypt hashing)
    });

    it('should handle concurrent registrations with acceptable latency', async () => {
      const result = await simulateConcurrentLoad(
        async (config: any) => {
          const startTime = performance.now();
          const res = await app.inject(config);
          return { statusCode: res.statusCode, latency: performance.now() - startTime };
        },
        {
          endpoint: '/api/users',
          method: 'POST',
          concurrency: 10,
          totalRequests: 20,
          requestFactory: (index) => ({
            method: 'POST',
            url: '/api/users',
            payload: {
              email: `user-${Date.now()}-${index}@example.com`,
              name: `User ${index}`,
              password: 'test-password-123',
            },
          }),
        }
      );

      results.push(result);
      expect(result.successCount).toBe(20);
      expect(result.latency.p95).toBeLessThan(1500); // p95 should be < 1500ms (includes password hashing)
    });
  });

  describe('E2: Login Performance', () => {
    it('should authenticate user in acceptable time', async () => {
      const { email } = { email: 'login-perf@example.com' };
      await registerAndLogin(email);

      const startTime = performance.now();
      const res = await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        payload: { email, password: 'test-password-123' },
      });
      const latency = performance.now() - startTime;

      expect(res.statusCode).toBe(200);
      expect(latency).toBeLessThan(300); // Single login should be < 300ms
    });

    it('should handle concurrent login attempts', async () => {
      const userEmail = `concurrent-login-${Date.now()}@example.com`;
      // Register user first
      const registerRes = await app.inject({
        method: 'POST',
        url: '/api/users',
        payload: { email: userEmail, name: 'Test User', password: 'test-password-123' },
      });
      expect(registerRes.statusCode).toBe(200);

      const result = await simulateConcurrentLoad(
        async (config: any) => {
          const startTime = performance.now();
          const res = await app.inject(config);
          return { statusCode: res.statusCode, latency: performance.now() - startTime };
        },
        {
          endpoint: '/api/auth/login',
          method: 'POST',
          concurrency: 3,
          totalRequests: 6,
          requestFactory: () => ({
            method: 'POST',
            url: '/api/auth/login',
            payload: { email: userEmail, password: 'test-password-123' },
          }),
        }
      );

      results.push(result);
      expect(result.successCount).toBeGreaterThan(2);
      expect(result.latency.p95).toBeLessThan(500); // p95 should be < 500ms
    });
  });

  describe('E3: Loan Portfolio Query Performance', () => {
    it('should query empty portfolio quickly', async () => {
      const { userId, token } = await registerAndLogin('loan-query@example.com');

      const startTime = performance.now();
      const res = await app.inject({
        method: 'GET',
        url: `/api/users/${userId}/loans`,
        headers: { authorization: `Bearer ${token}` },
      });
      const latency = performance.now() - startTime;

      expect(res.statusCode).toBe(200);
      expect(latency).toBeLessThan(150);
    });

    it('should query portfolio with multiple loans', async () => {
      const { userId, token } = await registerAndLogin(`loan-perf-${Date.now()}@example.com`);

      // Add 10 loans
      for (let i = 0; i < 10; i++) {
        await app.inject({
          method: 'POST',
          url: '/api/loans',
          headers: { authorization: `Bearer ${token}` },
          payload: {
            userId,
            productId: `product-${i}`,
            originalAmount: 100000 + i * 10000,
            interestRate: 3.0 + i * 0.1,
            termMonths: 60 + i * 12,
            startDate: '2025-01-01',
          },
        });
      }

      const startTime = performance.now();
      const res = await app.inject({
        method: 'GET',
        url: `/api/users/${userId}/loans`,
        headers: { authorization: `Bearer ${token}` },
      });
      const latency = performance.now() - startTime;

      expect(res.statusCode).toBe(200);
      expect(latency).toBeLessThan(250); // Should still be fast with 10 loans
      expect(res.json().data.length).toBe(10);
    });
  });

  describe('E4: Transaction History Query Performance', () => {
    it('should query empty transaction history quickly', async () => {
      const { userId, token } = await registerAndLogin(`tx-query@example.com`);

      const startTime = performance.now();
      const res = await app.inject({
        method: 'GET',
        url: `/api/users/${userId}/transactions`,
        headers: { authorization: `Bearer ${token}` },
      });
      const latency = performance.now() - startTime;

      expect(res.statusCode).toBe(200);
      expect(latency).toBeLessThan(150);
    });

    it('should handle multiple concurrent profile queries', async () => {
      const { userId, token } = await registerAndLogin(`concurrent-profile@example.com`);

      const result = await simulateConcurrentLoad(
        async (config: any) => {
          const startTime = performance.now();
          const res = await app.inject(config);
          return { statusCode: res.statusCode, latency: performance.now() - startTime };
        },
        {
          endpoint: `/api/users/${userId}`,
          method: 'GET',
          concurrency: 10,
          totalRequests: 20,
          requestFactory: () => ({
            method: 'GET',
            url: `/api/users/${userId}`,
            headers: { authorization: `Bearer ${token}` },
          }),
        }
      );

      results.push(result);
      expect(result.successCount).toBe(20);
      expect(result.latency.p95).toBeLessThan(250); // p95 for read should be < 250ms
    });
  });

  describe('E5: Database Performance Characteristics', () => {
    it('should measure transaction record creation latency', async () => {
      const { userId, token } = await registerAndLogin(`tx-record@example.com`);

      const latencies: number[] = [];
      for (let i = 0; i < 5; i++) {
        const startTime = performance.now();
        await app.inject({
          method: 'POST',
          url: '/api/transactions',
          headers: { authorization: `Bearer ${token}` },
          payload: {
            userId,
            transactionType: 'deposit',
            amount: 10000 + i * 1000,
            occurredAt: '2025-01-01',
          },
        });
        latencies.push(performance.now() - startTime);
      }

      const metrics = calculateMetrics(latencies);
      expect(metrics.p95).toBeLessThan(300); // Transaction creation should be < 300ms p95
    });

    it('should maintain performance under moderate load', async () => {
      const { userId, token } = await registerAndLogin(`load-test@example.com`);

      const result = await simulateConcurrentLoad(
        async (config: any) => {
          const startTime = performance.now();
          const res = await app.inject(config);
          return { statusCode: res.statusCode, latency: performance.now() - startTime };
        },
        {
          endpoint: '/api/loans',
          method: 'POST',
          concurrency: 5,
          totalRequests: 15,
          requestFactory: (index) => ({
            method: 'POST',
            url: '/api/loans',
            headers: { authorization: `Bearer ${token}` },
            payload: {
              userId,
              productId: `product-perf-${index}`,
              originalAmount: 200000,
              interestRate: 4.5,
              termMonths: 72,
              startDate: '2025-01-01',
            },
          }),
        }
      );

      results.push(result);
      expect(result.successCount).toBeGreaterThan(10);
      expect(result.errorRate).toBeLessThan(25); // Allow some failures under load
    });
  });

  describe('Performance Summary', () => {
    it('should output performance results', () => {
      // This test acts as a placeholder to collect results
      // In a real scenario, results would be written to a file or report
      if (results.length > 0) {
        console.log('\n=== Performance Benchmark Results ===');
        console.log(formatMetricsTable(results));
        console.log('\n');
      }
    });
  });
});
