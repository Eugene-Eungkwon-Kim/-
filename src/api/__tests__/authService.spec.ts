import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool } from 'pg';
import { getTestPool, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { registerUser } from '@api/userService';
import { issueRefreshToken, revokeRefreshToken, verifyCredentials, verifyRefreshToken } from '@api/authService';

describe('authService (Day 8 - Task 2: 로그인 & JWT 발급, δ=1535)', () => {
  let pool: Pool;

  beforeEach(async () => {
    pool = getTestPool();
    await registerUser(pool, { email: 'auth-user@example.com', name: 'Auth User', password: 'correct-horse' });
  });

  afterEach(async () => {
    await cleanupTestDatabase();
  });

  describe('[T-AUTH-11~14] 자격증명 검증', () => {
    it('[T-AUTH-11] 올바른 이메일/비밀번호는 사용자 프로필을 반환한다', async () => {
      const result = await verifyCredentials(pool, 'auth-user@example.com', 'correct-horse');
      expect(result.success).toBe(true);
      if (result.success) expect(result.data.email).toBe('auth-user@example.com');
    });

    it('[T-AUTH-12] 잘못된 비밀번호는 INVALID_CREDENTIALS를 반환한다', async () => {
      const result = await verifyCredentials(pool, 'auth-user@example.com', 'wrong-password');
      expect(result.success).toBe(false);
      if (!result.success) expect(result.error.code).toBe('INVALID_CREDENTIALS');
    });

    it('[T-AUTH-13] 존재하지 않는 이메일도 동일하게 INVALID_CREDENTIALS를 반환한다 (계정 존재 여부 노출 방지)', async () => {
      const result = await verifyCredentials(pool, 'no-such-user@example.com', 'anything');
      expect(result.success).toBe(false);
      if (!result.success) expect(result.error.code).toBe('INVALID_CREDENTIALS');
    });

    it('[T-AUTH-14] 빈 비밀번호로 로그인 시도는 VALIDATION_ERROR를 반환한다', async () => {
      const result = await verifyCredentials(pool, 'auth-user@example.com', '');
      expect(result.success).toBe(false);
      if (!result.success) expect(result.error.code).toBe('VALIDATION_ERROR');
    });
  });

  describe('[T-AUTH-27~29] 리프레시 토큰 서비스 (Day 9 - Task 3, δ=1155)', () => {
    it('[T-AUTH-27] 발급 → 검증이 동일 사용자로 왕복된다', async () => {
      const cred = await verifyCredentials(pool, 'auth-user@example.com', 'correct-horse');
      const userId = cred.success ? cred.data.id : '';

      const issued = await issueRefreshToken(pool, userId);
      expect(issued.success).toBe(true);
      if (!issued.success) return;

      const verified = await verifyRefreshToken(pool, issued.data.token);
      expect(verified.success).toBe(true);
      if (verified.success) expect(verified.data.userId).toBe(userId);
    });

    it('[T-AUTH-28] 알 수 없는 토큰 검증은 INVALID_REFRESH_TOKEN을 반환한다', async () => {
      const result = await verifyRefreshToken(pool, 'no-such-token');
      expect(result.success).toBe(false);
      if (!result.success) expect(result.error.code).toBe('INVALID_REFRESH_TOKEN');
    });

    it('[T-AUTH-29] 무효화 후에는 검증에 실패한다', async () => {
      const cred = await verifyCredentials(pool, 'auth-user@example.com', 'correct-horse');
      const userId = cred.success ? cred.data.id : '';
      const issued = await issueRefreshToken(pool, userId);
      const token = issued.success ? issued.data.token : '';

      await revokeRefreshToken(pool, token);

      const result = await verifyRefreshToken(pool, token);
      expect(result.success).toBe(false);
    });
  });
});
