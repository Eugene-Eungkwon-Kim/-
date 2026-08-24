import { randomUUID } from 'node:crypto';
import type { Pool } from 'pg';
import { NotificationNotFoundError } from './errors';
import {
  CreateNotificationInput,
  ListNotificationsOptions,
  NotificationRecord,
  NotificationSeverity,
  PruneNotificationsResult,
  buildDedupeKey
} from '../types/notification';

interface NotificationRow {
  id: string;
  user_id: string;
  metric: string;
  severity: NotificationSeverity;
  value: number;
  threshold: number;
  snapshot_date: string;
  read_at: string | null;
  created_at: string;
}

function mapRow(row: NotificationRow): NotificationRecord {
  return {
    id: row.id,
    userId: row.user_id,
    metric: row.metric,
    severity: row.severity,
    // PostgreSQL DOUBLE PRECISION은 pg 드라이버가 number로 주지만, NUMERIC 계열로
    // 바뀌더라도 문자열이 넘어오지 않도록 방어한다.
    value: Number(row.value),
    threshold: Number(row.threshold),
    snapshotDate: row.snapshot_date,
    readAt: row.read_at,
    createdAt: row.created_at
  };
}

export class NotificationRepository {
  constructor(private readonly pool: Pool) {}

  /**
   * 이미 같은 (user, metric, severity, date) 알림이 있으면 삽입하지 않고 null을 돌려준다.
   * 호출자는 null일 때 발행(publish)하지 않는다 — 이 한 가지 규칙으로 다중 인스턴스
   * 중복 발송이 DB 층에서 막힌다.
   */
  async insertIfNew(input: CreateNotificationInput): Promise<NotificationRecord | null> {
    const id = randomUUID();
    // created_at의 컬럼 기본값은 초 단위라, 같은 초에 기록된 두 알림의 선후를
    // 구분할 수 없다. getLatestStateByMetric이 그 순서에 의존하므로(전이 판정의
    // 좌변) 초 단위로는 등급이 뒤바뀌어 알림이 잘못 억제되거나 중복될 수 있다.
    // now()는 트랜잭션 시작 시각으로 고정되므로 매 호출마다 진행하는
    // clock_timestamp()를 마이크로초까지 기록한다.
    const result = await this.pool.query(
      `INSERT INTO notifications (id, user_id, metric, severity, value, threshold, snapshot_date, dedupe_key, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, to_char(clock_timestamp() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS.US'))
       ON CONFLICT (dedupe_key) DO NOTHING
       RETURNING *`,
      [id, input.userId, input.metric, input.severity, input.value, input.threshold, input.snapshotDate, buildDedupeKey(input)]
    );

    const row = result.rows[0] as NotificationRow | undefined;
    return row ? mapRow(row) : null;
  }

  /**
   * 지표별 가장 최근 알림의 등급. 상태 전이 판정의 좌변이 된다.
   *
   * 지표는 THRESHOLD_RULES 기준 4개로 상한이 있으므로, 윈도 함수를 쓰지 않고
   * 정렬된 목록을 훑으며 지표별 첫 항목만 취한다 — idx_notifications_user_metric와
   * 맞물려 단순하고 충분히 빠르다.
   */
  async getLatestStateByMetric(userId: string): Promise<Map<string, NotificationSeverity>> {
    const result = await this.pool.query(
      `SELECT metric, severity FROM notifications
       WHERE user_id = $1
       ORDER BY created_at DESC, id DESC`,
      [userId]
    );

    const latest = new Map<string, NotificationSeverity>();
    for (const row of result.rows as { metric: string; severity: NotificationSeverity }[]) {
      if (!latest.has(row.metric)) latest.set(row.metric, row.severity);
    }
    return latest;
  }

  async list(userId: string, options: ListNotificationsOptions = {}): Promise<NotificationRecord[]> {
    const conditions = ['user_id = $1'];
    const params: unknown[] = [userId];

    if (options.unreadOnly) conditions.push('read_at IS NULL');

    let sql = `SELECT * FROM notifications WHERE ${conditions.join(' AND ')} ORDER BY created_at DESC, id DESC`;
    if (options.limit !== undefined) {
      params.push(options.limit);
      sql += ` LIMIT $${params.length}`;
    }

    const result = await this.pool.query(sql, params);
    return (result.rows as NotificationRow[]).map(mapRow);
  }

  async countUnread(userId: string): Promise<number> {
    const result = await this.pool.query(
      'SELECT COUNT(*) as count FROM notifications WHERE user_id = $1 AND read_at IS NULL',
      [userId]
    );
    return Number((result.rows[0] as { count: string }).count);
  }

  /**
   * 보존기간을 넘긴 알림을 정리한다 (Phase 15 - B-3).
   *
   * 읽음 처리된 것만 지운다. 알림은 상태 전이에만 쌓여 증가가 느리므로 공간을
   * 아끼자고 읽지 않은 경고를 시스템이 임의로 없애는 건 대가가 맞지 않는다 —
   * 사용자가 못 본 위험 경고가 조용히 사라지는 쪽이 더 나쁜 실패다.
   * 읽지 않은 알림은 얼마나 오래됐든 남는다.
   *
   * BackupManager.pruneExpiredBackups와 같은 (retentionDays, now) 형태를 쓴다.
   */
  async pruneOldNotifications(retentionDays: number, now: string): Promise<PruneNotificationsResult> {
    const result = await this.pool.query(
      `DELETE FROM notifications
       WHERE read_at IS NOT NULL
         AND CAST(created_at AS TIMESTAMP) < (CAST($2 AS TIMESTAMP) - ($1 || ' days')::INTERVAL)
       RETURNING id`,
      [retentionDays, now]
    );

    const ids = (result.rows as { id: string }[]).map((r) => r.id);
    return { prunedCount: ids.length, prunedIds: ids };
  }

  /**
   * user_id를 WHERE에 포함해, 타인의 알림 id를 넘겨도 "없음"으로 처리한다 —
   * 존재 여부로 남의 알림 id를 탐지할 수 없게 한다.
   */
  async markRead(userId: string, notificationId: string): Promise<NotificationRecord> {
    const result = await this.pool.query(
      `UPDATE notifications
       SET read_at = to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')
       WHERE id = $1 AND user_id = $2
       RETURNING *`,
      [notificationId, userId]
    );

    const row = result.rows[0] as NotificationRow | undefined;
    if (!row) throw new NotificationNotFoundError(notificationId);
    return mapRow(row);
  }
}
