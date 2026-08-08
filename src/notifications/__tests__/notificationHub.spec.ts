import { describe, it, expect, afterEach } from 'vitest';
import {
  MemoryNotificationHub,
  RedisNotificationHub,
  createNotificationHub,
  type NotificationHub
} from '../notificationHub';
import type { NotificationRecord } from '../../types/notification';

function makeNotification(userId: string, id = 'n1'): NotificationRecord {
  return {
    id,
    userId,
    metric: 'creditScore',
    severity: 'warning',
    value: 580,
    threshold: 600,
    snapshotDate: '2026-01-01',
    readAt: null,
    createdAt: '2026-01-01 00:00:00'
  };
}

/** 이벤트가 도착할 때까지 기다린다 — 폴링 간격을 짧게 잡아 실패 시 빨리 끝난다. */
async function waitFor(predicate: () => boolean, timeoutMs = 2000): Promise<void> {
  const start = Date.now();
  while (!predicate()) {
    if (Date.now() - start > timeoutMs) throw new Error('timed out waiting for condition');
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
}

describe('NotificationHub', () => {
  const openHubs: NotificationHub[] = [];

  afterEach(async () => {
    await Promise.all(openHubs.splice(0).map((hub) => hub.close()));
  });

  describe('MemoryNotificationHub', () => {
    it('구독자에게 알림을 전달한다', async () => {
      const hub = new MemoryNotificationHub();
      openHubs.push(hub);

      const received: NotificationRecord[] = [];
      hub.subscribe('user-1', (n) => received.push(n));

      await hub.publish(makeNotification('user-1'));

      expect(received).toHaveLength(1);
      expect(received[0].id).toBe('n1');
    });

    it('대상이 아닌 사용자에게는 전달하지 않는다', async () => {
      const hub = new MemoryNotificationHub();
      openHubs.push(hub);

      const received: NotificationRecord[] = [];
      hub.subscribe('user-2', (n) => received.push(n));

      await hub.publish(makeNotification('user-1'));

      expect(received).toHaveLength(0);
    });

    it('구독 해제 후에는 전달되지 않는다', async () => {
      const hub = new MemoryNotificationHub();
      openHubs.push(hub);

      const received: NotificationRecord[] = [];
      const unsubscribe = hub.subscribe('user-1', (n) => received.push(n));

      await hub.publish(makeNotification('user-1', 'before'));
      unsubscribe();
      await hub.publish(makeNotification('user-1', 'after'));

      expect(received.map((n) => n.id)).toEqual(['before']);
    });

    it('같은 사용자의 구독자 여러 명 모두에게 전달한다', async () => {
      const hub = new MemoryNotificationHub();
      openHubs.push(hub);

      const a: NotificationRecord[] = [];
      const b: NotificationRecord[] = [];
      hub.subscribe('user-1', (n) => a.push(n));
      hub.subscribe('user-1', (n) => b.push(n));

      await hub.publish(makeNotification('user-1'));

      expect(a).toHaveLength(1);
      expect(b).toHaveLength(1);
    });

    it('한 구독자가 던져도 다른 구독자에게는 전달된다', async () => {
      const hub = new MemoryNotificationHub();
      openHubs.push(hub);

      const received: NotificationRecord[] = [];
      hub.subscribe('user-1', () => {
        throw new Error('broken listener');
      });
      hub.subscribe('user-1', (n) => received.push(n));

      await expect(hub.publish(makeNotification('user-1'))).resolves.toBeUndefined();
      expect(received).toHaveLength(1);
    });
  });

  describe('RedisNotificationHub (인스턴스 간 전달)', () => {
    const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';

    it('한 인스턴스에서 발행하면 다른 인스턴스의 구독자가 받는다', async () => {
      const publisher = new RedisNotificationHub(redisUrl);
      const subscriber = new RedisNotificationHub(redisUrl);
      openHubs.push(publisher, subscriber);

      // SUBSCRIBE 완료 전에 발행하면 메시지가 유실된다 (Pub/Sub은 저장하지 않는다).
      await subscriber.whenReady();

      const received: NotificationRecord[] = [];
      subscriber.subscribe('user-1', (n) => received.push(n));

      await publisher.publish(makeNotification('user-1', 'cross-instance'));
      await waitFor(() => received.length > 0);

      expect(received[0].id).toBe('cross-instance');
      expect(received[0].value).toBe(580);
    });

    it('대상이 아닌 사용자의 구독자에게는 전달하지 않는다', async () => {
      const publisher = new RedisNotificationHub(redisUrl);
      const subscriber = new RedisNotificationHub(redisUrl);
      openHubs.push(publisher, subscriber);
      await subscriber.whenReady();

      const mine: NotificationRecord[] = [];
      const theirs: NotificationRecord[] = [];
      subscriber.subscribe('user-1', (n) => mine.push(n));
      subscriber.subscribe('user-2', (n) => theirs.push(n));

      await publisher.publish(makeNotification('user-1'));
      await waitFor(() => mine.length > 0);

      expect(mine).toHaveLength(1);
      expect(theirs).toHaveLength(0);
    });
  });

  describe('createNotificationHub', () => {
    const original = process.env.REDIS_URL;

    afterEach(() => {
      if (original === undefined) delete process.env.REDIS_URL;
      else process.env.REDIS_URL = original;
    });

    it('REDIS_URL이 없으면 메모리 허브로 강등한다', () => {
      delete process.env.REDIS_URL;
      const hub = createNotificationHub();
      openHubs.push(hub);
      expect(hub).toBeInstanceOf(MemoryNotificationHub);
    });

    it('REDIS_URL이 있으면 Redis 허브를 만든다', () => {
      process.env.REDIS_URL = 'redis://localhost:6379';
      const hub = createNotificationHub();
      openHubs.push(hub);
      expect(hub).toBeInstanceOf(RedisNotificationHub);
    });
  });
});
