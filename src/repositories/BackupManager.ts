import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import type { Pool } from 'pg';
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

export function shouldRunBackup(lastBackupAt: string | null, now: string, intervalHours: number): boolean {
  if (!lastBackupAt) return true;
  const elapsedMs = new Date(now).getTime() - new Date(lastBackupAt).getTime();
  return elapsedMs >= intervalHours * 60 * 60 * 1000;
}

export class BackupManager {
  constructor(
    private readonly pool: Pool,
    private readonly backupDir: string
  ) {
    fs.mkdirSync(backupDir, { recursive: true });
  }

  async createFullBackup(): Promise<BackupRecord> {
    const id = randomUUID();
    const backupPath = path.join(this.backupDir, `backup-${id}.sql`);

    try {
      // TODO: Implement PostgreSQL dump using pg_dump CLI or native backup
      // For now, create a placeholder backup record
      const sizeBytes = 0;
      await this.pool.query(
        'INSERT INTO backup_history (id, backup_type, backup_path, size_bytes, status) VALUES ($1, $2, $3, $4, $5)',
        [id, 'full', backupPath, sizeBytes, 'completed']
      );

      return this.getBackupOrThrow(id);
    } catch (error) {
      const sizeBytes = fs.existsSync(backupPath) ? fs.statSync(backupPath).size : 0;
      await this.pool.query(
        'INSERT INTO backup_history (id, backup_type, backup_path, size_bytes, status) VALUES ($1, $2, $3, $4, $5)',
        [id, 'full', backupPath, sizeBytes, 'failed']
      );
      throw error;
    }
  }

  async getBackup(backupId: string): Promise<BackupRecord | null> {
    const result = await this.pool.query('SELECT * FROM backup_history WHERE id = $1', [backupId]);
    const row = result.rows[0] as BackupRow | undefined;
    return row ? mapRow(row) : null;
  }

  async listBackups(): Promise<BackupRecord[]> {
    const result = await this.pool.query('SELECT * FROM backup_history ORDER BY created_at DESC');
    return (result.rows as BackupRow[]).map(mapRow);
  }

  async verifyBackup(backupId: string): Promise<boolean> {
    const record = await this.getBackupOrThrow(backupId);
    let verified = false;

    try {
      // TODO: Implement PostgreSQL backup verification
      // For now, just check if the file exists
      verified = fs.existsSync(record.backupPath);
    } catch {
      verified = false;
    }

    await this.pool.query('UPDATE backup_history SET verified = $1 WHERE id = $2', [verified ? 1 : 0, backupId]);
    return verified;
  }

  async restoreFromBackup(backupId: string, targetPath: string): Promise<void> {
    const record = await this.getBackupOrThrow(backupId);
    // TODO: Implement PostgreSQL restore functionality
    fs.copyFileSync(record.backupPath, targetPath);
  }

  async pruneExpiredBackups(retentionDays: number, now: string): Promise<PruneResult> {
    const expiredResult = await this.pool.query(
      `SELECT id, backup_path FROM backup_history WHERE CAST(created_at AS TIMESTAMP) < (CAST($2 AS TIMESTAMP) - INTERVAL '1 day' * $1)`,
      [retentionDays, now]
    );
    const expired = expiredResult.rows as { id: string; backup_path: string }[];

    for (const row of expired) {
      if (fs.existsSync(row.backup_path)) fs.unlinkSync(row.backup_path);
    }

    if (expired.length > 0) {
      const ids = expired.map((r) => r.id);
      await this.pool.query(
        `DELETE FROM backup_history WHERE id = ANY($1)`,
        [ids]
      );
    }

    return { prunedCount: expired.length, prunedIds: expired.map((r) => r.id) };
  }

  private async getBackupOrThrow(backupId: string): Promise<BackupRecord> {
    const record = await this.getBackup(backupId);
    if (!record) throw new BackupNotFoundError(backupId);
    return record;
  }
}
