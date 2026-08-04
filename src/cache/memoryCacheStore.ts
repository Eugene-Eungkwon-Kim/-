import { MemoryCache } from './memoryCache';
import type { CacheStore, CacheStats } from './cacheStore';

export class MemoryCacheStore implements CacheStore {
  constructor(private readonly cache: MemoryCache = new MemoryCache()) {}

  async get<T>(key: string): Promise<T | undefined> {
    return this.cache.get(key) as T | undefined;
  }

  async set<T>(key: string, value: T, ttlMs?: number): Promise<void> {
    if (ttlMs !== undefined) {
      this.cache.set(key, value);
    } else {
      this.cache.set(key, value);
    }
  }

  async delete(key: string): Promise<void> {
    this.cache.delete(key);
  }

  async deleteByPrefix(prefix: string): Promise<number> {
    return this.cache.deleteByPrefix(prefix);
  }

  async getOrCompute<T>(key: string, loader: () => Promise<T>, ttlMs?: number): Promise<T> {
    const cached = await this.get<T>(key);
    if (cached !== undefined) return cached;
    const value = await loader();
    await this.set(key, value, ttlMs);
    return value;
  }

  async stats(): Promise<CacheStats> {
    const memStats = this.cache.stats();
    return {
      hits: memStats.hits,
      misses: memStats.misses,
      size: memStats.size
    };
  }
}
