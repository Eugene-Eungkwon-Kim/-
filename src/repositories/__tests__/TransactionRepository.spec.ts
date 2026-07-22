import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool } from 'pg';
import { getTestPool, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { UserRepository } from '@repositories/UserRepository';
import { TransactionRepository } from '@repositories/TransactionRepository';

describe('TransactionRepository (Day 5 - Task 3: 거래 기록 & 감시 로깅, δ=1415)', () => {
  let pool: Pool;
  let users: UserRepository;
  let transactions: TransactionRepository;
  let userId: string;

  beforeEach(async () => {
    pool = getTestPool();
    users = new UserRepository(pool);
    transactions = new TransactionRepository(pool);
    const user = await users.register({
      email: 'txn@example.com',
      name: 'Transaction User',
      financialSnapshot: { monthlyIncome: 5000000 }
    });
    userId = user.id;
  });

  afterEach(async () => {
    await cleanupTestDatabase();
  });

  describe('[T-API-A13~A18] 거래 기록 & 감시 로깅', () => {
    it('[T-API-A13] 트랜잭션 기록', async () => {
      const tx = await transactions.recordTransaction({
        userId,
        transactionType: 'deposit',
        amount: 1000000,
        occurredAt: '2026-01-15',
        description: '급여 입금'
      });

      expect(tx.status).toBe('completed');
      expect(tx.amount).toBe(1000000);

      const found = await transactions.getTransaction(tx.id);
      expect(found?.description).toBe('급여 입금');

      const list = await transactions.getTransactions(userId);
      expect(list.length).toBe(1);
    });

    it('[T-API-A14] 감시 로그 자동 기록', async () => {
      const tx = await transactions.recordTransaction({
        userId,
        transactionType: 'withdrawal',
        amount: 500000,
        occurredAt: '2026-01-20'
      });

      const auditEntries = await transactions.getAuditLog(tx.id);
      expect(auditEntries.length).toBe(1);
      expect(auditEntries[0].action).toBe('CREATE');
      expect(auditEntries[0].entityType).toBe('transaction');
      expect(auditEntries[0].changes.amount).toBe(500000);
      expect(auditEntries[0].actorId).toBe(userId);
    });

    it('[T-API-A15] 비정상 거래 감지', async () => {
      // 소득(500만원)의 50% 초과 거래는 즉시 flagged
      const flagged = await transactions.recordTransaction({
        userId,
        transactionType: 'withdrawal',
        amount: 3000000,
        occurredAt: '2026-02-01'
      });
      expect(flagged.status).toBe('flagged');

      // 등록 당시엔 정상이었지만 이후 소득이 낮아지면 재스캔으로 드리프트 감지
      const normal = await transactions.recordTransaction({
        userId,
        transactionType: 'withdrawal',
        amount: 2000000,
        occurredAt: '2026-02-05'
      });
      expect(normal.status).toBe('completed');

      const profile = await users.getProfile(userId);
      if (profile) {
        await users.updateProfile(userId, { financialSnapshot: { monthlyIncome: 1000000 } }, profile.metadata.version);
      }

      const rescanned = await transactions.rescanForAnomalies(userId);
      expect(rescanned.some((t) => t.id === normal.id)).toBe(true);
      const updated = await transactions.getTransaction(normal.id);
      expect(updated?.status).toBe('flagged');
    });

    it('[T-API-A16] 감시 로그 조회 & 필터', async () => {
      const tx1 = await transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 100000, occurredAt: '2026-01-01' });
      const tx2 = await transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 200000, occurredAt: '2026-03-01' });

      const onlyTx1 = await transactions.getAuditLog(tx1.id);
      expect(onlyTx1.length).toBe(1);
      expect(onlyTx1[0].entityId).toBe(tx1.id);

      const janOnly = await transactions.getAuditLog(undefined, { from: '2026-01-01', to: '2026-01-31' });
      expect(janOnly.some((e) => e.entityId === tx1.id)).toBe(true);
      expect(janOnly.some((e) => e.entityId === tx2.id)).toBe(false);
    });

    it('[T-API-A17] 거래 요약', async () => {
      await transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 1000000, occurredAt: '2026-01-01' });
      await transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 500000, occurredAt: '2026-01-10' });
      await transactions.recordTransaction({ userId, transactionType: 'withdrawal', amount: 300000, occurredAt: '2026-01-15' });
      await transactions.recordTransaction({ userId, transactionType: 'withdrawal', amount: 4000000, occurredAt: '2026-01-20' }); // flagged (>50% of income)

      const summary = await transactions.getSummary(userId);
      expect(summary.transactionCount).toBe(4);
      expect(summary.totalDeposits).toBe(1500000);
      expect(summary.totalWithdrawals).toBe(4300000);
      expect(summary.flaggedCount).toBe(1);
      expect(summary.lastTransactionAt).toBe('2026-01-20');
    });

    it('[T-API-A18] 시계열 분석 (월별 추이)', async () => {
      await transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 1000000, occurredAt: '2026-01-05' });
      await transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 500000, occurredAt: '2026-01-20' });
      await transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 700000, occurredAt: '2026-02-10' });

      const trend = await transactions.getMonthlyTrend(userId);
      expect(trend).toEqual([
        { month: '2026-01', totalAmount: 1500000, transactionCount: 2 },
        { month: '2026-02', totalAmount: 700000, transactionCount: 1 }
      ]);
    });
  });
});
