import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { Pool } from 'pg';
import { cleanupTestDatabase, initializeTestDatabase } from '@db/__tests__/testDatabase';
import { UserRepository } from '@repositories/UserRepository';
import { FinancialSnapshotRepository } from '@repositories/FinancialSnapshotRepository';
import { NotificationRepository } from '@repositories/NotificationRepository';
import { evaluateAndPublishAlerts, decideTransition } from '@api/alertTriggerService';
import { MemoryNotificationHub } from '@/notifications/notificationHub';
import type { NotificationRecord } from '@/types/notification';
import type { MetricEvaluation } from '@/types/financialSnapshot';

/**
 * Phase 15 - Section 2 (B-4): 상태 전이 기반 알림 판정.
 * 명세서의 전이 표 각 행을 테스트로 고정한다.
 */
describe('alertTriggerService (상태 전이 기반 알림)', () => {
  let pool: Pool;
  let hub: MemoryNotificationHub;
  let published: NotificationRecord[];
  let userId: string;

  const DATE_A = '2026-01-01';
  const DATE_B = '2026-02-01';
  const DATE_C = '2026-03-01';

  /** 신용점수만 지정하고 나머지 지표는 전부 정상 범위로 채운 스냅샷 */
  async function recordSnapshot(creditScore: number, snapshotDate: string): Promise<void> {
    await new FinancialSnapshotRepository(pool).recordSnapshot({
      userId,
      snapshotDate,
      creditScore,
      financialHealthScore: 80, // 정상 (>= 40)
      healthGrade: 'A',
      debtToIncomeRatio: 0.2, // 정상 (<= 0.5)
      assetToDebtRatio: 3,
      monthlySurplus: 1_000_000,
      riskScore: 20, // 정상 (<= 60)
      riskLevel: 'low',
      probabilityOfDefault: 0.01
    });
  }

  async function evaluate(): Promise<NotificationRecord[]> {
    return evaluateAndPublishAlerts(pool, userId, hub);
  }

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
    pool = await initializeTestDatabase();

    hub = new MemoryNotificationHub();
    published = [];

    const user = await new UserRepository(pool).register({
      email: 'alert@example.com',
      name: 'Alert User',
      password: 'correct-horse'
    });
    userId = user.id;

    hub.subscribe(userId, (n) => published.push(n));
  });

  afterEach(async () => {
    await hub.close();
    await cleanupTestDatabase();
    delete process.env.ENCRYPTION_KEY;
  });

  describe('decideTransition (순수 판정 로직)', () => {
    const evaluation = (severity: MetricEvaluation['severity']): MetricEvaluation => ({
      metric: 'creditScore',
      value: 550,
      threshold: 600,
      severity,
      date: DATE_A
    });

    it('none + ok → 알림 없음', () => {
      expect(decideTransition(undefined, evaluation('ok'))).toBeNull();
    });

    it('none + warning → warning', () => {
      expect(decideTransition(undefined, evaluation('warning'))).toBe('warning');
    });

    it('none + critical → critical', () => {
      expect(decideTransition(undefined, evaluation('critical'))).toBe('critical');
    });

    it('warning + warning → 억제', () => {
      expect(decideTransition('warning', evaluation('warning'))).toBeNull();
    });

    it('warning + critical → critical (악화)', () => {
      expect(decideTransition('warning', evaluation('critical'))).toBe('critical');
    });

    it('critical + warning → warning (완화)', () => {
      expect(decideTransition('critical', evaluation('warning'))).toBe('warning');
    });

    it('critical + critical → 억제', () => {
      expect(decideTransition('critical', evaluation('critical'))).toBeNull();
    });

    it('warning + ok → resolved (해소)', () => {
      expect(decideTransition('warning', evaluation('ok'))).toBe('resolved');
    });

    it('critical + ok → resolved (해소)', () => {
      expect(decideTransition('critical', evaluation('ok'))).toBe('resolved');
    });

    it('resolved + ok → 억제', () => {
      expect(decideTransition('resolved', evaluation('ok'))).toBeNull();
    });

    it('resolved + warning → warning (재발)', () => {
      expect(decideTransition('resolved', evaluation('warning'))).toBe('warning');
    });
  });

  describe('evaluateAndPublishAlerts (DB 연동)', () => {
    it('스냅샷이 없는 사용자는 예외 없이 0건을 반환한다', async () => {
      const created = await evaluate();
      expect(created).toEqual([]);
      expect(published).toHaveLength(0);
    });

    it('첫 평가에서 creditScore 580이면 warning 1건이 생성·발행된다', async () => {
      await recordSnapshot(580, DATE_A);
      const created = await evaluate();

      expect(created).toHaveLength(1);
      expect(created[0].metric).toBe('creditScore');
      expect(created[0].severity).toBe('warning');
      expect(created[0].value).toBe(580);
      expect(created[0].threshold).toBe(600);
      expect(published).toHaveLength(1);
      expect(published[0].id).toBe(created[0].id);
    });

    it('같은 값으로 재평가하면 억제되어 0건이다', async () => {
      await recordSnapshot(580, DATE_A);
      await evaluate();
      published = [];

      const created = await evaluate();
      expect(created).toHaveLength(0);
      expect(published).toHaveLength(0);
    });

    it('warning → critical 악화 시 critical 1건이 추가된다', async () => {
      await recordSnapshot(580, DATE_A);
      await evaluate();

      await recordSnapshot(480, DATE_B);
      const created = await evaluate();

      expect(created).toHaveLength(1);
      expect(created[0].severity).toBe('critical');
      expect(created[0].value).toBe(480);
    });

    it('critical → 정상 복귀 시 resolved 1건이 기록된다', async () => {
      await recordSnapshot(480, DATE_A);
      await evaluate();

      await recordSnapshot(720, DATE_B);
      const created = await evaluate();

      expect(created).toHaveLength(1);
      expect(created[0].severity).toBe('resolved');
      expect(created[0].value).toBe(720);
    });

    it('해소 이후 계속 정상이면 더 이상 알림이 없다', async () => {
      await recordSnapshot(480, DATE_A);
      await evaluate();
      await recordSnapshot(720, DATE_B);
      await evaluate();

      await recordSnapshot(730, DATE_C);
      const created = await evaluate();
      expect(created).toHaveLength(0);
    });

    it('여러 지표가 동시에 위반되면 각각 생성된다', async () => {
      await new FinancialSnapshotRepository(pool).recordSnapshot({
        userId,
        snapshotDate: DATE_A,
        creditScore: 480, // critical (< 500)
        financialHealthScore: 15, // critical (< 20)
        healthGrade: 'D',
        debtToIncomeRatio: 0.9, // critical (> 0.8)
        assetToDebtRatio: 0.1,
        monthlySurplus: -100,
        riskScore: 85, // critical (> 80)
        riskLevel: 'high',
        probabilityOfDefault: 0.6
      });

      const created = await evaluate();
      expect(created).toHaveLength(4);
      expect(created.every((n) => n.severity === 'critical')).toBe(true);
      expect(new Set(created.map((n) => n.metric))).toEqual(
        new Set(['creditScore', 'financialHealthScore', 'riskScore', 'debtToIncomeRatio'])
      );
    });

    it('동시에 두 번 평가해도 UNIQUE 제약으로 1건만 남는다', async () => {
      await recordSnapshot(580, DATE_A);

      const [first, second] = await Promise.all([evaluate(), evaluate()]);

      // 어느 쪽이 이기든 합계는 1건이어야 한다.
      expect(first.length + second.length).toBe(1);

      const stored = await new NotificationRepository(pool).list(userId);
      expect(stored).toHaveLength(1);
      expect(published).toHaveLength(1);
    });

    it('같은 날 warning → 정상 → warning 왕복은 두 번째 warning을 억제한다 (플래핑 흡수)', async () => {
      // dedupe_key에 snapshot_date가 포함되므로 같은 날 동일 등급은 한 번만 기록된다.
      await recordSnapshot(580, DATE_A);
      await evaluate();

      await recordSnapshot(720, DATE_A); // 같은 날짜로 덮어쓰기 → resolved
      const resolved = await evaluate();
      expect(resolved).toHaveLength(1);
      expect(resolved[0].severity).toBe('resolved');

      await recordSnapshot(580, DATE_A); // 다시 warning, 같은 날짜
      const reWarned = await evaluate();
      expect(reWarned).toHaveLength(0);
    });
  });
});
