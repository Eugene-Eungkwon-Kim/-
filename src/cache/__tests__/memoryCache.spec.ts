import { describe, it, expect } from 'vitest';
import { MemoryCache, getDbCache } from '../memoryCache';

/**
 * Day 15 - Task L: 인메모리 캐시 단위 테스트
 */
describe('MemoryCache', () => {
  describe('기본 동작', () => {
    it('set한 값을 get으로 조회할 수 있다', () => {
      const cache = new MemoryCache<number>();
      cache.set('a', 1);
      expect(cache.get('a')).toBe(1);
    });

    it('없는 키는 undefined를 반환한다', () => {
      const cache = new MemoryCache();
      expect(cache.get('missing')).toBeUndefined();
    });

    it('delete로 항목을 제거할 수 있다', () => {
      const cache = new MemoryCache<number>();
      cache.set('a', 1);
      cache.delete('a');
      expect(cache.get('a')).toBeUndefined();
    });

    it('clear로 전체를 비울 수 있다', () => {
      const cache = new MemoryCache<number>();
      cache.set('a', 1);
      cache.set('b', 2);
      cache.clear();
      expect(cache.stats().size).toBe(0);
    });

    it('같은 키에 set하면 값을 덮어쓴다', () => {
      const cache = new MemoryCache<number>();
      cache.set('a', 1);
      cache.set('a', 2);
      expect(cache.get('a')).toBe(2);
      expect(cache.stats().size).toBe(1);
    });
  });

  describe('TTL 만료', () => {
    it('TTL이 지난 항목은 조회되지 않는다', () => {
      let time = 1000;
      const cache = new MemoryCache<number>({ ttlMs: 100, now: () => time });
      cache.set('a', 1);
      expect(cache.get('a')).toBe(1);

      time += 101; // TTL 초과
      expect(cache.get('a')).toBeUndefined();
    });

    it('TTL 이내에는 계속 유효하다', () => {
      let time = 1000;
      const cache = new MemoryCache<number>({ ttlMs: 100, now: () => time });
      cache.set('a', 1);
      time += 99;
      expect(cache.get('a')).toBe(1);
    });

    it('만료된 항목은 저장소에서도 제거된다', () => {
      let time = 1000;
      const cache = new MemoryCache<number>({ ttlMs: 100, now: () => time });
      cache.set('a', 1);
      time += 200;
      cache.get('a');
      expect(cache.stats().size).toBe(0);
    });
  });

  describe('LRU 제거', () => {
    it('maxEntries 초과 시 가장 오래 안 쓴 항목부터 제거한다', () => {
      const cache = new MemoryCache<number>({ maxEntries: 2 });
      cache.set('a', 1);
      cache.set('b', 2);
      cache.set('c', 3); // 'a'가 제거되어야 함
      expect(cache.get('a')).toBeUndefined();
      expect(cache.get('b')).toBe(2);
      expect(cache.get('c')).toBe(3);
    });

    it('get으로 접근한 항목은 최근 사용으로 갱신되어 제거 순위가 밀린다', () => {
      const cache = new MemoryCache<number>({ maxEntries: 2 });
      cache.set('a', 1);
      cache.set('b', 2);
      cache.get('a'); // 'a'를 최근 사용으로 갱신 → 다음 제거 대상은 'b'
      cache.set('c', 3);
      expect(cache.get('a')).toBe(1);
      expect(cache.get('b')).toBeUndefined();
    });
  });

  describe('getOrCompute', () => {
    it('미스 시 loader를 실행해 캐시를 채운다', () => {
      const cache = new MemoryCache<number>();
      let calls = 0;
      const loader = () => {
        calls++;
        return 42;
      };
      expect(cache.getOrCompute('k', loader)).toBe(42);
      expect(cache.getOrCompute('k', loader)).toBe(42);
      expect(calls).toBe(1); // 두 번째는 캐시 히트
    });
  });

  describe('deleteByPrefix', () => {
    it('접두사가 일치하는 키만 제거한다', () => {
      const cache = new MemoryCache<number>();
      cache.set('txn:user-1:summary', 1);
      cache.set('txn:user-1:trend', 2);
      cache.set('txn:user-2:summary', 3);

      const deleted = cache.deleteByPrefix('txn:user-1:');
      expect(deleted).toBe(2);
      expect(cache.get('txn:user-1:summary')).toBeUndefined();
      expect(cache.get('txn:user-1:trend')).toBeUndefined();
      expect(cache.get('txn:user-2:summary')).toBe(3);
    });
  });

  describe('통계', () => {
    it('히트/미스를 집계한다', () => {
      const cache = new MemoryCache<number>();
      cache.set('a', 1);
      cache.get('a'); // hit
      cache.get('a'); // hit
      cache.get('x'); // miss
      const stats = cache.stats();
      expect(stats.hits).toBe(2);
      expect(stats.misses).toBe(1);
      expect(stats.size).toBe(1);
    });
  });
});

describe('getDbCache', () => {
  it('같은 객체에는 같은 캐시를 반환한다', () => {
    const db = {};
    expect(getDbCache(db)).toBe(getDbCache(db));
  });

  it('다른 객체는 서로 격리된 캐시를 갖는다', () => {
    const db1 = {};
    const db2 = {};
    getDbCache(db1).set('k', 'v1');
    expect(getDbCache(db2).get('k')).toBeUndefined();
  });
});
