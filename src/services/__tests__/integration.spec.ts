/**
 * D09: 금융로직 통합 테스트
 * Week 2: Integration Tests (필터 조합 + 금융 계산 흐름)
 */

import { describe, it, expect } from 'vitest';
import { filterLoanProducts } from '../loan-service';
import { calculateLoanPayment } from '../interest-calculator';
import { assessCredit } from '../credit-assessment';

// ============================================================================
// Part 1: Filter Combination Tests (필터 조합 테스트)
// ============================================================================

describe('Integration: Filter Combination Tests', () => {

  describe('[T-INT-001~006] 필터 조합 시나리오', () => {

    it('[T-INT-001] 신용도 + 부동산 필터 조합 (Grade B + 아파트)', async () => {
      // 신용점수 750 (Grade B) + 아파트만 조회
      const result = await filterLoanProducts({
        creditScore: 750,
        propertyType: '아파트'
      });

      // Grade B: 표준전세(700+) + 조건부대출(650+) 중
      // 아파트 지원: 표준전세(아파트,원룸,오피스텔)만 지원
      // 조건부(원룸,전세방)는 아파트 미지원
      // 결과: 표준전세만 반환 (1개)
      expect(result).toHaveLength(1);
      expect(result.every(p => p.propertyTypes.includes('아파트'))).toBe(true);
      expect(result.some(p => p.name.includes('표준'))).toBe(true);
    });

    it('[T-INT-002] 신용도 + 금액 범위 필터 조합 (Grade A + 2억~4억)', async () => {
      // 신용점수 800 (Grade A) + 금액 범위 제한
      const result = await filterLoanProducts({
        creditScore: 800,
        amountRange: [200000000, 400000000]
      });

      // Grade A: 프리미엄(500M), 표준(300M), 조건부(150M)
      // 금액 필터: min 200M <= maxAmount <= max 400M
      // 조건: 150M < 200M (제외), 300M OK, 500M > 400M (제외)
      // 예상: 표준 상품만 반환
      expect(result.every(p => p.maxAmount >= 200000000 && p.maxAmount <= 400000000)).toBe(true);
      expect(result.some(p => p.name.includes('표준'))).toBe(true);
    });

    it('[T-INT-003] 신용도 + 부동산 + 금액 삼중 필터 (Grade B + 원룸 + 150M~300M)', async () => {
      // 신용점수 700 (Grade B) + 원룸 + 금액 범위
      const result = await filterLoanProducts({
        creditScore: 700,
        propertyType: '원룸',
        amountRange: [150000000, 300000000]
      });

      // Grade B: 표준전세(700+) + 조건부대출(650+)
      // 원룸 지원: 표준전세(아파트,원룸,오피스텔) + 조건부(원룸,전세방)
      // 금액: 150M~300M
      // 예상: 표준(300M OK) + 조건부(150M OK)
      expect(result.every(p =>
        p.propertyTypes.includes('원룸') &&
        p.maxAmount >= 150000000 &&
        p.maxAmount <= 300000000
      )).toBe(true);
      expect(result.length).toBeGreaterThan(0);
    });

    it('[T-INT-004] 필터 없음 - 신용도만 입력 (Grade B)', async () => {
      // 신용점수 750만 입력, 부동산/금액 필터 없음
      const result = await filterLoanProducts({
        creditScore: 750
      });

      // Grade B: 신용도 700 이상인 모든 상품
      // 예상: 표준전세 + 조건부대출
      expect(result.length).toBeGreaterThan(0);
      expect(result.some(p => p.minCreditScore <= 750)).toBe(true);
    });

    it('[T-INT-005] 경계값 조합 (신용도 800 정확히 + 금액 500M)', async () => {
      // Grade A의 최소 신용점수 정확히 + 프리미엄 최대액 정확히
      const result = await filterLoanProducts({
        creditScore: 800,
        amountRange: [500000000, 500000000]
      });

      // 신용점수 800: Grade A 자격
      // 금액 500M: 프리미엄 상품의 최대액
      expect(result.some(p => p.maxAmount === 500000000)).toBe(true);
      expect(result.some(p => p.name.includes('프리미엄'))).toBe(true);
    });

    it('[T-INT-006] 조건 불만족 조합 (Grade D + 아파트 + 500M)', async () => {
      // 신용도 600 (Grade D = 거절) + 아파트 + 고액
      const result = await filterLoanProducts({
        creditScore: 600,
        propertyType: '아파트',
        amountRange: [500000000, 500000000]
      });

      // Grade D: 신용도 650 필요 (600 < 650)
      // 예상: 빈 배열 (상품 없음)
      expect(result).toHaveLength(0);
    });
  });
});

// ============================================================================
// Part 2: Financial Calculation Flow Tests (금융 계산 흐름)
// ============================================================================

