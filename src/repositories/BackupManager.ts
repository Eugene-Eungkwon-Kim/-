import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import Database from 'better-sqlite3';
import { BackupRecord } from '../types/backup';

interface BackupRow {
  id: string;
  backup_type: string;
  backup_path: string;
  size_bytes: number;
  status: string;
  verified: number;
  created_at: string;
}

function mapRow(row: BackupRow): BackupRecord {
  return {
    id: row.id,
    backupPath: row.backup_path,
    sizeBytes: row.size_bytes,
    status: row.status as BackupRecord['status'],
    verified: row.verified === 1,
    createdAt: row.created_at
  };
}

export class BackupNotFoundError extends Error {
  constructor(backupId: string) {
    super(`Backup not found: ${backupId}`);
    this.name = 'BackupNotFoundError';
  }
}

/**
 * 백업 & 복구 (Day 5 - Task 7, δ=1005)
 *
 * SQLite는 서버형 RDBMS와 달리 파일 하나에 전체 데이터가 들어있고, better-sqlite3의
 * Online Backup API(db.backup)는 사용 중에도 일관된 스냅샷을 원자적으로 뜬다.
 * 그래서 "핵심/중요/보조 테이블별 차등 백업"이나 "증분 백업"을 흉내내는 대신
 * 항상 전체 스냅샷 하나를 남긴다 — 테이블 간 정합성이 항상 보장되므로 오히려
 * 여러 계층으로 쪼개 백업하는 것보다 안전하다.
 */
export class BackupManager {
  constructor(
    private readonly db: Database.Database,
    private readonly backupDir: string
  ) {
    fs.mkdirSync(backupDir, { recursive: true });
  }

  async createFullBackup(): Promise<BackupRecord> {
    const id = randomUUID();
    const backupPath = path.join(this.backupDir, `backup-${id}.sqlite`);

    try {
      await this.db.backup(backupPath);
    } catch (error) {
      const sizeBytes = fs.existsSync(backupPath) ? fs.statSync(backupPath).size : 0;
      this.db
        .prepare('INSERT INTO backup_history (id, backup_type, backup_path, size_bytes, status) VALUES (?, ?, ?, ?, ?)')
        .run(id, 'full', backupPath, sizeBytes, 'failed');
      throw error;
    }

    const sizeBytes = fs.statSync(backupPath).size;
    this.db
      .prepare('INSERT INTO backup_history (id, backup_type, backup_path, size_bytes, status) VALUES (?, ?, ?, ?, ?)')
      .run(id, 'full', backupPath, sizeBytes, 'completed');

    return this.getBackupOrThrow(id);
  }

  getBackup(backupId: string): BackupRecord | null {
    const row = this.db.prepare('SELECT * FROM backup_history WHERE id = ?').get(backupId) as BackupRow | undefined;
    return row ? mapRow(row) : null;
  }

  listBackups(): BackupRecord[] {
    const rows = this.db.prepare('SELECT * FROM backup_history ORDER BY created_at DESC').all() as BackupRow[];
    return rows.map(mapRow);
  }

  /** 백업 파일이 실제로 열리는 유효한 SQLite DB이고 핵심 테이블(users)을 포함하는지 검증한다 */
  verifyBackup(backupId: string): boolean {
    const record = this.getBackupOrThrow(backupId);
    let verifyDb: Database.Database | undefined;
    let verified = false;

    try {
      verifyDb = new Database(record.backupPath, { readonly: true, fileMustExist: true });
      const tables = verifyDb.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all() as { name: string }[];
      verified = tables.some((t) => t.name === 'users');
    } catch {
      verified = false;
    } finally {
      verifyDb?.close();
    }

    this.db.prepare('UPDATE backup_history SET verified = ? WHERE id = ?').run(verified ? 1 : 0, backupId);
    return verified;
  }

  /** 백업 시점의 전체 데이터를 targetPath로 복원한다 (기존 파일이 있으면 덮어쓴다) */
  restoreFromBackup(backupId: string, targetPath: string): void {
    const record = this.getBackupOrThrow(backupId);
    fs.copyFileSync(record.backupPath, targetPath);
  }

  private getBackupOrThrow(backupId: string): BackupRecord {
    const record = this.getBackup(backupId);
    if (!record) throw new BackupNotFoundError(backupId);
    return record;
  }
}
