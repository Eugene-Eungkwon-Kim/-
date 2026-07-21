import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool } from 'pg';
import { getTestPool, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { getCreditHistory, getUserProfile, registerUser, updateUserProfile } from '@api/userService';

describe('userService (Day 6 - Task 1: 사용자 서비스 계층, δ=1615)', () => {
  let pool: Pool;

  beforeEach(async () => {
    pool = getTestPool();
  });

  afterEach(async () => {
    await cleanupTestDatabase();
  });

  describe('[T-SVC-101~106] 사용자 서비스', () => {
    it('[T-SVC-101] 정상 등록', async () => {
      const result = await registerUser(pool, { email: 'svc-user@example.com', name: 'Service User', password: 'test-password-123' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.email).toBe('svc-user@example.com');
        expect(result.data.metadata.version).toBe(1);
      }
    });

    it('[T-SVC-102] 중복 이메일', async () => {
      await registerUser(pool, { email: 'dup@example.com', name: 'First', password: 'test-password-123' });
      const result = await registerUser(pool, { email: 'dup@example.com', name: 'Second', password: 'test-password-123' });

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.code).toBe('DUPLICATE_EMAIL');
      }
    });

    it('[T-SVC-103] 프로필 조회 (존재/미존재)', async () => {
      const created = await registerUser(pool, { email: 'lookup@example.com', name: 'Lookup', password: 'test-password-123' });
      expect(created.success).toBe(true);
      const userId = created.success ? created.data.id : '';

      const found = await getUserProfile(pool, userId);
      expect(found.success).toBe(true);

      const missing = await getUserProfile(pool, 'no-such-id');
      expect(missing.success).toBe(false);
      if (!missing.success) {
        expect(missing.error.code).toBe('USER_NOT_FOUND');
      }
    });

    it('[T-SVC-104] 낙관적 락 충돌', async () => {
      const created = await registerUser(pool, { email: 'lock@example.com', name: 'Lock User', password: 'test-password-123' });
      const userId = created.success ? created.data.id : '';

      const firstUpdate = await updateUserProfile(pool, userId, { name: 'Updated Once' }, 1);
      expect(firstUpdate.success).toBe(true);

      const staleUpdate = await updateUserProfile(pool, userId, { name: 'Stale' }, 1);
      expect(staleUpdate.success).toBe(false);
      if (!staleUpdate.success) {
        expect(staleUpdate.error.code).toBe('VERSION_CONFLICT');
      }
    });

    it('[T-SVC-105] 검증 실패', async () => {
      const result = await registerUser(pool, { email: 'not-an-email', name: 'Bad Email', password: 'test-password-123' });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.code).toBe('VALIDATION_ERROR');
      }
    });

    it('[T-SVC-106] 신용도 히스토리 조회', async () => {
      const created = await registerUser(pool, { email: 'credit@example.com', name: 'Credit User', password: 'test-password-123', creditProfile: { score: 650 } });
      const userId = created.success ? created.data.id : '';

      await updateUserProfile(pool, userId, { creditProfile: { score: 700 } }, 1);

      const history = await getCreditHistory(pool, userId);
      expect(history.success).toBe(true);
      if (history.success) {
        expect(history.data.length).toBe(1);
        expect(history.data[0]).toMatchObject({ from: 650, to: 700 });
      }
    });
  });
});
