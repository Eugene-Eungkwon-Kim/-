/**
 * 서버 환경설정 검증 (Day 9 - Task 1, δ=1270 / 디버깅 세션에서 확장)
 *
 * JWT_SECRET이 없으면 지금까지는 조용히 'dev-secret-change-in-production'으로
 * 폴백했다 — 운영 배포 시 환경변수 설정을 잊으면 누구나 알려진 시크릿으로
 * 토큰을 위조할 수 있는 실제 취약점이었다. production에서는 fail-fast하고,
 * 개발 환경에서는 경고를 남기되 편의를 위해 폴백을 허용한다.
 *
 * ENCRYPTION_KEY도 같은 원칙을 적용한다. Day 13부터 회원가입이 무조건
 * PII 암호화를 수행하므로, 키가 없으면 서버는 정상 기동되지만 모든
 * 회원가입이 500으로 실패한다 — 헬스체크가 통과하는 만큼 더 찾기 어려운
 * 장애다. production에서는 부팅 전에 실패시키고, 개발에서는 결정적
 * 폴백 키를 사용해 재시작 후에도 기존 데이터를 복호화할 수 있게 한다.
 * 단, 형식이 잘못된 키는 환경을 불문하고 즉시 실패한다 — 조용히 다른
 * 키로 폴백하면 이미 저장된 암호문을 영영 못 읽게 되는 사고로 이어진다.
 */
export interface ServerEnv {
  jwtSecret: string;
  encryptionKey: string;
  nodeEnv: string;
}

export class MissingJwtSecretError extends Error {
  constructor() {
    super('JWT_SECRET environment variable must be set when NODE_ENV=production');
    this.name = 'MissingJwtSecretError';
  }
}

export class MissingEncryptionKeyError extends Error {
  constructor() {
    super('ENCRYPTION_KEY environment variable must be set when NODE_ENV=production');
    this.name = 'MissingEncryptionKeyError';
  }
}

export class InvalidEncryptionKeyError extends Error {
  constructor() {
    super('ENCRYPTION_KEY must be a 64-character hex string (256 bits)');
    this.name = 'InvalidEncryptionKeyError';
  }
}

const DEV_FALLBACK_SECRET = 'dev-secret-change-in-production';
// 개발 전용 결정적 폴백 키. 재시작마다 랜덤 생성하면 이전에 암호화된
// 개발 데이터를 복호화할 수 없게 되므로 고정값을 쓴다.
const DEV_FALLBACK_ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';

const ENCRYPTION_KEY_FORMAT = /^[0-9a-f]{64}$/i;

export function resolveServerEnv(env: NodeJS.ProcessEnv = process.env): ServerEnv {
  const nodeEnv = env.NODE_ENV ?? 'development';
  const isProduction = nodeEnv === 'production';

  let jwtSecret = env.JWT_SECRET;
  if (!jwtSecret) {
    if (isProduction) throw new MissingJwtSecretError();
    // eslint-disable-next-line no-console
    console.warn(
      '[server] JWT_SECRET is not set — using an insecure development fallback secret. ' +
        'Set JWT_SECRET before deploying to production.'
    );
    jwtSecret = DEV_FALLBACK_SECRET;
  }

  let encryptionKey = env.ENCRYPTION_KEY;
  if (encryptionKey) {
    // 형식 오류는 환경 불문 즉시 실패 — 잘못된 키로 폴백하면 기존 암호문을 못 읽는다
    if (!ENCRYPTION_KEY_FORMAT.test(encryptionKey)) throw new InvalidEncryptionKeyError();
  } else {
    if (isProduction) throw new MissingEncryptionKeyError();
    // eslint-disable-next-line no-console
    console.warn(
      '[server] ENCRYPTION_KEY is not set — using an insecure development fallback key. ' +
        'Set ENCRYPTION_KEY (64-char hex, e.g. from generateEncryptionKey()) before deploying to production.'
    );
    encryptionKey = DEV_FALLBACK_ENCRYPTION_KEY;
  }

  return { jwtSecret, encryptionKey, nodeEnv };
}
