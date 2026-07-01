import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { loanHandlers } from '../handlers';
import { assessRisk } from '@services/riskAssessment';
import { simulateCreditScore } from '@services/creditSimulation';
import { analyzeFinancials } from '@services/financialAnalysis';

/**
 * MSW 핸들러의 resolver를 실제 네트워크/서버 없이 직접 호출한다.
 * (test/setup.ts가 global.fetch를 vi.fn()으로 전역 스텁해버려서, 이 파일의
 * MSW 핸들러들은 지금까지 실제 fetch 경유로는 전혀 실행되지 않고 있었다 —
 * 그래서 Day3/4 당시 로직이 중복 작성돼도 아무 테스트도 이를 잡아내지 못했다.)
 */
function invokeHandler(method: string, urlPath: string, body: unknown): Promise<unknown> {
  const handler = loanHandlers.find((h) => h.info.method === method && h.info.path === urlPath);
  if (!handler) throw new Error(`Handler not found: ${method} ${urlPath}`);

  const req = { json: async () => body };
  const ctx = { json: (data: unknown) => data };
  const res = (result: unknown) => result;

  // MSW의 타입 선언은 resolver를 protected로 감춰두지만(공개 사용을 의도하지 않음),
  // 실제 fetch 서버를 띄우지 않고 핸들러 로직만 단위테스트하려면 이 방법뿐이다.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (handler as any).resolver(req, res, ctx);
}

describe('MSW mock ↔ 실서비스 위임 (Day 7 - Task 1, δ=1445)', () => {
  describe('[T-MOCK-01~04] risk-assessment / credit-score 핸들러', () => {
    it('[T-MOCK-01] risk-assessment 핸들러가 실제 모듈과 동일한 결과를 반환한다', async () => {
      const body = { userId: 'u1', creditScore: 720, income: 5000000, debt: 20000000, savingsRate: 15 };
      const viaHandler = await invokeHandler('POST', '/api/v1/analysis/risk-assessment', body);
      const viaModule = await assessRisk(body);
      expect(viaHandler).toEqual(viaModule);
    });

    it('[T-MOCK-02] credit-score 시뮬레이션 핸들러가 실제 모듈과 동일한 결과를 반환한다', async () => {
      // ideal 시나리오는 Math.random을 전혀 쓰지 않아 완전히 결정적이므로 값 전체를 비교할 수 있다
      const body = { userId: 'u1', currentScore: 750, scenarios: { scenario: 'ideal', duration: 12 } };
      const viaHandler = await invokeHandler('POST', '/api/v1/simulation/credit-score', body);
      const viaModule = await simulateCreditScore(body);
      expect(viaHandler).toEqual(viaModule);
      expect((viaModule as any).summary.trend).toBe('improving');
    });

    it('[T-MOCK-03] risk-assessment 핸들러가 요청 본문의 고용안정성을 실제로 반영한다', async () => {
      const stable = (await invokeHandler('POST', '/api/v1/analysis/risk-assessment', {
        creditScore: 700,
        income: 5000000,
        employmentStability: 'stable'
      })) as any;
      const unstable = (await invokeHandler('POST', '/api/v1/analysis/risk-assessment', {
        creditScore: 700,
        income: 5000000,
        employmentStability: 'unstable'
      })) as any;
      expect(unstable.riskScore).toBeGreaterThan(stable.riskScore);
    });

    it('[T-MOCK-04] 핸들러가 실제 서비스 모듈을 import해 위임한다 (재복제 회귀 방지)', () => {
      const content = fs.readFileSync(path.resolve(__dirname, '../handlers.ts'), 'utf-8');
      expect(content).toContain("import { assessRisk } from '@services/riskAssessment'");
      expect(content).toContain("import { simulateCreditScore } from '@services/creditSimulation'");
    });
  });

  describe('[T-MOCK-05~06] financial-analysis 핸들러 (Day 7 - Task 3, δ=1105)', () => {
    it('[T-MOCK-05] financial-analysis 핸들러가 실제 모듈과 동일한 결과를 반환한다', async () => {
      const body = { userId: 'u1', monthlyIncome: 5000000, monthlyExpenses: 2000000, totalDebt: 50000000, totalAssets: 300000000 };
      const viaHandler = await invokeHandler('POST', '/api/v1/planning/financial-analysis', body);
      const viaModule = await analyzeFinancials(body);
      expect(viaHandler).toEqual(viaModule);
    });

    it('[T-MOCK-06] 핸들러가 analyzeFinancials를 import해 위임한다 (세 번째 독립 구현이었던 회귀 방지)', () => {
      const content = fs.readFileSync(path.resolve(__dirname, '../handlers.ts'), 'utf-8');
      expect(content).toContain("import { analyzeFinancials } from '@services/financialAnalysis'");
    });
  });
});
