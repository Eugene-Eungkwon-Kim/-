import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '@db/connection';
import { registerUser } from '@api/userService';
import { getSnapshotTrend, runCreditSimulation, runFinancialAnalysis, runRiskAssessment } from '@api/financialAnalyticsService';
import { FinancialSnapshotRepository } from '@repositories/FinancialSnapshotRepository';

describe('financialAnalyticsService (Day 6 - Task 5: 금융분석 서비스 계층, δ=1350)', () => {
  let db: Database.Database;
  let userId: string;

  beforeEach(() => {
    db = createDatabase(':memory:');
    const created = registerUser(db, {
      email: 'analytics@example.com',
      name: 'Analytics User',
      creditProfile: { score: 680 },
      financialSnapshot: { monthlyIncome: 5000000, totalDebt: 50000000, totalAssets: 200000000, savingsRate: 12 }
    });
    userId = created.success ? created.data.id : '';
  });

  afterEach(() => {
    db.close();
  });

  describe('[T-SVC-501~506] 금융분석 서비스', () => {
    it('[T-SVC-501] 신용시뮬레이션이 DB의 현재 신용점수를 시작점으로 사용한다', async () => {
      const result = await runCreditSimulation(db, userId, { scenario: 'ideal', duration: 6 });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.currentScore).toBe(680); // 클라이언트 입력이 아니라 DB에 저장된 값
        expect(result.data.results.length).toBe(6);
      }
    });

    it('[T-SVC-502] 존재하지 않는 사용자', async () => {
      const result = await runCreditSimulation(db, 'no-such-user', { scenario: 'normal' });
      expect(result.success).toBe(false);
      if (!result.success) expect(result.error.code).toBe('USER_NOT_FOUND');
    });

    it('[T-SVC-503] 리스크평가가 DB의 소득/부채/자산을 사용한다', async () => {
      const result = await runRiskAssessment(db, userId, '2026-01-01');
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.riskComponents.creditRisk.factors[0]).toContain('680');
      }
    });

    it('[T-SVC-504] 리스크평가 결과가 스냅샷으로 자동 저장된다', async () => {
      await runRiskAssessment(db, userId, '2026-01-01');

      const snapshot = new FinancialSnapshotRepository(db).getSnapshotByDate(userId, '2026-01-01');
      expect(snapshot).not.toBeNull();
      expect(snapshot?.creditScore).toBe(680);
      expect(snapshot?.riskScore).toBeGreaterThan(0);
    });

    it('[T-SVC-505] 저장된 스냅샷으로 추세를 조회할 수 있다', async () => {
      await runRiskAssessment(db, userId, '2026-01-01');

      const trend = getSnapshotTrend(db, userId, 'riskScore');
      expect(trend.success).toBe(true);
      if (trend.success) {
        expect(trend.data.points.length).toBe(1);
      }
    });

    it('[T-SVC-506] 여러 시점의 리스크평가가 시계열 추세를 형성한다', async () => {
      await runRiskAssessment(db, userId, '2026-01-01');

      // 신용점수가 650~799 구간(creditRiskScore=40)에서 800+ 구간(=10)으로 개선
      const { updateUserProfile } = await import('@api/userService');
      updateUserProfile(db, userId, { creditProfile: { score: 820 } }, 1);
      await runRiskAssessment(db, userId, '2026-02-01');

      const trend = getSnapshotTrend(db, userId, 'riskScore');
      expect(trend.success).toBe(true);
      if (trend.success) {
        expect(trend.data.points.length).toBe(2);
        expect(trend.data.direction).toBe('improving'); // 리스크 점수 하락 = 개선
      }
    });
  });

  describe('[T-SVC-801~804] 재정분석 서비스 연결 (Day 7 - Task 3, δ=1105)', () => {
    it('[T-SVC-801] DB의 실제 income/expenses/debt/assets를 사용한다', async () => {
      const result = await runFinancialAnalysis(db, userId, '2026-01-01');
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.currentStatus.monthlyIncome).toBe(5000000); // beforeEach에서 설정한 DB 값
        expect(result.data.currentStatus.totalDebt).toBe(50000000);
      }
    });

    it('[T-SVC-802] 존재하지 않는 사용자', async () => {
      const result = await runFinancialAnalysis(db, 'no-such-user', '2026-01-01');
      expect(result.success).toBe(false);
      if (!result.success) expect(result.error.code).toBe('USER_NOT_FOUND');
    });

    it('[T-SVC-803] 결과가 스냅샷으로 자동 저장된다', async () => {
      await runFinancialAnalysis(db, userId, '2026-01-01');

      const snapshot = new FinancialSnapshotRepository(db).getSnapshotByDate(userId, '2026-01-01');
      expect(snapshot).not.toBeNull();
      expect(snapshot?.financialHealthScore).toBeGreaterThanOrEqual(0);
    });

    it('[T-SVC-804] 기존 리스크평가 스냅샷의 risk 필드를 재정분석이 덮어쓰지 않는다', async () => {
      const risk = await runRiskAssessment(db, userId, '2026-01-01');
      expect(risk.success).toBe(true);
      const riskScoreBefore = new FinancialSnapshotRepository(db).getSnapshotByDate(userId, '2026-01-01')?.riskScore;

      // 같은 날짜에 재정분석을 실행해도(리스크 계산을 하지 않는 분석) 기존 riskScore가 유지되어야 한다
      await runFinancialAnalysis(db, userId, '2026-01-01');
      const riskScoreAfter = new FinancialSnapshotRepository(db).getSnapshotByDate(userId, '2026-01-01')?.riskScore;

      expect(riskScoreAfter).toBe(riskScoreBefore);
    });
  });
});
