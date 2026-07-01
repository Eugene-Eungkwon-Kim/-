import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { registerUser } from '@api/userService';
import { applyForLoan } from '@api/loanService';
import { createBackup, listBackups, runIntegrityCheck, verifyBackup } from '@api/adminService';

describe('adminService (Day 6 - Task 6: 관리자 서비스, δ=1140)', () => {
  let db: Database.Database;
  let backupDir: string;

  beforeEach(() => {
    db = createDatabase(':memory:');
    backupDir = fs.mkdtempSync(path.join(os.tmpdir(), 'maars-admin-svc-'));
  });

  afterEach(() => {
    db.close();
    fs.rmSync(backupDir, { recursive: true, force: true });
  });

  describe('[T-SVC-601~606] 관리자 서비스', () => {
    it('[T-SVC-601] 무결성 체크 정상 실행', async () => {
      const created = registerUser(db, { email: 'admin-ok@example.com', name: 'Admin OK User' });
      const userId = created.success ? created.data.id : '';
      await applyForLoan(db, { userId, productId: 'p1', originalAmount: 100000000, interestRate: 3.2, termMonths: 120, startDate: '2026-01-01' });

      const result = await runIntegrityCheck(db, '2026-07-01');
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.every((r) => r.status === 'ok')).toBe(true);
      }
    });

    it('[T-SVC-602] 무결성 위반 감지', async () => {
      // 검증을 우회한 레거시 데이터 시뮬레이션 (2020년생 → 명백히 나이 범위 초과)
      db.prepare('INSERT INTO users (id, email, name, date_of_birth) VALUES (?, ?, ?, ?)').run(
        'legacy-admin-user',
        'legacy-admin@example.com',
        'Legacy',
        '2020-01-01'
      );

      const result = await runIntegrityCheck(db, '2026-07-01');
      expect(result.success).toBe(true);
      if (result.success) {
        const ageCheck = result.data.find((r) => r.checkType === 'age_out_of_range');
        expect(ageCheck?.status).toBe('violation');
      }
    });

    it('[T-SVC-603] 백업 생성', async () => {
      registerUser(db, { email: 'backup-svc@example.com', name: 'Backup Svc User' });

      const result = await createBackup(db, backupDir);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(fs.existsSync(result.data.backupPath)).toBe(true);
      }
    });

    it('[T-SVC-604] 백업 목록 조회', async () => {
      await createBackup(db, backupDir);
      await createBackup(db, backupDir);

      const result = listBackups(db, backupDir);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.length).toBe(2);
      }
    });

    it('[T-SVC-605] 백업 검증', async () => {
      const created = await createBackup(db, backupDir);
      const backupId = created.success ? created.data.id : '';

      const result = verifyBackup(db, backupDir, backupId);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toBe(true);
      }
    });

    it('[T-SVC-606] 존재하지 않는 백업 검증', () => {
      const result = verifyBackup(db, backupDir, 'no-such-backup-id');
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.code).toBe('BACKUP_NOT_FOUND');
      }
    });
  });
});
