import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createDatabase } from '../db/connection';
import { buildServer } from './app';
import { resolveServerEnv } from './env';
import { verifyEncryptionKeyAgainstDb } from '../utils/encryption';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = process.env.DATABASE_PATH ?? path.join(currentDir, '../../data/app.db');
const PORT = Number(process.env.PORT ?? 3001);

// 환경설정 검증을 DB 연결/포트 바인딩보다 먼저 수행해, production에서
// JWT_SECRET/ENCRYPTION_KEY가 빠졌다면 서버가 뜨기도 전에 즉시 실패하도록 한다.
let serverEnv;
try {
  serverEnv = resolveServerEnv();
} catch (error) {
  // eslint-disable-next-line no-console
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
}

// encryption.ts의 getEncryptionKey()는 process.env를 직접 읽으므로,
// 개발 폴백 키가 선택된 경우에도 여기서 주입해 단일 소스를 유지한다.
process.env.ENCRYPTION_KEY = serverEnv.encryptionKey;

const db = createDatabase(DB_PATH);

// 키가 교체/오타난 채 기동하면 암호화 컬럼을 읽는 모든 요청이 사용자별 500으로
// 산발한다. 기존 암호문 하나를 실제로 복호화해 부팅 단계에서 잡아낸다.
try {
  verifyEncryptionKeyAgainstDb(db);
} catch (error) {
  // eslint-disable-next-line no-console
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
}

const app = await buildServer(db, { jwtSecret: serverEnv.jwtSecret });

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
