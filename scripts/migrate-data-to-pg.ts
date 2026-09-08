/**
 * SQLite → PostgreSQL 데이터 마이그레이션 스크립트
 *
 * 사용법: ENCRYPTION_KEY=... vite-node scripts/migrate-data-to-pg.ts <sqlite-path> <output-sql-path>
 * 생성된 SQL을 psql로 적용한다: psql "$PG_URL" -v ON_ERROR_STOP=1 -f <output-sql-path>
 */

import fs from 'node:fs';
import Database from 'better-sqlite3';
import { exportDatabaseInserts, listUserTables } from '../src/db/pg/pgDataExporter';

const [sqlitePath, outputPath] = process.argv.slice(2);
if (!sqlitePath || !outputPath) {
  console.error('사용법: vite-node scripts/migrate-data-to-pg.ts <sqlite-path> <output-sql-path>');
  process.exit(1);
}

const db = new Database(sqlitePath, { readonly: true });

const tables = listUserTables(db);
const counts: Record<string, number> = {};
for (const table of tables) {
  counts[table] = (db.prepare(`SELECT COUNT(*) as c FROM ${table}`).get() as { c: number }).c;
}

// schema_migrations는 스키마 적용 시 이미 채워졌으므로 데이터 이전에서 제외한다.
// exportDatabaseInserts가 전체를 내보내므로 여기서 해당 섹션의 INSERT만 걸러낸다.
const script = exportDatabaseInserts(db)
  .split('\n')
  .filter((line) => !line.startsWith('INSERT INTO schema_migrations '))
  .join('\n');

fs.writeFileSync(outputPath, script);

console.log(`데이터 내보내기 완료: ${outputPath}`);
for (const [table, count] of Object.entries(counts).sort()) {
  if (count > 0) console.log(`  ${table}: ${count} rows`);
}
db.close();
