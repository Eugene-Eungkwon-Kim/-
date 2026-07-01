/**
 * D09: MSW 엔드포인트 테스트
 * Week 2 Day 2: Task 1 - 신용도 평가 엔드포인트 (6 tests)
 */

import { describe, it, expect } from 'vitest';

// Loan application endpoint logic (extracted from handlers for testing)
async function applyLoanEndpoint(input: any): Promise<any> {
  const products: { [key: string]: { maxAmount: number; maxTerm: number } } = {
    'prime-loan-1': { maxAmount: 500000000, maxTerm: 360 },
    'standard-loan-1': { maxAmount: 300000000, maxTerm: 240 },
    'conditional-loan-1': { maxAmount: 150000000, maxTerm: 180 }
  };

  if (!input.userId || input.loanAmount <= 0 || input.loanTerm <= 0) {
    throw new Error('Invalid input');
  }

  const product = products[input.productId];
  if (!product) throw new Error('Invalid productId');

  const creditScore = input.coApplicant?.creditScore || 750;
  let maxLoanAmount = 0;

  if (creditScore >= 800) {
    maxLoanAmount = 470000000;
  } else if (creditScore >= 700) {
    maxLoanAmount = 280000000;
  } else if (creditScore >= 650) {
    maxLoanAmount = 130000000;
  } else {
    return { status: 'rejected', approvedAmount: 0, approvedTerm: 0, monthlyPayment: 0 };
  }

  if (input.loanAmount > maxLoanAmount) {
    return { status: 'rejected', approvedAmount: maxLoanAmount, approvedTerm: 0, monthlyPayment: 0 };
  }

  if (input.loanTerm > product.maxTerm) {
    return { status: 'rejected', approvedAmount: input.loanAmount, approvedTerm: product.maxTerm, monthlyPayment: 0 };
  }

  const monthlyRate = 3.2 / 12 / 100;
  const monthlyPayment = input.loanAmount *
    (monthlyRate * Math.pow(1 + monthlyRate, input.loanTerm)) /
    (Math.pow(1 + monthlyRate, input.loanTerm) - 1);

  const estimatedMonthlyIncome = 4000000;
  const paymentRatio = (monthlyPayment / estimatedMonthlyIncome) * 100;

  if (paymentRatio > 40) {
    return {
      status: 'conditional',
      approvedAmount: input.loanAmount,
      approvedTerm: input.loanTerm,
      monthlyPayment: Math.round(monthlyPayment),
      totalInterest: Math.round(monthlyPayment * input.loanTerm - input.loanAmount),
      conditions: ['Provide collateral', 'Co-applicant required']
    };
  }

  return {
    status: 'approved',
    approvedAmount: input.loanAmount,
    approvedTerm: input.loanTerm,
    monthlyPayment: Math.round(monthlyPayment),
    totalInterest: Math.round(monthlyPayment * input.loanTerm - input.loanAmount)
  };
}

