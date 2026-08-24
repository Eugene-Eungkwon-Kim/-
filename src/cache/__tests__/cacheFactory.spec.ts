import { describe, it, expect, afterEach } from 'vitest';
import { createCacheStore, resetCacheStoreForTests } from '../cacheFactory';
import { MemoryCacheStore } from '../memoryCacheStore';
import { RedisCacheStore } from '../redisCacheStore';

describe('cacheFactory', () => {
  afterEach(() => {
    resetCacheStoreForTests();
    delete process.env.REDIS_URL;
  });

  it('should create MemoryCacheStore when REDIS_URL is not set', () => {
    delete process.env.REDIS_URL;
    const store = createCacheStore();
    expect(store).toBeInstanceOf(MemoryCacheStore);
  });

  it('should create RedisCacheStore when REDIS_URL is set', () => {
    process.env.REDIS_URL = 'redis://localhost:6379';
    const store = createCacheStore();
    expect(store).toBeInstanceOf(RedisCacheStore);
  });

  it('should return singleton instance', () => {
    delete process.env.REDIS_URL;
    const store1 = createCacheStore();
    const store2 = createCacheStore();
    expect(store1).toBe(store2);
  });

  it('should reset singleton for tests', () => {
    delete process.env.REDIS_URL;
    const store1 = createCacheStore();
    resetCacheStoreForTests();
    const store2 = createCacheStore();
    expect(store1).not.toBe(store2);
  });
});
