import type Database from 'better-sqlite3';
import { UserRepository } from '../repositories/UserRepository';
import { FinancialSnapshotRepository } from '../repositories/FinancialSnapshotRepository';
import { UserNotFoundError } from '../repositories/errors';
import { simulateCreditScore } from '../services/creditSimulation';
import { assessRisk } from '../services/riskAssessment';
import { TrendAnalysis, TrendMetric } from '../types/financialSnapshot';
import { ServiceResult, toServiceResult, toServiceResultAsync } from './errorMapping';

export interface CreditSimulationRequest {
  scenario: 'ideal' | 'normal' | 'risky' | 'crisis';
  duration?: number;
}

/**
 * UserProfile.employment.status(고용 형태)와 assessRisk가 기대하는
 * employmentStability(고용 안정성)는 서로 다른 축의 개념이라 직접 대입하면 안 된다
 * (예: 'employed' 문자열을 그대로 넘기면 assessRisk의 어떤 분기에도 안 걸려
 * 최악 케이스로 취급될 뻔했다). 명시적으로 매핑한다.
 */
function toEmploymentStability(status: 'employed' | 'self-employed' | 'unemployed' | null): 'stable' | 'moderate' | 'unstable' {
  if (status === 'employed') return 'stable';
  if (status === 'self-employed') return 'moderate';
  if (status === 'unemployed') return 'unstable';
  return 'stable';
}

/**
 * 금융분석 서비스 계층 (Day 6 - Task 5, δ=1350)
 *
 * Day4의 creditSimulation/riskAssessment는 클라이언트가 넘긴 입력값만으로
 * 계산하고 결과를 그대로 버렸다. 여기서는 DB에 저장된 사용자의 실제 신용점수/
 * 소득/부채를 시작점으로 사용하고, 리스크평가 결과는 FinancialSnapshotRepository에
 * 자동 저장해 시계열 추세 조회(getSnapshotTrend)가 가능하게 한다.
 */
export function runCreditSimulation(
  db: Database.Database,
  userId: string,
  request: CreditSimulationRequest
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<ServiceResult<any>> {
  return toServiceResultAsync(async () => {
    const profile = new UserRepository(db).getProfile(userId);
    if (!profile) throw new UserNotFoundError(userId);

    return simulateCreditScore({
      userId,
      currentScore: profile.creditProfile.score ?? 700,
      scenarios: { scenario: request.scenario, duration: request.duration ?? 12 }
    });
  });
}

export function runRiskAssessment(
  db: Database.Database,
  userId: string,
  snapshotDate: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<ServiceResult<any>> {
  return toServiceResultAsync(async () => {
    const profile = new UserRepository(db).getProfile(userId);
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

    new FinancialSnapshotRepository(db).recordSnapshot({
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

export function getSnapshotTrend(db: Database.Database, userId: string, metric: TrendMetric): ServiceResult<TrendAnalysis> {
  return toServiceResult(() => new FinancialSnapshotRepository(db).getTrend(userId, metric));
}
