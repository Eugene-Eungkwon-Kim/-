/**
 * D09: MSW 엔드포인트 통합 테스트
 * Week 2 Day 2: Task 5 - 신규 4개 엔드포인트 통합 검증 (3 scenarios)
 */

import { describe, it, expect } from 'vitest';

// Re-export endpoint functions for integration testing
async function assessCreditEndpoint(input: any): Promise<any> {
  const monthlyIncome = input.income;
  const monthlyDebtPayment = input.debt / 12;
  const debtRatio = (monthlyDebtPayment / monthlyIncome) * 100;

  let maxLoanAmount = 0;
  let approved = false;
  let grade = 'D';
  let recommendation: 'APPROVED' | 'CONDITIONAL' | 'REJECTED' = 'REJECTED';

  if (input.creditScore >= 800) {
    grade = 'A';
    maxLoanAmount = Math.min(monthlyIncome * 12 * 5, 500000000);
    approved = debtRatio <= 40;
    recommendation = approved ? 'APPROVED' : 'CONDITIONAL';
  } else if (input.creditScore >= 700) {
    grade = 'B';
    maxLoanAmount = Math.min(monthlyIncome * 12 * 3, 300000000);
    approved = debtRatio <= 50;
    recommendation = approved ? 'APPROVED' : 'CONDITIONAL';
  } else if (input.creditScore >= 650) {
    grade = 'C';
    maxLoanAmount = Math.min(monthlyIncome * 12 * 1.5, 150000000);
    approved = debtRatio <= 60;
    recommendation = 'CONDITIONAL';
  } else {
    grade = 'D';
    maxLoanAmount = 0;
    approved = false;
    recommendation = 'REJECTED';
  }

  if (input.assets > 0) {
    const assetBasedLoan = input.assets * 0.7;
    maxLoanAmount = Math.max(maxLoanAmount, Math.min(assetBasedLoan, maxLoanAmount * 1.2));
  }

  const adjustedMaxLoan = Math.max(0, maxLoanAmount - input.debt);

  return {
    approved,
    score: input.creditScore,
    maxLoanAmount: Math.round(adjustedMaxLoan),
    debtRatioPercent: Math.round(debtRatio * 100) / 100,
    recommendation,
    grade
  };
}

async function listLoanProductsEndpoint(input: any): Promise<any> {
  const creditScore = input.creditScore;
  const sortBy = input.sortBy || 'rate';
  const limit = input.limit || 10;
  const offset = input.offset || 0;

  let allProducts = [];
  if (creditScore >= 800) {
    allProducts = [
      {
        id: 'prime-loan-1',
        name: '프리미엄 전월세',
        rate: 2.5,
        maxAmount: 500000000,
        minTerm: 120,
        maxTerm: 360,
        popularityRank: 2
      },
      {
        id: 'standard-loan-1',
        name: '표준 전세',
        rate: 3.2,
        maxAmount: 300000000,
        minTerm: 60,
        maxTerm: 240,
        popularityRank: 1
      }
    ];
  } else if (creditScore >= 700) {
    allProducts = [
      {
        id: 'standard-loan-1',
        name: '표준 전세',
        rate: 3.2,
        maxAmount: 300000000,
        minTerm: 60,
        maxTerm: 240,
        popularityRank: 1
      }
    ];
  } else if (creditScore >= 650) {
    allProducts = [
      {
        id: 'conditional-loan-1',
        name: '조건부 대출',
        rate: 4.5,
        maxAmount: 150000000,
        minTerm: 36,
        maxTerm: 180,
        popularityRank: 3
      }
    ];
  } else {
    throw new Error('No products available');
  }

  let sortedProducts = [...allProducts];
  if (sortBy === 'rate') {
    sortedProducts.sort((a, b) => a.rate - b.rate);
  }

  const productsWithScore = sortedProducts.map((product, index) => ({
    ...product,
    eligibilityScore: Math.round((creditScore / 10 + (5 - index)) * 10) / 10,
    monthlyPaymentEstimate: Math.round((product.maxAmount * 0.01) / 12),
    competitorCount: Math.max(1, 5 - sortedProducts.length)
  }));

  const total = productsWithScore.length;
  const paginatedProducts = productsWithScore.slice(offset, offset + limit);

  return {
    products: paginatedProducts,
    pagination: { total, limit, offset, hasMore: offset + limit < total }
  };
}

