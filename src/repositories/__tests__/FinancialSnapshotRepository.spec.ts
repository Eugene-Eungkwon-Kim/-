import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { UserRepository } from '@repositories/UserRepository';
import { FinancialSnapshotRepository } from '@repositories/FinancialSnapshotRepository';

describe('FinancialSnapshotRepository (Day 5 - Task 4: 금융 지표 저장소, δ=1255)', () => {
  let db: Database.Database;
  let users: UserRepository;
  let snapshots: FinancialSnapshotRepository;
  let userId: string;

  const baseSnapshot = (overrides: Partial<Parameters<FinancialSnapshotRepository['recordSnapshot']>[0]> = {}) => ({
    userId,
    snapshotDate: '2026-01-01',
    creditScore: 750,
    financialHealthScore: 75,
    healthGrade: 'B',
    debtToIncomeRatio: 0.3,
    assetToDebtRatio: 2.5,
    monthlySurplus: 1000000,
    riskScore: 30,
    riskLevel: 'low',
    probabilityOfDefault: 2.5,
    ...overrides
  });

  beforeEach(() => {
    db = createDatabase(':memory:');
    users = new UserRepository(db);
    snapshots = new FinancialSnapshotRepository(db);
    userId = users.register({ email: 'snapshot@example.com', name: 'Snapshot User' }).id;
  });

  afterEach(() => {
    db.close();
  });

  describe('[T-API-A19~A24] 금융 지표 저장소', () => {
    it('[T-API-A19] 재정 스냅샷 저장 (upsert)', () => {
      const created = snapshots.recordSnapshot(baseSnapshot());
      expect(created.creditScore).toBe(750);

      // 같은 날짜로 재기록하면 갱신될 뿐 중복 생성되지 않는다
      const updated = snapshots.recordSnapshot(baseSnapshot({ creditScore: 770 }));
      expect(updated.id).toBe(created.id);
      expect(updated.creditScore).toBe(770);

      const history = snapshots.getHistory(userId);
      expect(history.length).toBe(1);
    });

    it('[T-API-A20] 히스토리 조회 (기간 필터)', () => {
      snapshots.recordSnapshot(baseSnapshot({ snapshotDate: '2026-01-01' }));
      snapshots.recordSnapshot(baseSnapshot({ snapshotDate: '2026-02-01' }));
      snapshots.recordSnapshot(baseSnapshot({ snapshotDate: '2026-03-01' }));

      const all = snapshots.getHistory(userId);
      expect(all.map((s) => s.snapshotDate)).toEqual(['2026-01-01', '2026-02-01', '2026-03-01']);

      const filtered = snapshots.getHistory(userId, '2026-02-01', '2026-02-28');
      expect(filtered.length).toBe(1);
      expect(filtered[0].snapshotDate).toBe('2026-02-01');
    });

    it('[T-API-A21] 시계열 분석 (신용점수 추세)', () => {
      snapshots.recordSnapshot(baseSnapshot({ snapshotDate: '2026-01-01', creditScore: 700 }));
      snapshots.recordSnapshot(baseSnapshot({ snapshotDate: '2026-02-01', creditScore: 730 }));
      snapshots.recordSnapshot(baseSnapshot({ snapshotDate: '2026-03-01', creditScore: 760 }));

      const trend = snapshots.getTrend(userId, 'creditScore');
      expect(trend.points.map((p) => p.value)).toEqual([700, 730, 760]);
      expect(trend.direction).toBe('improving');
      expect(trend.changeFromFirst).toBe(60);
    });

    it('[T-API-A22] 추세 분석 & 예측 (리스크 점수는 낮을수록 개선)', () => {
      snapshots.recordSnapshot(baseSnapshot({ snapshotDate: '2026-01-01', riskScore: 20 }));
      snapshots.recordSnapshot(baseSnapshot({ snapshotDate: '2026-02-01', riskScore: 35 }));
      snapshots.recordSnapshot(baseSnapshot({ snapshotDate: '2026-03-01', riskScore: 55 }));

      // riskScore가 상승했다는 것은 위험이 커졌다는 뜻 → declining으로 해석되어야 한다
      const riskTrend = snapshots.getTrend(userId, 'riskScore');
      expect(riskTrend.direction).toBe('declining');

      const surplusTrend = snapshots.getTrend(userId, 'monthlySurplus');
      expect(surplusTrend.direction).toBe('stable'); // 매 스냅샷 동일값(1,000,000)
    });

    it('[T-API-A23] 임계값 경고', () => {
      snapshots.recordSnapshot(
        baseSnapshot({ creditScore: 450, financialHealthScore: 35, riskScore: 45, debtToIncomeRatio: 0.9 })
      );

      const alerts = snapshots.checkThresholds(userId);
      const byMetric = Object.fromEntries(alerts.map((a) => [a.metric, a]));

      expect(byMetric.creditScore.severity).toBe('critical'); // < 500
      expect(byMetric.financialHealthScore.severity).toBe('warning'); // < 40
      expect(byMetric.debtToIncomeRatio.severity).toBe('critical'); // > 0.8
      expect(byMetric.riskScore).toBeUndefined(); // 45는 임계값(60) 미만이라 경고 없음
    });

    it('[T-API-A24] 성과 비교 (기간 간 지표 변화)', () => {
      snapshots.recordSnapshot(
        baseSnapshot({ snapshotDate: '2026-01-01', creditScore: 650, financialHealthScore: 50, riskScore: 50, monthlySurplus: 500000 })
      );
      snapshots.recordSnapshot(
        baseSnapshot({ snapshotDate: '2026-06-01', creditScore: 780, financialHealthScore: 80, riskScore: 20, monthlySurplus: 1200000 })
      );

      const comparison = snapshots.comparePerformance(userId, '2026-01-01', '2026-06-01');
      const byMetric = Object.fromEntries(comparison.map((c) => [c.metric, c]));

      expect(byMetric.creditScore.change).toBe(130);
      expect(byMetric.financialHealthScore.changePercent).toBe(60); // 50→80 = +60%
      expect(byMetric.riskScore.change).toBe(-30);
      expect(byMetric.monthlySurplus.change).toBe(700000);
    });
  });
});
