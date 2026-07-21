import { randomBytes, randomUUID, createHash } from 'node:crypto';
import type { Pool } from 'pg';

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

function hashToken(token: string): string {
  return createHash('sha256').update(token).digest('hex');
}

export class RefreshTokenRepository {
  constructor(private readonly pool: Pool) {}

  async issue(userId: string): Promise<IssuedRefreshToken> {
    const token = randomBytes(32).toString('base64url');
    const expiresAt = new Date(Date.now() + REFRESH_TOKEN_TTL_MS).toISOString();

    await this.pool.query(
      'INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at) VALUES ($1, $2, $3, $4)',
      [randomUUID(), userId, hashToken(token), expiresAt]
    );

    return { token, expiresAt };
  }

  async verify(token: string): Promise<VerifiedRefreshToken | null> {
    const result = await this.pool.query(
      'SELECT * FROM refresh_tokens WHERE token_hash = $1',
      [hashToken(token)]
    );
    const row = result.rows[0] as RefreshTokenRow | undefined;

    if (!row || row.revoked_at) return null;
    if (row.expires_at < new Date().toISOString()) return null;

    return { userId: row.user_id };
  }

  async revoke(token: string): Promise<void> {
    await this.pool.query(
      'UPDATE refresh_tokens SET revoked_at = CURRENT_TIMESTAMP WHERE token_hash = $1',
      [hashToken(token)]
    );
  }
}
