import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { registerUser } from '@api/userService';
import { issueRefreshToken, revokeRefreshToken, verifyCredentials, verifyRefreshToken } from '@api/authService';

describe('authService (Day 8 - Task 2: 로그인 & JWT 발급, δ=1535)', () => {
  let db: Database.Database;

  beforeEach(() => {
    db = createDatabase(':memory:');
    registerUser(db, { email: 'auth-user@example.com', name: 'Auth User', password: 'correct-horse' });
    registerUser(db, { email: 'no-password-user@example.com', name: 'No Password User' });
  });

  afterEach(() => {
    db.close();
  });

  describe('[T-AUTH-11~14] 자격증명 검증', () => {
    it('[T-AUTH-11] 올바른 이메일/비밀번호는 사용자 프로필을 반환한다', () => {
      const result = verifyCredentials(db, 'auth-user@example.com', 'correct-horse');
      expect(result.success).toBe(true);
      if (result.success) expect(result.data.email).toBe('auth-user@example.com');
    });

    it('[T-AUTH-12] 잘못된 비밀번호는 INVALID_CREDENTIALS를 반환한다', () => {
      const result = verifyCredentials(db, 'auth-user@example.com', 'wrong-password');
      expect(result.success).toBe(false);
      if (!result.success) expect(result.error.code).toBe('INVALID_CREDENTIALS');
    });

    it('[T-AUTH-13] 존재하지 않는 이메일도 동일하게 INVALID_CREDENTIALS를 반환한다 (계정 존재 여부 노출 방지)', () => {
      const result = verifyCredentials(db, 'no-such-user@example.com', 'anything');
      expect(result.success).toBe(false);
      if (!result.success) expect(result.error.code).toBe('INVALID_CREDENTIALS');
    });

    it('[T-AUTH-14] 비밀번호를 설정하지 않은 사용자는 로그인할 수 없다', () => {
      const result = verifyCredentials(db, 'no-password-user@example.com', '');
      expect(result.success).toBe(false);
      if (!result.success) expect(result.error.code).toBe('INVALID_CREDENTIALS');
    });
  });

  describe('[T-AUTH-27~29] 리프레시 토큰 서비스 (Day 9 - Task 3, δ=1155)', () => {
    it('[T-AUTH-27] 발급 → 검증이 동일 사용자로 왕복된다', () => {
      const cred = verifyCredentials(db, 'auth-user@example.com', 'correct-horse');
      const userId = cred.success ? cred.data.id : '';

      const issued = issueRefreshToken(db, userId);
      expect(issued.success).toBe(true);
      if (!issued.success) return;

      const verified = verifyRefreshToken(db, issued.data.token);
      expect(verified.success).toBe(true);
      if (verified.success) expect(verified.data.userId).toBe(userId);
    });

    it('[T-AUTH-28] 알 수 없는 토큰 검증은 INVALID_REFRESH_TOKEN을 반환한다', () => {
      const result = verifyRefreshToken(db, 'no-such-token');
      expect(result.success).toBe(false);
      if (!result.success) expect(result.error.code).toBe('INVALID_REFRESH_TOKEN');
    });

    it('[T-AUTH-29] 무효화 후에는 검증에 실패한다', () => {
      const cred = verifyCredentials(db, 'auth-user@example.com', 'correct-horse');
      const userId = cred.success ? cred.data.id : '';
      const issued = issueRefreshToken(db, userId);
      const token = issued.success ? issued.data.token : '';

      revokeRefreshToken(db, token);

      const result = verifyRefreshToken(db, token);
      expect(result.success).toBe(false);
    });
  });
});