describe('Integration: Financial Calculation Flows', () => {

  describe('[T-INT-101~104] 금융 서비스 통합 흐름', () => {

    it('[T-INT-101] 대출상품 필터링 → 이자 계산 흐름', async () => {
      // Step 1: 대출상품 조회
      const products = await filterLoanProducts({
        creditScore: 750
      });

      expect(products.length).toBeGreaterThan(0);

      // Step 2: 표준전세 선택 (첫 번째 상품)
      const selectedProduct = products[0];
      expect(selectedProduct.rate).toBeDefined();

      // Step 3: 선택한 상품의 이율로 이자 계산
      const loanPayment = await calculateLoanPayment({
        principal: 300000000,
        rate: selectedProduct.rate,
        term: 36
      });

      // Step 4: 계산 결과 검증
      expect(loanPayment.monthlyPayment).toBeGreaterThan(0);
      expect(loanPayment.totalPayment).toBeGreaterThan(loanPayment.monthlyPayment);
      expect(loanPayment.totalInterest).toBeGreaterThan(0);

      // Step 5: 데이터 일관성 검증
      const expectedMonthlyRate = selectedProduct.rate / 12 / 100;
      const expectedPayment =
        300000000 *
        (expectedMonthlyRate * Math.pow(1 + expectedMonthlyRate, 36)) /
        (Math.pow(1 + expectedMonthlyRate, 36) - 1);

      expect(loanPayment.monthlyPayment).toBeCloseTo(Math.round(expectedPayment), -3);
    });

    it('[T-INT-102] 신용도 평가 → 최대 대출액 → 상품 필터링', async () => {
      // Step 1: 신용도 평가
      const creditAssessment = await assessCredit({
        income: 50000000,
        debt: 30000000,
        creditScore: 750,
        assets: 200000000
      });

      expect(creditAssessment.approved).toBeDefined();
      expect(creditAssessment.maxLoanAmount).toBeGreaterThan(0);

      // Step 2: 신용도 정보 추출
      const maxLoan = creditAssessment.maxLoanAmount;
      const creditScore = creditAssessment.score;

      // Step 3: 최대 대출액 범위 내에서 상품 조회
      const products = await filterLoanProducts({
        creditScore: creditScore,
        amountRange: [0, maxLoan]
      });

      // Step 4: 검증
      expect(products.length).toBeGreaterThan(0);
      expect(products.every(p => p.maxAmount <= maxLoan)).toBe(true);
    });

    it('[T-INT-103] 서류 검증 + 신용도 평가 + 대출 신청 통합 흐름', async () => {
      // Note: Document validation은 현재 fetch 기반이 아니므로
      // 신용도 평가부터 시작

      // Step 1: 사용자 정보로 신용도 평가
      const creditAssessment = await assessCredit({
        income: 30000000,
        debt: 15000000,
        creditScore: 750,
        assets: 150000000
      });

      expect(creditAssessment.approved).toBe(true);
      expect(creditAssessment.recommendation).toBe('APPROVED');

      // Step 2: 승인된 신용도로 상품 조회
      const products = await filterLoanProducts({
        creditScore: creditAssessment.score
      });

      expect(products.length).toBeGreaterThan(0);

      // Step 3: 선택 상품으로 이자 계산
      const loanPayment = await calculateLoanPayment({
        principal: 200000000,
        rate: products[0].rate,
        term: 240
      });

      // Step 4: 최종 결과 검증 (대출 가능함)
      expect(loanPayment.monthlyPayment).toBeGreaterThan(0);
      expect(loanPayment.monthlyPayment * 240).toBeCloseTo(loanPayment.totalPayment, -5);
    });

    it('[T-INT-104] End-to-End 전체 대출 프로세스 (5단계)', async () => {
      // 시나리오: 신용도 우수 사용자의 대출 신청 완전 프로세스

      // Step 1: 신용도 평가
      console.log('Step 1: 신용도 평가');
      const creditAssessment = await assessCredit({
        income: 50000000,
        debt: 30000000,
        creditScore: 820,
        assets: 500000000
      });

      // Grade A: 신용도 800+ (score 820)
      expect(creditAssessment.score).toBeGreaterThanOrEqual(800);
      expect(creditAssessment.approved).toBe(true);
      const maxLoan = creditAssessment.maxLoanAmount;

      // Step 2: 대출 상품 조회
      console.log('Step 2: 대출 상품 조회');
      const products = await filterLoanProducts({
        creditScore: creditAssessment.score,
        propertyType: '아파트',
        amountRange: [200000000, maxLoan]
      });

      expect(products.length).toBeGreaterThan(0);
      const selectedProduct = products[0];

      // Step 3: 이자 계산
      console.log('Step 3: 이자 계산');
      const loanAmount = 300000000;
      const loanTerm = 240; // 20년

      const loanPayment = await calculateLoanPayment({
        principal: loanAmount,
        rate: selectedProduct.rate,
        term: loanTerm
      });

      expect(loanPayment.monthlyPayment).toBeGreaterThan(0);

      // Step 4: 월상환액 가능성 검증
      console.log('Step 4: 월상환액 가능성 검증');
      const monthlyIncome = creditAssessment.maxLoanAmount / (12 * 5); // 대략적 월소득
      const paymentToIncomeRatio = loanPayment.monthlyPayment / monthlyIncome;

      expect(paymentToIncomeRatio).toBeLessThan(1); // 월상환액 < 월소득

      // Step 5: 최종 결과 요약
      console.log('Step 5: 최종 결과 요약');
      const result = {
        creditGrade: creditAssessment.grade,
        approved: creditAssessment.approved,
        maxLoanAmount: creditAssessment.maxLoanAmount,
        selectedProduct: selectedProduct.name,
        interestRate: selectedProduct.rate,
        loanAmount: loanAmount,
        monthlyPayment: loanPayment.monthlyPayment,
        totalInterest: loanPayment.totalInterest,
        loanTerm: loanTerm
      };

      // 최종 검증
      expect(result.approved).toBe(true);
      expect(result.loanAmount).toBeLessThanOrEqual(result.maxLoanAmount);
      expect(result.monthlyPayment).toBeGreaterThan(0);
      expect(result.totalInterest).toBeGreaterThan(0);

      console.log('✅ 대출 프로세스 완료:', result);
    });
  });
});
