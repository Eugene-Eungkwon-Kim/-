import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Database from 'better-sqlite3';
import {
  applyMigrations,
  dryRunMigrations,
  getMigrationStatus,
  rollbackLastMigration,
  validateMigrationsIntegrity
} from './migrationRunner';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const MIGRATIONS_DIR = path.join(currentDir, 'migrations');
const DEFAULT_DB_PATH = path.join(currentDir, '../../data/app.db');

function openDatabase(): Database.Database {
  const db = new Database(process.env.DATABASE_PATH ?? DEFAULT_DB_PATH);
  db.pragma('foreign_keys = ON');
  return db;
}

function printStatus(db: Database.Database): void {
  for (const entry of getMigrationStatus(db, MIGRATIONS_DIR)) {
    console.log(`[${entry.applied ? 'x' : ' '}] ${entry.version} ${entry.filename}`);
  }
}

function run(): void {
  const command = process.argv[2];

  const issues = validateMigrationsIntegrity(MIGRATIONS_DIR);
  if (issues.length > 0) {
    console.error('Migration integrity issues detected:');
    for (const issue of issues) console.error(`  - [${issue.version}] ${issue.message}`);
    process.exitCode = 1;
    return;
  }

  const db = openDatabase();
  try {
    switch (command) {
      case 'up': {
        const applied = applyMigrations(db, MIGRATIONS_DIR);
        console.log(applied.length > 0 ? `Applied: ${applied.join(', ')}` : 'Already up to date.');
        break;
      }
      case 'down': {
        const rolledBack = rollbackLastMigration(db, MIGRATIONS_DIR);
        console.log(rolledBack ? `Rolled back: ${rolledBack}` : 'No migrations to roll back.');
        break;
      }
      case 'status': {
        printStatus(db);
        break;
      }
      case 'dry-run': {
        const result = dryRunMigrations(db, MIGRATIONS_DIR);
        console.log(`Would apply: ${result.wouldApply.join(', ') || '(none)'}`);
        if (result.errors.length > 0) {
          console.error('Errors:');
          for (const err of result.errors) console.error(`  - [${err.version}] ${err.message}`);
          process.exitCode = 1;
        }
        break;
      }
      default: {
        console.error('Usage: migrate-cli <up|down|status|dry-run>');
        process.exitCode = 1;
      }
    }
  } finally {
    db.close();
  }
}

run();
