/**
 * Day 15 - Task K: PostgreSQL 통합 스키마 생성 스크립트
 *
 * 사용법: npm run pg:schema
 * 출력: docs/postgres/schema.sql
 */

import fs from 'node:fs';
import path from 'node:path';
import { MIGRATIONS_DIR } from '../src/db/connection';
import { generatePostgresSchema, findSqliteArtifacts } from '../src/db/pg/pgSchemaGenerator';

const outDir = path.join(process.cwd(), 'docs', 'postgres');
const outFile = path.join(outDir, 'schema.sql');

const schema = generatePostgresSchema(MIGRATIONS_DIR);

const artifacts = findSqliteArtifacts(schema);
if (artifacts.length > 0) {
  console.error(`변환 실패: SQLite 전용 구문이 남아있습니다 — ${artifacts.join(', ')}`);
  process.exit(1);
}

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(outFile, schema);
console.log(`PostgreSQL 스키마 생성 완료: ${outFile} (${schema.split('\n').length} lines)`);
