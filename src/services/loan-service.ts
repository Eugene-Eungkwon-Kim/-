/**
 * 대출 상품 필터링 서비스
 * D09: 금융로직 단위테스트
 */

import { LoanProduct, LoanFilter } from '@types/loan';

// Mock 데이터 (실제로는 API에서 가져옴)
const mockProducts: LoanProduct[] = [
  {
    id: 'prime-loan-1',
    name: '프리미엄 전월세',
    type: 'premium',
    minCreditScore: 800,
    rate: 2.5,
    maxAmount: 500000000,
    term: [120, 240],
    propertyTypes: ['아파트', '오피스텔'],
    requirements: { minIncome: 30000000, maxDebtRatio: 0.3 }
  },
  {
    id: 'standard-loan-1',
    name: '표준 전세',
    type: 'standard',
    minCreditScore: 700,
    rate: 3.2,
    maxAmount: 300000000,
    term: [120, 180, 240],
    propertyTypes: ['아파트', '원룸', '오피스텔'],
    requirements: { minIncome: 15000000, maxDebtRatio: 0.5 }
  },
  {
    id: 'conditional-loan-1',
    name: '조건부 대출',
    type: 'conditional',
    minCreditScore: 650,
    rate: 4.5,
    maxAmount: 150000000,
    term: [60, 120, 180],
    propertyTypes: ['원룸', '전세방'],
    requirements: { minIncome: 8000000, maxDebtRatio: 0.6, additionalReview: true }
  }
];

/**
 * 신용도에 따라 가능한 대출 상품 필터링
 * @param filter 필터 조건 (신용도, 부동산 유형, 금액 범위)
 * @returns 가능한 상품 목록
 */
export async function filterLoanProducts(filter: LoanFilter): Promise<LoanProduct[]> {
  // 입력 검증
  if (filter.creditScore < 0 || filter.creditScore > 999) {
    throw new Error('Credit score must be between 0 and 999');
  }

  // 신용도별 필터링
  let filtered = mockProducts.filter(p => p.minCreditScore <= filter.creditScore);

  // 부동산 유형별 필터링
  if (filter.propertyType) {
    filtered = filtered.filter(p => p.propertyTypes.includes(filter.propertyType!));
  }

  // 금액 범위 필터링
  if (filter.amountRange) {
    const [min, max] = filter.amountRange;
    filtered = filtered.filter(p => p.maxAmount >= min && p.maxAmount <= max);
  }

  return filtered;
}
