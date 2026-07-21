import { randomUUID } from 'node:crypto';
import type { Pool } from 'pg';
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

  async checkThresholds(userId: string): Promise<ThresholdAlert[]> {
    const result = await this.pool.query(
      'SELECT * FROM financial_snapshots WHERE user_id = $1 ORDER BY snapshot_date DESC LIMIT 1',
      [userId]
    );
    const latest = result.rows[0] as SnapshotRow | undefined;
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

  async comparePerformance(userId: string, fromDate: string, toDate: string): Promise<PerformanceComparison[]> {
    const from = await this.getSnapshotByDate(userId, fromDate);
    const to = await this.getSnapshotByDate(userId, toDate);
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

  private async getSnapshotByDateOrThrow(userId: string, snapshotDate: string): Promise<FinancialSnapshotRecord> {
    const record = await this.getSnapshotByDate(userId, snapshotDate);
    if (!record) throw new Error(`Snapshot not found after write: user=${userId} date=${snapshotDate}`);
    return record;
  }
}