// Repayment schedule endpoint logic (extracted from handlers for testing)
async function repaymentScheduleEndpoint(input: {
  loanId: string;
  format?: 'summary' | 'detailed';
  currency?: 'KRW' | 'USD';
}): Promise<any> {
  const format = input.format || 'detailed';
  const currency = input.currency || 'KRW';
  const exchangeRate = 0.00075;

  const mockLoans: { [key: string]: { principal: number; rate: number; term: number } } = {
    'loan-001': { principal: 300000000, rate: 3.2, term: 240 },
    'loan-002': { principal: 150000000, rate: 4.5, term: 180 }
  };

  const loan = mockLoans[input.loanId];
  if (!loan) {
    throw new Error('Loan not found');
  }

  const monthlyRate = loan.rate / 12 / 100;
  const monthlyPayment = loan.principal *
    (monthlyRate * Math.pow(1 + monthlyRate, loan.term)) /
    (Math.pow(1 + monthlyRate, loan.term) - 1);

  const schedule = [];
  let balance = loan.principal;
  let totalPaid = 0;

  for (let period = 1; period <= loan.term; period++) {
    const interestPayment = Math.round(balance * monthlyRate);
    const principalPayment = Math.round(monthlyPayment - interestPayment);
    balance = Math.max(0, balance - principalPayment);
    totalPaid += Math.round(monthlyPayment);

    if (format === 'detailed' || period <= 12 || period % 12 === 0 || period === loan.term) {
      const scheduleEntry: any = {
        period,
        payment: Math.round(monthlyPayment)
      };

      if (format === 'detailed') {
        scheduleEntry.principal = principalPayment;
        scheduleEntry.interest = interestPayment;
        scheduleEntry.balance = balance;
        scheduleEntry.status = balance === 0 ? 'completed' : 'active';
      }

      if (currency === 'USD') {
        scheduleEntry.payment = Math.round(scheduleEntry.payment * exchangeRate);
        if (format === 'detailed') {
          scheduleEntry.principal = Math.round(scheduleEntry.principal * exchangeRate);
          scheduleEntry.interest = Math.round(scheduleEntry.interest * exchangeRate);
          scheduleEntry.balance = Math.round(scheduleEntry.balance * exchangeRate);
        }
      }

      schedule.push(scheduleEntry);
    }
  }

  const totalInterest = Math.round(monthlyPayment * loan.term - loan.principal);
  const totalInterestDisplay = currency === 'USD' ? Math.round(totalInterest * exchangeRate) : totalInterest;
  const monthlyPaymentDisplay = currency === 'USD' ? Math.round(monthlyPayment * exchangeRate) : Math.round(monthlyPayment);
  const principalDisplay = currency === 'USD' ? Math.round(loan.principal * exchangeRate) : loan.principal;

  return {
    loanId: input.loanId,
    loanDetails: {
      principal: principalDisplay,
      rate: loan.rate,
      term: loan.term
    },
    summary: {
      monthlyPayment: monthlyPaymentDisplay,
      totalPayment: Math.round(monthlyPayment * loan.term),
      totalInterest: totalInterestDisplay,
      paidAmount: totalPaid,
      remainingAmount: Math.max(0, Math.round(loan.principal - totalPaid))
    },
    schedule,
    earlyRepaymentOptions: {
      possibleFrom: 12,
      penaltyPercentage: 0,
      estimatedSavings: Math.round(totalInterest * 0.3)
    },
    currency
  };
}

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

// Enhanced product listing endpoint logic (extracted from handlers for testing)
async function listLoanProductsEndpoint(input: {
  creditScore: number;
  sortBy?: 'rate' | 'amount' | 'term';
  limit?: number;
  offset?: number;
}): Promise<any> {
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
    throw new Error('No products available for this credit score');
  }

  let sortedProducts = [...allProducts];
  if (sortBy === 'rate') {
    sortedProducts.sort((a, b) => a.rate - b.rate);
  } else if (sortBy === 'amount') {
    sortedProducts.sort((a, b) => b.maxAmount - a.maxAmount);
  } else if (sortBy === 'term') {
    sortedProducts.sort((a, b) => b.maxTerm - a.maxTerm);
  }

  const productsWithScore = sortedProducts.map((product, index) => ({
    ...product,
    eligibilityScore: Math.round((creditScore / 10 + (5 - index)) * 10) / 10,
    monthlyPaymentEstimate: Math.round((product.maxAmount * 0.01) / 12),
    competitorCount: Math.max(1, 5 - sortedProducts.length)
  }));

  const total = productsWithScore.length;
  const paginatedProducts = productsWithScore.slice(offset, offset + limit);
  const hasMore = offset + limit < total;

  return {
    products: paginatedProducts,
    pagination: {
      total,
      limit,
      offset,
      hasMore
    },
    timestamp: new Date().toISOString()
  };
}

