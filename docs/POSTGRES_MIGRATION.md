# PostgreSQL 마이그레이션 가이드 (Day 15 - Task K)

SQLite에서 PostgreSQL로 이전하기 위한 준비 자산과 절차를 정리한다.

> **리허설 완료 (2026-07-20)**: 아래 절차를 PostgreSQL 16.13 실인스턴스에
> 실제로 수행해 검증했다. 결과는 [마이그레이션 리허설 결과](#마이그레이션-리허설-결과) 참조.

## 준비된 자산

| 자산 | 위치 | 역할 |
|------|------|------|
| 스키마 변환기 | `src/db/pg/pgSchemaGenerator.ts` | SQLite 마이그레이션 → PG 통합 DDL |
| 데이터 내보내기 | `src/db/pg/pgDataExporter.ts` | 전체 데이터 → FK-안전 순서의 INSERT 스크립트 |
| 스키마 생성 | `npm run pg:schema` | `docs/postgres/schema.sql` 생성 |
| 데이터 내보내기 CLI | `npm run pg:export -- <sqlite-path> <output.sql>` | 운영 SQLite → INSERT 스크립트 (schema_migrations 제외) |
| 리허설 시드 | `scripts/seed-migration-source.ts` | 실제 리포지토리 경로로 원본 DB 생성 (리허설용) |
| 통합 스키마 | `docs/postgres/schema.sql` | 마이그레이션 001~017 반영, 자동 생성물 |

## 방언 차이 처리 내역

현재 마이그레이션에서 실제 사용 중인 SQLite 전용 구문은 두 가지이며, 변환기가 자동 처리한다:

| SQLite | PostgreSQL | 비고 |
|--------|-----------|------|
| `DEFAULT (datetime('now'))` | `DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS'))` | SQLite와 동일한 UTC 문자열 포맷 유지 → 앱 날짜 파싱 로직 무변경 |
| `REAL` | `DOUBLE PRECISION` | PG의 REAL은 4바이트 단정밀도라 정밀도 손실 위험 |

그 외 구문(TEXT/INTEGER, CHECK, REFERENCES, CREATE/DROP INDEX, ALTER TABLE ADD/DROP COLUMN)은 양쪽 문법이 동일하다. `findSqliteArtifacts()`가 생성물에 SQLite 잔여 구문이 없는지 검증하며, 스키마 생성 스크립트는 잔여 구문 발견 시 실패한다.

## 이전 절차 (리허설로 검증됨)

```bash
# 1. 스키마 생성 (마이그레이션 변경 시마다 재실행)
npm run pg:schema

# 2. PostgreSQL에 스키마 적용 (ON_ERROR_STOP으로 부분 적용 방지)
psql "$PG_URL" -v ON_ERROR_STOP=1 -f docs/postgres/schema.sql

# 3. 데이터 내보내기 (운영 SQLite 파일 기준)
#    - BEGIN/COMMIT으로 감싸져 있고 FK 위상 정렬이 적용되어 순서대로 실행하면 안전
#    - schema_migrations는 2단계에서 이미 채워지므로 자동 제외됨
npm run pg:export -- /path/to/app.db /tmp/data.sql

# 4. 데이터 적용
psql "$PG_URL" -v ON_ERROR_STOP=1 -f /tmp/data.sql

# 5. 검증
#    - 테이블별 row count 비교 (SQLite vs PG)
#    - schema_migrations version 목록이 001~017과 일치하는지 확인
#    - 암호화 컬럼 왕복: PG에서 읽은 encrypted_email을 운영 키로 decrypt
```

## 마이그레이션 리허설 결과

PostgreSQL 16.13 실인스턴스 대상, 실제 리포지토리 경로(암호화·감사 로그·
대출 상환·이상거래 플래깅)로 생성한 원본 DB를 이전해 확인한 항목:

| 검증 항목 | 결과 |
|----------|------|
| 스키마 적용 (`ON_ERROR_STOP=1`) | ✅ 13개 테이블, 39개 인덱스, 오류 0건 |
| 테이블별 행 수 대조 (12개 테이블) | ✅ 전체 일치 |
| 작은따옴표 이스케이프 (`Alice O'Brien`) | ✅ 원문 보존 |
| flagged 거래 상태 보존 | ✅ |
| FK 무결성 (고아 행 검사: loans/transactions/loan_payments) | ✅ 0건 |
| JSON 필드 (users_audit.changed_fields) | ✅ 원문 보존 |
| **암호문 왕복** (PG에서 읽은 encrypted_email/phone을 원래 키로 복호화) | ✅ 평문 일치 |
| 변환된 `DEFAULT (to_char(...))` 동작 | ✅ SQLite와 동일한 `YYYY-MM-DD HH:MM:SS` 생성 |
| CHECK 제약 이전 (잘못된 status INSERT 거부) | ✅ |
| schema_migrations 상태 (001~017, 17건) | ✅ |

## 애플리케이션 코드 전환 시 남는 작업 (범위 외)

이 준비 단계는 **스키마·데이터 이전**까지만 다룬다. 실제 커넥션 전환 시 추가로 필요한 작업:

1. **드라이버 교체**: `better-sqlite3`(동기) → `pg`(비동기) — 리포지토리 전 계층의 async 전환 필요
2. **쿼리 방언**: `json_extract()` (UserRepository.getCreditHistory, 감사 로그) → PG `jsonb` 연산자로 교체
3. **파라미터 바인딩**: `?` / `@name` → `$1, $2, ...`
4. **PRAGMA 제거**: `foreign_keys = ON`은 PG에서 기본 동작
5. **트랜잭션 API**: better-sqlite3의 `db.transaction()` → pg의 BEGIN/COMMIT

## 자동 검증

`src/db/pg/__tests__/pgMigration.spec.ts` (19개 테스트):
- 변환 규칙 (datetime/REAL, 호환 구문 보존)
- 실제 마이그레이션 17개 기준 생성물에 SQLite 구문 부재
- 핵심 테이블 포함 여부, 버전 순서 유지
- 리터럴 이스케이프 (인젝션 페이로드 포함), FK 위상 정렬, 왕복 내보내기
