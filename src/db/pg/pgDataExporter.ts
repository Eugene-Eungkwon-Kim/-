/**
 * Day 15 - Task K: PostgreSQL 마이그레이션 준비 — 데이터 내보내기
 *
 * PostgreSQL 데이터베이스의 모든 사용자 테이블을 FK 의존성 순서에 맞춰
 * PostgreSQL INSERT 문으로 변환한다. 부모 테이블(참조 대상)이
 * 자식보다 먼저 오도록 위상 정렬하므로, 생성된 SQL을 순서대로
 * 실행하면 FK 제약 위반이 발생하지 않는다.
 */

import type { Pool } from 'pg';

/**
 * 값 하나를 PostgreSQL 리터럴로 이스케이프한다.
 * (standard_conforming_strings=on 기준: 작은따옴표만 이중화하면 된다)
 */
export function escapePgLiteral(value: unknown): string {
  if (value === null || value === undefined) return 'NULL';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error(`Cannot export non-finite number: ${value}`);
    return String(value);
  }
  if (typeof value === 'bigint') return value.toString();
  if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE';
  if (Buffer.isBuffer(value)) return `'\\x${value.toString('hex')}'`;
  return `'${String(value).replace(/'/g, "''")}'`;
}

/**
 * 사용자 테이블 목록 (public 스키마 기준).
 *
 * 마이그레이션 상태 관리용 부킹 테이블 schema_migrations는 제외한다.
 * (SQLite 시절에는 이런 테이블이 사용자 데이터 내보내기 범위에 없었으므로,
 *  실제 사용자/도메인 테이블만 대상으로 유지한다.)
 */
export async function listUserTables(pool: Pool): Promise<string[]> {
  const result = await pool.query(
    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'schema_migrations'"
  );
  return result.rows.map((r: { tablename: string }) => r.tablename);
}

/**
 * FK 의존성 기준 위상 정렬: 참조되는(부모) 테이블이 먼저 온다.
 * 순환 참조가 있으면 에러를 던진다 (현재 스키마에는 없음).
 */
export async function sortTablesByForeignKeys(pool: Pool, tables: string[]): Promise<string[]> {
  const dependsOn = new Map<string, Set<string>>();
  for (const table of tables) {
    const result = await pool.query(
      `SELECT ccu.table_name AS parent
       FROM information_schema.table_constraints tc
       JOIN information_schema.constraint_column_usage ccu
         ON tc.constraint_name = ccu.constraint_name
        AND tc.table_schema = ccu.table_schema
       WHERE tc.constraint_type = 'FOREIGN KEY'
         AND tc.table_name = $1
         AND tc.table_schema = 'public'`,
      [table]
    );
    const parents = result.rows.map((fk: { parent: string }) => fk.parent);
    dependsOn.set(
      table,
      new Set(parents.filter((parent) => parent !== table && tables.includes(parent)))
    );
  }

  const sorted: string[] = [];
  const visited = new Set<string>();
  const visiting = new Set<string>();

  const visit = (table: string): void => {
    if (visited.has(table)) return;
    if (visiting.has(table)) throw new Error(`Circular foreign key dependency involving: ${table}`);
    visiting.add(table);
    for (const parent of dependsOn.get(table) ?? []) visit(parent);
    visiting.delete(table);
    visited.add(table);
    sorted.push(table);
  };

  for (const table of tables) visit(table);
  return sorted;
}

/**
 * 한 테이블의 모든 행을 INSERT 문 배열로 변환한다.
 */
export async function exportTableInserts(pool: Pool, table: string): Promise<string[]> {
  const columnsResult = await pool.query(
    `SELECT column_name FROM information_schema.columns
     WHERE table_name = $1 AND table_schema = 'public'
     ORDER BY ordinal_position`,
    [table]
  );
  const columns = columnsResult.rows.map((c: { column_name: string }) => c.column_name);

  // 테이블/컬럼 이름은 카탈로그(신뢰 가능한 출처)에서 얻으므로
  // SQL에 직접 삽입해도 안전하다 (원본 SQLite 구현과 동일).
  const rows = (await pool.query(`SELECT * FROM ${table}`)).rows as Record<string, unknown>[];

  return rows.map((row) => {
    const values = columns.map((col) => escapePgLiteral(row[col])).join(', ');
    return `INSERT INTO ${table} (${columns.join(', ')}) VALUES (${values});`;
  });
}

/**
 * 데이터베이스 전체를 FK-안전 순서의 PostgreSQL INSERT 스크립트로 변환한다.
 */
export async function exportDatabaseInserts(pool: Pool): Promise<string> {
  const tables = await sortTablesByForeignKeys(pool, await listUserTables(pool));

  const sections: string[] = [];
  for (const table of tables) {
    const inserts = await exportTableInserts(pool, table);
    const header = `-- ${table} (${inserts.length} rows)`;
    sections.push(inserts.length > 0 ? `${header}\n${inserts.join('\n')}` : header);
  }

  return ['BEGIN;', '', ...sections, '', 'COMMIT;', ''].join('\n\n');
}
