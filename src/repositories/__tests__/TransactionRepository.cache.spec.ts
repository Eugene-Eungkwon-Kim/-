import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool } from 'pg';
import {
  initializeTestDatabase,
  cleanupTestDatabase
} from '../../db/__tests__/testDatabase';
import { UserRepository } from '../UserRepository';
import { TransactionRepository } from '../TransactionRepository';
import { getDbCache } from '../../cache/memoryCache';
import { resetCacheStoreForTests } from '../../cache/cacheFactory';

/**
 * Day 15 - Task L: TransactionRepository 캐시 통합 테스트
 *
 * 요약/월별 추세 집계가 캐시되고, 쓰기(거래 기록, 이상탐지 재스캔) 시
 * 해당 사용자의 캐시만 무효화되는지 검증한다.
 */
describe('TransactionRepository 캐싱', () => {
  let pool: Pool;
  let userRepo: UserRepository;
  let txnRepo: TransactionRepository;
  let userId: string;

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY =
      '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef';
    pool = await initializeTestDatabase();
    userRepo = new UserRepository(pool);
    txnRepo = new TransactionRepository(pool);
    const user = await userRepo.register({
      email: 'cache@example.com',
      name: 'Cache User',
      password: 'test-password-123',
      contact: { address: {} },
      financialSnapshot: { monthlyIncome: 5000000 }
    });
    userId = user.id;
  });

  afterEach(async () => {
    await cleanupTestDatabase();
    resetCacheStoreForTests();
    delete process.env.ENCRYPTION_KEY;
  });

  async function record(amount: number, occurredAt = '2026-01-01'): Promise<void> {
    await txnRepo.recordTransaction({ userId, transactionType: 'deposit', amount, occurredAt });
  }

  it('getSummary 반복 호출은 캐시 히트로 처리된다', async () => {
    await record(1000);
    const statsBefore = getDbCache(pool).stats();
    await txnRepo.getSummary(userId); // miss → 계산 후 캐시
    await txnRepo.getSummary(userId); // hit
    await txnRepo.getSummary(userId); // hit
    const statsAfter = getDbCache(pool).stats();
    expect(statsAfter.hits - statsBefore.hits).toBeGreaterThanOrEqual(2);
  });

  it('거래 기록 후 요약이 즉시 갱신된다 (무효화 검증)', async () => {
    await record(1000);
    let summary = await txnRepo.getSummary(userId);
    expect(summary.transactionCount).toBe(1);

    await record(2000);
    summary = await txnRepo.getSummary(userId);
    expect(summary.transactionCount).toBe(2);
    expect(summary.totalDeposits).toBe(3000);
  });

  it('거래 기록 후 월별 추세가 즉시 갱신된다', async () => {
    await record(1000, '2026-01-15');
    let trend = await txnRepo.getMonthlyTrend(userId);
    expect(trend.length).toBe(1);

    await record(2000, '2026-02-15');
    trend = await txnRepo.getMonthlyTrend(userId);
    expect(trend.length).toBe(2);
    expect(trend[1].month).toBe('2026-02');
  });

  it('이상탐지 재스캔이 플래깅하면 요약의 flaggedCount가 갱신된다', async () => {
    // 소득(500만)의 50% 이하로 기록해 completed 상태로 만든다
    await record(2000000);
    let summary = await txnRepo.getSummary(userId);
    expect(summary.flaggedCount).toBe(0);

    // 소득을 낮춰 기존 거래가 임계값을 넘게 만든 후 재스캔
    const profile = await userRepo.getProfile(userId);
    await userRepo.updateProfile(
      userId,
      { financialSnapshot: { monthlyIncome: 1000000 } },
      profile!.metadata.version
    );
    const flagged = await txnRepo.rescanForAnomalies(userId);
    expect(flagged.length).toBe(1);

    summary = await txnRepo.getSummary(userId);
    expect(summary.flaggedCount).toBe(1);
  });

  it('다른 사용자의 캐시는 무효화되지 않는다', async () => {
    const otherUser = await userRepo.register({
      email: 'other@example.com',
      name: 'Other User',
      password: 'test-password-123',
      contact: { address: {} }
    });
    const otherId = otherUser.id;

    await record(1000);
    await txnRepo.getSummary(userId);
    await txnRepo.getSummary(otherId); // other 캐시 적재 (0건)

    // userId에만 쓰기 → other의 캐시는 유지되어야 한다
    await record(2000);
    const cache = getDbCache(pool);
    expect(cache.get(`txn:${userId}:summary`)).toBeUndefined();
    expect(cache.get(`txn:${otherId}:summary`)).toBeDefined();
  });

  it('같은 DB를 쓰는 새 리포지토리 인스턴스도 캐시를 공유한다', async () => {
    await record(1000);
    await txnRepo.getSummary(userId); // 캐시 적재

    const anotherRepo = new TransactionRepository(pool);
    const statsBefore = getDbCache(pool).stats();
    await anotherRepo.getSummary(userId);
    expect(getDbCache(pool).stats().hits).toBe(statsBefore.hits + 1);
  });

  it('캐시된 요약과 비캐시 재계산 결과가 일치한다', async () => {
    await record(1000, '2026-01-01');
    await record(3000, '2026-02-01');
    const cached = await txnRepo.getSummary(userId);

    getDbCache(pool).clear();
    const fresh = await txnRepo.getSummary(userId);
    expect(fresh).toEqual(cached);
  });

  it('캐시 계층 실패 시 직접 계산으로 폴백된다', async () => {
    await record(1000, '2026-01-01');

    // Clear cache to force recomputation on next call
    getDbCache(pool).clear();

    // getSummary should still return correct data even if cache fails
    const summary = await txnRepo.getSummary(userId);
    expect(summary).toBeDefined();
    expect(summary.transactionCount).toBe(1);
    expect(summary.totalDeposits).toBe(1000);
  });
});
