# 캐싱 전략 (Day 15 - Task L)

## 왜 Redis가 아닌 인메모리인가

better-sqlite3는 **동기·인프로세스** 엔진이다. 외부 캐시(Redis)를 두면
로컬 함수 호출(마이크로초)을 네트워크 왕복(밀리초)으로 바꾸는 셈이라
오히려 느려진다. 따라서 프로세스 내부의 얇은 TTL+LRU 캐시를 사용한다.
PostgreSQL 전환(docs/POSTGRES_MIGRATION.md) 후 다중 인스턴스 배포가
필요해지는 시점이 Redis 도입을 재검토할 타이밍이다.

## 구조

| 구성 요소 | 위치 | 역할 |
|----------|------|------|
| `MemoryCache` | `src/cache/memoryCache.ts` | TTL(기본 30초) + LRU(기본 500개) + 히트/미스 통계 |
| `getDbCache(db)` | 〃 | Database 인스턴스당 캐시 1개 (WeakMap) |
| 통합 지점 | `src/repositories/TransactionRepository.ts` | 요약/월별 추세 집계 캐싱 |

### Database 단위 스코프인 이유

리포지토리는 요청마다 새로 생성될 수 있어 인스턴스 필드 캐시는 효과가 없다.
WeakMap<Database, MemoryCache>로 스코프를 잡으면:
- 같은 DB를 쓰는 모든 리포지토리 인스턴스가 캐시를 공유
- 테스트의 `:memory:` DB끼리는 자동 격리
- DB 객체가 GC되면 캐시도 함께 회수

## 캐시 대상과 무효화 규칙

| 캐시 키 | 대상 | 무효화 시점 |
|---------|------|------------|
| `txn:{userId}:summary` | `getSummary()` — 전체 거래 로드 후 JS 집계 | `recordTransaction`, `rescanForAnomalies`(플래깅 발생 시) |
| `txn:{userId}:trend` | `getMonthlyTrend()` — GROUP BY 스캔 | 〃 |

무효화는 `deleteByPrefix('txn:{userId}:')`로 **사용자 단위**로만 수행한다 —
다른 사용자의 캐시는 유지된다.

## 안전장치 (staleness 상한)

- **무효화 우선**: 리포지토리를 거치는 모든 쓰기는 관련 키를 즉시 삭제
- **TTL 30초**: 리포지토리를 우회한 쓰기(원시 SQL, 관리자 수동 조작 등)로
  인한 staleness는 최대 30초로 제한
- **LRU 500개**: 메모리 사용량 상한 (항목당 수백 바이트 수준 → 최대 수백 KB)

## 캐시 대상 확장 시 판단 기준

1. **읽기가 쓰기보다 훨씬 잦은가?** — 요약/추세는 조회가 지배적
2. **무효화 지점을 전부 나열할 수 있는가?** — 쓰기 경로가 리포지토리 안에 닫혀 있어야 함
3. **우회 쓰기의 staleness가 치명적인가?** — 치명적이면 캐싱 금지
   (예: `UserRepository.getProfile`은 테스트·운영에서 원시 SQL로 role을
   변경하는 경로가 있어 의도적으로 캐싱하지 않았다)

## 검증

- `src/cache/__tests__/memoryCache.spec.ts` (15 테스트): TTL 만료, LRU 제거
  순서, get 시 LRU 갱신, read-through, 접두사 무효화, 통계, DB별 격리
- `src/repositories/__tests__/TransactionRepository.cache.spec.ts` (7 테스트):
  히트 확인, 쓰기 후 즉시 갱신, 사용자 단위 무효화 격리, 인스턴스 간 공유,
  캐시/비캐시 결과 동일성