describe('MSW Handlers: Enhanced Product Listing Endpoint (Task 4)', () => {

  describe('[T-API-301~305] 상품 조회 강화 기능', () => {

    it('[T-API-301] 이자율 정렬 (sortBy: rate)', async () => {
      const data = await listLoanProductsEndpoint({
        creditScore: 800,
        sortBy: 'rate'
      });

      expect(data.products.length).toBeGreaterThan(0);
      expect(data.pagination.total).toBe(data.products.length);

      // 이자율 오름차순 확인
      for (let i = 0; i < data.products.length - 1; i++) {
        expect(data.products[i].rate).toBeLessThanOrEqual(data.products[i + 1].rate);
      }
    });

    it('[T-API-302] 대출액 정렬 (sortBy: amount)', async () => {
      const data = await listLoanProductsEndpoint({
        creditScore: 800,
        sortBy: 'amount'
      });

      expect(data.products.length).toBeGreaterThan(0);

      // 대출액 내림차순 확인
      for (let i = 0; i < data.products.length - 1; i++) {
        expect(data.products[i].maxAmount).toBeGreaterThanOrEqual(data.products[i + 1].maxAmount);
      }
    });

    it('[T-API-303] 페이징 (limit: 1, offset: 0)', async () => {
      const data1 = await listLoanProductsEndpoint({
        creditScore: 800,
        limit: 1,
        offset: 0
      });

      expect(data1.products.length).toBe(1);
      expect(data1.pagination.total).toBe(2);
      expect(data1.pagination.hasMore).toBe(true);
      expect(data1.pagination.offset).toBe(0);

      const data2 = await listLoanProductsEndpoint({
        creditScore: 800,
        limit: 1,
        offset: 1
      });

      expect(data2.products.length).toBe(1);
      expect(data2.pagination.hasMore).toBe(false);
      expect(data2.pagination.offset).toBe(1);
      expect(data2.products[0].id).not.toBe(data1.products[0].id);
    });

    it('[T-API-304] 적합도 점수 (eligibilityScore)', async () => {
      const data = await listLoanProductsEndpoint({
        creditScore: 750
      });

      expect(data.products.length).toBeGreaterThan(0);
      expect(data.products[0].eligibilityScore).toBeDefined();

      for (const product of data.products) {
        expect(product.eligibilityScore).toBeGreaterThan(0);
        expect(product.monthlyPaymentEstimate).toBeGreaterThan(0);
        expect(product.competitorCount).toBeGreaterThan(0);
      }
    });

    it('[T-API-305] 상품 추천 정보 (popularityRank, competitorCount)', async () => {
      const data = await listLoanProductsEndpoint({
        creditScore: 800
      });

      expect(data.products.length).toBeGreaterThan(0);

      for (const product of data.products) {
        expect(product.popularityRank).toBeDefined();
        expect(product.popularityRank).toBeGreaterThan(0);
        expect(product.competitorCount).toBeDefined();
      }

      expect(data.timestamp).toBeDefined();
    });
  });
});

describe('MSW Handlers: Loan Application Endpoint (Task 1 - Day 3)', () => {

  describe('[T-API-401~405] 대출 신청 기능', () => {

    it('[T-API-401] 승인된 신청 (모든 조건 충족)', async () => {
      const data = await applyLoanEndpoint({
        userId: 'user123',
        loanAmount: 200000000,
        loanTerm: 240,
        productId: 'standard-loan-1',
        purpose: 'deposit',
        coApplicant: { name: 'John', creditScore: 800 }
      });

      expect(data.status).toBe('approved');
      expect(data.approvedAmount).toBe(200000000);
      expect(data.approvedTerm).toBe(240);
      expect(data.monthlyPayment).toBeGreaterThan(0);
      expect(data.totalInterest).toBeGreaterThan(0);
      expect(data.monthlyPayment).toBeLessThan(1700000); // 약 169만 예상
    });

    it('[T-API-402] 조건부 승인 (월상환액 과다)', async () => {
      const data = await applyLoanEndpoint({
        userId: 'user456',
        loanAmount: 250000000,
        loanTerm: 60,
        productId: 'standard-loan-1',
        purpose: 'purchase',
        coApplicant: { name: 'Jane', creditScore: 750 }
      });

      // Grade B (750) - maxLoan 280M OK, but high monthly payment triggers conditional
      expect(data.status).toBe('conditional');
      expect(data.approvedAmount).toBe(250000000);
      expect(data.conditions).toBeDefined();
    });

    it('[T-API-403] 거절 (월상환액 초과)', async () => {
      const data = await applyLoanEndpoint({
        userId: 'user789',
        loanAmount: 500000000,
        loanTerm: 36,
        productId: 'prime-loan-1',
        purpose: 'monthly-rent'
      });

      // Grade B (750) - maxLoan 280M, but trying 500M
      expect(data.status).toBe('rejected');
      expect(data.approvedAmount).toBeLessThanOrEqual(280000000);
    });

    it('[T-API-404] 거절 (신청액 > 최대액)', async () => {
      const data = await applyLoanEndpoint({
        userId: 'user999',
        loanAmount: 600000000,
        loanTerm: 240,
        productId: 'prime-loan-1',
        purpose: 'other'
      });

      expect(data.status).toBe('rejected');
      expect(data.approvedAmount).toBeLessThan(600000000);
    });

    it('[T-API-405] 공동신청자 포함 승인 (높은 신용도)', async () => {
      const data = await applyLoanEndpoint({
        userId: 'user111',
        loanAmount: 150000000,
        loanTerm: 180,
        productId: 'conditional-loan-1',
        purpose: 'deposit',
        coApplicant: { name: 'Co-Applicant', creditScore: 820 }
      });

      expect(data.status).toBe('approved');
      expect(data.approvedAmount).toBe(150000000);
      expect(data.monthlyPayment).toBeGreaterThan(0);
      expect(data.totalInterest).toBeGreaterThan(0);
    });
  });
});

