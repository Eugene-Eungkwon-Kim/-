import type { Pool } from 'pg';
import { TransactionRepository } from '../repositories/TransactionRepository';
import { FinancialSnapshotRepository } from '../repositories/FinancialSnapshotRepository';
import { FinancialSnapshotRecord, ThresholdAlert } from '../types/financialSnapshot';
import { MonthlyTrendPoint, TransactionSummary } from '../types/transaction';
import { ServiceResult, toServiceResultAsync } from './errorMapping';

/**
 * 대시보드 집계 (Phase 15 - Section 3, A-4).
 *
 * 프론트가 4개 엔드포인트를 순차 호출하던 것을 1회로 줄인다. 새로운 계산은 없고
 * 기존 리포지토리 호출을 조합만 한다.
 */
export interface DashboardView {
  summary: TransactionSummary | null;
  monthlyTrend: MonthlyTrendPoint[];
  latestSnapshot: FinancialSnapshotRecord | null;
  activeAlerts: ThresholdAlert[];
  /** 조합 중 실패해 낮춰진 필드 이름. 비어 있으면 전부 성공. */
  degraded: string[];
}

/**
 * Promise.all이 아니라 allSettled를 쓴다: 대시보드는 읽기 전용 조합 뷰라,
 * 한 조각(예: 스냅샷 이력이 아직 없는 신규 사용자)이 실패했다고 화면 전체가
 * 비어서는 안 된다. 실패한 필드만 빈 값으로 낮추고 degraded에 이름을 남긴다.
 */
export async function getDashboard(pool: Pool, userId: string): Promise<ServiceResult<DashboardView>> {
  return toServiceResultAsync(async () => {
    const txnRepo = new TransactionRepository(pool);
    const snapshotRepo = new FinancialSnapshotRepository(pool);

    const [summary, monthlyTrend, history, activeAlerts] = await Promise.allSettled([
      txnRepo.getSummary(userId),
      txnRepo.getMonthlyTrend(userId),
      snapshotRepo.getHistory(userId),
      snapshotRepo.checkThresholds(userId)
    ]);

    const degraded: string[] = [];
    const take = <T>(result: PromiseSettledResult<T>, name: string, fallback: T): T => {
      if (result.status === 'fulfilled') return result.value;
      degraded.push(name);
      // eslint-disable-next-line no-console
      console.error(`[dashboard] ${name} failed for user ${userId}:`, result.reason);
      return fallback;
    };

    const snapshots = take(history, 'latestSnapshot', [] as FinancialSnapshotRecord[]);

    return {
      summary: take(summary, 'summary', null as TransactionSummary | null),
      monthlyTrend: take(monthlyTrend, 'monthlyTrend', [] as MonthlyTrendPoint[]),
      latestSnapshot: snapshots.length > 0 ? snapshots[snapshots.length - 1] : null,
      activeAlerts: take(activeAlerts, 'activeAlerts', [] as ThresholdAlert[]),
      degraded
    };
  });
}
