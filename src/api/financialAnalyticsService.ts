import type { Pool } from 'pg';
import { UserRepository } from '../repositories/UserRepository';
import { FinancialSnapshotRepository } from '../repositories/FinancialSnapshotRepository';
import { UserNotFoundError } from '../repositories/errors';
import { simulateCreditScore } from '../services/creditSimulation';
import { assessRisk } from '../services/riskAssessment';
import { analyzeFinancials } from '../services/financialAnalysis';
import { PerformanceComparison, TrendAnalysis, TrendMetric } from '../types/financialSnapshot';
import type { NotificationHub } from '../notifications/notificationHub';
import { evaluateAndPublishAlerts } from './alertTriggerService';
import { ServiceResult, toServiceResultAsync } from './errorMapping';

export interface CreditSimulationRequest {
  scenario: 'ideal' | 'normal' | 'risky' | 'crisis';
  duration?: number;
}

function toEmploymentStability(status: 'employed' | 'self-employed' | 'unemployed' | null): 'stable' | 'moderate' | 'unstable' {
  if (status === 'employed') return 'stable';
  if (status === 'self-employed') return 'moderate';
  if (status === 'unemployed') return 'unstable';
  return 'stable';
}

export async function runCreditSimulation(
  pool: Pool,
  userId: string,
  request: CreditSimulationRequest
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<ServiceResult<any>> {
  return toServiceResultAsync(async () => {
    const profile = await new UserRepository(pool).getProfile(userId);
    if (!profile) throw new UserNotFoundError(userId);

    return simulateCreditScore({
      userId,
      currentScore: profile.creditProfile.score ?? 700,
      scenarios: { scenario: request.scenario, duration: request.duration ?? 12 }
    });
  });
}

/**
 * 스냅샷 기록 직후 알림을 판정·발행한다 (Phase 15 - Section 2, B-7).
 *
 * 알림 실패가 분석 요청 자체를 실패시켜서는 안 된다 — 분석은 이미 성공했고 스냅샷도
 * 기록됐다. 그렇다고 조용히 삼키지도 않고 로그에 남긴다. void로 던져두는
 * fire-and-forget은 쓰지 않는다: 테스트에서 경합이 생기고 미처리 거부가 다른
 * 테스트를 오염시킨다.
 */
async function publishAlertsQuietly(pool: Pool, userId: string, hub?: NotificationHub): Promise<void> {
  if (!hub) return;
  try {
    await evaluateAndPublishAlerts(pool, userId, hub);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(`[alerts] evaluation failed for user ${userId}:`, error);
  }
}

export async function runRiskAssessment(
  pool: Pool,
  userId: string,
  snapshotDate: string,
  hub?: NotificationHub
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<ServiceResult<any>> {
  return toServiceResultAsync(async () => {
    const profile = await new UserRepository(pool).getProfile(userId);
    if (!profile) throw new UserNotFoundError(userId);

    const income = profile.financialSnapshot.monthlyIncome ?? 4000000;
    const debt = profile.financialSnapshot.totalDebt ?? 0;
    const assets = profile.financialSnapshot.totalAssets ?? 0;
    const creditScore = profile.creditProfile.score ?? 700;

    const result = await assessRisk({
      userId,
      creditScore,
      income,
      debt,
      savingsRate: profile.financialSnapshot.savingsRate ?? 15,
      employmentStability: toEmploymentStability(profile.employment.status)
    });

    const debtToIncomeRatio = income > 0 ? debt / (income * 12) : 0;
    const assetToDebtRatio = debt > 0 ? assets / debt : 0;
    const financialHealthScore = Math.max(0, Math.min(100, 100 - result.riskScore));

    await new FinancialSnapshotRepository(pool).recordSnapshot({
      userId,
      snapshotDate,
      creditScore,
      financialHealthScore,
      healthGrade: profile.creditProfile.grade ?? 'C',
      debtToIncomeRatio,
      assetToDebtRatio,
      monthlySurplus: income,
      riskScore: result.riskScore,
      riskLevel: result.overallRiskLevel,
      probabilityOfDefault: result.probabilityOfDefault
    });

    await publishAlertsQuietly(pool, userId, hub);

    return result;
  });
}

export async function runFinancialAnalysis(
  pool: Pool,
  userId: string,
  snapshotDate: string,
  hub?: NotificationHub
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<ServiceResult<any>> {
  return toServiceResultAsync(async () => {
    const profile = await new UserRepository(pool).getProfile(userId);
    if (!profile) throw new UserNotFoundError(userId);

    const result = await analyzeFinancials({
      userId,
      monthlyIncome: profile.financialSnapshot.monthlyIncome ?? undefined,
      monthlyExpenses: profile.financialSnapshot.monthlyExpenses ?? undefined,
      totalDebt: profile.financialSnapshot.totalDebt ?? undefined,
      totalAssets: profile.financialSnapshot.totalAssets ?? undefined
    });

    const snapshotRepo = new FinancialSnapshotRepository(pool);
    const history = await snapshotRepo.getHistory(userId);
    const latestExisting = history.length > 0 ? history[history.length - 1] : null;

    await snapshotRepo.recordSnapshot({
      userId,
      snapshotDate,
      creditScore: profile.creditProfile.score ?? 700,
      financialHealthScore: result.financialHealthScore,
      healthGrade: result.healthGrade,
      debtToIncomeRatio: result.currentStatus.debtToIncomeRatio,
      assetToDebtRatio: result.currentStatus.assetToDebtRatio,
      monthlySurplus: result.currentStatus.monthlySurplus,
      riskScore: latestExisting?.riskScore ?? 0,
      riskLevel: latestExisting?.riskLevel ?? 'unknown',
      probabilityOfDefault: latestExisting?.probabilityOfDefault ?? 0
    });

    await publishAlertsQuietly(pool, userId, hub);

    return result;
  });
}

export async function getSnapshotTrend(pool: Pool, userId: string, metric: TrendMetric): Promise<ServiceResult<TrendAnalysis>> {
  return toServiceResultAsync(async () => new FinancialSnapshotRepository(pool).getTrend(userId, metric));
}

/** 두 시점 스냅샷의 지표별 변화 비교 (Phase 15 - Section 3, A-2) */
export async function compareSnapshotPerformance(
  pool: Pool,
  userId: string,
  fromDate: string,
  toDate: string
): Promise<ServiceResult<PerformanceComparison[]>> {
  return toServiceResultAsync(async () =>
    new FinancialSnapshotRepository(pool).comparePerformance(userId, fromDate, toDate)
  );
}
