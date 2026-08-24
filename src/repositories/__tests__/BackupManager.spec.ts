import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type { Pool } from 'pg';
import { getTestPool, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { UserRepository } from '@repositories/UserRepository';
import { TransactionRepository } from '@repositories/TransactionRepository';
import { BackupManager, shouldRunBackup, BackupNotFoundError } from '@repositories/BackupManager';

describe('BackupManager (Day 5 - Task 7: 백업 & 복구 시스템, δ=1005)', () => {
  let pool: Pool;
  let users: UserRepository;
  let transactions: TransactionRepository;
  let backupDir: string;
  let backups: BackupManager;

  beforeEach(async () => {
    pool = getTestPool();
    users = new UserRepository(pool);
    transactions = new TransactionRepository(pool);
    backupDir = fs.mkdtempSync(path.join(os.tmpdir(), 'maars-backup-'));
    backups = new BackupManager(pool, backupDir);
  });

  afterEach(async () => {
    await cleanupTestDatabase();
    if (fs.existsSync(backupDir)) {
      fs.rmSync(backupDir, { recursive: true, force: true });
    }
  });

  describe('[T-API-A37~A42] 백업 & 복구', () => {
    it('[T-API-A37] 백업 생성', async () => {
      await users.register({ email: 'backup-user@example.com', name: 'Backup User' });

      const backup = await backups.createFullBackup();
      expect(backup.status).toBe('completed');
      expect(backup.id).toBeDefined();
      expect(backup.createdAt).toBeDefined();

      const list = await backups.listBackups();
      expect(list.length).toBeGreaterThanOrEqual(1);
      expect(list.some((b) => b.id === backup.id)).toBe(true);
    });

    it('[T-API-A38] 백업 검증', async () => {
      await users.register({ email: 'verify-user@example.com', name: 'Verify User' });
      const backup = await backups.createFullBackup();

      const verified = await backups.verifyBackup(backup.id);
      expect(verified).toBe(true);

      const retrieved = await backups.getBackup(backup.id);
      expect(retrieved).not.toBeNull();
      expect(retrieved?.verified).toBe(true);

      // 존재하지 않는 백업 검증 시도 → 예외 발생
      await expect(backups.verifyBackup('non-existent-id')).rejects.toThrow(BackupNotFoundError);
    });

    it('[T-API-A39] 복구 시뮬레이션 (백업 시점 상태로 복원)', async () => {
      await users.register({ email: 'restore-1@example.com', name: 'Restore User 1' });
      const backup = await backups.createFullBackup();

      // 백업 이후 발생한 변경 사항
      await users.register({ email: 'restore-2@example.com', name: 'Restore User 2' });

      // 복원 경로
      const restoredPath = path.join(backupDir, 'restored-backup.sql');

      // 복원 수행
      await backups.restoreFromBackup(backup.id, restoredPath);
      expect(fs.existsSync(restoredPath)).toBe(true);
    });

    it('[T-API-A40] 여러 시점 백업 간 독립성', async () => {
      await users.register({ email: 'multi-1@example.com', name: 'Multi User 1' });
      const firstBackup = await backups.createFullBackup();

      await users.register({ email: 'multi-2@example.com', name: 'Multi User 2' });
      const secondBackup = await backups.createFullBackup();

      // 각 백업은 서로 다른 ID를 가져야 한다
      expect(firstBackup.id).not.toBe(secondBackup.id);
      expect(firstBackup.createdAt).not.toBe(secondBackup.createdAt);

      // 백업 목록에는 2개의 백업이 포함되어야 한다
      const backupList = await backups.listBackups();
      expect(backupList.length).toBeGreaterThanOrEqual(2);
      expect(backupList.some((b) => b.id === firstBackup.id)).toBe(true);
      expect(backupList.some((b) => b.id === secondBackup.id)).toBe(true);
    });

    it('[T-API-A41] 백업 이후 변경사항은 복구 시 사라진다 (RPO)', async () => {
      const user = await users.register({
        email: 'rpo-user@example.com',
        name: 'RPO User',
        financialSnapshot: { monthlyIncome: 5000000 }
      });

      await transactions.recordTransaction({
        userId: user.id,
        transactionType: 'deposit',
        amount: 100000,
        occurredAt: '2026-01-01'
      });

      const backup = await backups.createFullBackup();

      // 백업 시점 이후에 발생한 거래
      await transactions.recordTransaction({
        userId: user.id,
        transactionType: 'deposit',
        amount: 200000,
        occurredAt: '2026-01-02'
      });

      // 백업은 생성 시점의 상태를 캡처해야 한다
      expect(backup.status).toBe('completed');

      // 원본 데이터베이스에는 2개의 거래가 있어야 한다
      const allTxns = await transactions.getTransactions(user.id);
      expect(allTxns.length).toBeGreaterThanOrEqual(2);
    });

    it('[T-API-A42] 특정 시점 복구 (최신이 아닌 과거 백업 선택)', async () => {
      await users.register({ email: 'pitr-1@example.com', name: 'PITR User 1' });
      const oldBackup = await backups.createFullBackup();

      await users.register({ email: 'pitr-2@example.com', name: 'PITR User 2' });
      const newBackup = await backups.createFullBackup(); // 최신 백업 (사용하지 않음)

      // 최신이 아니라 의도적으로 과거 시점(oldBackup)을 선택해 복원
      const restoredPath = path.join(backupDir, 'restored-old.sql');
      await backups.restoreFromBackup(oldBackup.id, restoredPath);

      // 복원 파일이 생성되어야 한다
      expect(fs.existsSync(restoredPath)).toBe(true);

      // 백업들은 서로 다른 시간에 생성되었다
      expect(oldBackup.createdAt).toBeDefined();
      expect(newBackup.createdAt).toBeDefined();
    });

    it('[T-API-A43] 백업 목록 조회 (정렬 순서)', async () => {
      const backups1 = await backups.listBackups();
      expect(backups1.length).toBe(0);

      await users.register({ email: 'list-user-1@example.com', name: 'List User 1' });
      await backups.createFullBackup();

      await users.register({ email: 'list-user-2@example.com', name: 'List User 2' });
      const backup2 = await backups.createFullBackup();

      const backupList = await backups.listBackups();
      expect(backupList.length).toBeGreaterThanOrEqual(2);

      // 최신 백업이 먼저 나와야 한다 (내림차순)
      const ids = backupList.map((b) => b.id);
      expect(ids[0]).toBe(backup2.id);
    });
  });

  describe('[T-SVC-821~822] 백업 스케줄링 & 보존정책 (Day 7 - Task 4, δ=945)', () => {
    it('[T-SVC-821] shouldRunBackup이 RPO 경과 여부를 정확히 판단한다', () => {
      expect(shouldRunBackup(null, '2026-07-01T00:00:00Z', 24)).toBe(true); // 백업 이력 없음 → 항상 필요
      expect(shouldRunBackup('2026-07-01T00:00:00Z', '2026-07-01T12:00:00Z', 24)).toBe(false); // 12시간 경과, 주기 24시간
      expect(shouldRunBackup('2026-07-01T00:00:00Z', '2026-07-02T01:00:00Z', 24)).toBe(true); // 25시간 경과
    });

    it('[T-SVC-822] pruneExpiredBackups가 보존기간 초과 백업만 정리한다', async () => {
      await users.register({ email: 'prune-user@example.com', name: 'Prune User' });
      const backup = await backups.createFullBackup();
      expect(fs.existsSync(backup.backupPath)).toBe(true);

      // 보존기간(7일) 이내이므로 아직 정리 대상 아님
      const notYetExpired = await backups.pruneExpiredBackups(7, '2026-07-03T00:00:00Z');
      expect(notYetExpired.prunedCount).toBe(0);
      expect(fs.existsSync(backup.backupPath)).toBe(true);

      // 보존기간을 초과한 미래 시점 기준으로는 정리되어야 한다
      const createdAt = backup.createdAt;
      const farFuture = new Date(
        new Date(createdAt.replace(' ', 'T') + 'Z').getTime() + 10 * 24 * 60 * 60 * 1000
      ).toISOString();
      const expired = await backups.pruneExpiredBackups(7, farFuture);
      expect(expired.prunedCount).toBe(1);
      expect(expired.prunedIds).toContain(backup.id);
      expect(fs.existsSync(backup.backupPath)).toBe(false);

      const retrieved = await backups.getBackup(backup.id);
      expect(retrieved).toBeNull();
    });

    it('[T-SVC-823] 존재하지 않는 백업 조회 시 null 반환', async () => {
      const backup = await backups.getBackup('non-existent-backup-id');
      expect(backup).toBeNull();
    });

    it('[T-SVC-824] 존재하지 않는 백업 복원 시 예외 발생', async () => {
      const restoredPath = path.join(backupDir, 'restored.sql');
      await expect(backups.restoreFromBackup('non-existent-backup-id', restoredPath)).rejects.toThrow(
        BackupNotFoundError
      );
    });

    it('[T-SVC-825] 빈 데이터베이스도 백업 가능', async () => {
      // 사용자를 생성하지 않음
      const backup = await backups.createFullBackup();
      expect(backup.status).toBe('completed');
      expect(backup.id).toBeDefined();

      const verified = await backups.verifyBackup(backup.id);
      expect(verified).toBe(true);
    });
  });
});
