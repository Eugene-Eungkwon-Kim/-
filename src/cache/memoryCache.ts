/**
 * Day 15 - Task L: 캐싱 전략 — 인메모리 TTL + LRU 캐시
 *
 * better-sqlite3는 동기·인프로세스 엔진이므로 Redis 같은 외부 캐시는
 * 네트워크 왕복만 추가할 뿐 이득이 없다. 대신 집계 쿼리(요약/추세)의
 * 반복 계산을 줄이는 얇은 인메모리 캐시를 둔다.
 *
 * 설계 원칙:
 *  - 무효화 우선: 리포지토리를 거치는 모든 쓰기는 관련 키를 즉시 삭제한다.
 *  - TTL은 안전망: 리포지토리를 우회한 쓰기(원시 SQL 등)로 인한 staleness를
 *    TTL(기본 30초)로 상한선을 둔다.
 *  - LRU 상한: 키 수가 maxEntries를 넘으면 가장 오래 안 쓴 항목부터 제거한다.
 */

export interface CacheStats {
  hits: number;
  misses: number;
  size: number;
}

export interface MemoryCacheOptions {
  /** 항목 유효 시간 (ms). 기본 30초 */
  ttlMs?: number;
  /** 최대 항목 수. 초과 시 LRU 제거. 기본 500 */
  maxEntries?: number;
  /** 시간 소스 (테스트 주입용). 기본 Date.now */
  now?: () => number;
}

interface CacheEntry<T> {
  value: T;
  expiresAt: number;
}

export class MemoryCache<T = unknown> {
  private readonly ttlMs: number;
  private readonly maxEntries: number;
  private readonly now: () => number;
  // Map은 삽입 순서를 유지한다. get 시 재삽입해 "가장 최근 사용"을 맨 뒤로
  // 보내는 방식으로 LRU를 구현한다 — 맨 앞이 항상 가장 오래 안 쓴 항목이다.
  private readonly entries = new Map<string, CacheEntry<T>>();
  private hits = 0;
  private misses = 0;

  constructor(options: MemoryCacheOptions = {}) {
    this.ttlMs = options.ttlMs ?? 30_000;
    this.maxEntries = options.maxEntries ?? 500;
    this.now = options.now ?? Date.now;
  }

  get(key: string): T | undefined {
    const entry = this.entries.get(key);
    if (!entry) {
      this.misses++;
      return undefined;
    }
    if (entry.expiresAt <= this.now()) {
      this.entries.delete(key);
      this.misses++;
      return undefined;
    }
    // LRU 갱신: 재삽입으로 맨 뒤(가장 최근)로 이동
    this.entries.delete(key);
    this.entries.set(key, entry);
    this.hits++;
    return entry.value;
  }

  set(key: string, value: T): void {
    this.entries.delete(key);
    this.entries.set(key, { value, expiresAt: this.now() + this.ttlMs });
    if (this.entries.size > this.maxEntries) {
      const oldest = this.entries.keys().next().value;
      if (oldest !== undefined) this.entries.delete(oldest);
    }
  }

  /** 캐시 미스 시 loader를 실행해 채우는 read-through 헬퍼 */
  getOrCompute(key: string, loader: () => T): T {
    const cached = this.get(key);
    if (cached !== undefined) return cached;
    const value = loader();
    this.set(key, value);
    return value;
  }

  delete(key: string): void {
    this.entries.delete(key);
  }

  /** 주어진 접두사로 시작하는 모든 키를 무효화한다 (사용자 단위 무효화 등) */
  deleteByPrefix(prefix: string): number {
    let deleted = 0;
    for (const key of this.entries.keys()) {
      if (key.startsWith(prefix)) {
        this.entries.delete(key);
        deleted++;
      }
    }
    return deleted;
  }

  clear(): void {
    this.entries.clear();
  }

  stats(): CacheStats {
    return { hits: this.hits, misses: this.misses, size: this.entries.size };
  }
}

/**
 * Database 인스턴스별 캐시 저장소.
 *
 * 리포지토리는 요청마다 새로 생성될 수 있으므로 인스턴스 필드에 캐시를 두면
 * 효과가 없다. WeakMap으로 Database 객체당 하나의 캐시를 공유하면
 *  - 같은 DB를 쓰는 모든 리포지토리 인스턴스가 캐시를 공유하고
 *  - 테스트의 :memory: DB끼리는 격리되며
 *  - DB가 GC되면 캐시도 함께 회수된다.
 */
const cacheByDb = new WeakMap<object, MemoryCache>();

export function getDbCache(db: object, options?: MemoryCacheOptions): MemoryCache {
  let cache = cacheByDb.get(db);
  if (!cache) {
    cache = new MemoryCache(options);
    cacheByDb.set(db, cache);
  }
  return cache;
}
