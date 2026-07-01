/**
 * D09: MSW 엔드포인트 테스트
 * Week 2 Day 2: Task 1 - 신용도 평가 엔드포인트 (6 tests)
 */

import { describe, it, expect } from 'vitest';

// Credit assessment endpoint logic (extracted from handlers for testing)
async function assessCreditEndpoint(input: {
  income: number;
  debt: number;
  creditScore: number;
  assets: number;
}): Promise<any> {
  // 입력 검증
  if (input.income <= 0) {
    throw new Error('Income must be greater than 0');
  }
  if (input.debt < 0) {
    throw new Error('Debt cannot be negative');
  }
  if (input.creditScore < 0 || input.creditScore > 999) {
    throw new Error('Credit score must be between 0 and 999');
  }
  if (input.assets < 0) {
    throw new Error('Assets cannot be negative');
  }

  // 월간 부채 비율 계산
  const monthlyIncome = input.income;
  const monthlyDebtPayment = input.debt / 12;
  const debtRatio = (monthlyDebtPayment / monthlyIncome) * 100;

  // 신용 등급 결정 및 최대 대출액 계산
  let maxLoanAmount = 0;
  let approved = false;
  let recommendation: 'APPROVED' | 'CONDITIONAL' | 'REJECTED' = 'REJECTED';
  let grade = 'D';

  if (input.creditScore >= 800) {
    grade = 'A';
    maxLoanAmount = Math.min(
      monthlyIncome * 12 * 5,
      500000000
    );
    approved = debtRatio <= 40;
    recommendation = approved ? 'APPROVED' : 'CONDITIONAL';
  } else if (input.creditScore >= 700) {
    grade = 'B';
    maxLoanAmount = Math.min(
      monthlyIncome * 12 * 3,
      300000000
    );
    approved = debtRatio <= 50;
    recommendation = approved ? 'APPROVED' : 'CONDITIONAL';
  } else if (input.creditScore >= 650) {
    grade = 'C';
    maxLoanAmount = Math.min(
      monthlyIncome * 12 * 1.5,
      150000000
    );
    approved = debtRatio <= 60;
    recommendation = 'CONDITIONAL';
  } else {
    grade = 'D';
    maxLoanAmount = 0;
    approved = false;
    recommendation = 'REJECTED';
  }

  // 자산 기반 추가 대출액 계산
  if (input.assets > 0) {
    const assetBasedLoan = input.assets * 0.7;
    maxLoanAmount = Math.max(maxLoanAmount, Math.min(assetBasedLoan, maxLoanAmount * 1.2));
  }

  // 현재 부채를 고려한 최종 대출액 조정
  const adjustedMaxLoan = Math.max(0, maxLoanAmount - input.debt);

  return {
    approved,
    score: input.creditScore,
    maxLoanAmount: Math.round(adjustedMaxLoan),
    debtRatioPercent: Math.round(debtRatio * 100) / 100,
    recommendation,
    grade,
    message: approved
      ? `Credit assessment approved. Grade ${grade}. Max loan: ${Math.round(adjustedMaxLoan).toLocaleString()}원`
      : `Credit assessment ${recommendation.toLowerCase()}. Grade ${grade}.`
  };
}

// Advanced interest calculation endpoint logic (extracted from handlers for testing)
async function calculateLoanAdvancedEndpoint(input: {
  principal: number;
  rate: number;
  term: number;
  frequency?: 'monthly' | 'quarterly' | 'annual';
  downPayment?: number;
  generateSchedule?: boolean;
}): Promise<any> {
  const frequency = input.frequency || 'monthly';
  const downPayment = input.downPayment || 0;
  const generateSchedule = input.generateSchedule || false;
  const actualPrincipal = Math.max(0, input.principal - downPayment);

  const periodsPerYear = frequency === 'monthly' ? 12 : frequency === 'quarterly' ? 4 : 1;
  const periodicRate = (input.rate / 100) / periodsPerYear;
  const totalPeriods = Math.round((input.term * 12) / (12 / periodsPerYear));

  const periodicPayment = actualPrincipal *
    (periodicRate * Math.pow(1 + periodicRate, totalPeriods)) /
    (Math.pow(1 + periodicRate, totalPeriods) - 1);

  const totalPayment = Math.round(periodicPayment * totalPeriods);
  const totalInterest = Math.round(totalPayment - actualPrincipal);

  let amortizationSchedule = undefined;
  if (generateSchedule) {
    amortizationSchedule = [];
    let balance = actualPrincipal;

    for (let i = 1; i <= Math.min(totalPeriods, 360); i++) {
      const interestPayment = Math.round(balance * periodicRate);
      const principalPayment = Math.round(periodicPayment - interestPayment);
      balance = Math.max(0, balance - principalPayment);

      if (i <= 12 || i % 12 === 0 || i === totalPeriods) {
        amortizationSchedule.push({
          period: i,
          payment: Math.round(periodicPayment),
          principal: principalPayment,
          interest: interestPayment,
          balance: balance
        });
      }
    }
  }

  const earlyRepaymentInfo = {
    possibleFrom: 12,
    penaltyPercentage: 0,
    estimatedSavings: Math.round(totalInterest * 0.3)
  };

  return {
    monthlyPayment: frequency === 'monthly' ? Math.round(periodicPayment) : undefined,
    quarterlyPayment: frequency === 'quarterly' ? Math.round(periodicPayment) : undefined,
    annualPayment: frequency === 'annual' ? Math.round(periodicPayment) : undefined,
    periodicPayment: Math.round(periodicPayment),
    totalPayment,
    totalInterest,
    downPayment,
    actualPrincipal,
    amortizationSchedule,
    earlyRepaymentInfo,
    frequency,
    term: input.term
  };
}

