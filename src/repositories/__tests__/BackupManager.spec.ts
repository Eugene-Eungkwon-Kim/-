import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { UserRepository } from '@repositories/UserRepository';
import { TransactionRepository } from '@repositories/TransactionRepository';
import { BackupManager } from '@repositories/BackupManager';

describe('BackupManager (Day 5 - Task 7: 백업 & 복구 시스템, δ=1005)', () => {
  let db: Database.Database;
  let users: UserRepository;
  let transactions: TransactionRepository;
  let backupDir: string;
  let backups: BackupManager;

  beforeEach(() => {
    db = createDatabase(':memory:');
    users = new UserRepository(db);
    transactions = new TransactionRepository(db);
    backupDir = fs.mkdtempSync(path.join(os.tmpdir(), 'maars-backup-'));
    backups = new BackupManager(db, backupDir);
  });

  afterEach(() => {
    db.close();
    fs.rmSync(backupDir, { recursive: true, force: true });
  });

  function countUsersIn(dbPath: string): number {
    const readonlyDb = new Database(dbPath, { readonly: true, fileMustExist: true });
    const row = readonlyDb.prepare('SELECT COUNT(*) as count FROM users').get() as { count: number };
    readonlyDb.close();
    return row.count;
  }

  describe('[T-API-A37~A42] 백업 & 복구', () => {
    it('[T-API-A37] 백업 생성', async () => {
      users.register({ email: 'backup-user@example.com', name: 'Backup User' });

      const backup = await backups.createFullBackup();
      expect(backup.status).toBe('completed');
      expect(backup.sizeBytes).toBeGreaterThan(0);
      expect(fs.existsSync(backup.backupPath)).toBe(true);
      expect(backups.listBackups().length).toBe(1);
    });

    it('[T-API-A38] 백업 검증', async () => {
      users.register({ email: 'verify-user@example.com', name: 'Verify User' });
      const backup = await backups.createFullBackup();

      expect(backups.verifyBackup(backup.id)).toBe(true);
      expect(backups.getBackup(backup.id)?.verified).toBe(true);

      // 손상된 백업 파일은 검증 실패로 처리되어야 하며 예외를 던지지 않는다
      fs.writeFileSync(backup.backupPath, 'not a real sqlite file');
      expect(backups.verifyBackup(backup.id)).toBe(false);
    });

    it('[T-API-A39] 복구 시뮬레이션 (백업 시점 상태로 복원)', async () => {
      users.register({ email: 'restore-1@example.com', name: 'Restore User 1' });
      const backup = await backups.createFullBackup();

      // 백업 이후 발생한 변경 사항
      users.register({ email: 'restore-2@example.com', name: 'Restore User 2' });

      const restoredPath = path.join(backupDir, 'restored.sqlite');
      backups.restoreFromBackup(backup.id, restoredPath);

      // 복원된 파일에는 백업 시점의 사용자 1명만 있어야 한다 (이후 변경분은 없음)
      expect(countUsersIn(restoredPath)).toBe(1);

      const restoredDb = new Database(restoredPath, { readonly: true });
      const restoredUser = restoredDb.prepare('SELECT email FROM users').get() as { email: string };
      expect(restoredUser.email).toBe('restore-1@example.com');
      restoredDb.close();
    });

    it('[T-API-A40] 여러 시점 백업 간 독립성', async () => {
      users.register({ email: 'multi-1@example.com', name: 'Multi User 1' });
      const firstBackup = await backups.createFullBackup();

      users.register({ email: 'multi-2@example.com', name: 'Multi User 2' });
      const secondBackup = await backups.createFullBackup();

      // 각 백업 파일은 그 시점의 상태를 독립적으로 보존해야 한다
      expect(countUsersIn(firstBackup.backupPath)).toBe(1);
      expect(countUsersIn(secondBackup.backupPath)).toBe(2);
      expect(backups.listBackups().length).toBe(2);
    });

    it('[T-API-A41] 백업 이후 변경사항은 복구 시 사라진다 (RPO)', async () => {
      const userId = users.register({ email: 'rpo-user@example.com', name: 'RPO User', financialSnapshot: { monthlyIncome: 5000000 } }).id;
      transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 100000, occurredAt: '2026-01-01' });

      const backup = await backups.createFullBackup();

      // 백업 시점 이후에 발생한 거래는 이번 백업에 포함되지 않는다
      transactions.recordTransaction({ userId, transactionType: 'deposit', amount: 200000, occurredAt: '2026-01-02' });

      const backedUpDb = new Database(backup.backupPath, { readonly: true });
      const txCount = backedUpDb.prepare('SELECT COUNT(*) as count FROM transactions').get() as { count: number };
      backedUpDb.close();

      expect(txCount.count).toBe(1); // 백업 이후 거래(2번째)는 포함되지 않음 → RPO는 "마지막 백업 이후" 구간
    });

    it('[T-API-A42] 특정 시점 복구 (최신이 아닌 과거 백업 선택)', async () => {
      users.register({ email: 'pitr-1@example.com', name: 'PITR User 1' });
      const oldBackup = await backups.createFullBackup();

      users.register({ email: 'pitr-2@example.com', name: 'PITR User 2' });
      await backups.createFullBackup(); // 최신 백업 (사용하지 않음)

      // 최신이 아니라 의도적으로 과거 시점(oldBackup)을 선택해 복원
      const restoredPath = path.join(backupDir, 'restored-old.sqlite');
      backups.restoreFromBackup(oldBackup.id, restoredPath);

      expect(countUsersIn(restoredPath)).toBe(1);
    });
  });
});
