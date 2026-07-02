/**
 * 서버 환경설정 검증 (Day 9 - Task 1, δ=1270)
 *
 * JWT_SECRET이 없으면 지금까지는 조용히 'dev-secret-change-in-production'으로
 * 폴백했다 — 운영 배포 시 환경변수 설정을 잊으면 누구나 알려진 시크릿으로
 * 토큰을 위조할 수 있는 실제 취약점이었다. production에서는 fail-fast하고,
 * 개발 환경에서는 경고를 남기되 편의를 위해 폴백을 허용한다.
 */
export interface ServerEnv {
  jwtSecret: string;
  nodeEnv: string;
}

export class MissingJwtSecretError extends Error {
  constructor() {
    super('JWT_SECRET environment variable must be set when NODE_ENV=production');
    this.name = 'MissingJwtSecretError';
  }
}

const DEV_FALLBACK_SECRET = 'dev-secret-change-in-production';

export function resolveServerEnv(env: NodeJS.ProcessEnv = process.env): ServerEnv {
  const nodeEnv = env.NODE_ENV ?? 'development';
  const jwtSecretFromEnv = env.JWT_SECRET;

  if (jwtSecretFromEnv) {
    return { jwtSecret: jwtSecretFromEnv, nodeEnv };
  }

  if (nodeEnv === 'production') {
    throw new MissingJwtSecretError();
  }

  // eslint-disable-next-line no-console
  console.warn(
    '[server] JWT_SECRET is not set — using an insecure development fallback secret. ' +
      'Set JWT_SECRET before deploying to production.'
  );
  return { jwtSecret: DEV_FALLBACK_SECRET, nodeEnv };
}
