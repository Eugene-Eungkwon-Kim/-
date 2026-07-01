import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { UserRepository } from '@repositories/UserRepository';
import { TransactionRepository } from '@repositories/TransactionRepository';

describe('TransactionRepository (Day 5 - Task 3: 거래 기록 & 감시 로깅, δ=1415)', () => {
  let db: Database.Database;
  let users: UserRepository;
  let transactions: TransactionRepository;
  let userId: string;

  beforeEach(() => {
    db = createDatabase(':memory:');
    users = new UserRepository(db);
    transactions = new TransactionRepository(db);
    userId = users.register({
      email: 'txn@example.com',
      name: 'Transaction User',
      financialSnapshot: { monthlyIncome: 5000000 }
    }).id;
  });

  afterEach(() => {
    db.close();
  });

  describe('[T-API-A13~A18] 거래 기록 & 감시 로깅', () => {
    it('[T-API-A13] 트랜잭션 기록', () => {
      const tx = transactions.recordTransaction({
        userId,
        transactionType: 'deposit',
        amount: 1000000,
        occurredAt: '2026-01-15',
        description: '급여 입금'
      });

      expect(tx.status).toBe('completed');
      expect(tx.amount).toBe(1000000);

      const found = transactions.getTransaction(tx.id);
      expect(found?.description).toBe('급여 입금');

      const list = transactions.getTransactions(userId);
      expect(list.length).toBe(1);
    });

    it('[T-API-A14] 감시 로그 자동 기록', () => {
      const tx = transactions.recordTransaction({
        userId,
        transactionType: 'withdrawal',
        amount: 500000,
        occurredAt: '2026-01-20'
      });

      const auditEntries = transactions.getAuditLog(tx.id);
      expect(auditEntries.length).toBe(1);
      expect(auditEntries[0].action).toBe('CREATE');
      expect(auditEntries[0].entityType).toBe('transaction');
      expect(auditEntries[0].changes.amount).toBe(500000);
      expect(auditEntries[0].actorId).toBe(userId);
    });

    it('[T-API-A15] 비정상 거래 감지', () => {
      // 소득(500만원)의 50% 초과 거래는 즉시 flagged
      const flagged = transactions.recordTransaction({
        userId,
        transactionType: 'withdrawal',
        amount: 3000000,
        occurredAt: '2026-02-01'
      });
      expect(flagged.status).toBe('flagged');

      // 등록 당시엔 정상이었지만 이후 소득이 낮아지면 재스캔으로 드리프트 감지
      const normal = transactions.recordTransaction({
        userId,
        transactionType: 'withdrawal',
        amount: 2000000,
        occurredAt: '2026-02-05'
      });
      expect(normal.status).toBe('completed');

      const profile = users.getProfile(userId)!;
      users.updateProfile(userId, { financialSnapshot: { monthlyIncome: 1000000 } }, profile.metadata.version);

      const rescanned = transactions.rescanForAnomalies(userId);
      expect(rescanned.some((t) => t.id === normal.id)).toBe(true);
      expect(transactions.getTransaction(normal.id)?.status).toBe('flagged');
    });

    it('[T-API-A16] 감시 로그 조회 & 필터', () => {
      const tx1 = transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 100000, occurredAt: '2026-01-01' });
      const tx2 = transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 200000, occurredAt: '2026-03-01' });

      const onlyTx1 = transactions.getAuditLog(tx1.id);
      expect(onlyTx1.length).toBe(1);
      expect(onlyTx1[0].entityId).toBe(tx1.id);

      const janOnly = transactions.getAuditLog(undefined, { from: '2026-01-01', to: '2026-01-31' });
      expect(janOnly.some((e) => e.entityId === tx1.id)).toBe(true);
      expect(janOnly.some((e) => e.entityId === tx2.id)).toBe(false);
    });

    it('[T-API-A17] 거래 요약', () => {
      transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 1000000, occurredAt: '2026-01-01' });
      transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 500000, occurredAt: '2026-01-10' });
      transactions.recordTransaction({ userId, transactionType: 'withdrawal', amount: 300000, occurredAt: '2026-01-15' });
      transactions.recordTransaction({ userId, transactionType: 'withdrawal', amount: 4000000, occurredAt: '2026-01-20' }); // flagged (>50% of income)

      const summary = transactions.getSummary(userId);
      expect(summary.transactionCount).toBe(4);
      expect(summary.totalDeposits).toBe(1500000);
      expect(summary.totalWithdrawals).toBe(4300000);
      expect(summary.flaggedCount).toBe(1);
      expect(summary.lastTransactionAt).toBe('2026-01-20');
    });

    it('[T-API-A18] 시계열 분석 (월별 추이)', () => {
      transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 1000000, occurredAt: '2026-01-05' });
      transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 500000, occurredAt: '2026-01-20' });
      transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 700000, occurredAt: '2026-02-10' });

      const trend = transactions.getMonthlyTrend(userId);
      expect(trend).toEqual([
        { month: '2026-01', totalAmount: 1500000, transactionCount: 2 },
        { month: '2026-02', totalAmount: 700000, transactionCount: 1 }
      ]);
    });
  });
});
