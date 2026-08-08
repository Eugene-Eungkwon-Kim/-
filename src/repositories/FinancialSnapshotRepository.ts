import { randomUUID } from 'node:crypto';
import type { Pool } from 'pg';
import { SnapshotNotFoundError } from './errors';
import {
  FinancialSnapshotRecord,
  MetricEvaluation,
  PerformanceComparison,
  RecordSnapshotInput,
  ThresholdAlert,
  TrendAnalysis,
  TrendDirection,
  TrendMetric,
  TrendPoint
} from '../types/financialSnapshot';

export interface SnapshotRow {
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
 * THRESHOLD_RULES 전체를 평가한다 — 위반하지 않은 지표도 severity:'ok'로 포함한다
 * (Phase 15 - Section 2, B-2).
 *
 * checkThresholds()는 위반 항목만 돌려주므로, "경고가 해소됐다"는 전이를 감지할 수
 * 없다. 해소를 알리려면 정상으로 돌아온 지표의 현재 값도 필요하기 때문에 규칙 평가를
 * 순수 함수로 분리한다. checkThresholds()는 이 함수의 결과를 필터링하는 래퍼가 되며,
 * 기존 호출자의 동작은 바뀌지 않는다.
 */
export function evaluateSnapshotThresholds(row: SnapshotRow): MetricEvaluation[] {
  return THRESHOLD_RULES.map((rule) => {
    const value = row[rule.column] as number;
    if (rule.isCritical(value)) {
      return { metric: rule.metric, value, threshold: rule.criticalThreshold, severity: 'critical' as const, date: row.snapshot_date };
    }
    if (rule.isWarning(value)) {
      return { metric: rule.metric, value, threshold: rule.warningThreshold, severity: 'warning' as const, date: row.snapshot_date };
    }
    // 정상 지표는 "여기를 넘으면 경고"인 값을 임계값으로 함께 보고한다.
    return { metric: rule.metric, value, threshold: rule.warningThreshold, severity: 'ok' as const, date: row.snapshot_date };
  });
}

export class FinancialSnapshotRepository {
  constructor(private readonly pool: Pool) {}

  async recordSnapshot(input: RecordSnapshotInput): Promise<FinancialSnapshotRecord> {
    const id = randomUUID();

    await this.pool.query(
      `INSERT INTO financial_snapshots (
        id, user_id, snapshot_date, credit_score, financial_health_score, health_grade,
        debt_to_income_ratio, asset_to_debt_ratio, monthly_surplus, risk_score, risk_level, probability_of_default
      ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
      )
      ON CONFLICT(user_id, snapshot_date) DO UPDATE SET
        credit_score = EXCLUDED.credit_score,
        financial_health_score = EXCLUDED.financial_health_score,
        health_grade = EXCLUDED.health_grade,
        debt_to_income_ratio = EXCLUDED.debt_to_income_ratio,
        asset_to_debt_ratio = EXCLUDED.asset_to_debt_ratio,
        monthly_surplus = EXCLUDED.monthly_surplus,
        risk_score = EXCLUDED.risk_score,
        risk_level = EXCLUDED.risk_level,
        probability_of_default = EXCLUDED.probability_of_default`,
      [
        id,
        input.userId,
        input.snapshotDate,
        input.creditScore,
        input.financialHealthScore,
        input.healthGrade,
        input.debtToIncomeRatio,
        input.assetToDebtRatio,
        input.monthlySurplus,
        input.riskScore,
        input.riskLevel,
        input.probabilityOfDefault
      ]
    );

    return this.getSnapshotByDateOrThrow(input.userId, input.snapshotDate);
  }

  async getSnapshotByDate(userId: string, snapshotDate: string): Promise<FinancialSnapshotRecord | null> {
    const result = await this.pool.query(
      'SELECT * FROM financial_snapshots WHERE user_id = $1 AND snapshot_date = $2',
      [userId, snapshotDate]
    );
    const row = result.rows[0] as SnapshotRow | undefined;
    return row ? mapRow(row) : null;
  }

  async getHistory(userId: string, from?: string, to?: string): Promise<FinancialSnapshotRecord[]> {
    const conditions: string[] = ['user_id = $1'];
    const params: unknown[] = [userId];
    let paramIndex = 2;

    if (from) {
      conditions.push(`snapshot_date >= $${paramIndex}`);
      params.push(from);
      paramIndex++;
    }
    if (to) {
      conditions.push(`snapshot_date <= $${paramIndex}`);
      params.push(to);
      paramIndex++;
    }

    const result = await this.pool.query(
      `SELECT * FROM financial_snapshots WHERE ${conditions.join(' AND ')} ORDER BY snapshot_date ASC`,
      params
    );

    return (result.rows as SnapshotRow[]).map(mapRow);
  }

  async getTrend(userId: string, metric: TrendMetric): Promise<TrendAnalysis> {
    const column = METRIC_COLUMNS[metric];
    const result = await this.pool.query(
      `SELECT snapshot_date as date, ${column} as value FROM financial_snapshots WHERE user_id = $1 ORDER BY snapshot_date ASC`,
      [userId]
    );
    const rows = result.rows as { date: string; value: number }[];

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

  /** 최신 스냅샷 원본 1행. 알림 판정이 스냅샷을 한 번만 읽도록 노출한다 (B-4). */
  async getLatestSnapshotRow(userId: string): Promise<SnapshotRow | null> {
    const result = await this.pool.query(
      'SELECT * FROM financial_snapshots WHERE user_id = $1 ORDER BY snapshot_date DESC LIMIT 1',
      [userId]
    );
    return (result.rows[0] as SnapshotRow | undefined) ?? null;
  }

  async checkThresholds(userId: string): Promise<ThresholdAlert[]> {
    const latest = await this.getLatestSnapshotRow(userId);
    if (!latest) return [];

    return evaluateSnapshotThresholds(latest)
      .filter((e) => e.severity !== 'ok')
      .map((e) => ({
        metric: e.metric,
        date: e.date,
        value: e.value,
        threshold: e.threshold,
        severity: e.severity as 'warning' | 'critical'
      }));
  }

  async comparePerformance(userId: string, fromDate: string, toDate: string): Promise<PerformanceComparison[]> {
    const from = await this.getSnapshotByDate(userId, fromDate);
    const to = await this.getSnapshotByDate(userId, toDate);
    if (!from || !to) {
      // 어느 쪽이 없는지 알려준다 — 둘 다 없으면 fromDate를 먼저 보고한다.
      throw new SnapshotNotFoundError(userId, !from ? fromDate : toDate);
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

  private async getSnapshotByDateOrThrow(userId: string, snapshotDate: string): Promise<FinancialSnapshotRecord> {
    const record = await this.getSnapshotByDate(userId, snapshotDate);
    if (!record) throw new Error(`Snapshot not found after write: user=${userId} date=${snapshotDate}`);
    return record;
  }
}
