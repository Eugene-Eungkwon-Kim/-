import { MemoryCacheStore } from './memoryCacheStore';
import { RedisCacheStore } from './redisCacheStore';
import { getDbCache } from './memoryCache';
import type { CacheStore } from './cacheStore';
import type { Pool } from 'pg';

let singleton: CacheStore | null = null;
const cacheByDb = new WeakMap<object, MemoryCacheStore>();

export function createCacheStore(pool?: Pool): CacheStore {
  const redisUrl = process.env.REDIS_URL;

  if (redisUrl) {
    if (singleton) return singleton;
    singleton = new RedisCacheStore(redisUrl);
    return singleton;
  }

  // Memory mode: use per-DB cache for test isolation when pool is provided
  if (pool) {
    let store = cacheByDb.get(pool);
    if (!store) {
      store = new MemoryCacheStore(getDbCache(pool));
      cacheByDb.set(pool, store);
    }
    return store;
  }

  // Fallback: global singleton for non-pool usage
  if (singleton) return singleton;
  singleton = new MemoryCacheStore();
  return singleton;
}

export function resetCacheStoreForTests(): void {
  singleton = null;
}
