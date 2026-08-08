import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import type { Pool } from 'pg';
import { BackupRecord } from '../types/backup';
import { exportDatabaseInserts } from '../db/pg/pgDataExporter';

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
      // pg_dump CLI에 의존하지 않고, 이미 있는 pgDataExporter로 FK-안전 순서의
      // INSERT 스크립트를 직접 만든다. 외부 바이너리·자격증명이 필요 없어
      // 테스트와 컨테이너 환경에서 그대로 동작한다.
      fs.writeFileSync(backupPath, await exportDatabaseInserts(this.pool), 'utf-8');

      const sizeBytes = fs.statSync(backupPath).size;
      // created_at의 컬럼 기본값은 초 단위라(datetime('now') 변환 결과) 같은 초에 만든
      // 두 백업을 구분·정렬할 수 없다. 밀리초까지 명시해 목록 정렬을 결정적으로 만든다.
      // 기존 초 단위 값과도 사전식 비교가 그대로 성립한다.
      await this.pool.query(
        `INSERT INTO backup_history (id, backup_type, backup_path, size_bytes, status, created_at)
         VALUES ($1, $2, $3, $4, $5, to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS.MS'))`,
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
    // id를 보조 정렬키로 둬, 초 단위로만 기록된 과거 행들 사이에서도 순서가 흔들리지 않게 한다.
    const result = await this.pool.query('SELECT * FROM backup_history ORDER BY created_at DESC, id DESC');
    return (result.rows as BackupRow[]).map(mapRow);
  }

  async verifyBackup(backupId: string): Promise<boolean> {
    const record = await this.getBackupOrThrow(backupId);
    let verified = false;

    try {
      // 파일 존재만으로는 "쓰다 만 백업"을 통과시킨다. 덤프가 트랜잭션으로
      // 감싸여 끝까지 기록됐는지(COMMIT 도달) 확인한다.
      if (fs.existsSync(record.backupPath)) {
        const contents = fs.readFileSync(record.backupPath, 'utf-8');
        verified = contents.startsWith('BEGIN;') && contents.trimEnd().endsWith('COMMIT;');
      }
    } catch {
      verified = false;
    }

    await this.pool.query('UPDATE backup_history SET verified = $1 WHERE id = $2', [verified ? 1 : 0, backupId]);
    return verified;
  }

  /**
   * 백업 스크립트를 targetPath로 꺼낸다. 실제 복원(psql 실행)은 운영 절차이며,
   * 여기서는 복원에 쓸 스크립트를 추출하는 데까지만 책임진다.
   */
  async restoreFromBackup(backupId: string, targetPath: string): Promise<void> {
    const record = await this.getBackupOrThrow(backupId);
    if (!fs.existsSync(record.backupPath)) {
      throw new Error(`Backup file is missing: ${record.backupPath}`);
    }
    fs.copyFileSync(record.backupPath, targetPath);
  }

  async pruneExpiredBackups(retentionDays: number, now: string): Promise<PruneResult> {
    const expiredResult = await this.pool.query(
      `SELECT id, backup_path FROM backup_history WHERE CAST(created_at AS TIMESTAMP) < (CAST($2 AS TIMESTAMP) - ($1 || ' days')::INTERVAL)`,
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