describe('MSW Handlers: Credit Assessment Endpoint (Task 1)', () => {

  describe('[T-API-001~004] 신용 등급별 평가', () => {

    it('[T-API-001] Grade A: 신용도 우수 승인 (신용점수 800+)', async () => {
      const data = await assessCreditEndpoint({
        income: 50000000,
        debt: 30000000,
        creditScore: 820,
        assets: 500000000
      });

      expect(data.approved).toBe(true);
      expect(data.grade).toBe('A');
      expect(data.recommendation).toBe('APPROVED');
      expect(data.maxLoanAmount).toBeGreaterThan(200000000);
      expect(data.debtRatioPercent).toBeLessThan(40);
      expect(data.message).toContain('Grade A');
    });

    it('[T-API-002] Grade B: 신용도 양호 승인 (신용점수 700-799)', async () => {
      const data = await assessCreditEndpoint({
        income: 40000000,
        debt: 20000000,
        creditScore: 750,
        assets: 200000000
      });

      expect(data.approved).toBe(true);
      expect(data.grade).toBe('B');
      expect(data.recommendation).toBe('APPROVED');
      expect(data.maxLoanAmount).toBeGreaterThan(100000000);
      expect(data.maxLoanAmount).toBeLessThanOrEqual(300000000);
      expect(data.debtRatioPercent).toBeLessThan(50);
    });

    it('[T-API-003] Grade C: 신용도 보통 조건부 (신용점수 650-699)', async () => {
      const data = await assessCreditEndpoint({
        income: 30000000,
        debt: 15000000,
        creditScore: 670,
        assets: 100000000
      });

      expect(data.grade).toBe('C');
      expect(data.recommendation).toBe('CONDITIONAL');
      expect(data.maxLoanAmount).toBeGreaterThan(0);
      expect(data.maxLoanAmount).toBeLessThanOrEqual(150000000);
    });

    it('[T-API-004] Grade D: 신용도 불량 거절 (신용점수 <650)', async () => {
      const data = await assessCreditEndpoint({
        income: 30000000,
        debt: 15000000,
        creditScore: 600,
        assets: 50000000
      });

      expect(data.approved).toBe(false);
      expect(data.grade).toBe('D');
      expect(data.recommendation).toBe('REJECTED');
      expect(data.maxLoanAmount).toBe(0);
      expect(data.message).toContain('rejected');
    });
  });

  describe('[T-API-005~006] 부채비율 경계 및 초과', () => {

    it('[T-API-005] 부채비율 경계값 (정확히 40% at Grade A)', async () => {
      const monthlyIncome = 50000000;
      const monthlyDebtTarget = (monthlyIncome * 40) / 100;
      const debt = monthlyDebtTarget * 12;

      const data = await assessCreditEndpoint({
        income: monthlyIncome,
        debt: debt,
        creditScore: 800,
        assets: 0
      });

      expect(data.approved).toBe(true);
      expect(data.debtRatioPercent).toBe(40);
      expect(data.grade).toBe('A');
    });

    it('[T-API-006] 부채비율 초과 (41% at Grade A, 거절)', async () => {
      const monthlyIncome = 50000000;
      const monthlyDebtTarget = (monthlyIncome * 41) / 100;
      const debt = monthlyDebtTarget * 12;

      const data = await assessCreditEndpoint({
        income: monthlyIncome,
        debt: debt,
        creditScore: 800,
        assets: 0
      });

      expect(data.approved).toBe(false);
      expect(data.debtRatioPercent).toBeGreaterThan(40);
      expect(data.recommendation).toBe('CONDITIONAL');
      expect(data.grade).toBe('A');
    });
  });
});

