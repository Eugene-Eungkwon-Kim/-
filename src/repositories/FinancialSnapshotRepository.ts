import { randomUUID } from 'node:crypto';
import type Database from 'better-sqlite3';
import {
  FinancialSnapshotRecord,
  PerformanceComparison,
  RecordSnapshotInput,
  ThresholdAlert,
  TrendAnalysis,
  TrendDirection,
  TrendMetric,
  TrendPoint
} from '../types/financialSnapshot';

interface SnapshotRow {
  id: string;
  user_id: string;
  snapshot_date: string;
  credit_score: number;
  financial_health_score: number;
  health_grade: string;
  debt_to_income_ratio: number;
  asset_to_debt_ratio: number;
  monthly_surplus: number;
  risk_score: number;
  risk_level: string;
  probability_of_default: number;
  created_at: string;
}

function mapRow(row: SnapshotRow): FinancialSnapshotRecord {
  return {
    id: row.id,
    userId: row.user_id,
    snapshotDate: row.snapshot_date,
    creditScore: row.credit_score,
    financialHealthScore: row.financial_health_score,
    healthGrade: row.health_grade,
    debtToIncomeRatio: row.debt_to_income_ratio,
    assetToDebtRatio: row.asset_to_debt_ratio,
    monthlySurplus: row.monthly_surplus,
    riskScore: row.risk_score,
    riskLevel: row.risk_level,
    probabilityOfDefault: row.probability_of_default,
    createdAt: row.created_at
  };
}

const METRIC_COLUMNS: Record<TrendMetric, string> = {
  creditScore: 'credit_score',
  financialHealthScore: 'financial_health_score',
  riskScore: 'risk_score',
  monthlySurplus: 'monthly_surplus'
};

/** true면 값이 클수록 좋은 지표 (riskScore는 낮을수록 좋으므로 false) */
const HIGHER_IS_BETTER: Record<TrendMetric, boolean> = {
  creditScore: true,
  financialHealthScore: true,
  monthlySurplus: true,
  riskScore: false
};

interface ThresholdRule {
  metric: string;
  column: keyof SnapshotRow;
  warningThreshold: number;
  criticalThreshold: number;
  isWarning: (value: number) => boolean;
  isCritical: (value: number) => boolean;
}

const THRESHOLD_RULES: ThresholdRule[] = [
  {
    metric: 'creditScore',
    column: 'credit_score',
    warningThreshold: 600,
    criticalThreshold: 500,
    isWarning: (v) => v < 600,
    isCritical: (v) => v < 500
  },
  {
    metric: 'financialHealthScore',
    column: 'financial_health_score',
    warningThreshold: 40,
    criticalThreshold: 20,
    isWarning: (v) => v < 40,
    isCritical: (v) => v < 20
  },
  {
    metric: 'riskScore',
    column: 'risk_score',
    warningThreshold: 60,
    criticalThreshold: 80,
    isWarning: (v) => v > 60,
    isCritical: (v) => v > 80
  },
  {
    metric: 'debtToIncomeRatio',
    column: 'debt_to_income_ratio',
    warningThreshold: 0.5,
    criticalThreshold: 0.8,
    isWarning: (v) => v > 0.5,
    isCritical: (v) => v > 0.8
  }
];

/**
 * 금융 지표 저장소 (Day 5 - Task 4, δ=1255)
 *
 * Day 4의 신용시뮬레이션/재정분석/리스크평가 엔드포인트는 계산 결과를 응답으로만
 * 돌려주고 버렸다. 이 리포지토리는 그 결과를 사용자별 월간 스냅샷으로 저장해
 * 시계열 추세/임계값 경고/기간 비교를 가능하게 한다.
 */
export class FinancialSnapshotRepository {
  constructor(private readonly db: Database.Database) {}

  /** (user_id, snapshot_date) upsert — 같은 날짜로 재실행해도 최신 값으로 갱신될 뿐 중복 생성되지 않는다 */
  recordSnapshot(input: RecordSnapshotInput): FinancialSnapshotRecord {
    const id = randomUUID();

    this.db
      .prepare(
        `
        INSERT INTO financial_snapshots (
          id, user_id, snapshot_date, credit_score, financial_health_score, health_grade,
          debt_to_income_ratio, asset_to_debt_ratio, monthly_surplus, risk_score, risk_level, probability_of_default
        ) VALUES (
          @id, @userId, @snapshotDate, @creditScore, @financialHealthScore, @healthGrade,
          @debtToIncomeRatio, @assetToDebtRatio, @monthlySurplus, @riskScore, @riskLevel, @probabilityOfDefault
        )
        ON CONFLICT(user_id, snapshot_date) DO UPDATE SET
          credit_score = excluded.credit_score,
          financial_health_score = excluded.financial_health_score,
          health_grade = excluded.health_grade,
          debt_to_income_ratio = excluded.debt_to_income_ratio,
          asset_to_debt_ratio = excluded.asset_to_debt_ratio,
          monthly_surplus = excluded.monthly_surplus,
          risk_score = excluded.risk_score,
          risk_level = excluded.risk_level,
          probability_of_default = excluded.probability_of_default
      `
      )
      .run({ id, ...input });

    return this.getSnapshotByDateOrThrow(input.userId, input.snapshotDate);
  }

