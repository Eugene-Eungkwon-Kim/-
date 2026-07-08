import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { getCreditHistory, getUserProfile, registerUser, updateUserProfile } from '@api/userService';

describe('userService (Day 6 - Task 1: 사용자 서비스 계층, δ=1615)', () => {
  let db: Database.Database;

  beforeEach(() => {
    db = createDatabase(':memory:');
  });

  afterEach(() => {
    db.close();
  });

  describe('[T-SVC-101~106] 사용자 서비스', () => {
    it('[T-SVC-101] 정상 등록', () => {
      const result = registerUser(db, { email: 'svc-user@example.com', name: 'Service User', password: 'test-password-123' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.email).toBe('svc-user@example.com');
        expect(result.data.metadata.version).toBe(1);
      }
    });

    it('[T-SVC-102] 중복 이메일', () => {
      registerUser(db, { email: 'dup@example.com', name: 'First', password: 'test-password-123' });
      const result = registerUser(db, { email: 'dup@example.com', name: 'Second', password: 'test-password-123' });

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.code).toBe('DUPLICATE_EMAIL');
      }
    });

    it('[T-SVC-103] 프로필 조회 (존재/미존재)', () => {
      const created = registerUser(db, { email: 'lookup@example.com', name: 'Lookup', password: 'test-password-123' });
      expect(created.success).toBe(true);
      const userId = created.success ? created.data.id : '';

      const found = getUserProfile(db, userId);
      expect(found.success).toBe(true);

      const missing = getUserProfile(db, 'no-such-id');
      expect(missing.success).toBe(false);
      if (!missing.success) {
        expect(missing.error.code).toBe('USER_NOT_FOUND');
      }
    });

    it('[T-SVC-104] 낙관적 락 충돌', () => {
      const created = registerUser(db, { email: 'lock@example.com', name: 'Lock User', password: 'test-password-123' });
      const userId = created.success ? created.data.id : '';

      const firstUpdate = updateUserProfile(db, userId, { name: 'Updated Once' }, 1);
      expect(firstUpdate.success).toBe(true);

      const staleUpdate = updateUserProfile(db, userId, { name: 'Stale' }, 1);
      expect(staleUpdate.success).toBe(false);
      if (!staleUpdate.success) {
        expect(staleUpdate.error.code).toBe('VERSION_CONFLICT');
      }
    });

    it('[T-SVC-105] 검증 실패', () => {
      const result = registerUser(db, { email: 'not-an-email', name: 'Bad Email', password: 'test-password-123' });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.code).toBe('VALIDATION_ERROR');
      }
    });

    it('[T-SVC-106] 신용도 히스토리 조회', () => {
      const created = registerUser(db, { email: 'credit@example.com', name: 'Credit User', password: 'test-password-123', creditProfile: { score: 650 } });
      const userId = created.success ? created.data.id : '';

      updateUserProfile(db, userId, { creditProfile: { score: 700 } }, 1);

      const history = getCreditHistory(db, userId);
      expect(history.success).toBe(true);
      if (history.success) {
        expect(history.data.length).toBe(1);
        expect(history.data[0]).toMatchObject({ from: 650, to: 700 });
      }
    });
  });
});
