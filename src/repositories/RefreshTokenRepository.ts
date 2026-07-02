import { randomBytes, randomUUID, createHash } from 'node:crypto';
import type Database from 'better-sqlite3';

const REFRESH_TOKEN_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7일

interface RefreshTokenRow {
  id: string;
  user_id: string;
  token_hash: string;
  expires_at: string;
  revoked_at: string | null;
  created_at: string;
}

export interface IssuedRefreshToken {
  token: string;
  expiresAt: string;
}

export interface VerifiedRefreshToken {
  userId: string;
}

/**
 * 발급된 토큰 원문은 저장하지 않고 SHA-256 해시만 UNIQUE 인덱스로 저장한다.
 * bcrypt가 아니라 SHA-256을 쓰는 이유: bcrypt는 솔트가 매번 달라 결정적이지
 * 않으므로 인덱싱된 조회 키로 쓸 수 없다(UserRepository.verifyPassword처럼
 * email이라는 별도의 조회 키가 없다 — 토큰 값 자체가 유일한 조회 키다).
 * 이 토큰은 randomBytes(32)로 생성된 256비트 무작위값이라 사용자가 고른
 * 저엔트로피 비밀번호와 달리 오프라인 무차별 대입이 애초에 불가능하므로,
 * bcrypt의 의도적인 느림이 주는 이점이 없다.
 */
function hashToken(token: string): string {
  return createHash('sha256').update(token).digest('hex');
}

export class RefreshTokenRepository {
  constructor(private readonly db: Database.Database) {}

  issue(userId: string): IssuedRefreshToken {
    const token = randomBytes(32).toString('base64url');
    const expiresAt = new Date(Date.now() + REFRESH_TOKEN_TTL_MS).toISOString();

    this.db
      .prepare('INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at) VALUES (@id, @userId, @tokenHash, @expiresAt)')
      .run({ id: randomUUID(), userId, tokenHash: hashToken(token), expiresAt });

    return { token, expiresAt };
  }

  /** UserRepository.verifyPassword와 동일한 패턴: 실패는 예외가 아니라 null로 표현한다 */
  verify(token: string): VerifiedRefreshToken | null {
    const row = this.db.prepare('SELECT * FROM refresh_tokens WHERE token_hash = ?').get(hashToken(token)) as
      | RefreshTokenRow
      | undefined;

    if (!row || row.revoked_at) return null;
    if (row.expires_at < new Date().toISOString()) return null;

    return { userId: row.user_id };
  }

  /** 알 수 없거나 이미 무효화된 토큰이어도 항상 성공 처리한다 — 토큰 존재 여부를 노출하지 않기 위함 */
  revoke(token: string): void {
    this.db.prepare("UPDATE refresh_tokens SET revoked_at = datetime('now') WHERE token_hash = ?").run(hashToken(token));
  }
}