describe('MSW Handlers: Advanced Loan Calculation Endpoint (Task 2)', () => {

  describe('[T-API-101~105] 고급 이자 계산 기능', () => {

    it('[T-API-101] 월상환 기본 계산 (frequency: monthly)', async () => {
      const data = await calculateLoanAdvancedEndpoint({
        principal: 300000000,
        rate: 3.2,
        term: 36,
        frequency: 'monthly'
      });

      expect(data.frequency).toBe('monthly');
      expect(data.monthlyPayment).toBeGreaterThan(0);
      expect(data.periodicPayment).toBe(data.monthlyPayment);
      expect(data.totalPayment).toBeGreaterThan(data.actualPrincipal);
      expect(data.totalInterest).toBeGreaterThan(0);
      expect(data.downPayment).toBe(0);
      expect(data.actualPrincipal).toBe(300000000);
    });

    it('[T-API-102] 분기상환 계산 (frequency: quarterly)', async () => {
      const data = await calculateLoanAdvancedEndpoint({
        principal: 300000000,
        rate: 3.2,
        term: 36,
        frequency: 'quarterly'
      });

      expect(data.frequency).toBe('quarterly');
      expect(data.quarterlyPayment).toBeGreaterThan(0);
      expect(data.periodicPayment).toBe(data.quarterlyPayment);
      expect(data.quarterlyPayment).toBeGreaterThan(0);
      expect(data.totalPayment).toBeGreaterThan(data.actualPrincipal);
    });

    it('[T-API-103] 선금 포함 계산 (downPayment: 50M)', async () => {
      const downPayment = 50000000;
      const principal = 300000000;

      const data = await calculateLoanAdvancedEndpoint({
        principal: principal,
        rate: 3.2,
        term: 36,
        frequency: 'monthly',
        downPayment: downPayment
      });

      expect(data.downPayment).toBe(downPayment);
      expect(data.actualPrincipal).toBe(principal - downPayment);
      expect(data.totalPayment).toBeGreaterThan(data.actualPrincipal);
      expect(data.totalInterest).toBeGreaterThan(0);
      expect(data.monthlyPayment).toBeGreaterThan(0);
    });

    it('[T-API-104] 상환 일정 생성 (generateSchedule: true)', async () => {
      const data = await calculateLoanAdvancedEndpoint({
        principal: 100000000,
        rate: 3.2,
        term: 12,
        frequency: 'monthly',
        generateSchedule: true
      });

      expect(data.amortizationSchedule).toBeDefined();
      expect(Array.isArray(data.amortizationSchedule)).toBe(true);
      expect(data.amortizationSchedule!.length).toBeGreaterThan(0);

      const firstSchedule = data.amortizationSchedule![0];
      expect(firstSchedule.period).toBe(1);
      expect(firstSchedule.payment).toBeGreaterThan(0);
      expect(firstSchedule.principal).toBeGreaterThan(0);
      expect(firstSchedule.interest).toBeGreaterThan(0);
      expect(firstSchedule.balance).toBeGreaterThan(0);
      expect(firstSchedule.balance).toBeLessThan(data.actualPrincipal);
    });

    it('[T-API-105] 조기 상환 정보 제공', async () => {
      const data = await calculateLoanAdvancedEndpoint({
        principal: 300000000,
        rate: 3.2,
        term: 240,
        frequency: 'monthly'
      });

      expect(data.earlyRepaymentInfo).toBeDefined();
      expect(data.earlyRepaymentInfo.possibleFrom).toBe(12);
      expect(data.earlyRepaymentInfo.penaltyPercentage).toBe(0);
      expect(data.earlyRepaymentInfo.estimatedSavings).toBeGreaterThan(0);
      expect(data.earlyRepaymentInfo.estimatedSavings).toBeLessThanOrEqual(data.totalInterest);
    });
  });
});

