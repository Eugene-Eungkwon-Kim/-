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
