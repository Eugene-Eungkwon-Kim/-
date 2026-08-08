import { MemoryCacheStore } from './memoryCacheStore';
import { RedisCacheStore } from './redisCacheStore';
import { getDbCache } from './memoryCache';
import type { CacheStore } from './cacheStore';
import type { Pool } from 'pg';

let singleton: CacheStore | null = null;
const cacheByDb = new WeakMap<object, CacheStore>();

export function createCacheStore(pool?: Pool): CacheStore {
  const redisUrl = process.env.REDIS_URL;

  // Both Redis and memory modes use per-DB isolation when pool is provided
  if (pool) {
    let store = cacheByDb.get(pool);
    if (!store) {
      if (redisUrl) {
        store = new RedisCacheStore(redisUrl);
      } else {
        store = new MemoryCacheStore(getDbCache(pool));
      }
      cacheByDb.set(pool, store);
    }
    return store;
  }

  // Fallback: global singleton for non-pool usage (e.g., CLI scripts)
  if (redisUrl) {
    if (singleton) return singleton;
    singleton = new RedisCacheStore(redisUrl);
    return singleton;
  }

  if (singleton) return singleton;
  singleton = new MemoryCacheStore();
  return singleton;
}

export function resetCacheStoreForTests(): void {
  singleton = null;
}
