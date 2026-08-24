/**
 * 금융 지표 저장소 관련 타입 정의
 * Day 5 - Task 4: Financial Metrics Repository (δ=1255)
 *
 * Day 4에서 계산만 하고 버리던 신용 시뮬레이션/재정분석/리스크평가 결과를
 * 월별 스냅샷으로 영속화해 시계열 추세 분석을 가능하게 한다.
 */

export type TrendMetric = 'creditScore' | 'financialHealthScore' | 'riskScore' | 'monthlySurplus';
export type TrendDirection = 'improving' | 'declining' | 'stable';
export type AlertSeverity = 'warning' | 'critical';

export interface RecordSnapshotInput {
  userId: string;
  snapshotDate: string; // YYYY-MM-DD
  creditScore: number;
  financialHealthScore: number;
  healthGrade: string;
  debtToIncomeRatio: number;
  assetToDebtRatio: number;
  monthlySurplus: number;
  riskScore: number;
  riskLevel: string;
  probabilityOfDefault: number;
}

export interface FinancialSnapshotRecord extends RecordSnapshotInput {
  id: string;
  createdAt: string;
}

export interface TrendPoint {
  date: string;
  value: number;
}

export interface TrendAnalysis {
  metric: TrendMetric;
  points: TrendPoint[];
  direction: TrendDirection;
  changeFromFirst: number;
}

export interface ThresholdAlert {
  metric: string;
  date: string;
  value: number;
  threshold: number;
  severity: AlertSeverity;
}

export interface PerformanceComparison {
  metric: TrendMetric;
  from: TrendPoint;
  to: TrendPoint;
  change: number;
  changePercent: number;
}

/**
 * 임계값 평가 결과 (Phase 15 - Section 2, B-2).
 * ThresholdAlert와 달리 위반하지 않은 지표도 severity:'ok'로 포함해,
 * 알림 상태 전이(특히 "해소")를 판정할 수 있게 한다.
 */
export type MetricSeverity = 'ok' | 'warning' | 'critical';

export interface MetricEvaluation {
  metric: string;
  value: number;
  /** 현재 등급에 해당하는 임계값. 'ok'면 경고 임계값을 보고한다. */
  threshold: number;
  severity: MetricSeverity;
  date: string;
}
