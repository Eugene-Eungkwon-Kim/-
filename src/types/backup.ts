/**
 * 백업 & 복구 관련 타입 정의
 * Day 5 - Task 7: Backup & Recovery System (δ=1005)
 */

export type BackupStatus = 'completed' | 'failed';

export interface BackupRecord {
  id: string;
  backupPath: string;
  sizeBytes: number;
  status: BackupStatus;
  verified: boolean;
  createdAt: string;
}
