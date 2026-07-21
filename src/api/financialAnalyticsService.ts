import type { Pool } from 'pg';
import { UserRepository } from '../repositories/UserRepository';
import { FinancialSnapshotRepository } from '../repositories/FinancialSnapshotRepository';
import { UserNotFoundError } from '../repositories/errors';
import { simulateCreditScore } from '../services/creditSimulation';
import { assessRisk } from '../services/riskAssessment';
import { analyzeFinancials } from '../services/financialAnalysis';
import { TrendAnalysis, TrendMetric } from '../types/financialSnapshot';
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

export async function runRiskAssessment(
  pool: Pool,
  userId: string,
  snapshotDate: string
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

    return result;
  });
}

export async function runFinancialAnalysis(
  pool: Pool,
  userId: string,
  snapshotDate: string
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

    return result;
  });
}

export async function getSnapshotTrend(pool: Pool, userId: string, metric: TrendMetric): Promise<ServiceResult<TrendAnalysis>> {
  return toServiceResultAsync(async () => new FinancialSnapshotRepository(pool).getTrend(userId, metric));
}
