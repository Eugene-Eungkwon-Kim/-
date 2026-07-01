/**
 * D09: 대출 상품 필터링 테스트
 * Week 3 핵심 5개 테스트 + 추가 테스트
 */

import { describe, it, expect } from 'vitest';
import { filterLoanProducts } from './loan-service';

describe('LoanService.filterLoanProducts()', () => {

  describe('[T-L001~L004] 신용도별 필터링 (핵심 5개)', () => {

    it('[T-L001] 신용등급 A(800+): 프리미엄 + 표준 모두 조회', async () => {
      const result = await filterLoanProducts({ creditScore: 820 });

      expect(result).toHaveLength(2);
      expect(result[0].name).toBe('프리미엄 전월세');
      expect(result[0].rate).toBe(2.5);
      expect(result[1].name).toBe('표준 전세');
    });

    it('[T-L002] 신용등급 B(700-799): 표준만 조회', async () => {
      const result = await filterLoanProducts({ creditScore: 750 });

      expect(result).toHaveLength(1);
      expect(result[0].name).toBe('표준 전세');
      expect(result[0].rate).toBe(3.2);
    });

    it('[T-L003] 신용등급 C(650-699): 조건부 조회', async () => {
      const result = await filterLoanProducts({ creditScore: 670 });

      expect(result.length).toBeGreaterThan(0);
      expect(result.some(p => p.name.includes('조건부'))).toBe(true);
    });

    it('[T-L004] 신용등급 D(650 미만): 결과 없음', async () => {
      const result = await filterLoanProducts({ creditScore: 600 });

      expect(result).toHaveLength(0);
    });

    it('[T-L005] 신용도 경계값(800): 프리미엄 포함', async () => {
      const result = await filterLoanProducts({ creditScore: 800 });

      expect(result.some(p => p.name.includes('프리미엄'))).toBe(true);
    });
  });

  describe('[T-L101~L103] 부동산 유형별 필터링', () => {

    it('[T-L101] 아파트 필터링', async () => {
      const result = await filterLoanProducts({
        creditScore: 800,
        propertyType: '아파트'
      });

      expect(result.length).toBeGreaterThan(0);
      expect(result.every(p => p.propertyTypes.includes('아파트'))).toBe(true);
    });

    it('[T-L102] 원룸 필터링', async () => {
      const result = await filterLoanProducts({
        creditScore: 750,
        propertyType: '원룸'
      });

      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe('[T-L201~L203] 금액 범위 필터링', () => {

    it('[T-L201] 최소 금액 이상만 반환', async () => {
      const result = await filterLoanProducts({
        creditScore: 800,
        amountRange: [300000000, 500000000]
      });

      expect(result.every(p => p.maxAmount >= 300000000)).toBe(true);
    });

    it('[T-L202] 금액 범위 없을 시 모든 상품', async () => {
      const result = await filterLoanProducts({ creditScore: 750 });

      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe('[T-L301~L302] 에러 처리', () => {

    it('[T-L301] 음수 신용점수 입력 거부', () => {
      expect(async () => {
        await filterLoanProducts({ creditScore: -100 });
      }).rejects.toThrow('Credit score must be between 0 and 999');
    });

    it('[T-L302] 999 초과 신용점수 입력 거부', () => {
      expect(async () => {
        await filterLoanProducts({ creditScore: 1000 });
      }).rejects.toThrow('Credit score must be between 0 and 999');
    });
  });

});
