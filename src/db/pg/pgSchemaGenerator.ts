/**
 * Day 15 - Task K: PostgreSQL 마이그레이션 준비 — 스키마 변환기
 *
 * SQLite 마이그레이션(UP 섹션)을 PostgreSQL 호환 DDL로 변환해
 * 하나의 통합 스키마 파일을 생성한다. 실제 데이터 이전은
 * pgDataExporter.ts가 담당한다.
 *
 * 현재 마이그레이션에서 실제로 사용 중인 SQLite 전용 구문은 두 가지뿐이다:
 *   1. DEFAULT (datetime('now'))  — UTC 'YYYY-MM-DD HH:MM:SS' 문자열
 *   2. REAL 타입
 * 그 외(TEXT/INTEGER, CHECK, REFERENCES, CREATE/DROP INDEX,
 * ALTER TABLE ADD/DROP COLUMN)는 PostgreSQL과 문법이 동일하다.
 */

import { loadMigrations } from '../migrationRunner';

/**
 * SQLite DDL 한 조각을 PostgreSQL 호환 DDL로 변환한다.
 */
export function translateSqliteDdlToPostgres(sql: string): string {
  let out = sql;

  // datetime('now')는 SQLite에서 UTC 기준 'YYYY-MM-DD HH:MM:SS' 문자열을 반환한다.
  // 컬럼 타입이 TEXT이므로, PostgreSQL에서도 동일한 포맷의 문자열을 기본값으로
  // 생성해 애플리케이션 레이어의 날짜 파싱 로직을 그대로 유지한다.
  out = out.replace(
    /\(datetime\('now'\)\)/g,
    "(to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS'))"
  );

  // REAL → DOUBLE PRECISION (PostgreSQL의 REAL은 4바이트 단정밀도라 정밀도가 다르다)
  out = out.replace(/\bREAL\b/g, 'DOUBLE PRECISION');

  return out;
}

/**
 * 변환 결과에 SQLite 전용 구문이 남아있으면 그 목록을 반환한다 (검증용).
 */
export function findSqliteArtifacts(sql: string): string[] {
  const artifacts: Array<[RegExp, string]> = [
    [/datetime\(/, "datetime('now')"],
    [/strftime\(/, 'strftime()'],
    [/\bAUTOINCREMENT\b/, 'AUTOINCREMENT'],
    [/\bPRAGMA\b/, 'PRAGMA'],
    [/\bWITHOUT ROWID\b/, 'WITHOUT ROWID'],
    [/\bREAL\b/, 'REAL']
  ];
  return artifacts.filter(([re]) => re.test(sql)).map(([, name]) => name);
}

/**
 * schema_migrations 테이블은 코드(ensureMigrationsTable)가 만들기 때문에
 * 마이그레이션 파일에 없다. PostgreSQL 스키마에는 명시적으로 포함하고,
 * 모든 버전을 적용됨으로 기록해 이중 적용을 방지한다.
 */
function migrationsTableDdl(versions: Array<{ version: string; filename: string }>): string {
  const inserts = versions
    .map(
      (m) =>
        `INSERT INTO schema_migrations (version, filename) VALUES ('${m.version}', '${m.filename}');`
    )
    .join('\n');

  return [
    'CREATE TABLE schema_migrations (',
    '  version TEXT PRIMARY KEY,',
    '  filename TEXT NOT NULL,',
    "  applied_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS'))",
    ');',
    '',
    inserts
  ].join('\n');
}

/**
 * 마이그레이션 디렉토리 전체를 PostgreSQL 통합 스키마로 변환한다.
 */
export function generatePostgresSchema(migrationsDir: string): string {
  const migrations = loadMigrations(migrationsDir);

  const sections = migrations.map((m) => {
    const translated = translateSqliteDdlToPostgres(m.up);
    return `-- ===== ${m.filename} =====\n${translated}`;
  });

  const header = [
    '-- MAARS PostgreSQL 통합 스키마',
    '-- SQLite 마이그레이션에서 자동 생성됨 — 직접 수정하지 말 것',
    `-- 원본 마이그레이션: ${migrations.length}개 (${migrations[0]?.version} ~ ${migrations[migrations.length - 1]?.version})`,
    ''
  ].join('\n');

  return [
    header,
    ...sections,
    '',
    '-- ===== schema_migrations (마이그레이션 러너 상태) =====',
    migrationsTableDdl(migrations.map((m) => ({ version: m.version, filename: m.filename }))),
    ''
  ].join('\n\n');
}
