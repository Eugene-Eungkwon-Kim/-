import Redis from 'ioredis';
import type { CacheStore, CacheStats } from './cacheStore';

export class RedisCacheStore implements CacheStore {
  private readonly client: Redis;
  private hits = 0;
  private misses = 0;

  constructor(redisUrl: string) {
    this.client = new Redis(redisUrl, { maxRetriesPerRequest: 1 });
  }

  async get<T>(key: string): Promise<T | undefined> {
    const raw = await this.client.get(key);
    if (raw === null) {
      this.misses++;
      return undefined;
    }
    this.hits++;
    return JSON.parse(raw) as T;
  }

  async set<T>(key: string, value: T, ttlMs = 30_000): Promise<void> {
    await this.client.set(key, JSON.stringify(value), 'PX', ttlMs);
  }

  async delete(key: string): Promise<void> {
    await this.client.del(key);
  }

  async deleteByPrefix(prefix: string): Promise<number> {
    let cursor = '0';
    let deleted = 0;
    do {
      const [next, keys] = await this.client.scan(cursor, 'MATCH', `${prefix}*`, 'COUNT', 100);
      cursor = next;
      if (keys.length > 0) {
        deleted += await this.client.del(...keys);
      }
    } while (cursor !== '0');
    return deleted;
  }

  async getOrCompute<T>(key: string, loader: () => Promise<T>, ttlMs?: number): Promise<T> {
    const cached = await this.get<T>(key);
    if (cached !== undefined) return cached;
    const value = await loader();
    await this.set(key, value, ttlMs);
    return value;
  }

  async stats(): Promise<CacheStats> {
    return { hits: this.hits, misses: this.misses, size: null };
  }

  async disconnect(): Promise<void> {
    await this.client.quit();
  }

  async flushdb(): Promise<void> {
    await this.client.flushdb();
  }
}
