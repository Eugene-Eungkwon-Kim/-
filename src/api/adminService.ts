import type Database from 'better-sqlite3';
import { IntegrityChecker, IntegrityCheckResult } from '../repositories/IntegrityChecker';
import { BackupManager } from '../repositories/BackupManager';
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
