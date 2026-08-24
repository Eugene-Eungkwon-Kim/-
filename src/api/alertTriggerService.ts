import type { Pool } from 'pg';
import { FinancialSnapshotRepository, evaluateSnapshotThresholds } from '../repositories/FinancialSnapshotRepository';
import { NotificationRepository } from '../repositories/NotificationRepository';
import type { NotificationHub } from '../notifications/notificationHub';
import type { MetricEvaluation } from '../types/financialSnapshot';
import type { CreateNotificationInput, NotificationRecord, NotificationSeverity } from '../types/notification';

/**
 * 상태 전이 기반 알림 판정 (Phase 15 - Section 2, B-4).
 *
 * 중복 제거를 값이 아니라 상태 전이로 판단한다. 신용점수가 590 → 585로 떨어져도
 * 둘 다 warning이면 알림은 발생하지 않는다. none→warning, warning→critical,
 * critical→resolved처럼 등급이 바뀔 때만 1건이 나간다. 이렇게 하지 않으면 스냅샷을
 * 기록할 때마다 같은 경고가 반복 발송된다.
 */

/**
 * 직전 상태와 현재 평가로부터 기록할 등급을 정한다. null이면 알림 없음.
 *
 *   직전 none      + ok        → null (억제)
 *   직전 none      + warning   → warning
 *   직전 warning   + warning   → null (억제)
 *   직전 warning   + critical  → critical (악화)
 *   직전 critical  + warning   → warning (완화)
 *   직전 warning   + ok        → resolved (해소)
 *   직전 resolved  + ok        → null (억제)
 *   직전 resolved  + warning   → warning (재발)
 */
export function decideTransition(
  previous: NotificationSeverity | undefined,
  current: MetricEvaluation
): NotificationSeverity | null {
  const isOpen = previous === 'warning' || previous === 'critical';

  if (current.severity === 'ok') {
    // 열려 있던 경고만 해소로 기록한다. 처음부터 정상이었거나 이미 해소된 지표는 조용히 둔다.
    return isOpen ? 'resolved' : null;
  }

  // 등급이 그대로면 억제. 바뀌었으면(악화/완화/신규/재발) 현재 등급을 기록한다.
  return previous === current.severity ? null : current.severity;
}

/**
 * 최신 스냅샷을 평가해 상태가 바뀐 지표만 알림으로 기록하고 발행한다.
 * 실제로 새로 생성된 알림만 돌려준다 — 억제되거나 경합에서 진 것은 포함되지 않는다.
 */
export async function evaluateAndPublishAlerts(
  pool: Pool,
  userId: string,
  hub: NotificationHub
): Promise<NotificationRecord[]> {
  const snapshotRepo = new FinancialSnapshotRepository(pool);
  const latest = await snapshotRepo.getLatestSnapshotRow(userId);
  if (!latest) return [];

  const notificationRepo = new NotificationRepository(pool);
  const evaluations = evaluateSnapshotThresholds(latest);
  const previousState = await notificationRepo.getLatestStateByMetric(userId);

  const pending: CreateNotificationInput[] = [];
  for (const evaluation of evaluations) {
    const severity = decideTransition(previousState.get(evaluation.metric), evaluation);
    if (!severity) continue;

    pending.push({
      userId,
      metric: evaluation.metric,
      severity,
      value: evaluation.value,
      threshold: evaluation.threshold,
      snapshotDate: evaluation.date
    });
  }

  const created: NotificationRecord[] = [];
  for (const input of pending) {
    // insertIfNew가 null이면 다른 인스턴스(또는 같은 날 재평가)가 이미 기록한 것이다.
    // 그 경우 발행하지 않아야 중복 발송이 생기지 않는다.
    const record = await notificationRepo.insertIfNew(input);
    if (!record) continue;

    await hub.publish(record);
    created.push(record);
  }

  return created;
}
