import { describe, it, expect, beforeEach } from 'vitest';
import { MemoryCacheStore } from '../memoryCacheStore';

describe('MemoryCacheStore', () => {
  let store: MemoryCacheStore;

  beforeEach(() => {
    store = new MemoryCacheStore();
  });

  it('should get and set values', async () => {
    await store.set('key1', { value: 'test' });
    const result = await store.get('key1');
    expect(result).toEqual({ value: 'test' });
  });

  it('should return undefined for missing keys', async () => {
    const result = await store.get('nonexistent');
    expect(result).toBeUndefined();
  });

  it('should delete keys', async () => {
    await store.set('key1', { value: 'test' });
    await store.delete('key1');
    const result = await store.get('key1');
    expect(result).toBeUndefined();
  });

  it('should delete keys by prefix', async () => {
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

  it('should provide cache statistics', async () => {
    await store.set('key1', { value: 'test' });
    await store.get('key1'); // hit
    await store.get('key1'); // hit
    await store.get('missing'); // miss

    const stats = await store.stats();
    expect(stats.hits).toBe(2);
    expect(stats.misses).toBe(1);
    expect(stats.size).toBe(1);
  });

  it('should respect TTL (basic coverage)', async () => {
    // Note: TTL is managed by underlying MemoryCache with 30s default.
    // This test just verifies that set/get work; detailed TTL testing
    // happens in memoryCache.spec.ts.
    await store.set('key1', { value: 'test' });
    const result = await store.get('key1');
    expect(result).toEqual({ value: 'test' });
  });
});