  getSnapshotByDate(userId: string, snapshotDate: string): FinancialSnapshotRecord | null {
    const row = this.db
      .prepare('SELECT * FROM financial_snapshots WHERE user_id = ? AND snapshot_date = ?')
      .get(userId, snapshotDate) as SnapshotRow | undefined;
    return row ? mapRow(row) : null;
  }

  getHistory(userId: string, from?: string, to?: string): FinancialSnapshotRecord[] {
    const conditions: string[] = ['user_id = @userId'];
    const params: Record<string, unknown> = { userId };

    if (from) {
      conditions.push('snapshot_date >= @from');
      params.from = from;
    }
    if (to) {
      conditions.push('snapshot_date <= @to');
      params.to = to;
    }

    const rows = this.db
      .prepare(`SELECT * FROM financial_snapshots WHERE ${conditions.join(' AND ')} ORDER BY snapshot_date ASC`)
      .all(params) as SnapshotRow[];

    return rows.map(mapRow);
  }

  getTrend(userId: string, metric: TrendMetric): TrendAnalysis {
    const column = METRIC_COLUMNS[metric];
    const rows = this.db
      .prepare(
        `SELECT snapshot_date as date, ${column} as value FROM financial_snapshots WHERE user_id = ? ORDER BY snapshot_date ASC`
      )
      .all(userId) as { date: string; value: number }[];

    const points: TrendPoint[] = rows.map((r) => ({ date: r.date, value: r.value }));
    if (points.length === 0) {
      return { metric, points, direction: 'stable', changeFromFirst: 0 };
    }

    const first = points[0].value;
    const last = points[points.length - 1].value;
    const changeFromFirst = last - first;
    const epsilon = Math.max(Math.abs(first) * 0.02, 1);

    let direction: TrendDirection = 'stable';
    if (Math.abs(changeFromFirst) > epsilon) {
      const isIncreasing = changeFromFirst > 0;
      const isGood = HIGHER_IS_BETTER[metric] ? isIncreasing : !isIncreasing;
      direction = isGood ? 'improving' : 'declining';
    }

    return { metric, points, direction, changeFromFirst };
  }

  /** 가장 최근 스냅샷을 기준으로 위험 임계값을 초과한 지표를 경고한다 */
  checkThresholds(userId: string): ThresholdAlert[] {
    const latest = this.db
      .prepare('SELECT * FROM financial_snapshots WHERE user_id = ? ORDER BY snapshot_date DESC LIMIT 1')
      .get(userId) as SnapshotRow | undefined;
    if (!latest) return [];

    const alerts: ThresholdAlert[] = [];
    for (const rule of THRESHOLD_RULES) {
      const value = latest[rule.column] as number;
      if (rule.isCritical(value)) {
        alerts.push({ metric: rule.metric, date: latest.snapshot_date, value, threshold: rule.criticalThreshold, severity: 'critical' });
      } else if (rule.isWarning(value)) {
        alerts.push({ metric: rule.metric, date: latest.snapshot_date, value, threshold: rule.warningThreshold, severity: 'warning' });
      }
    }
    return alerts;
  }

  comparePerformance(userId: string, fromDate: string, toDate: string): PerformanceComparison[] {
    const from = this.getSnapshotByDate(userId, fromDate);
    const to = this.getSnapshotByDate(userId, toDate);
    if (!from || !to) {
      throw new Error(`Snapshot not found for comparison (from=${fromDate}, to=${toDate})`);
    }

    const metrics: TrendMetric[] = ['creditScore', 'financialHealthScore', 'riskScore', 'monthlySurplus'];
    return metrics.map((metric) => {
      const fromValue = from[metric];
      const toValue = to[metric];
      const change = toValue - fromValue;
      const changePercent = fromValue !== 0 ? Math.round((change / Math.abs(fromValue)) * 1000) / 10 : 0;

      return {
        metric,
        from: { date: fromDate, value: fromValue },
        to: { date: toDate, value: toValue },
        change,
        changePercent
      };
    });
  }

  private getSnapshotByDateOrThrow(userId: string, snapshotDate: string): FinancialSnapshotRecord {
    const record = this.getSnapshotByDate(userId, snapshotDate);
    if (!record) throw new Error(`Snapshot not found after write: user=${userId} date=${snapshotDate}`);
    return record;
  }
}
