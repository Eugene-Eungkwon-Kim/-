import { createPgPool, initializeDatabase, closeDatabasePool } from '../db/connection';
import { buildServer } from './app';
import { resolveServerEnv } from './env';
import { verifyEncryptionKeyAgainstDb } from '../utils/encryption';

const PORT = Number(process.env.PORT ?? 3001);

async function start() {
  let serverEnv;
  try {
    serverEnv = resolveServerEnv();
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  }

  process.env.ENCRYPTION_KEY = serverEnv.encryptionKey;

  const pool = createPgPool();

  try {
    await initializeDatabase(pool);

    await verifyEncryptionKeyAgainstDb(pool);

    const app = await buildServer(pool, { jwtSecret: serverEnv.jwtSecret });

    app
      .listen({ port: PORT, host: '0.0.0.0' })
      .then(() => {
        // eslint-disable-next-line no-console
        console.log(`API server listening on http://localhost:${PORT}`);
      })
      .catch((error) => {
        // eslint-disable-next-line no-console
        console.error(error);
        process.exit(1);
      });

    // 종료 시 app.close()를 먼저 호출해야 buildServer가 등록한 onClose 훅이 돌고,
    // 그 훅이 알림 허브의 Redis 연결(발행·구독 2개)을 닫는다. 이 호출 없이
    // closeDatabasePool()만 하거나 process.exit()을 먼저 부르면 연결이 그대로 남고
    // 열려 있던 SSE 연결도 배수되지 않는다.
    let shuttingDown = false;
    const shutdown = async (signal: string): Promise<void> => {
      if (shuttingDown) return;
      shuttingDown = true;

      // eslint-disable-next-line no-console
      console.log(`${signal} received, shutting down`);
      try {
        await app.close();
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('Error while closing server:', error);
      }
      await closeDatabasePool();
      process.exit(0);
    };

    for (const signal of ['SIGTERM', 'SIGINT'] as const) {
      process.on(signal, () => {
        void shutdown(signal);
      });
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(error instanceof Error ? error.message : error);
    await closeDatabasePool();
    process.exit(1);
  }
}

start();
