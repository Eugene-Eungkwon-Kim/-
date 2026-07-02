import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createDatabase } from '../db/connection';
import { buildServer } from './app';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = process.env.DATABASE_PATH ?? path.join(currentDir, '../../data/app.db');
const PORT = Number(process.env.PORT ?? 3001);

const db = createDatabase(DB_PATH);
const app = buildServer(db);

app
  .listen({ port: PORT, host: '0.0.0.0' })
  .then(() => {
    // eslint-disable-next-line no-console
    console.log(`API server listening on http://localhost:${PORT} (db: ${DB_PATH})`);
  })
  .catch((error) => {
    // eslint-disable-next-line no-console
    console.error(error);
    process.exit(1);
  });
