import Redis from 'ioredis';

/**
 * 사용자별 열린 SSE 스트림 집계 (Phase 15).
 *
 * 인스턴스 로컬 카운트로는 다중 인스턴스에서 사용자가 인스턴스 수만큼 곱한 만큼
 * 열 수 있다. 그렇다고 단순 INCR/DECR 카운터를 쓰면 프로세스가 비정상 종료될 때
 * DECR이 실행되지 않아 카운터가 영구히 부풀고, 그 사용자는 다시는 스트림을 열지
 * 못한다 — 상한이 사용자를 잠그는 셈이 된다.
 *
 * 그래서 "마지막 생존 신호 시각"을 값으로 갖는 정렬 집합을 쓴다. 열린 스트림은
 * 하트비트마다 자기 항목을 갱신하고, 집계 시 오래된 항목을 먼저 걷어낸다. 죽은
 * 프로세스의 항목은 아무도 갱신하지 않으므로 STALE_AFTER_MS가 지나면 스스로 사라진다.
 */

/** 하트비트 주기(25초)보다 넉넉히 커야 한다 — 3회 누락까지 견딘다. */
export const STALE_AFTER_MS = 90_000;

export interface StreamRegistry {
  /**
   * 등록하고 등록 후의 개수를 돌려준다.
   *
   * 먼저 세고 나서 등록하면 두 인스턴스가 동시에 같은 빈자리를 보고 둘 다 통과한다.
   * 등록부터 하고 결과를 세면 초과 여부를 스스로 알 수 있으므로, 호출자는 초과일 때
   * 되돌리면 된다.
   */
  registerAndCount(userId: string, streamId: string, now: number): Promise<number>;
  heartbeat(userId: string, streamId: string, now: number): Promise<void>;
  unregister(userId: string, streamId: string): Promise<void>;
  count(userId: string, now: number): Promise<number>;
  close(): Promise<void>;
}

const keyFor = (userId: string): string => `sse:streams:${userId}`;

/** 단일 프로세스 전용. Redis가 없을 때 쓰이며 인스턴스 로컬로만 정확하다. */
export class MemoryStreamRegistry implements StreamRegistry {
  private readonly streams = new Map<string, Map<string, number>>();

  async registerAndCount(userId: string, streamId: string, now: number): Promise<number> {
    let entries = this.streams.get(userId);
    if (!entries) {
      entries = new Map();
      this.streams.set(userId, entries);
    }
    entries.set(streamId, now);
    return this.prune(userId, now);
  }

  async heartbeat(userId: string, streamId: string, now: number): Promise<void> {
    this.streams.get(userId)?.set(streamId, now);
  }

  async unregister(userId: string, streamId: string): Promise<void> {
    const entries = this.streams.get(userId);
    if (!entries) return;
    entries.delete(streamId);
    if (entries.size === 0) this.streams.delete(userId);
  }

  async count(userId: string, now: number): Promise<number> {
    return this.prune(userId, now);
  }

  async close(): Promise<void> {
    this.streams.clear();
  }

  private prune(userId: string, now: number): number {
    const entries = this.streams.get(userId);
    if (!entries) return 0;

    for (const [streamId, lastSeen] of entries) {
      if (lastSeen <= now - STALE_AFTER_MS) entries.delete(streamId);
    }
    if (entries.size === 0) this.streams.delete(userId);
    return entries.size;
  }
}

export class RedisStreamRegistry implements StreamRegistry {
  private readonly client: Redis;

  constructor(redisUrl: string) {
    this.client = new Redis(redisUrl, { maxRetriesPerRequest: 1 });
  }

  async registerAndCount(userId: string, streamId: string, now: number): Promise<number> {
    const key = keyFor(userId);
    const results = await this.client
      .multi()
      .zadd(key, now, streamId)
      .zremrangebyscore(key, '-inf', now - STALE_AFTER_MS)
      .zcard(key)
      // 마지막 스트림이 unregister 없이 사라져도 키 자체가 남지 않도록 하는 안전망.
      .pexpire(key, STALE_AFTER_MS * 2)
      .exec();

    // exec()는 [error, value] 쌍의 배열을 준다. zcard는 세 번째 명령이다.
    const zcard = results?.[2];
    if (!zcard || zcard[0]) throw zcard?.[0] ?? new Error('ZCARD failed');
    return Number(zcard[1]);
  }

  async heartbeat(userId: string, streamId: string, now: number): Promise<void> {
    const key = keyFor(userId);
    await this.client.multi().zadd(key, now, streamId).pexpire(key, STALE_AFTER_MS * 2).exec();
  }

  async unregister(userId: string, streamId: string): Promise<void> {
    await this.client.zrem(keyFor(userId), streamId);
  }

  async count(userId: string, now: number): Promise<number> {
    const key = keyFor(userId);
    const results = await this.client
      .multi()
      .zremrangebyscore(key, '-inf', now - STALE_AFTER_MS)
      .zcard(key)
      .exec();

    const zcard = results?.[1];
    if (!zcard || zcard[0]) throw zcard?.[0] ?? new Error('ZCARD failed');
    return Number(zcard[1]);
  }

  async close(): Promise<void> {
    await this.client.quit();
  }
}

export function createStreamRegistry(): StreamRegistry {
  const redisUrl = process.env.REDIS_URL;
  return redisUrl ? new RedisStreamRegistry(redisUrl) : new MemoryStreamRegistry();
}
