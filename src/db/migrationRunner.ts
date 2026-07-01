import fs from 'node:fs';
import path from 'node:path';
import type Database from 'better-sqlite3';

const UP_MARKER = '-- UP';
const DOWN_MARKER = '-- DOWN';

export interface Migration {
  version: string;
  filename: string;
  up: string;
  down: string;
}

function parseMigrationFile(filePath: string): Migration {
  const content = fs.readFileSync(filePath, 'utf-8');
  const filename = path.basename(filePath);
  const version = filename.split('_')[0];

  const upIndex = content.indexOf(UP_MARKER);
  const downIndex = content.indexOf(DOWN_MARKER);
  if (upIndex === -1 || downIndex === -1) {
    throw new Error(`Migration ${filename} is missing ${UP_MARKER} / ${DOWN_MARKER} markers`);
  }

  const up = content.slice(upIndex + UP_MARKER.length, downIndex).trim();
  const down = content.slice(downIndex + DOWN_MARKER.length).trim();

  return { version, filename, up, down };
}

export function loadMigrations(migrationsDir: string): Migration[] {
  return fs
    .readdirSync(migrationsDir)
    .filter((f) => f.endsWith('.sql'))
    .sort()
    .map((f) => parseMigrationFile(path.join(migrationsDir, f)));
}

export function ensureMigrationsTable(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version TEXT PRIMARY KEY,
      filename TEXT NOT NULL,
      applied_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
  `);
}

export function getAppliedVersions(db: Database.Database): Set<string> {
  ensureMigrationsTable(db);
  const rows = db.prepare('SELECT version FROM schema_migrations').all() as { version: string }[];
  return new Set(rows.map((r) => r.version));
}

export function applyMigrations(db: Database.Database, migrationsDir: string): string[] {
  ensureMigrationsTable(db);
  const migrations = loadMigrations(migrationsDir);
  const applied = getAppliedVersions(db);
  const newlyApplied: string[] = [];

  for (const migration of migrations) {
    if (applied.has(migration.version)) continue;

    const runMigration = db.transaction(() => {
      db.exec(migration.up);
      db.prepare('INSERT INTO schema_migrations (version, filename) VALUES (?, ?)').run(
        migration.version,
        migration.filename
      );
    });
    runMigration();
    newlyApplied.push(migration.version);
  }

  return newlyApplied;
}

export function rollbackLastMigration(db: Database.Database, migrationsDir: string): string | null {
  ensureMigrationsTable(db);
  const lastRow = db
    .prepare('SELECT version, filename FROM schema_migrations ORDER BY version DESC LIMIT 1')
    .get() as { version: string; filename: string } | undefined;

  if (!lastRow) return null;

  const migrations = loadMigrations(migrationsDir);
  const migration = migrations.find((m) => m.version === lastRow.version);
  if (!migration) {
    throw new Error(`Migration file for applied version ${lastRow.version} was not found`);
  }

  const runRollback = db.transaction(() => {
    db.exec(migration.down);
    db.prepare('DELETE FROM schema_migrations WHERE version = ?').run(lastRow.version);
  });
  runRollback();

  return lastRow.version;
}

export function getMigrationStatus(
  db: Database.Database,
  migrationsDir: string
): { version: string; filename: string; applied: boolean }[] {
  const applied = getAppliedVersions(db);
  return loadMigrations(migrationsDir).map((m) => ({
    version: m.version,
    filename: m.filename,
    applied: applied.has(m.version)
  }));
}

export interface MigrationIntegrityIssue {
  version: string;
  message: string;
}

/** DB에 손대지 않고 마이그레이션 파일 자체의 결함(중복 버전, 빈 UP/DOWN)을 미리 잡아낸다 */
export function validateMigrationsIntegrity(migrationsDir: string): MigrationIntegrityIssue[] {
  const migrations = loadMigrations(migrationsDir);
  const issues: MigrationIntegrityIssue[] = [];
  const seenVersions = new Set<string>();

  for (const migration of migrations) {
    if (seenVersions.has(migration.version)) {
      issues.push({
        version: migration.version,
        message: `Duplicate migration version ${migration.version} (${migration.filename})`
      });
    }
    seenVersions.add(migration.version);

    if (migration.up.length === 0) {
      issues.push({ version: migration.version, message: `${migration.filename} has an empty UP section` });
    }
    if (migration.down.length === 0) {
      issues.push({ version: migration.version, message: `${migration.filename} has an empty DOWN section` });
    }
  }

  return issues;
}

export interface DryRunResult {
  wouldApply: string[];
  errors: { version: string; message: string }[];
}

const DRY_RUN_ABORT = Symbol('DRY_RUN_ABORT');

/**
 * 대기 중인 마이그레이션을 트랜잭션 안에서 실제로 실행해 SQL 오류를 미리 잡아내되,
 * 성공 여부와 무관하게 항상 롤백해 DB에 아무 흔적도 남기지 않는다.
 */
export function dryRunMigrations(db: Database.Database, migrationsDir: string): DryRunResult {
  const migrations = loadMigrations(migrationsDir);
  const wouldApply: string[] = [];
  const errors: { version: string; message: string }[] = [];

  try {
    // schema_migrations 생성까지 트랜잭션 안에서 수행해야, 완전히 새 DB에 대한
    // dry-run이 롤백 후 정말로 아무 흔적도 남기지 않는다.
    const attempt = db.transaction(() => {
      ensureMigrationsTable(db);
      const applied = getAppliedVersions(db);
      const pending = migrations.filter((m) => !applied.has(m.version));

      for (const migration of pending) {
        try {
          db.exec(migration.up);
          wouldApply.push(migration.version);
        } catch (error) {
          errors.push({ version: migration.version, message: error instanceof Error ? error.message : String(error) });
          throw error;
        }
      }
      throw DRY_RUN_ABORT;
    });
    attempt();
  } catch (error) {
    if (error !== DRY_RUN_ABORT && errors.length === 0) {
      errors.push({ version: 'unknown', message: error instanceof Error ? error.message : String(error) });
    }
  }

  return { wouldApply, errors };
}
