import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Pool } from 'pg';
import { applyMigrationsAsync } from './migrationRunner';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
export const MIGRATIONS_DIR = path.join(currentDir, 'migrations');

export interface DBConnection {
  query: (text: string, values?: any[]) => Promise<any>;
  close: () => Promise<void>;
}

let globalPool: Pool | null = null;

export function createPgPool(): Pool {
  return new Pool({
    host: process.env.PG_HOST || 'localhost',
    port: parseInt(process.env.PG_PORT || '5432'),
    database: process.env.PG_DATABASE || 'maars',
    user: process.env.PG_USER || 'postgres',
    password: process.env.PG_PASSWORD,
    max: 20,
  });
}

export async function initializeDatabase(pool: Pool): Promise<void> {
  globalPool = pool;
  const client = await pool.connect();
  try {
    await applyMigrationsAsync(client, MIGRATIONS_DIR);
  } finally {
    client.release();
  }
}

export function getDatabase(): Pool {
  if (!globalPool) {
    throw new Error('Database pool not initialized. Call initializeDatabase first.');
  }
  return globalPool;
}

export async function closeDatabasePool(): Promise<void> {
  if (globalPool) {
    await globalPool.end();
    globalPool = null;
  }
}
