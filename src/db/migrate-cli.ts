import { createPgPool, MIGRATIONS_DIR } from './connection';
import {
  applyMigrationsAsync,
  dryRunMigrationsAsync,
  getMigrationStatusAsync,
  rollbackLastMigrationAsync,
  validateMigrationsIntegrity
} from './migrationRunner';

/**
 * 마이그레이션 CLI (PostgreSQL).
 *
 * PostgreSQL 이관 전에는 better-sqlite3 동기 API를 썼는데, 그 패키지가 의존성에서
 * 제거된 뒤에도 임포트가 남아 CLI 전체가 기동조차 못 하는 상태였다. 애플리케이션과
 * 테스트가 이미 쓰고 있는 async 러너로 옮긴다.
 */
async function run(): Promise<void> {
  const command = process.argv[2];

  // DB에 연결하기 전에 파일 자체의 결함(중복 버전, 빈 UP/DOWN)을 먼저 잡는다.
  const issues = validateMigrationsIntegrity(MIGRATIONS_DIR);
  if (issues.length > 0) {
    console.error('Migration integrity issues detected:');
    for (const issue of issues) console.error(`  - [${issue.version}] ${issue.message}`);
    process.exitCode = 1;
    return;
  }

  const pool = createPgPool();
  const client = await pool.connect();

  try {
    switch (command) {
      case 'up': {
        const applied = await applyMigrationsAsync(client, MIGRATIONS_DIR);
        console.log(applied.length > 0 ? `Applied: ${applied.join(', ')}` : 'Already up to date.');
        break;
      }
      case 'down': {
        const rolledBack = await rollbackLastMigrationAsync(client, MIGRATIONS_DIR);
        console.log(rolledBack ? `Rolled back: ${rolledBack}` : 'No migrations to roll back.');
        break;
      }
      case 'status': {
        for (const entry of await getMigrationStatusAsync(client, MIGRATIONS_DIR)) {
          console.log(`[${entry.applied ? 'x' : ' '}] ${entry.version} ${entry.filename}`);
        }
        break;
      }
      case 'dry-run': {
        const result = await dryRunMigrationsAsync(client, MIGRATIONS_DIR);
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
    client.release();
    await pool.end();
  }
}

run().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
