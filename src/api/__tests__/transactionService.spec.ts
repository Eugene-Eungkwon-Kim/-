import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
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
  let db: Database.Database;
  let userId: string;

  beforeEach(() => {
    db = createDatabase(':memory:');
    const created = registerUser(db, { email: 'txn-svc@example.com', name: 'Txn Service User', financialSnapshot: { monthlyIncome: 5000000 } });
    userId = created.success ? created.data.id : '';
  });

  afterEach(() => {
    db.close();
  });

  describe('[T-SVC-401~406] 거래/감사 서비스', () => {
    it('[T-SVC-401] 거래 기록', () => {
      const result = recordTransaction(db, { userId, transactionType: 'deposit', amount: 500000, occurredAt: '2026-01-01' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.status).toBe('completed');
      }
    });

    it('[T-SVC-402] 거래 이력 조회 & 필터', () => {
      recordTransaction(db, { userId, transactionType: 'deposit', amount: 100000, occurredAt: '2026-01-01' });
      recordTransaction(db, { userId, transactionType: 'deposit', amount: 200000, occurredAt: '2026-03-01' });

      const all = getTransactionHistory(db, userId);
      expect(all.success).toBe(true);
      if (all.success) expect(all.data.length).toBe(2);

      const filtered = getTransactionHistory(db, userId, { from: '2026-01-01', to: '2026-01-31' });
      expect(filtered.success).toBe(true);
      if (filtered.success) expect(filtered.data.length).toBe(1);
    });

    it('[T-SVC-403] 거래 요약', () => {
      recordTransaction(db, { userId, transactionType: 'deposit', amount: 1000000, occurredAt: '2026-01-01' });
      recordTransaction(db, { userId, transactionType: 'withdrawal', amount: 300000, occurredAt: '2026-01-05' });

      const result = getTransactionSummary(db, userId);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.totalDeposits).toBe(1000000);
        expect(result.data.totalWithdrawals).toBe(300000);
      }
    });

    it('[T-SVC-404] 이상거래 자동 감지', () => {
      const result = recordTransaction(db, { userId, transactionType: 'withdrawal', amount: 3000000, occurredAt: '2026-01-01' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.status).toBe('flagged'); // 소득(500만)의 50% 초과
      }
    });

    it('[T-SVC-405] 재스캔으로 드리프트 감지', () => {
      const normal = recordTransaction(db, { userId, transactionType: 'withdrawal', amount: 2000000, occurredAt: '2026-01-01' });
      expect(normal.success).toBe(true);
      const txnId = normal.success ? normal.data.id : '';

      const profile = updateUserProfile(db, userId, { financialSnapshot: { monthlyIncome: 1000000 } }, 1);
      expect(profile.success).toBe(true);

      const rescanned = rescanAnomalies(db, userId);
      expect(rescanned.success).toBe(true);
      if (rescanned.success) {
        expect(rescanned.data.some((t) => t.id === txnId)).toBe(true);
      }
    });

    it('[T-SVC-406] 감사로그 조회 & 월별 추이', () => {
      const tx = recordTransaction(db, { userId, transactionType: 'deposit', amount: 500000, occurredAt: '2026-01-01' });
      const txnId = tx.success ? tx.data.id : '';
      recordTransaction(db, { userId, transactionType: 'deposit', amount: 300000, occurredAt: '2026-02-01' });

      const auditResult = getTransactionAuditLog(db, txnId);
      expect(auditResult.success).toBe(true);
      if (auditResult.success) expect(auditResult.data.length).toBe(1);

      const trendResult = getTransactionMonthlyTrend(db, userId);
      expect(trendResult.success).toBe(true);
      if (trendResult.success) {
        expect(trendResult.data.map((p) => p.month)).toEqual(['2026-01', '2026-02']);
      }
    });
  });
});
