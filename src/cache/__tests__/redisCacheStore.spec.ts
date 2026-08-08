import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { RedisCacheStore } from '../redisCacheStore';

describe('RedisCacheStore', () => {
  let store: RedisCacheStore;

  beforeEach(async () => {
    const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';
    store = new RedisCacheStore(redisUrl);
    // Flush Redis to ensure test isolation - previous test data persists in Redis across instances
    await store.flushdb();
  });

  afterEach(async () => {
    await store.disconnect();
  });

  it('should get and set values', async () => {
    await store.set('key1', { value: 'test' });
    const result = await store.get('key1');
    expect(result).toEqual({ value: 'test' });
  });

  it('should return undefined for missing keys', async () => {
    const result = await store.get('nonexistent-key');
    expect(result).toBeUndefined();
  });

  it('should delete keys', async () => {
    await store.set('key1', { value: 'test' });
    await store.delete('key1');
    const result = await store.get('key1');
    expect(result).toBeUndefined();
  });

  it('should delete keys by prefix using SCAN', async () => {
    // Set keys with prefix
    await store.set('user:1:summary', { data: 'a' });
    await store.set('user:1:trend', { data: 'b' });
    await store.set('user:2:summary', { data: 'c' });

    const deleted = await store.deleteByPrefix('user:1:');
    expect(deleted).toBe(2);

    const summary = await store.get('user:1:summary');
    const trend = await store.get('user:1:trend');
    const otherSummary = await store.get('user:2:summary');

    expect(summary).toBeUndefined();
    expect(trend).toBeUndefined();
    expect(otherSummary).toEqual({ data: 'c' });
  });

  it('should handle prefix deletion with many keys', async () => {
    // Create enough keys to test SCAN pagination (COUNT=100)
    for (let i = 0; i < 150; i++) {
      await store.set(`prefix:${i}:data`, { index: i });
    }

    const deleted = await store.deleteByPrefix('prefix:');
    expect(deleted).toBe(150);

    const result = await store.get('prefix:0:data');
    expect(result).toBeUndefined();
  });

  it('should compute and cache values', async () => {
    let callCount = 0;
    const loader = async () => {
      callCount++;
      return { value: 'computed' };
    };

    const result1 = await store.getOrCompute('key1', loader);
    const result2 = await store.getOrCompute('key1', loader);

    expect(result1).toEqual({ value: 'computed' });
    expect(result2).toEqual({ value: 'computed' });
    expect(callCount).toBe(1);
  });

  it('should not cache failed computations', async () => {
    let callCount = 0;
    const failingLoader = async () => {
      callCount++;
      throw new Error('loader failed');
    };

    await expect(store.getOrCompute('key1', failingLoader)).rejects.toThrow('loader failed');
    await expect(store.getOrCompute('key1', failingLoader)).rejects.toThrow('loader failed');
    expect(callCount).toBe(2);
  });

  it('should respect custom TTL in getOrCompute', async () => {
    const loader = async () => ({ value: 'test' });

    // Set with 100ms TTL
    await store.getOrCompute('key1', loader, 100);
    const result1 = await store.get('key1');
    expect(result1).toEqual({ value: 'test' });

    // Wait for expiry
    await new Promise(resolve => setTimeout(resolve, 150));
    const result2 = await store.get('key1');
    expect(result2).toBeUndefined();
  });

  it('should provide cache statistics', async () => {
    await store.set('key1', { value: 'test' });
    await store.get('key1'); // hit
    await store.get('key1'); // hit
    await store.get('missing'); // miss

    const stats = await store.stats();
    expect(stats.hits).toBe(2);
    expect(stats.misses).toBe(1);
    expect(stats.size).toBeNull();
  });

  it('should serialize complex objects', async () => {
    const complex = {
      nested: { data: [1, 2, 3] },
      date: new Date('2024-01-01').toISOString(),
      number: 42
    };

    await store.set('complex', complex);
    const result = await store.get('complex');
    expect(result).toEqual(complex);
  });
});