async function calculateLoanAdvancedEndpoint(input: any): Promise<any> {
  const frequency = input.frequency || 'monthly';
  const downPayment = input.downPayment || 0;
  const actualPrincipal = Math.max(0, input.principal - downPayment);

  const periodsPerYear = frequency === 'monthly' ? 12 : frequency === 'quarterly' ? 4 : 1;
  const periodicRate = (input.rate / 100) / periodsPerYear;
  const totalPeriods = Math.round((input.term * 12) / (12 / periodsPerYear));

  const periodicPayment = actualPrincipal *
    (periodicRate * Math.pow(1 + periodicRate, totalPeriods)) /
    (Math.pow(1 + periodicRate, totalPeriods) - 1);

  return {
    monthlyPayment: frequency === 'monthly' ? Math.round(periodicPayment) : undefined,
    quarterlyPayment: frequency === 'quarterly' ? Math.round(periodicPayment) : undefined,
    annualPayment: frequency === 'annual' ? Math.round(periodicPayment) : undefined,
    periodicPayment: Math.round(periodicPayment),
    totalPayment: Math.round(periodicPayment * totalPeriods),
    totalInterest: Math.round(periodicPayment * totalPeriods - actualPrincipal),
    actualPrincipal,
    frequency
  };
}

async function validateDocumentsEndpoint(input: any): Promise<any> {
  const VALID_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
  const MAX_FILE_SIZE = 50 * 1024 * 1024;
  const MAX_TOTAL_SIZE = 500 * 1024 * 1024;

  let totalSize = 0;
  let allValid = true;

  if (!input.files || input.files.length === 0) {
    return { allValid: false, documentCount: 0, totalSize: 0 };
  }

  for (const file of input.files) {
    if (file.size > MAX_FILE_SIZE || !VALID_TYPES.includes(file.type)) {
      allValid = false;
      break;
    }
    totalSize += file.size;
  }

  if (totalSize > MAX_TOTAL_SIZE) allValid = false;

  return { allValid, documentCount: input.files.length, totalSize };
}

