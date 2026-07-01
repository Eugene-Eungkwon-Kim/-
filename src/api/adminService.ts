import type Database from 'better-sqlite3';
import { IntegrityChecker, IntegrityCheckResult } from '../repositories/IntegrityChecker';
import { BackupManager, PruneResult, shouldRunBackup } from '../repositories/BackupManager';
import { BackupRecord } from '../types/backup';
import { ServiceResult, toServiceResult, toServiceResultAsync } from './errorMapping';

/** 관리자 서비스 계층 (Day 6 - Task 6: 무결성/백업, δ=1140) */
export function runIntegrityCheck(db: Database.Database, asOfDate: string): Promise<ServiceResult<IntegrityCheckResult[]>> {
  return toServiceResultAsync(() => new IntegrityChecker(db).runFullCheck(asOfDate));
}

export function createBackup(db: Database.Database, backupDir: string): Promise<ServiceResult<BackupRecord>> {
  return toServiceResultAsync(() => new BackupManager(db, backupDir).createFullBackup());
}

export function listBackups(db: Database.Database, backupDir: string): ServiceResult<BackupRecord[]> {
  return toServiceResult(() => new BackupManager(db, backupDir).listBackups());
}

export function verifyBackup(db: Database.Database, backupDir: string, backupId: string): ServiceResult<boolean> {
  return toServiceResult(() => new BackupManager(db, backupDir).verifyBackup(backupId));
}

/** 백업 스케줄링 & 보존정책 (Day 7 - Task 4, δ=945). 실제 cron 배선은 배포 환경 몫이며,
 * 여기서는 "지금 백업이 필요한가"와 "보존기간 초과 백업 정리"라는 순수 판단만 제공한다. */
export function checkBackupDue(
  db: Database.Database,
  backupDir: string,
  intervalHours: number,
  now: string
): ServiceResult<boolean> {
  return toServiceResult(() => {
    const backups = new BackupManager(db, backupDir).listBackups(); // created_at 내림차순 정렬됨
    const lastBackupAt = backups.length > 0 ? backups[0].createdAt : null;
    return shouldRunBackup(lastBackupAt, now, intervalHours);
  });
}

export function pruneOldBackups(
  db: Database.Database,
  backupDir: string,
  retentionDays: number,
  now: string
): ServiceResult<PruneResult> {
  return toServiceResult(() => new BackupManager(db, backupDir).pruneExpiredBackups(retentionDays, now));
}
