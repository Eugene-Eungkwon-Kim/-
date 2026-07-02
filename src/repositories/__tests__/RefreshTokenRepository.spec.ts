import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { UserRepository } from '@repositories/UserRepository';
import { RefreshTokenRepository } from '@repositories/RefreshTokenRepository';

describe('RefreshTokenRepository (Day 9 - Task 3: 리프레시 토큰 & 세션 연장, δ=1155)', () => {
  let db: Database.Database;
  let users: UserRepository;
  let tokens: RefreshTokenRepository;
  let userId: string;

  beforeEach(() => {
    db = createDatabase(':memory:');
    users = new UserRepository(db);
    tokens = new RefreshTokenRepository(db);
    userId = users.register({ email: 'refresh-user@example.com', name: 'Refresh User', password: 'correct-horse' }).id;
  });

  afterEach(() => {
    db.close();
  });

  describe('[T-AUTH-21~26] 리프레시 토큰 발급/검증/무효화', () => {
    it('[T-AUTH-21] 발급된 토큰은 원문 그대로 DB에 저장되지 않는다', () => {
      const issued = tokens.issue(userId);
      const row = db.prepare('SELECT token_hash FROM refresh_tokens').get() as { token_hash: string };
      expect(row.token_hash).not.toBe(issued.token);
      expect(row.token_hash).toHaveLength(64); // sha256 hex
    });

    it('[T-AUTH-22] 발급된 토큰으로 verify하면 userId를 반환한다', () => {
      const issued = tokens.issue(userId);
      const verified = tokens.verify(issued.token);
      expect(verified?.userId).toBe(userId);
    });

    it('[T-AUTH-23] 존재하지 않는 토큰은 null을 반환한다', () => {
      expect(tokens.verify('not-a-real-token')).toBeNull();
    });

    it('[T-AUTH-24] 무효화(revoke)된 토큰은 재검증에 실패한다', () => {
      const issued = tokens.issue(userId);
      tokens.revoke(issued.token);
      expect(tokens.verify(issued.token)).toBeNull();
    });

    it('[T-AUTH-25] 알 수 없는 토큰을 revoke해도 예외 없이 성공 처리된다 (존재 여부 비노출)', () => {
      expect(() => tokens.revoke('unknown-token')).not.toThrow();
    });

    it('[T-AUTH-26] 만료된 토큰은 검증에 실패한다', () => {
      const issued = tokens.issue(userId);
      // 발급 로직을 우회해 만료 시각을 과거로 직접 조작 (실제 만료 시나리오 재현)
      db.prepare('UPDATE refresh_tokens SET expires_at = ? WHERE token_hash IS NOT NULL').run(
        new Date(Date.now() - 1000).toISOString()
      );
      expect(tokens.verify(issued.token)).toBeNull();
    });
  });
});