// Document validation endpoint logic (extracted from handlers for testing)
async function validateDocumentsEndpoint(input: {
  files: Array<{
    name: string;
    type: string;
    size: number;
  }>;
}): Promise<any> {
  const VALID_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
  const MAX_FILE_SIZE = 50 * 1024 * 1024;
  const MAX_TOTAL_SIZE = 500 * 1024 * 1024;

  const validations = [];
  let totalSize = 0;
  let allValid = true;

  if (!input.files || input.files.length === 0) {
    return {
      allValid: false,
      documentCount: 0,
      totalSize: 0,
      validations: [{
        filename: 'unknown',
        valid: false,
        errors: ['At least one file is required']
      }],
      message: 'No files provided'
    };
  }

  for (const file of input.files) {
    const errors: string[] = [];
    let fileValid = true;

    if (file.size > MAX_FILE_SIZE) {
      errors.push(`File size exceeds 50MB limit`);
      fileValid = false;
      allValid = false;
    }

    if (!VALID_TYPES.includes(file.type)) {
      errors.push(`File type ${file.type} not allowed. Must be PDF, JPEG, or PNG`);
      fileValid = false;
      allValid = false;
    }

    totalSize += file.size;

    validations.push({
      filename: file.name,
      valid: fileValid,
      size: file.size,
      type: file.type,
      errors
    });
  }

  if (totalSize > MAX_TOTAL_SIZE) {
    allValid = false;
    for (const validation of validations) {
      validation.errors = validation.errors || [];
      validation.errors.push('Total file size exceeds 500MB limit');
    }
  }

  return {
    allValid,
    documentCount: input.files.length,
    totalSize,
    validations,
    message: allValid ? 'All documents valid' : 'Some documents failed validation'
  };
}

describe('MSW Handlers: Document Validation Endpoint (Task 3)', () => {

  describe('[T-API-201~205] 서류 검증 기능', () => {

    it('[T-API-201] 유효한 PDF 파일 검증', async () => {
      const data = await validateDocumentsEndpoint({
        files: [
          {
            name: 'contract.pdf',
            type: 'application/pdf',
            size: 2 * 1024 * 1024
          }
        ]
      });

      expect(data.allValid).toBe(true);
      expect(data.documentCount).toBe(1);
      expect(data.totalSize).toBe(2 * 1024 * 1024);
      expect(data.validations[0].valid).toBe(true);
      expect(data.validations[0].errors).toHaveLength(0);
      expect(data.message).toContain('valid');
    });

    it('[T-API-202] 유효하지 않은 파일 형식 (image/gif)', async () => {
      const data = await validateDocumentsEndpoint({
        files: [
          {
            name: 'document.gif',
            type: 'image/gif',
            size: 1 * 1024 * 1024
          }
        ]
      });

      expect(data.allValid).toBe(false);
      expect(data.validations[0].valid).toBe(false);
      expect(data.validations[0].errors.length).toBeGreaterThan(0);
      expect(data.validations[0].errors[0]).toContain('not allowed');
    });

    it('[T-API-203] 파일 크기 초과 (60MB > 50MB)', async () => {
      const data = await validateDocumentsEndpoint({
        files: [
          {
            name: 'large_file.pdf',
            type: 'application/pdf',
            size: 60 * 1024 * 1024
          }
        ]
      });

      expect(data.allValid).toBe(false);
      expect(data.validations[0].valid).toBe(false);
      expect(data.validations[0].errors.some((e: string) => e.includes('exceeds 50MB'))).toBe(true);
    });

    it('[T-API-204] 여러 파일 검증 (혼합 유효성)', async () => {
      const data = await validateDocumentsEndpoint({
        files: [
          {
            name: 'contract.pdf',
            type: 'application/pdf',
            size: 2 * 1024 * 1024
          },
          {
            name: 'photo.png',
            type: 'image/png',
            size: 3 * 1024 * 1024
          },
          {
            name: 'invalid.doc',
            type: 'application/msword',
            size: 1 * 1024 * 1024
          }
        ]
      });

      expect(data.allValid).toBe(false);
      expect(data.documentCount).toBe(3);
      expect(data.validations[0].valid).toBe(true);
      expect(data.validations[1].valid).toBe(true);
      expect(data.validations[2].valid).toBe(false);
      expect(data.totalSize).toBe(6 * 1024 * 1024);
    });

    it('[T-API-205] 전체 용량 초과 (600MB > 500MB)', async () => {
      const data = await validateDocumentsEndpoint({
        files: [
          {
            name: 'file1.pdf',
            type: 'application/pdf',
            size: 300 * 1024 * 1024
          },
          {
            name: 'file2.pdf',
            type: 'application/pdf',
            size: 300 * 1024 * 1024
          }
        ]
      });

      expect(data.allValid).toBe(false);
      expect(data.totalSize).toBe(600 * 1024 * 1024);
      expect(data.validations.every((v: any) => v.errors.some((e: string) => e.includes('500MB')))).toBe(true);
    });
  });
});
