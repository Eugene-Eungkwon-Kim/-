import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type { Pool } from 'pg';
import { getTestPool, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { registerUser } from '@api/userService';
import { applyForLoan } from '@api/loanService';
import { checkBackupDue, createBackup, listBackups, pruneOldBackups, runIntegrityCheck, verifyBackup } from '@api/adminService';

describe('adminService (Day 6 - Task 6: 관리자 서비스, δ=1140)', () => {
  let pool: Pool;
  let backupDir: string;

  beforeEach(async () => {
    pool = getTestPool();
    backupDir = fs.mkdtempSync(path.join(os.tmpdir(), 'maars-admin-svc-'));
  });

  afterEach(async () => {
    fs.rmSync(backupDir, { recursive: true, force: true });
    await cleanupTestDatabase();
  });

  describe('[T-SVC-601~606] 관리자 서비스', () => {
    it('[T-SVC-601] 무결성 체크 정상 실행', async () => {
      const created = await registerUser(pool, { email: 'admin-ok@example.com', name: 'Admin OK User', password: 'test-password-123' });
      const userId = created.success ? created.data.id : '';
      await applyForLoan(pool, { userId, productId: 'p1', originalAmount: 100000000, interestRate: 3.2, termMonths: 120, startDate: '2026-01-01' });

      const result = await runIntegrityCheck(pool, '2026-07-01');
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.every((r) => r.status === 'ok')).toBe(true);
      }
    });

    it('[T-SVC-602] 무결성 위반 감지', async () => {
      // 검증을 우회한 레거시 데이터 시뮬레이션 (2020년생 → 명백히 나이 범위 초과)
      await pool.query('INSERT INTO users (id, email, name, date_of_birth) VALUES ($1, $2, $3, $4)',
        ['legacy-admin-user', 'legacy-admin@example.com', 'Legacy', '2020-01-01']
      );

      const result = await runIntegrityCheck(pool, '2026-07-01');
      expect(result.success).toBe(true);
      if (result.success) {
        const ageCheck = result.data.find((r) => r.checkType === 'age_out_of_range');
        expect(ageCheck?.status).toBe('violation');
      }
    });

    it('[T-SVC-603] 백업 생성', async () => {
      await registerUser(pool, { email: 'backup-svc@example.com', name: 'Backup Svc User', password: 'test-password-123' });

      const result = await createBackup(pool, backupDir);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(fs.existsSync(result.data.backupPath)).toBe(true);
      }
    });

    it('[T-SVC-604] 백업 목록 조회', async () => {
      await createBackup(pool, backupDir);
      await createBackup(pool, backupDir);

      const result = await listBackups(pool, backupDir);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.length).toBe(2);
      }
    });

    it('[T-SVC-605] 백업 검증', async () => {
      const created = await createBackup(pool, backupDir);
      const backupId = created.success ? created.data.id : '';

      const result = await verifyBackup(pool, backupDir, backupId);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toBe(true);
      }
    });

    it('[T-SVC-606] 존재하지 않는 백업 검증', async () => {
      const result = await verifyBackup(pool, backupDir, 'no-such-backup-id');
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.code).toBe('BACKUP_NOT_FOUND');
      }
    });
  });

  describe('[T-SVC-823~824] 백업 스케줄링 & 보존정책 서비스 (Day 7 - Task 4, δ=945)', () => {
    it('[T-SVC-823] 백업 이력이 없으면 즉시 백업이 필요하다고 판단한다', async () => {
      const result = await checkBackupDue(pool, backupDir, 24, '2026-07-01T00:00:00Z');
      expect(result.success).toBe(true);
      if (result.success) expect(result.data).toBe(true);
    });

    it('[T-SVC-824] 보존기간 초과 백업을 서비스 계층에서 정리할 수 있다', async () => {
      await registerUser(pool, { email: 'prune-svc@example.com', name: 'Prune Svc User', password: 'test-password-123' });
      const created = await createBackup(pool, backupDir);
      const createdAt = created.success ? created.data.createdAt : '';

      const farFuture = new Date(new Date(createdAt.replace(' ', 'T') + 'Z').getTime() + 30 * 24 * 60 * 60 * 1000).toISOString();
      const result = await pruneOldBackups(pool, backupDir, 7, farFuture);
      expect(result.success).toBe(true);
      if (result.success) expect(result.data.prunedCount).toBe(1);

      const remaining = await listBackups(pool, backupDir);
      expect(remaining.success).toBe(true);
      if (remaining.success) expect(remaining.data.length).toBe(0);
    });
  });
});
