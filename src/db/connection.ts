import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Database from 'better-sqlite3';
import { applyMigrations } from './migrationRunner';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
export const MIGRATIONS_DIR = path.join(currentDir, 'migrations');

/**
 * SQLite는 서버 프로세스 없이 임베디드로 동작하는 실제 SQL 엔진이다.
 * 실제 제약조건(CHECK/UNIQUE/FK)과 인덱스를 강제할 수 있어 테스트 환경에서도
 * "가짜 DB"가 아닌 진짜 무결성 검증이 가능하다. filename에 ':memory:'를 넘기면
 * 테스트마다 격리된 인스턴스를, 파일 경로를 넘기면 영속 저장소를 얻는다.
 */
export function createDatabase(filename: string = ':memory:'): Database.Database {
  const db = new Database(filename);
  db.pragma('foreign_keys = ON');
  applyMigrations(db, MIGRATIONS_DIR);
  return db;
}
