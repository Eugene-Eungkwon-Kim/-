import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createDatabase } from '../db/connection';
import { buildServer } from './app';
import { resolveServerEnv } from './env';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = process.env.DATABASE_PATH ?? path.join(currentDir, '../../data/app.db');
const PORT = Number(process.env.PORT ?? 3001);

// 환경설정 검증을 DB 연결/포트 바인딩보다 먼저 수행해, production에서
// JWT_SECRET이 빠졌다면 서버가 뜨기도 전에 즉시 실패하도록 한다.
let serverEnv;
try {
  serverEnv = resolveServerEnv();
} catch (error) {
  // eslint-disable-next-line no-console
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
}

const db = createDatabase(DB_PATH);
const app = buildServer(db, { jwtSecret: serverEnv.jwtSecret });

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