describe('MSW Handlers: Repayment Schedule Endpoint (Task 2 - Day 3)', () => {

  describe('[T-API-501~505] 상환 일정 조회 기능', () => {

    it('[T-API-501] 요약 형식 (format: summary)', async () => {
      const data = await repaymentScheduleEndpoint({
        loanId: 'loan-001',
        format: 'summary',
        currency: 'KRW'
      });

      expect(data.loanId).toBe('loan-001');
      expect(data.loanDetails).toBeDefined();
      expect(data.loanDetails.principal).toBe(300000000);
      expect(data.summary).toBeDefined();
      expect(data.summary.monthlyPayment).toBeGreaterThan(0);
      expect(data.summary.totalPayment).toBeGreaterThan(0);
      expect(data.summary.totalInterest).toBeGreaterThan(0);
      expect(data.currency).toBe('KRW');

      // 요약 형식에서는 스케줄이 축약됨
      expect(Array.isArray(data.schedule)).toBe(true);
      expect(data.schedule.length).toBeLessThan(240);
    });

    it('[T-API-502] 상세 형식 (format: detailed)', async () => {
      const data = await repaymentScheduleEndpoint({
        loanId: 'loan-001',
        format: 'detailed',
        currency: 'KRW'
      });

      expect(data.loanId).toBe('loan-001');
      expect(data.schedule).toBeDefined();
      expect(Array.isArray(data.schedule)).toBe(true);
      expect(data.schedule.length).toBeGreaterThan(0);

      // 상세 형식에서는 각 항목에 principal, interest, balance 포함
      const firstSchedule = data.schedule[0];
      expect(firstSchedule.period).toBe(1);
      expect(firstSchedule.payment).toBeGreaterThan(0);
      expect(firstSchedule.principal).toBeGreaterThan(0);
      expect(firstSchedule.interest).toBeGreaterThan(0);
      expect(firstSchedule.balance).toBeGreaterThan(0);
      expect(firstSchedule.balance).toBeLessThan(data.loanDetails.principal);
      expect(firstSchedule.status).toBe('active');
    });

    it('[T-API-503] 부분 상환 추적 (주기별 잔액)', async () => {
      const data = await repaymentScheduleEndpoint({
        loanId: 'loan-002',
        format: 'detailed',
        currency: 'KRW'
      });

      expect(data.schedule).toBeDefined();
      expect(data.schedule.length).toBeGreaterThan(0);

      // 잔액이 점차 감소하는지 확인
      let prevBalance = data.loanDetails.principal;
      for (const item of data.schedule) {
        expect(item.balance).toBeLessThanOrEqual(prevBalance);
        prevBalance = item.balance;
      }

      // 마지막 항목의 잔액은 0에 가까워야 함
      const lastSchedule = data.schedule[data.schedule.length - 1];
      expect(lastSchedule.status).toBe('completed');
      expect(lastSchedule.balance).toBe(0);
    });

    it('[T-API-504] 조기 상환 옵션 (earlyRepaymentOptions)', async () => {
      const data = await repaymentScheduleEndpoint({
        loanId: 'loan-001',
        format: 'summary',
        currency: 'KRW'
      });

      expect(data.earlyRepaymentOptions).toBeDefined();
      expect(data.earlyRepaymentOptions.possibleFrom).toBe(12);
      expect(data.earlyRepaymentOptions.penaltyPercentage).toBe(0);
      expect(data.earlyRepaymentOptions.estimatedSavings).toBeGreaterThan(0);
      expect(data.earlyRepaymentOptions.estimatedSavings).toBeLessThanOrEqual(data.summary.totalInterest);
    });

    it('[T-API-505] 통화 변환 (currency: USD)', async () => {
      const dataKRW = await repaymentScheduleEndpoint({
        loanId: 'loan-001',
        format: 'summary',
        currency: 'KRW'
      });

      const dataUSD = await repaymentScheduleEndpoint({
        loanId: 'loan-001',
        format: 'summary',
        currency: 'USD'
      });

      expect(dataUSD.currency).toBe('USD');
      expect(dataKRW.currency).toBe('KRW');

      // USD 금액이 KRW에 환율을 곱한 것과 거의 같아야 함
      const exchangeRate = 0.00075;
      expect(dataUSD.summary.monthlyPayment).toBe(Math.round(dataKRW.summary.monthlyPayment * exchangeRate));
      expect(dataUSD.loanDetails.principal).toBe(Math.round(dataKRW.loanDetails.principal * exchangeRate));
    });
  });
});
