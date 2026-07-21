import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool } from 'pg';
import { getTestPool, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { UserRepository } from '@repositories/UserRepository';
import { DuplicateEmailError, OptimisticLockError, ValidationError } from '@repositories/errors';

describe('UserRepository (Day 5 - Task 1: 사용자 프로필 & 계정 관리, δ=1635)', () => {
  let pool: Pool;
  let repo: UserRepository;

  beforeEach(async () => {
    pool = getTestPool();
    repo = new UserRepository(pool);
  });

  afterEach(async () => {
    await cleanupTestDatabase();
  });

  describe('[T-API-A01~A06] 사용자 프로필 & 계정 관리', () => {
    it('[T-API-A01] 사용자 등록 (정상)', async () => {
      const profile = await repo.register({
        email: 'jane.doe@example.com',
        name: 'Jane Doe',
        employment: { status: 'employed', industry: 'finance', tenure: 36, company: 'Acme' },
        contact: { phone: '010-1234-5678', address: { city: 'Seoul', country: 'KR' } },
        creditProfile: { score: 820 },
        financialSnapshot: { monthlyIncome: 6000000, monthlyExpenses: 2000000, totalAssets: 300000000, totalDebt: 50000000, savingsRate: 20 }
      });

      expect(profile.id).toBeDefined();
      expect(profile.email).toBe('jane.doe@example.com');
      expect(profile.creditProfile.grade).toBe('A');
      expect(profile.metadata.version).toBe(1);
      expect(profile.metadata.status).toBe('active');
      expect(profile.employment.company).toBe('Acme');
    });

    it('[T-API-A02] 중복 이메일 방지', async () => {
      await repo.register({ email: 'dup@example.com', name: 'First User' });

      await expect(repo.register({ email: 'dup@example.com', name: 'Second User' })).rejects.toThrow(DuplicateEmailError);
    });

    it('[T-API-A03] 프로필 조회', async () => {
      const created = await repo.register({ email: 'lookup@example.com', name: 'Lookup User', creditProfile: { score: 710 } });

      const found = await repo.getProfile(created.id);
      expect(found).not.toBeNull();
      expect(found?.email).toBe('lookup@example.com');
      expect(found?.creditProfile.grade).toBe('B');

      const missing = await repo.getProfile('non-existent-id');
      expect(missing).toBeNull();
    });

    it('[T-API-A04] 프로필 수정 (동시성 - 낙관적 락)', async () => {
      const created = await repo.register({ email: 'concurrent@example.com', name: 'Concurrent User', creditProfile: { score: 650 } });
      expect(created.metadata.version).toBe(1);

      const updated = await repo.updateProfile(created.id, { name: 'Updated Name' }, 1);
      expect(updated.name).toBe('Updated Name');
      expect(updated.metadata.version).toBe(2);

      // 두 번째 갱신자가 구버전(version=1) 그대로 재시도 → 충돌 감지
      await expect(repo.updateProfile(created.id, { name: 'Stale Writer' }, 1)).rejects.toThrow(OptimisticLockError);

      // 최신 버전(2)으로 재시도하면 성공
      const secondUpdate = await repo.updateProfile(created.id, { name: 'Second Writer' }, 2);
      expect(secondUpdate.name).toBe('Second Writer');
      expect(secondUpdate.metadata.version).toBe(3);
    });

    it('[T-API-A05] 신용도 히스토리 조회', async () => {
      const created = await repo.register({ email: 'credit-history@example.com', name: 'History User', creditProfile: { score: 650 } });

      await repo.updateProfile(created.id, { creditProfile: { score: 700 } }, 1);
      await repo.updateProfile(created.id, { creditProfile: { score: 680 } }, 2);

      const history = await repo.getCreditHistory(created.id);
      expect(history.length).toBe(2);
      expect(history[0]).toEqual({ changedAt: history[0].changedAt, from: 650, to: 700 });
      expect(history[1]).toEqual({ changedAt: history[1].changedAt, from: 700, to: 680 });
    });

    it('[T-API-A06] 감사 로그 추적', async () => {
      const created = await repo.register({ email: 'audit@example.com', name: 'Audit User' });
      await repo.updateProfile(created.id, { name: 'Audit User Renamed' }, 1);
      await repo.updateProfile(created.id, { creditProfile: { score: 720 } }, 2);

      const auditLog = await repo.getAuditLog(created.id);
      expect(auditLog.length).toBe(3);
      expect(auditLog[0].action).toBe('CREATE');
      expect(auditLog[1].action).toBe('UPDATE');
      expect(auditLog[1].changedFields.name).toEqual({ from: 'Audit User', to: 'Audit User Renamed' });
      expect(auditLog[2].changedFields.credit_score).toEqual({ from: null, to: 720 });
    });
  });

  describe('[T-AUTH-01~05] 비밀번호 저장 & 해싱 (Day 8 - Task 1, δ=1535)', () => {
    it('[T-AUTH-01] 비밀번호로 등록하면 평문이 응답에 노출되지 않는다', async () => {
      const profile = await repo.register({ email: 'pw@example.com', name: 'Password User', password: 'correct-horse' });
      expect(JSON.stringify(profile)).not.toContain('correct-horse');
      expect((profile as any).passwordHash).toBeUndefined();
      expect((profile as any).password).toBeUndefined();
    });

    it('[T-AUTH-02] 올바른 비밀번호로 verifyPassword가 프로필을 반환한다', async () => {
      await repo.register({ email: 'login-ok@example.com', name: 'Login OK', password: 'correct-horse' });
      const verified = await repo.verifyPassword('login-ok@example.com', 'correct-horse');
      expect(verified?.email).toBe('login-ok@example.com');
    });

    it('[T-AUTH-03] 틀린 비밀번호로 verifyPassword는 null을 반환한다', async () => {
      await repo.register({ email: 'login-bad@example.com', name: 'Login Bad', password: 'correct-horse' });
      expect(await repo.verifyPassword('login-bad@example.com', 'wrong-password')).toBeNull();
    });

    it('[T-AUTH-04] 비밀번호 없이 등록한 사용자는 로그인할 수 없다', async () => {
      await repo.register({ email: 'no-password@example.com', name: 'No Password' });
      expect(await repo.verifyPassword('no-password@example.com', 'anything')).toBeNull();
      expect(await repo.verifyPassword('no-password@example.com', '')).toBeNull();
    });

    it('[T-AUTH-05] 8자 미만 비밀번호는 등록 시 거부된다', async () => {
      await expect(repo.register({ email: 'short-pw@example.com', name: 'Short PW', password: 'short' })).rejects.toThrow(ValidationError);
    });
  });

  describe('[T-AUTH-30] 관리자 역할 (Day 10 - Task 3, δ=1065)', () => {
    it('신규 등록 사용자는 기본적으로 role이 user다', async () => {
      const profile = await repo.register({ email: 'role-default@example.com', name: 'Role Default' });
      expect(profile.metadata.role).toBe('user');
    });
  });
});
