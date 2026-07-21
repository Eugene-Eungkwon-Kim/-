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

    process.on('SIGTERM', async () => {
      await closeDatabasePool();
      process.exit(0);
    });
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(error instanceof Error ? error.message : error);
    await closeDatabasePool();
    process.exit(1);
  }
}

start();
