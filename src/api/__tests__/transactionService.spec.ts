import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool } from 'pg';
import { getTestPool, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { registerUser, updateUserProfile } from '@api/userService';
import {
  getTransactionAuditLog,
  getTransactionHistory,
  getTransactionMonthlyTrend,
  getTransactionSummary,
  recordTransaction,
  rescanAnomalies
} from '@api/transactionService';

describe('transactionService (Day 6 - Task 4: 거래/감사 서비스 계층, δ=1410)', () => {
  let pool: Pool;
  let userId: string;

  beforeEach(async () => {
    pool = getTestPool();
    const created = await registerUser(pool, { email: 'txn-svc@example.com', name: 'Txn Service User', password: 'test-password-123', financialSnapshot: { monthlyIncome: 5000000 } });
    userId = created.success ? created.data.id : '';
  });

  afterEach(async () => {
    await cleanupTestDatabase();
  });

  describe('[T-SVC-401~406] 거래/감사 서비스', () => {
    it('[T-SVC-401] 거래 기록', async () => {
      const result = await recordTransaction(pool, { userId, transactionType: 'deposit', amount: 500000, occurredAt: '2026-01-01' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.status).toBe('completed');
      }
    });

    it('[T-SVC-402] 거래 이력 조회 & 필터', async () => {
      await recordTransaction(pool, { userId, transactionType: 'deposit', amount: 100000, occurredAt: '2026-01-01' });
      await recordTransaction(pool, { userId, transactionType: 'deposit', amount: 200000, occurredAt: '2026-03-01' });

      const all = await getTransactionHistory(pool, userId);
      expect(all.success).toBe(true);
      if (all.success) expect(all.data.length).toBe(2);

      const filtered = await getTransactionHistory(pool, userId, { from: '2026-01-01', to: '2026-01-31' });
      expect(filtered.success).toBe(true);
      if (filtered.success) expect(filtered.data.length).toBe(1);
    });

    it('[T-SVC-403] 거래 요약', async () => {
      await recordTransaction(pool, { userId, transactionType: 'deposit', amount: 1000000, occurredAt: '2026-01-01' });
      await recordTransaction(pool, { userId, transactionType: 'withdrawal', amount: 300000, occurredAt: '2026-01-05' });

      const result = await getTransactionSummary(pool, userId);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.totalDeposits).toBe(1000000);
        expect(result.data.totalWithdrawals).toBe(300000);
      }
    });

    it('[T-SVC-404] 이상거래 자동 감지', async () => {
      const result = await recordTransaction(pool, { userId, transactionType: 'withdrawal', amount: 3000000, occurredAt: '2026-01-01' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.status).toBe('flagged'); // 소득(500만)의 50% 초과
      }
    });

    it('[T-SVC-405] 재스캔으로 드리프트 감지', async () => {
      const normal = await recordTransaction(pool, { userId, transactionType: 'withdrawal', amount: 2000000, occurredAt: '2026-01-01' });
      expect(normal.success).toBe(true);
      const txnId = normal.success ? normal.data.id : '';

      const profile = await updateUserProfile(pool, userId, { financialSnapshot: { monthlyIncome: 1000000 } }, 1);
      expect(profile.success).toBe(true);

      const rescanned = await rescanAnomalies(pool, userId);
      expect(rescanned.success).toBe(true);
      if (rescanned.success) {
        expect(rescanned.data.some((t) => t.id === txnId)).toBe(true);
      }
    });

    it('[T-SVC-406] 감사로그 조회 & 월별 추이', async () => {
      const tx = await recordTransaction(pool, { userId, transactionType: 'deposit', amount: 500000, occurredAt: '2026-01-01' });
      const txnId = tx.success ? tx.data.id : '';
      await recordTransaction(pool, { userId, transactionType: 'deposit', amount: 300000, occurredAt: '2026-02-01' });

      const auditResult = await getTransactionAuditLog(pool, txnId);
      expect(auditResult.success).toBe(true);
      if (auditResult.success) expect(auditResult.data.length).toBe(1);

      const trendResult = await getTransactionMonthlyTrend(pool, userId);
      expect(trendResult.success).toBe(true);
      if (trendResult.success) {
        expect(trendResult.data.map((p) => p.month)).toEqual(['2026-01', '2026-02']);
      }
    });
  });
});
