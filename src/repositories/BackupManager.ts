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

export interface PruneResult {
  prunedCount: number;
  prunedIds: string[];
}

/**
 * RPO(마지막 백업 이후 허용 가능한 데이터 손실 시간) 기준으로 다음 백업이
 * 필요한지 판단하는 순수 함수. 실제 cron 배선은 이 환경에서 검증할 수 없으므로
 * (배포 인프라 몫), 판단 로직만 여기서 구현하고 테스트로 보장한다.
 */
export function shouldRunBackup(lastBackupAt: string | null, now: string, intervalHours: number): boolean {
  if (!lastBackupAt) return true;
  const elapsedMs = new Date(now).getTime() - new Date(lastBackupAt).getTime();
  return elapsedMs >= intervalHours * 60 * 60 * 1000;
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

  /** 보존기간(retentionDays)을 초과한 백업 파일과 기록을 정리한다 */
  pruneExpiredBackups(retentionDays: number, now: string): PruneResult {
    const expired = this.db
      .prepare(`SELECT id, backup_path FROM backup_history WHERE created_at < datetime(?, '-' || ? || ' days')`)
      .all(now, retentionDays) as { id: string; backup_path: string }[];

    for (const row of expired) {
      if (fs.existsSync(row.backup_path)) fs.unlinkSync(row.backup_path);
    }

    if (expired.length > 0) {
      const placeholders = expired.map(() => '?').join(',');
      this.db.prepare(`DELETE FROM backup_history WHERE id IN (${placeholders})`).run(...expired.map((r) => r.id));
    }

    return { prunedCount: expired.length, prunedIds: expired.map((r) => r.id) };
  }

  private getBackupOrThrow(backupId: string): BackupRecord {
    const record = this.getBackup(backupId);
    if (!record) throw new BackupNotFoundError(backupId);
    return record;
  }
}