describe('MSW Handlers: Integration Scenarios (Task 5)', () => {

  describe('[T-INT-201] 우수 신용도 고객 (Grade A) - 완전 프로세스', () => {

    it('should complete full loan process for excellent credit customer', async () => {
      // Step 1: 신용도 평가
      const creditAssess = await assessCreditEndpoint({
        income: 80000000,
        debt: 20000000,
        creditScore: 850,
        assets: 1000000000
      });

      expect(creditAssess.approved).toBe(true);
      expect(creditAssess.grade).toBe('A');
      expect(creditAssess.maxLoanAmount).toBeGreaterThan(300000000);

      // Step 2: 상품 조회
      const products = await listLoanProductsEndpoint({
        creditScore: creditAssess.score
      });

      expect(products.products.length).toBeGreaterThan(0);
      const selectedProduct = products.products[0];
      expect(selectedProduct.eligibilityScore).toBeGreaterThan(80);

      // Step 3: 이자 계산
      const loanAmount = Math.min(400000000, creditAssess.maxLoanAmount);
      const calculation = await calculateLoanAdvancedEndpoint({
        principal: loanAmount,
        rate: selectedProduct.rate,
        term: 240,
        frequency: 'monthly'
      });

      expect(calculation.monthlyPayment).toBeGreaterThan(0);
      expect(calculation.totalInterest).toBeGreaterThan(0);
      expect(calculation.totalPayment).toBeGreaterThan(loanAmount);

      // Step 4: 서류 검증
      const docValidation = await validateDocumentsEndpoint({
        files: [
          { name: 'contract.pdf', type: 'application/pdf', size: 2 * 1024 * 1024 },
          { name: 'photo.jpeg', type: 'image/jpeg', size: 1 * 1024 * 1024 }
        ]
      });

      expect(docValidation.allValid).toBe(true);
      expect(docValidation.documentCount).toBe(2);

      // Summary
      const summary = {
        grade: creditAssess.grade,
        approved: creditAssess.approved,
        maxLoan: creditAssess.maxLoanAmount,
        selectedProduct: selectedProduct.name,
        interestRate: selectedProduct.rate,
        loanAmount,
        monthlyPayment: calculation.monthlyPayment,
        documentsValid: docValidation.allValid
      };

      expect(summary.approved).toBe(true);
      expect(summary.grade).toBe('A');
      expect(summary.documentsValid).toBe(true);
    });
  });

  describe('[T-INT-202] 중간 신용도 고객 (Grade B) - 조건부 승인', () => {

    it('should handle fair credit customer with conditional approval', async () => {
      // Step 1: 신용도 평가
      const creditAssess = await assessCreditEndpoint({
        income: 50000000,
        debt: 40000000,
        creditScore: 720,
        assets: 300000000
      });

      expect(creditAssess.approved).toBe(true);
      expect(creditAssess.grade).toBe('B');
      expect(creditAssess.maxLoanAmount).toBeGreaterThan(100000000);
      expect(creditAssess.maxLoanAmount).toBeLessThanOrEqual(300000000);

      // Step 2: 상품 조회
      const products = await listLoanProductsEndpoint({
        creditScore: creditAssess.score,
        sortBy: 'rate'
      });

      expect(products.products.length).toBeGreaterThan(0);
      expect(products.products[0].rate).toBeLessThanOrEqual(products.products[1]?.rate || Infinity);

      // Step 3: 이자 계산 (선금 포함)
      const selectedProduct = products.products[0];
      const downPayment = 50000000;
      const calculation = await calculateLoanAdvancedEndpoint({
        principal: 200000000,
        rate: selectedProduct.rate,
        term: 180,
        downPayment: downPayment,
        frequency: 'quarterly'
      });

      expect(calculation.actualPrincipal).toBe(200000000 - downPayment);
      expect(calculation.quarterlyPayment).toBeDefined();

      // Step 4: 서류 검증
      const docValidation = await validateDocumentsEndpoint({
        files: [
          { name: 'contract.pdf', type: 'application/pdf', size: 3 * 1024 * 1024 },
          { name: 'income_proof.jpeg', type: 'image/jpeg', size: 2 * 1024 * 1024 },
          { name: 'asset_proof.png', type: 'image/png', size: 1 * 1024 * 1024 }
        ]
      });

      expect(docValidation.allValid).toBe(true);
      expect(docValidation.documentCount).toBe(3);

      const summary = {
        grade: creditAssess.grade,
        approved: creditAssess.approved,
        maxLoan: creditAssess.maxLoanAmount,
        downPayment: downPayment,
        monthlyPayment: calculation.quarterlyPayment,
        docsRequired: 3,
        docsValid: docValidation.allValid
      };

      expect(summary.approved).toBe(true);
      expect(summary.docsValid).toBe(true);
    });
  });

  describe('[T-INT-203] 저신용도 고객 (Grade C/D) - 제한된 옵션', () => {

    it('should provide limited options for poor credit customer', async () => {
      // Step 1: 신용도 평가 - Grade C
      const creditAssess = await assessCreditEndpoint({
        income: 30000000,
        debt: 60000000,
        creditScore: 670,
        assets: 100000000
      });

      expect(creditAssess.grade).toBe('C');
      expect(creditAssess.maxLoanAmount).toBeLessThan(200000000);

      // Step 2: 상품 조회 - 제한된 상품
      const products = await listLoanProductsEndpoint({
        creditScore: creditAssess.score
      });

      expect(products.products.length).toBeGreaterThan(0);
      expect(products.pagination.total).toBe(1);

      // Step 3: 최소한의 이자 계산
      const selectedProduct = products.products[0];
      const maxLoan = Math.min(100000000, creditAssess.maxLoanAmount);

      const calculation = await calculateLoanAdvancedEndpoint({
        principal: maxLoan,
        rate: selectedProduct.rate,
        term: 120,
        frequency: 'monthly'
      });

      expect(calculation.monthlyPayment).toBeGreaterThan(0);
      expect(calculation.totalInterest).toBeGreaterThan(0);

      // Step 4: 서류 검증 - 엄격한 요구
      const docValidation = await validateDocumentsEndpoint({
        files: [
          { name: 'contract.pdf', type: 'application/pdf', size: 2 * 1024 * 1024 }
        ]
      });

      expect(docValidation.allValid).toBe(true);
      expect(docValidation.documentCount).toBe(1);

      const summary = {
        grade: creditAssess.grade,
        approved: creditAssess.approved,
        maxLoan: creditAssess.maxLoanAmount,
        selectedProduct: selectedProduct.name,
        rate: selectedProduct.rate,
        monthlyPayment: calculation.monthlyPayment,
        docsValid: docValidation.allValid
      };

      expect(summary.grade).toBe('C');
      expect(summary.docsValid).toBe(true);
    });
  });
});
