export interface CacheStats {
  hits: number;
  misses: number;
  size: number | null; // Redis는 정확한 크기 조회가 비용이 커 null 허용
}

export interface CacheStore {
  get<T>(key: string): Promise<T | undefined>;
  set<T>(key: string, value: T, ttlMs?: number): Promise<void>;
  delete(key: string): Promise<void>;
  deleteByPrefix(prefix: string): Promise<number>;
  getOrCompute<T>(key: string, loader: () => Promise<T>, ttlMs?: number): Promise<T>;
  stats(): Promise<CacheStats>;
}
