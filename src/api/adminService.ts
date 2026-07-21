import type { Pool } from 'pg';
import { IntegrityChecker, IntegrityCheckResult } from '../repositories/IntegrityChecker';
import { BackupManager, PruneResult, shouldRunBackup } from '../repositories/BackupManager';
import { BackupRecord } from '../types/backup';
import { ServiceResult, toServiceResultAsync } from './errorMapping';

export async function runIntegrityCheck(pool: Pool, asOfDate: string): Promise<ServiceResult<IntegrityCheckResult[]>> {
  return toServiceResultAsync(async () => new IntegrityChecker(pool).runFullCheck(asOfDate));
}

export async function createBackup(pool: Pool, backupDir: string): Promise<ServiceResult<BackupRecord>> {
  return toServiceResultAsync(async () => new BackupManager(pool, backupDir).createFullBackup());
}

export async function listBackups(pool: Pool, backupDir: string): Promise<ServiceResult<BackupRecord[]>> {
  return toServiceResultAsync(async () => new BackupManager(pool, backupDir).listBackups());
}

export async function verifyBackup(pool: Pool, backupDir: string, backupId: string): Promise<ServiceResult<boolean>> {
  return toServiceResultAsync(async () => new BackupManager(pool, backupDir).verifyBackup(backupId));
}

export async function checkBackupDue(
  pool: Pool,
  backupDir: string,
  intervalHours: number,
  now: string
): Promise<ServiceResult<boolean>> {
  return toServiceResultAsync(async () => {
    const backups = await new BackupManager(pool, backupDir).listBackups();
    const lastBackupAt = backups.length > 0 ? backups[0].createdAt : null;
    return shouldRunBackup(lastBackupAt, now, intervalHours);
  });
}

export async function pruneOldBackups(
  pool: Pool,
  backupDir: string,
  retentionDays: number,
  now: string
): Promise<ServiceResult<PruneResult>> {
  return toServiceResultAsync(async () => new BackupManager(pool, backupDir).pruneExpiredBackups(retentionDays, now));
}
