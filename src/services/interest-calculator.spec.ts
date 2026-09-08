/**
 * D09: 이자 계산 서비스 테스트
 * Week 1 Tuesday: 8개 테스트 케이스
 */

import { describe, it, expect } from 'vitest';
import { calculateLoanPayment } from './interest-calculator';

describe('InterestCalculator.calculateLoanPayment()', () => {

  describe('[T-I001~I004] 기본 이자 계산', () => {

    it('[T-I001] 기본 대출 계산 (300만원, 3%, 36개월)', async () => {
      const result = await calculateLoanPayment({
        principal: 30000000,
        rate: 3,
        term: 36
      });

      expect(result.monthlyPayment).toBeGreaterThan(0);
      expect(result.totalPayment).toBeGreaterThan(result.monthlyPayment);
      expect(result.totalInterest).toBeGreaterThan(0);
    });

    it('[T-I002] 높은 이율 영향 (같은 조건에서 이율 증가)', async () => {
      const low = await calculateLoanPayment({
        principal: 30000000,
        rate: 2,
        term: 36
      });

      const high = await calculateLoanPayment({
        principal: 30000000,
        rate: 5,
        term: 36
      });

      expect(high.monthlyPayment).toBeGreaterThan(low.monthlyPayment);
      expect(high.totalInterest).toBeGreaterThan(low.totalInterest);
    });

    it('[T-I003] 상환 기간 영향 (같은 조건에서 기간 연장)', async () => {
      const short = await calculateLoanPayment({
        principal: 30000000,
        rate: 3,
        term: 24
      });

      const long = await calculateLoanPayment({
        principal: 30000000,
        rate: 3,
        term: 60
      });

      expect(long.monthlyPayment).toBeLessThan(short.monthlyPayment);
      expect(long.totalInterest).toBeGreaterThan(short.totalInterest);
    });

    it('[T-I004] 0% 이율 특수 처리', async () => {
      const result = await calculateLoanPayment({
        principal: 30000000,
        rate: 0,
        term: 36
      });

      expect(result.totalInterest).toBe(0);
      expect(result.totalPayment).toBe(30000000);
      expect(result.monthlyPayment).toBe(Math.round(30000000 / 36));
    });
  });

  describe('[T-I101~I104] 특수 조건 계산', () => {

    it('[T-I101] 초고이율 대출 (10% 이율)', async () => {
      const result = await calculateLoanPayment({
        principal: 10000000,
        rate: 10,
        term: 24
      });

      expect(result.monthlyPayment).toBeGreaterThan(0);
      expect(result.totalInterest).toBeGreaterThan(result.monthlyPayment);
      expect(result.totalPayment).toBe(result.monthlyPayment * 24);
    });

    it('[T-I102] 장기 상환 계획 (50년 = 600개월)', async () => {
      const principal = 500000000;
      const result = await calculateLoanPayment({
        principal,
        rate: 2,
        term: 600
      });

      const baseMonthlyPayment = principal / 600;
      expect(result.monthlyPayment).toBeGreaterThan(baseMonthlyPayment);
      expect(result.totalPayment).toBeGreaterThan(principal);
    });

    it('[T-I103] 소액 대출 (최소 단위)', async () => {
      const result = await calculateLoanPayment({
        principal: 1000000,
        rate: 4,
        term: 12
      });

      expect(result.monthlyPayment).toBeGreaterThan(0);
      expect(result.totalInterest).toBeGreaterThan(0);
      expect(result.totalPayment).toBe(result.monthlyPayment * 12);
    });

    it('[T-I104] 대규모 대출 (5억원)', async () => {
      const principal = 500000000;
      const result = await calculateLoanPayment({
        principal,
        rate: 2.5,
        term: 240
      });

      expect(result.monthlyPayment).toBeGreaterThan(0);
      expect(result.totalPayment).toBeGreaterThan(principal);
      expect(result.totalInterest).toBeGreaterThan(0);
    });
  });

  describe('[T-I301~I303] 에러 처리', () => {

    it('[T-I301] 음수 원금 입력 거부', () => {
      expect(async () => {
        await calculateLoanPayment({
          principal: -10000000,
          rate: 3,
          term: 36
        });
      }).rejects.toThrow('Principal must be greater than 0');
    });

    it('[T-I302] 음수 이율 입력 거부', () => {
      expect(async () => {
        await calculateLoanPayment({
          principal: 30000000,
          rate: -1,
          term: 36
        });
      }).rejects.toThrow('Interest rate must be between 0 and 100');
    });

    it('[T-I303] 무효한 상환 기간 입력 거부', () => {
      expect(async () => {
        await calculateLoanPayment({
          principal: 30000000,
          rate: 3,
          term: 0
        });
      }).rejects.toThrow('Term must be between 1 and 600 months');
    });
  });

});
