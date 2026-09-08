import { describe, it, expect, afterEach } from 'vitest';
import {
  MemoryStreamRegistry,
  RedisStreamRegistry,
  STALE_AFTER_MS,
  createStreamRegistry,
  type StreamRegistry
} from '../streamRegistry';

/**
 * Phase 15: 사용자별 열린 SSE 스트림 집계.
 *
 * 단순 INCR/DECR 카운터로 하면 프로세스가 비정상 종료될 때 감소가 실행되지 않아
 * 카운터가 영구히 부풀고 그 사용자가 잠긴다. 여기서 검증하는 핵심은 그 시나리오다.
 */
describe('StreamRegistry', () => {
  const open: StreamRegistry[] = [];
  const T0 = 1_800_000_000_000;
  const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';

  afterEach(async () => {
    await Promise.all(open.splice(0).map((registry) => registry.close()));
  });

  /** 두 구현이 같은 계약을 지키는지 동일한 표로 검증한다. */
  const implementations: [string, () => StreamRegistry][] = [
    ['MemoryStreamRegistry', () => new MemoryStreamRegistry()],
    ['RedisStreamRegistry', () => new RedisStreamRegistry(redisUrl)]
  ];

  for (const [name, create] of implementations) {
    describe(name, () => {
      /** Redis는 프로세스 밖에 상태가 남으므로 사용자 id를 매번 다르게 잡는다. */
      let counter = 0;
      const freshUser = (): string => `u-${name}-${Date.now()}-${counter++}`;

      it('등록하면 개수가 는다', async () => {
        const registry = create();
        open.push(registry);
        const user = freshUser();

        expect(await registry.registerAndCount(user, 's1', T0)).toBe(1);
        expect(await registry.registerAndCount(user, 's2', T0)).toBe(2);
      });

      it('같은 스트림을 다시 등록해도 중복 집계되지 않는다', async () => {
        const registry = create();
        open.push(registry);
        const user = freshUser();

        await registry.registerAndCount(user, 's1', T0);
        expect(await registry.registerAndCount(user, 's1', T0)).toBe(1);
      });

      it('해제하면 개수가 준다', async () => {
        const registry = create();
        open.push(registry);
        const user = freshUser();

        await registry.registerAndCount(user, 's1', T0);
        await registry.registerAndCount(user, 's2', T0);
        await registry.unregister(user, 's1');

        expect(await registry.count(user, T0)).toBe(1);
      });

      it('사용자별로 분리된다', async () => {
        const registry = create();
        open.push(registry);
        const a = freshUser();
        const b = freshUser();

        await registry.registerAndCount(a, 's1', T0);
        await registry.registerAndCount(a, 's2', T0);
        await registry.registerAndCount(b, 's1', T0);

        expect(await registry.count(a, T0)).toBe(2);
        expect(await registry.count(b, T0)).toBe(1);
      });

      it('갱신되지 않은 항목은 만료돼 스스로 사라진다 (크래시 누수 방지)', async () => {
        const registry = create();
        open.push(registry);
        const user = freshUser();

        // 프로세스가 죽어 unregister가 실행되지 못한 스트림을 흉내낸다.
        await registry.registerAndCount(user, 'dead', T0);

        const later = T0 + STALE_AFTER_MS + 1;
        expect(await registry.count(user, later)).toBe(0);
      });

      it('하트비트로 갱신된 항목은 살아남는다', async () => {
        const registry = create();
        open.push(registry);
        const user = freshUser();

        await registry.registerAndCount(user, 'alive', T0);
        const later = T0 + STALE_AFTER_MS + 1;
        await registry.heartbeat(user, 'alive', later);

        expect(await registry.count(user, later)).toBe(1);
      });

      it('죽은 항목이 걷히면 그 자리를 새 스트림이 쓸 수 있다', async () => {
        const registry = create();
        open.push(registry);
        const user = freshUser();

        await registry.registerAndCount(user, 'dead', T0);
        const later = T0 + STALE_AFTER_MS + 1;

        // 카운터 방식이었다면 여기서 2가 나오고 상한에 영원히 갇힌다.
        expect(await registry.registerAndCount(user, 'new', later)).toBe(1);
      });

      it('알 수 없는 스트림을 해제해도 예외가 나지 않는다', async () => {
        const registry = create();
        open.push(registry);

        await expect(registry.unregister(freshUser(), 'never-registered')).resolves.toBeUndefined();
      });
    });
  }

  describe('RedisStreamRegistry (인스턴스 간)', () => {
    it('한 인스턴스의 등록이 다른 인스턴스의 집계에 보인다', async () => {
      const first = new RedisStreamRegistry(redisUrl);
      const second = new RedisStreamRegistry(redisUrl);
      open.push(first, second);
      const user = `u-cross-${Date.now()}`;

      await first.registerAndCount(user, 's1', T0);

      // 인스턴스 로컬 카운트로는 잡히지 않는 부분 — 상한이 배수로 뚫리는 이유였다.
      expect(await second.registerAndCount(user, 's2', T0)).toBe(2);
    });
  });

  describe('createStreamRegistry', () => {
    const original = process.env.REDIS_URL;

    afterEach(() => {
      if (original === undefined) delete process.env.REDIS_URL;
      else process.env.REDIS_URL = original;
    });

    it('REDIS_URL이 없으면 메모리 레지스트리로 강등한다', () => {
      delete process.env.REDIS_URL;
      const registry = createStreamRegistry();
      open.push(registry);
      expect(registry).toBeInstanceOf(MemoryStreamRegistry);
    });

    it('REDIS_URL이 있으면 Redis 레지스트리를 만든다', () => {
      process.env.REDIS_URL = redisUrl;
      const registry = createStreamRegistry();
      open.push(registry);
      expect(registry).toBeInstanceOf(RedisStreamRegistry);
    });
  });
});
