import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool } from 'pg';
import { cleanupTestDatabase, initializeTestDatabase } from '@db/__tests__/testDatabase';
import { UserRepository } from '@repositories/UserRepository';
import { NotificationRepository } from '@repositories/NotificationRepository';
import { NotificationNotFoundError } from '@repositories/errors';
import type { CreateNotificationInput } from '@/types/notification';

describe('NotificationRepository (Phase 15 - Section 2, B-3)', () => {
  let pool: Pool;
  let repo: NotificationRepository;
  let userId: string;
  let otherUserId: string;

  function input(overrides: Partial<CreateNotificationInput> = {}): CreateNotificationInput {
    return {
      userId,
      metric: 'creditScore',
      severity: 'warning',
      value: 580,
      threshold: 600,
      snapshotDate: '2026-01-01',
      ...overrides
    };
  }

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
    pool = await initializeTestDatabase();
    repo = new NotificationRepository(pool);

    const userRepo = new UserRepository(pool);
    userId = (await userRepo.register({ email: 'n-owner@example.com', name: 'Owner', password: 'correct-horse' })).id;
    otherUserId = (await userRepo.register({ email: 'n-other@example.com', name: 'Other', password: 'correct-horse' })).id;
  });

  afterEach(async () => {
    await cleanupTestDatabase();
    delete process.env.ENCRYPTION_KEY;
  });

  describe('insertIfNew', () => {
    it('새 알림을 저장하고 레코드를 반환한다', async () => {
      const record = await repo.insertIfNew(input());

      expect(record).not.toBeNull();
      expect(record!.metric).toBe('creditScore');
      expect(record!.severity).toBe('warning');
      expect(record!.value).toBe(580);
      expect(record!.readAt).toBeNull();
    });

    it('같은 dedupe_key로 다시 넣으면 null을 반환한다', async () => {
      await repo.insertIfNew(input());
      const duplicate = await repo.insertIfNew(input());

      expect(duplicate).toBeNull();
      expect(await repo.list(userId)).toHaveLength(1);
    });

    it('등급이 다르면 같은 날짜여도 별도 알림이다', async () => {
      await repo.insertIfNew(input({ severity: 'warning' }));
      const escalated = await repo.insertIfNew(input({ severity: 'critical', threshold: 500, value: 480 }));

      expect(escalated).not.toBeNull();
      expect(await repo.list(userId)).toHaveLength(2);
    });

    it('날짜가 다르면 같은 등급이어도 별도 알림이다', async () => {
      await repo.insertIfNew(input({ snapshotDate: '2026-01-01' }));
      const nextDay = await repo.insertIfNew(input({ snapshotDate: '2026-01-02' }));

      expect(nextDay).not.toBeNull();
    });

    it('사용자가 다르면 서로 간섭하지 않는다', async () => {
      await repo.insertIfNew(input());
      const forOther = await repo.insertIfNew(input({ userId: otherUserId }));

      expect(forOther).not.toBeNull();
      expect(await repo.list(userId)).toHaveLength(1);
      expect(await repo.list(otherUserId)).toHaveLength(1);
    });
  });

  describe('getLatestStateByMetric', () => {
    it('알림이 없으면 빈 맵이다', async () => {
      expect((await repo.getLatestStateByMetric(userId)).size).toBe(0);
    });

    it('지표별로 가장 최근 등급만 남는다', async () => {
      await repo.insertIfNew(input({ severity: 'warning', snapshotDate: '2026-01-01' }));
      await repo.insertIfNew(input({ severity: 'critical', snapshotDate: '2026-01-02' }));
      await repo.insertIfNew(input({ metric: 'riskScore', severity: 'warning', snapshotDate: '2026-01-02' }));

      const state = await repo.getLatestStateByMetric(userId);

      expect(state.get('creditScore')).toBe('critical');
      expect(state.get('riskScore')).toBe('warning');
      expect(state.size).toBe(2);
    });

    it('타인의 알림은 포함하지 않는다', async () => {
      await repo.insertIfNew(input({ userId: otherUserId }));

      expect((await repo.getLatestStateByMetric(userId)).size).toBe(0);
    });
  });

  describe('list / countUnread', () => {
    it('unreadOnly는 읽지 않은 것만 돌려준다', async () => {
      const first = await repo.insertIfNew(input({ snapshotDate: '2026-01-01' }));
      await repo.insertIfNew(input({ snapshotDate: '2026-01-02' }));
      await repo.markRead(userId, first!.id);

      expect(await repo.list(userId)).toHaveLength(2);
      expect(await repo.list(userId, { unreadOnly: true })).toHaveLength(1);
      expect(await repo.countUnread(userId)).toBe(1);
    });

    it('limit이 적용된다', async () => {
      await repo.insertIfNew(input({ snapshotDate: '2026-01-01' }));
      await repo.insertIfNew(input({ snapshotDate: '2026-01-02' }));
      await repo.insertIfNew(input({ snapshotDate: '2026-01-03' }));

      expect(await repo.list(userId, { limit: 2 })).toHaveLength(2);
    });
  });

  describe('pruneOldNotifications', () => {
    /** created_at을 직접 조작해 오래된 알림을 만든다. */
    async function ageTo(id: string, createdAt: string): Promise<void> {
      await pool.query('UPDATE notifications SET created_at = $1 WHERE id = $2', [createdAt, id]);
    }

    const NOW = '2026-06-01 00:00:00';

    it('읽었고 보존기간을 넘긴 알림은 지운다', async () => {
      const record = await repo.insertIfNew(input());
      await repo.markRead(userId, record!.id);
      await ageTo(record!.id, '2026-01-01 00:00:00');

      const result = await repo.pruneOldNotifications(30, NOW);

      expect(result.prunedCount).toBe(1);
      expect(result.prunedIds).toEqual([record!.id]);
      expect(await repo.list(userId)).toHaveLength(0);
    });

    it('읽지 않은 알림은 아무리 오래돼도 남긴다', async () => {
      const record = await repo.insertIfNew(input());
      await ageTo(record!.id, '2020-01-01 00:00:00');

      const result = await repo.pruneOldNotifications(30, NOW);

      // 사용자가 못 본 위험 경고가 조용히 사라지는 쪽이 더 나쁜 실패다.
      expect(result.prunedCount).toBe(0);
      expect(await repo.list(userId)).toHaveLength(1);
    });

    it('보존기간 안의 읽은 알림은 남긴다', async () => {
      const record = await repo.insertIfNew(input());
      await repo.markRead(userId, record!.id);
      await ageTo(record!.id, '2026-05-25 00:00:00');

      const result = await repo.pruneOldNotifications(30, NOW);

      expect(result.prunedCount).toBe(0);
      expect(await repo.list(userId)).toHaveLength(1);
    });

    it('사용자를 가리지 않고 전체를 정리한다 (관리자 배치)', async () => {
      const mine = await repo.insertIfNew(input());
      const theirs = await repo.insertIfNew(input({ userId: otherUserId }));
      await repo.markRead(userId, mine!.id);
      await repo.markRead(otherUserId, theirs!.id);
      await ageTo(mine!.id, '2026-01-01 00:00:00');
      await ageTo(theirs!.id, '2026-01-01 00:00:00');

      const result = await repo.pruneOldNotifications(30, NOW);

      expect(result.prunedCount).toBe(2);
    });

    it('지울 것이 없으면 0건을 반환한다', async () => {
      const result = await repo.pruneOldNotifications(30, NOW);
      expect(result).toEqual({ prunedCount: 0, prunedIds: [] });
    });
  });

  describe('markRead', () => {
    it('read_at을 채운다', async () => {
      const record = await repo.insertIfNew(input());
      const updated = await repo.markRead(userId, record!.id);

      expect(updated.readAt).not.toBeNull();
    });

    it('없는 id는 NotificationNotFoundError다', async () => {
      await expect(repo.markRead(userId, '00000000-0000-0000-0000-000000000000')).rejects.toThrow(NotificationNotFoundError);
    });

    it('타인의 알림 id는 존재해도 찾을 수 없다', async () => {
      const record = await repo.insertIfNew(input({ userId: otherUserId }));

      await expect(repo.markRead(userId, record!.id)).rejects.toThrow(NotificationNotFoundError);
    });
  });
});
