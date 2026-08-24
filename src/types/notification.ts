/**
 * 임계값 알림 타입 (Phase 15 - Section 2)
 */

/**
 * 기록되는 알림 등급. 'resolved'는 경고/위험이 정상으로 돌아왔음을 뜻하며,
 * MetricSeverity의 'ok'(현재 평가 결과)와는 구분된다 — 'ok'는 상태이고
 * 'resolved'는 상태 전이의 기록이다.
 */
export type NotificationSeverity = 'warning' | 'critical' | 'resolved';

export interface NotificationRecord {
  id: string;
  userId: string;
  metric: string;
  severity: NotificationSeverity;
  value: number;
  threshold: number;
  snapshotDate: string;
  readAt: string | null;
  createdAt: string;
}

export interface CreateNotificationInput {
  userId: string;
  metric: string;
  severity: NotificationSeverity;
  value: number;
  threshold: number;
  snapshotDate: string;
}

export interface ListNotificationsOptions {
  unreadOnly?: boolean;
  limit?: number;
}

/** 상태 전이 판정에 쓰는 직전 상태. 알림 이력이 없으면 'none'. */
export type NotificationState = NotificationSeverity | 'none';

export function buildDedupeKey(input: CreateNotificationInput): string {
  return `${input.userId}:${input.metric}:${input.severity}:${input.snapshotDate}`;
}

/** 알림 정리 결과 (Phase 15 - B-3). BackupManager의 PruneResult와 같은 형태다. */
export interface PruneNotificationsResult {
  prunedCount: number;
  prunedIds: string[];
}
