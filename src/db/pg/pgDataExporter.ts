/**
 * Day 15 - Task K: PostgreSQL 마이그레이션 준비 — 데이터 내보내기
 *
 * SQLite 데이터베이스의 모든 사용자 테이블을 FK 의존성 순서에 맞춰
 * PostgreSQL INSERT 문으로 변환한다. 부모 테이블(참조 대상)이
 * 자식보다 먼저 오도록 위상 정렬하므로, 생성된 SQL을 순서대로
 * 실행하면 FK 제약 위반이 발생하지 않는다.
 */

import type Database from 'better-sqlite3';

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
 * 사용자 테이블 목록 (sqlite 내부 테이블 제외).
 */
export function listUserTables(db: Database.Database): string[] {
  const rows = db
    .prepare(
      "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    )
    .all() as { name: string }[];
  return rows.map((r) => r.name);
}

/**
 * FK 의존성 기준 위상 정렬: 참조되는(부모) 테이블이 먼저 온다.
 * 순환 참조가 있으면 에러를 던진다 (현재 스키마에는 없음).
 */
export function sortTablesByForeignKeys(db: Database.Database, tables: string[]): string[] {
  const dependsOn = new Map<string, Set<string>>();
  for (const table of tables) {
    const fks = db.prepare(`PRAGMA foreign_key_list(${table})`).all() as { table: string }[];
    dependsOn.set(
      table,
      new Set(fks.map((fk) => fk.table).filter((parent) => parent !== table && tables.includes(parent)))
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
export function exportTableInserts(db: Database.Database, table: string): string[] {
  const columns = (db.prepare(`PRAGMA table_info(${table})`).all() as { name: string }[]).map(
    (c) => c.name
  );
  const rows = db.prepare(`SELECT * FROM ${table}`).all() as Record<string, unknown>[];

  return rows.map((row) => {
    const values = columns.map((col) => escapePgLiteral(row[col])).join(', ');
    return `INSERT INTO ${table} (${columns.join(', ')}) VALUES (${values});`;
  });
}

/**
 * 데이터베이스 전체를 FK-안전 순서의 PostgreSQL INSERT 스크립트로 변환한다.
 */
export function exportDatabaseInserts(db: Database.Database): string {
  const tables = sortTablesByForeignKeys(db, listUserTables(db));

  const sections = tables.map((table) => {
    const inserts = exportTableInserts(db, table);
    const header = `-- ${table} (${inserts.length} rows)`;
    return inserts.length > 0 ? `${header}\n${inserts.join('\n')}` : header;
  });

  return ['BEGIN;', '', ...sections, '', 'COMMIT;', ''].join('\n\n');
}
