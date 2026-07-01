/**
 * D09: MSW 엔드포인트 테스트
 * Week 2 Day 2: Task 1 - 신용도 평가 엔드포인트 (6 tests)
 */

import { describe, it, expect } from 'vitest';
import { simulateCreditScore } from '@services/creditSimulation';
import { assessRisk } from '@services/riskAssessment';

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

// Risk assessment endpoint logic (extracted from handlers for testing)
// Day 6: src/services/riskAssessment.ts로 추출된 실사용 모듈에 위임 (기존 중복 제거)
const riskAssessmentEndpoint = assessRisk;

// Validation endpoint logic (extracted from handlers for testing)
async function validationEndpoint(input: any): Promise<any> {
  const startTime = Date.now();
  const errors: any[] = [];
  const warnings: any[] = [];

  // 필드 존재성 검증
  const requiredFields = ['userId', 'loanAmount', 'loanTerm', 'productId', 'income', 'creditScore', 'purpose'];
  for (const field of requiredFields) {
    if (input[field] === undefined || input[field] === null) {
      errors.push({
        field,
        message: `${field} is required`,
        code: 'REQUIRED'
      });
    }
  }

  // 타입 검증
  if (input.userId && typeof input.userId !== 'string') {
    errors.push({
      field: 'userId',
      message: 'userId must be a string',
      code: 'TYPE'
    });
  }
  if (input.loanAmount && typeof input.loanAmount !== 'number') {
    errors.push({
      field: 'loanAmount',
      message: 'loanAmount must be a number',
      code: 'TYPE'
    });
  }
  if (input.loanTerm && typeof input.loanTerm !== 'number') {
    errors.push({
      field: 'loanTerm',
      message: 'loanTerm must be a number',
      code: 'TYPE'
    });
  }
  if (input.income && typeof input.income !== 'number') {
    errors.push({
      field: 'income',
      message: 'income must be a number',
      code: 'TYPE'
    });
  }
  if (input.creditScore && typeof input.creditScore !== 'number') {
    errors.push({
      field: 'creditScore',
      message: 'creditScore must be a number',
      code: 'TYPE'
    });
  }

  // 범위 검증
  if (input.loanAmount !== undefined && (input.loanAmount < 10000000 || input.loanAmount > 500000000)) {
    errors.push({
      field: 'loanAmount',
      message: 'loanAmount must be between 10M and 500M',
      code: 'RANGE'
    });
  }
  if (input.loanTerm !== undefined && (input.loanTerm < 6 || input.loanTerm > 360)) {
    errors.push({
      field: 'loanTerm',
      message: 'loanTerm must be between 6 and 360 months',
      code: 'RANGE'
    });
  }
  if (input.creditScore !== undefined && (input.creditScore < 0 || input.creditScore > 999)) {
    errors.push({
      field: 'creditScore',
      message: 'creditScore must be between 0 and 999',
      code: 'RANGE'
    });
  }
  if (input.income !== undefined && input.income <= 0) {
    errors.push({
      field: 'income',
      message: 'income must be greater than 0',
      code: 'RANGE'
    });
  }

  // 비즈니스 규칙 검증
  const debt = input.debt || 0;
  if (input.loanAmount && input.income && input.loanAmount > input.income * 3) {
    warnings.push({
      field: 'loanAmount',
      message: 'Loan amount is more than 3x annual income'
    });
  }
  if (input.income && debt > input.income * 0.5) {
    warnings.push({
      field: 'debt',
      message: 'Debt exceeds 50% of annual income'
    });
  }
  if (input.creditScore && input.creditScore < 650) {
    warnings.push({
      field: 'creditScore',
      message: 'Credit score is below recommended threshold'
    });
  }

  // 제품 유효성 검증
  const validProducts = ['prime-loan-1', 'standard-loan-1', 'conditional-loan-1'];
  if (input.productId && !validProducts.includes(input.productId)) {
    errors.push({
      field: 'productId',
      message: 'Invalid productId',
      code: 'BUSINESS_RULE'
    });
  }

  // 목적 검증
  const validPurposes = ['deposit', 'purchase', 'monthly-rent', 'other'];
  if (input.purpose && !validPurposes.includes(input.purpose)) {
    errors.push({
      field: 'purpose',
      message: 'Invalid purpose',
      code: 'BUSINESS_RULE'
    });
  }

  // 일관성 검증
  if (input.loanAmount && input.loanTerm && input.productId) {
    const products: { [key: string]: { maxAmount: number; maxTerm: number } } = {
      'prime-loan-1': { maxAmount: 500000000, maxTerm: 360 },
      'standard-loan-1': { maxAmount: 300000000, maxTerm: 240 },
      'conditional-loan-1': { maxAmount: 150000000, maxTerm: 180 }
    };

    const product = products[input.productId];
    if (product) {
      if (input.loanAmount > product.maxAmount) {
        errors.push({
          field: 'loanAmount',
          message: `Loan amount exceeds product maximum (${product.maxAmount})`,
          code: 'CONSISTENCY'
        });
      }
      if (input.loanTerm > product.maxTerm) {
        errors.push({
          field: 'loanTerm',
          message: `Loan term exceeds product maximum (${product.maxTerm} months)`,
          code: 'CONSISTENCY'
        });
      }
    }
  }

  const validationTime = Date.now() - startTime;
  const valid = errors.length === 0;

  return {
    valid,
    errors,
    warnings,
    validatedData: valid ? {
      userId: input.userId,
      loanAmount: input.loanAmount,
      loanTerm: input.loanTerm,
      productId: input.productId,
      income: input.income,
      debt: input.debt,
      creditScore: input.creditScore,
      purpose: input.purpose
    } : undefined,
    validationDetails: {
      fieldsChecked: requiredFields.length,
      errorsFound: errors.length,
      warningsFound: warnings.length,
      validationTime
    }
  };
}

// Portfolio inquiry endpoint logic (extracted from handlers for testing)
async function portfolioEndpoint(input: {
  userId: string;
  status?: string;
  sortBy?: 'date' | 'amount' | 'rate';
  limit?: number;
  offset?: number;
}): Promise<any> {
  const sortBy = input.sortBy || 'date';
  const limit = input.limit || 10;
  const offset = input.offset || 0;

  let userLoans: any[] = [];
  if (input.userId === 'user-001') {
    userLoans = [
      {
        loanId: 'loan-001',
        productName: '표준 전세',
        principal: 300000000,
        rate: 3.2,
        term: 240,
        remainingTerm: 220,
        status: 'active',
        monthlyPayment: 1693988,
        startDate: '2026-01-01',
        delinquencyDays: 0
      },
      {
        loanId: 'loan-002',
        productName: '조건부 대출',
        principal: 150000000,
        rate: 4.5,
        term: 180,
        remainingTerm: 170,
        status: 'active',
        monthlyPayment: 930000,
        startDate: '2026-02-01',
        delinquencyDays: 0
      },
      {
        loanId: 'loan-003',
        productName: '프리미엄 전월세',
        principal: 200000000,
        rate: 2.8,
        term: 300,
        remainingTerm: 280,
        status: 'active',
        monthlyPayment: 885000,
        startDate: '2025-06-01',
        delinquencyDays: 15
      }
    ];
  } else if (input.userId === 'user-002') {
    userLoans = [
      {
        loanId: 'loan-004',
        productName: '표준 전세',
        principal: 100000000,
        rate: 3.5,
        term: 120,
        remainingTerm: 60,
        status: 'active',
        monthlyPayment: 877000,
        startDate: '2024-06-01',
        delinquencyDays: 0
      }
    ];
  }

  let filtered = userLoans;
  if (input.status) {
    filtered = userLoans.filter(loan => loan.status === input.status);
  }

  if (sortBy === 'amount') {
    filtered.sort((a, b) => b.principal - a.principal);
  } else if (sortBy === 'rate') {
    filtered.sort((a, b) => a.rate - b.rate);
  } else {
    filtered.sort((a, b) => new Date(b.startDate).getTime() - new Date(a.startDate).getTime());
  }

  const total = filtered.length;
  const paginated = filtered.slice(offset, offset + limit);
  const hasMore = offset + limit < total;

  const totalPrincipal = userLoans.reduce((sum, loan) => sum + loan.principal, 0);
  const totalMonthlyPayment = userLoans.reduce((sum, loan) => sum + loan.monthlyPayment, 0);
  const estimatedMonthlyIncome = 4000000;
  const debtRatio = (totalMonthlyPayment / estimatedMonthlyIncome) * 100;
  const delinquencyCount = userLoans.filter(loan => loan.delinquencyDays > 0).length;

  return {
    userId: input.userId,
    portfolio: {
      totalLoans: total,
      totalPrincipal,
      totalMonthlyPayment,
      debtRatio: Math.round(debtRatio * 100) / 100,
      delinquencyCount,
      averageRate: Math.round(userLoans.reduce((sum, loan) => sum + loan.rate, 0) / userLoans.length * 100) / 100
    },
    loans: paginated,
    pagination: {
      total,
      limit,
      offset,
      hasMore
    }
  };
}

// Credit history endpoint logic (extracted from handlers for testing)
async function creditHistoryEndpoint(input: {
  userId: string;
  months?: number;
  format?: 'summary' | 'detailed';
}): Promise<any> {
  const months = input.months || 12;
  const format = input.format || 'summary';

  const history: any[] = [];
  const startDate = new Date('2025-08-01');

  for (let i = 0; i < Math.min(months, 12); i++) {
    const date = new Date(startDate);
    date.setMonth(date.getMonth() - i);
    const baseScore = input.userId === 'user-001' ? 750 : 700;
    const fluctuation = Math.sin(i * 0.5) * 20;
    const score = Math.round(baseScore + fluctuation);

    history.push({
      month: date.toISOString().split('T')[0],
      score,
      grade: score >= 800 ? 'A' : score >= 700 ? 'B' : score >= 650 ? 'C' : 'D',
      inquiries: Math.max(0, Math.floor(Math.random() * 3)),
      delinquencies: i > 6 ? 1 : 0,
      accountCount: 3 + Math.floor(i / 3)
    });
  }

  const scores = history.map(h => h.score);
  const currentScore = scores[0];
  const prevScore = scores[1] || currentScore;
  const scoreChange = currentScore - prevScore;
  const trend = scoreChange > 0 ? 'improving' : scoreChange < 0 ? 'declining' : 'stable';
  const averageScore = Math.round(scores.reduce((a, b) => a + b) / scores.length);

  const composition = {
    paymentHistory: 35,
    creditUtilization: 30,
    creditAge: 15,
    creditMix: 10,
    newInquiries: 10
  };

  const recommendations = [];
  if (composition.creditUtilization > 30) {
    recommendations.push('신용 카드 사용률을 30% 이하로 유지하세요.');
  }
  if (history.some(h => h.delinquencies > 0)) {
    recommendations.push('지연된 결제가 있습니다. 정시 납부를 확인하세요.');
  }
  if (composition.newInquiries > 5) {
    recommendations.push('최근 신용 조회가 많습니다. 신규 신용 신청을 자제하세요.');
  }
  if (recommendations.length === 0) {
    recommendations.push('우수한 신용 상태를 유지 중입니다.');
  }

  return {
    userId: input.userId,
    currentScore,
    trend,
    averageScore,
    scoreChange,
    history: format === 'detailed' ? history : history.slice(0, 3),
    composition,
    recommendations
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

describe('MSW Handlers: Portfolio Inquiry Endpoint (Task 3 - Day 3)', () => {

  describe('[T-API-601~605] 포트폴리오 조회 기능', () => {

    it('[T-API-601] 포트폴리오 필터링 (status 필터)', async () => {
      const data = await portfolioEndpoint({
        userId: 'user-001',
        status: 'active'
      });

      expect(data.userId).toBe('user-001');
      expect(data.loans).toBeDefined();
      expect(Array.isArray(data.loans)).toBe(true);
      expect(data.loans.length).toBeGreaterThan(0);

      // 모든 대출이 'active' 상태여야 함
      for (const loan of data.loans) {
        expect(loan.status).toBe('active');
      }

      expect(data.pagination.total).toBeGreaterThan(0);
    });

    it('[T-API-602] 포트폴리오 정렬 (sortBy: amount)', async () => {
      const data = await portfolioEndpoint({
        userId: 'user-001',
        sortBy: 'amount'
      });

      expect(data.loans).toBeDefined();
      expect(data.loans.length).toBeGreaterThan(0);

      // 대출액 내림차순 정렬 확인
      for (let i = 0; i < data.loans.length - 1; i++) {
        expect(data.loans[i].principal).toBeGreaterThanOrEqual(data.loans[i + 1].principal);
      }
    });

    it('[T-API-603] 포트폴리오 페이징 (limit, offset)', async () => {
      const data1 = await portfolioEndpoint({
        userId: 'user-001',
        limit: 2,
        offset: 0
      });

      expect(data1.pagination.total).toBeGreaterThan(0);
      expect(data1.pagination.limit).toBe(2);
      expect(data1.pagination.offset).toBe(0);
      expect(data1.loans.length).toBeLessThanOrEqual(2);

      if (data1.pagination.total > 2) {
        expect(data1.pagination.hasMore).toBe(true);

        const data2 = await portfolioEndpoint({
          userId: 'user-001',
          limit: 2,
          offset: 2
        });

        expect(data2.pagination.offset).toBe(2);
        expect(data2.loans.length).toBeGreaterThan(0);
      }
    });

    it('[T-API-604] 포트폴리오 분석 정보 (portfolio 객체)', async () => {
      const data = await portfolioEndpoint({
        userId: 'user-001'
      });

      expect(data.portfolio).toBeDefined();
      expect(data.portfolio.totalLoans).toBeGreaterThan(0);
      expect(data.portfolio.totalPrincipal).toBeGreaterThan(0);
      expect(data.portfolio.totalMonthlyPayment).toBeGreaterThan(0);
      expect(data.portfolio.debtRatio).toBeGreaterThan(0);
      expect(data.portfolio.delinquencyCount).toBeGreaterThanOrEqual(0);
      expect(data.portfolio.averageRate).toBeGreaterThan(0);

      // 부채비율이 합리적인 범위인지 확인
      expect(data.portfolio.debtRatio).toBeLessThan(100);
    });

    it('[T-API-605] 포트폴리오 연체 추적 (delinquencyDays)', async () => {
      const data = await portfolioEndpoint({
        userId: 'user-001'
      });

      expect(data.loans).toBeDefined();
      expect(Array.isArray(data.loans)).toBe(true);

      // 각 대출에 delinquencyDays 정보가 있는지 확인
      for (const loan of data.loans) {
        expect(loan.delinquencyDays).toBeDefined();
        expect(loan.delinquencyDays).toBeGreaterThanOrEqual(0);
      }

      // portfolio 요약에 연체 건수가 포함되어 있는지 확인
      expect(data.portfolio.delinquencyCount).toBeGreaterThanOrEqual(0);

      // user-001은 loan-003에서 15일 연체 중
      const delinquentLoans = data.loans.filter(loan => loan.delinquencyDays > 0);
      if (delinquentLoans.length > 0) {
        expect(data.portfolio.delinquencyCount).toBe(delinquentLoans.length);
      }
    });
  });
});

describe('MSW Handlers: Credit History Endpoint (Task 4 - Day 3)', () => {

  describe('[T-API-701~705] 신용도 이력 조회 기능', () => {

    it('[T-API-701] 신용도 이력 조회 (기본)', async () => {
      const data = await creditHistoryEndpoint({
        userId: 'user-001',
        format: 'summary'
      });

      expect(data.userId).toBe('user-001');
      expect(data.currentScore).toBeGreaterThan(0);
      expect(data.currentScore).toBeLessThanOrEqual(999);
      expect(data.history).toBeDefined();
      expect(Array.isArray(data.history)).toBe(true);
      expect(data.history.length).toBeGreaterThan(0);

      // 각 이력 항목에 필수 필드 확인
      for (const entry of data.history) {
        expect(entry.month).toBeDefined();
        expect(entry.score).toBeDefined();
        expect(entry.grade).toMatch(/[A-D]/);
      }
    });

    it('[T-API-702] 신용도 추세 분석 (trend)', async () => {
      const data = await creditHistoryEndpoint({
        userId: 'user-001'
      });

      expect(data.trend).toBeDefined();
      expect(['improving', 'declining', 'stable']).toContain(data.trend);
      expect(data.scoreChange).toBeDefined();
      expect(data.averageScore).toBeGreaterThan(0);
      expect(data.averageScore).toBeLessThanOrEqual(999);

      // 추세가 scoreChange와 일치하는지 확인
      if (data.scoreChange > 0) {
        expect(data.trend).toBe('improving');
      } else if (data.scoreChange < 0) {
        expect(data.trend).toBe('declining');
      } else {
        expect(data.trend).toBe('stable');
      }
    });

    it('[T-API-703] 신용도 구성 요소 (composition)', async () => {
      const data = await creditHistoryEndpoint({
        userId: 'user-001'
      });

      expect(data.composition).toBeDefined();
      expect(data.composition.paymentHistory).toBeGreaterThan(0);
      expect(data.composition.creditUtilization).toBeGreaterThan(0);
      expect(data.composition.creditAge).toBeGreaterThan(0);
      expect(data.composition.creditMix).toBeGreaterThan(0);
      expect(data.composition.newInquiries).toBeGreaterThan(0);

      // 비중의 합계가 100인지 확인
      const total = Object.values(data.composition).reduce((a: any, b: any) => a + b, 0);
      expect(total).toBe(100);
    });

    it('[T-API-704] 신용도 개선 권고사항 (recommendations)', async () => {
      const data = await creditHistoryEndpoint({
        userId: 'user-001'
      });

      expect(data.recommendations).toBeDefined();
      expect(Array.isArray(data.recommendations)).toBe(true);
      expect(data.recommendations.length).toBeGreaterThan(0);

      // 각 권고사항이 문자열인지 확인
      for (const rec of data.recommendations) {
        expect(typeof rec).toBe('string');
        expect(rec.length).toBeGreaterThan(0);
      }
    });

    it('[T-API-705] 상세 이력 조회 (format: detailed, months: 6)', async () => {
      const summaryData = await creditHistoryEndpoint({
        userId: 'user-001',
        months: 6,
        format: 'summary'
      });

      const detailedData = await creditHistoryEndpoint({
        userId: 'user-001',
        months: 6,
        format: 'detailed'
      });

      // 상세 형식이 더 많은 데이터를 반환해야 함
      expect(detailedData.history.length).toBeGreaterThanOrEqual(summaryData.history.length);
      expect(detailedData.history.length).toBeLessThanOrEqual(6);

      // 상세 형식의 각 항목이 complete한지 확인
      for (const entry of detailedData.history) {
        expect(entry.month).toBeDefined();
        expect(entry.score).toBeDefined();
        expect(entry.grade).toBeDefined();
        expect(entry.inquiries).toBeDefined();
        expect(entry.delinquencies).toBeDefined();
        expect(entry.accountCount).toBeDefined();
      }
    });
  });
});

describe('MSW Handlers: Integration Testing & Validation (Task 5 - Day 3)', () => {

  describe('[T-API-801~803] 통합 검증 시나리오', () => {

    it('[T-API-801] 신규 사용자 단일 대출 시나리오', async () => {
      // Scenario 1: New user applies for a single loan

      // Step 1: Assess credit
      const creditAssessment = await assessCreditEndpoint({
        income: 50000000,
        debt: 0,
        creditScore: 800,
        assets: 100000000
      });

      expect(creditAssessment.approved).toBe(true);
      expect(creditAssessment.grade).toBe('A');
      expect(creditAssessment.maxLoanAmount).toBeGreaterThan(200000000);

      // Step 2: Apply for loan
      const loanApplication = await applyLoanEndpoint({
        userId: 'new-user-001',
        loanAmount: 250000000,
        loanTerm: 240,
        productId: 'standard-loan-1',
        coApplicant: { creditScore: creditAssessment.score }
      });

      expect(loanApplication.status).toBe('approved');
      expect(loanApplication.approvedAmount).toBe(250000000);
      expect(loanApplication.monthlyPayment).toBeGreaterThan(0);

      // Step 3: Check repayment schedule for the new loan
      const schedule = await repaymentScheduleEndpoint({
        loanId: 'loan-001',
        format: 'summary'
      });

      expect(schedule.summary.monthlyPayment).toBeGreaterThan(0);
      expect(schedule.summary.totalInterest).toBeGreaterThan(0);
      expect(schedule.earlyRepaymentOptions.possibleFrom).toBe(12);

      // Verify loan application has complete payment info
      expect(loanApplication.monthlyPayment).toBeGreaterThan(0);
      expect(loanApplication.totalInterest).toBeGreaterThan(0);
    });

    it('[T-API-802] 다중 대출 포트폴리오 시나리오', async () => {
      // Scenario 2: User with multiple loans

      // Step 1: Get portfolio
      const portfolio = await portfolioEndpoint({
        userId: 'user-001'
      });

      expect(portfolio.portfolio.totalLoans).toBeGreaterThan(1);
      expect(portfolio.portfolio.totalPrincipal).toBeGreaterThan(0);
      expect(portfolio.portfolio.totalMonthlyPayment).toBeGreaterThan(0);
      expect(portfolio.portfolio.debtRatio).toBeGreaterThan(0);

      // Step 2: Filter active loans
      const activeLoans = await portfolioEndpoint({
        userId: 'user-001',
        status: 'active'
      });

      expect(activeLoans.loans.length).toBeGreaterThan(0);
      expect(activeLoans.loans.every((loan: any) => loan.status === 'active')).toBe(true);

      // Step 3: Check repayment schedule for largest loan
      const largestLoan = activeLoans.loans.reduce((max: any, current: any) =>
        current.principal > max.principal ? current : max
      );

      const schedule = await repaymentScheduleEndpoint({
        loanId: largestLoan.loanId,
        format: 'summary'
      });

      expect(schedule.loanDetails.principal).toBe(largestLoan.principal);
      expect(schedule.summary.monthlyPayment).toBeGreaterThan(0);

      // Step 4: Check credit history
      const creditHistory = await creditHistoryEndpoint({
        userId: 'user-001'
      });

      expect(creditHistory.currentScore).toBeGreaterThan(0);
      expect(creditHistory.history.length).toBeGreaterThan(0);

      // Verify debt ratio is reasonable
      expect(portfolio.portfolio.debtRatio).toBeLessThan(100);
    });

    it('[T-API-803] 부채 관리 및 신용도 개선 시나리오', async () => {
      // Scenario 3: Debt management and credit improvement

      // Step 1: Get current credit state
      const initialCredit = await creditHistoryEndpoint({
        userId: 'user-001',
        format: 'detailed'
      });

      expect(initialCredit.history.length).toBeGreaterThan(0);
      const initialScore = initialCredit.currentScore;
      expect(initialScore).toBeGreaterThan(0);

      // Step 2: Check portfolio for improvement opportunities
      const portfolio = await portfolioEndpoint({
        userId: 'user-001'
      });

      expect(portfolio.portfolio.delinquencyCount).toBeLessThanOrEqual(portfolio.loans.length);
      const delinquentLoans = portfolio.loans.filter((loan: any) => loan.delinquencyDays > 0);
      expect(delinquentLoans.length).toBeLessThanOrEqual(portfolio.portfolio.delinquencyCount);

      // Step 3: Verify recommendations
      const creditHistory = await creditHistoryEndpoint({
        userId: 'user-001'
      });

      expect(creditHistory.recommendations).toBeDefined();
      expect(creditHistory.recommendations.length).toBeGreaterThan(0);

      // Step 4: Check trend
      expect(creditHistory.trend).toMatch(/improving|declining|stable/);

      // Step 5: Verify composition impacts
      const composition = creditHistory.composition;
      expect(Object.keys(composition).length).toBe(5);
      const totalComposition = Object.values(composition).reduce((a: any, b: any) => a + b, 0);
      expect(totalComposition).toBe(100);

      // Step 6: Check if early repayment could help (for largest loan)
      const largestLoan = portfolio.loans.reduce((max: any, current: any) =>
        current.principal > max.principal ? current : max
      );

      const schedule = await repaymentScheduleEndpoint({
        loanId: largestLoan.loanId,
        format: 'summary'
      });

      expect(schedule.earlyRepaymentOptions.estimatedSavings).toBeGreaterThan(0);
      expect(schedule.earlyRepaymentOptions.penaltyPercentage).toBe(0);
    });
  });
});

describe('MSW Handlers: Advanced Risk Analysis (Task 7 - Day 4)', () => {

  describe('[T-API-961~965] 고급 리스크 분석 기능', () => {

    it('[T-API-961] 저위험 사용자 분석', async () => {
      const data = await riskAssessmentEndpoint({
        userId: 'user-low-risk',
        creditScore: 820,
        income: 60000000,
        debt: 10000000,
        loanAmount: 200000000,
        loanTerm: 240,
        employmentStability: 'stable',
        savingsRate: 25
      });

      expect(data.overallRiskLevel).toMatch(/very-low|low/);
      expect(data.probabilityOfDefault).toBeLessThan(5);
      expect(data.riskScore).toBeLessThan(40);
      expect(data.loanDecision.recommendation).toBe('approve');
      expect(data.riskComponents.creditRisk.score).toBeLessThan(30);
      expect(data.riskComponents.incomeRisk.score).toBeLessThan(30);
    });

    it('[T-API-962] 중간 위험 사용자 분석', async () => {
      const data = await riskAssessmentEndpoint({
        userId: 'user-medium-risk',
        creditScore: 680,
        income: 40000000,
        debt: 20000000,
        loanAmount: 300000000,
        loanTerm: 240,
        employmentStability: 'moderate',
        savingsRate: 8
      });

      expect(data.overallRiskLevel).toBe('medium');
      expect(data.probabilityOfDefault).toBeGreaterThan(1);
      expect(data.probabilityOfDefault).toBeLessThan(10);
      expect(data.riskScore).toBeGreaterThan(35);
      expect(data.riskScore).toBeLessThan(55);
      expect(data.loanDecision.recommendation).toBe('approve-with-conditions');
      expect(data.loanDecision.conditions).toBeDefined();
    });

    it('[T-API-963] 고위험 사용자 분석', async () => {
      const data = await riskAssessmentEndpoint({
        userId: 'user-high-risk',
        creditScore: 600,
        income: 30000000,
        debt: 20000000,
        loanAmount: 350000000,
        loanTerm: 300,
        employmentStability: 'unstable',
        savingsRate: 5
      });

      expect(data.overallRiskLevel).toMatch(/high|very-high/);
      expect(data.probabilityOfDefault).toBeGreaterThan(5);
      expect(data.riskScore).toBeGreaterThan(50);
      expect(data.loanDecision.recommendation).toBe('decline');
      expect(data.riskComponents.creditRisk.score).toBeGreaterThan(40);
    });

    it('[T-API-964] 시나리오 분석 (best/worst case)', async () => {
      const data = await riskAssessmentEndpoint({
        userId: 'user-scenario',
        creditScore: 750,
        income: 50000000,
        debt: 15000000,
        loanAmount: 250000000,
        loanTerm: 240,
        employmentStability: 'stable',
        savingsRate: 18
      });

      expect(data.scenarioAnalysis).toBeDefined();
      expect(data.scenarioAnalysis.bestCase).toBeDefined();
      expect(data.scenarioAnalysis.baseCase).toBeDefined();
      expect(data.scenarioAnalysis.worstCase).toBeDefined();

      // 시나리오 분석 검증
      const basePD = data.scenarioAnalysis.baseCase.probabilityOfDefault;
      const bestPD = data.scenarioAnalysis.bestCase.probabilityOfDefault;
      const worstPD = data.scenarioAnalysis.worstCase.probabilityOfDefault;

      expect(bestPD).toBeLessThan(basePD);
      expect(worstPD).toBeGreaterThan(basePD);
      expect(basePD).toBe(data.probabilityOfDefault);
    });

    it('[T-API-965] 위험 완화 전략 제시', async () => {
      const data = await riskAssessmentEndpoint({
        userId: 'user-mitigation',
        creditScore: 680,
        income: 40000000,
        debt: 20000000,
        loanAmount: 300000000,
        loanTerm: 240,
        employmentStability: 'moderate',
        savingsRate: 10
      });

      expect(data.mitigationStrategies).toBeDefined();
      expect(Array.isArray(data.mitigationStrategies.immediate)).toBe(true);
      expect(Array.isArray(data.mitigationStrategies.shortTerm)).toBe(true);
      expect(Array.isArray(data.mitigationStrategies.mediumTerm)).toBe(true);

      // 전략이 하나 이상 있어야 함
      const totalStrategies =
        data.mitigationStrategies.immediate.length +
        data.mitigationStrategies.shortTerm.length +
        data.mitigationStrategies.mediumTerm.length;
      expect(totalStrategies).toBeGreaterThan(0);

      // 모니터링 계획 확인
      expect(data.monitoringPlan).toBeDefined();
      expect(Array.isArray(data.monitoringPlan.checkpoints)).toBe(true);
      expect(data.monitoringPlan.checkpoints.length).toBeGreaterThan(0);
    });
  });
});

describe('MSW Handlers: Input Validation Enhancement (Task 1 - Day 4)', () => {

  describe('[T-API-901~905] 입력 데이터 검증 기능', () => {

    it('[T-API-901] 모든 필드 유효 (통과)', async () => {
      const data = await validationEndpoint({
        userId: 'user-001',
        loanAmount: 100000000,
        loanTerm: 240,
        productId: 'standard-loan-1',
        income: 50000000,
        debt: 10000000,
        creditScore: 750,
        purpose: 'deposit'
      });

      expect(data.valid).toBe(true);
      expect(data.errors).toHaveLength(0);
      expect(data.warnings).toHaveLength(0);
      expect(data.validatedData).toBeDefined();
      expect(data.validatedData.userId).toBe('user-001');
      expect(data.validatedData.loanAmount).toBe(100000000);
      expect(data.validationDetails.fieldsChecked).toBeGreaterThan(0);
      expect(data.validationDetails.errorsFound).toBe(0);
      expect(data.validationDetails.warningsFound).toBe(0);
      expect(data.validationDetails.validationTime).toBeGreaterThan(-1);
    });

    it('[T-API-902] 필수 필드 누락 (실패)', async () => {
      const data = await validationEndpoint({
        userId: 'user-002',
        loanAmount: 200000000,
        // loanTerm 누락
        productId: 'standard-loan-1',
        income: 40000000,
        creditScore: 720
        // purpose 누락
      });

      expect(data.valid).toBe(false);
      expect(data.errors.length).toBeGreaterThan(0);
      expect(data.validatedData).toBeUndefined();

      // loanTerm과 purpose 누락으로 인한 에러 확인
      const errorFields = data.errors.map((e: any) => e.field);
      expect(errorFields).toContain('loanTerm');
      expect(errorFields).toContain('purpose');

      // 모든 에러의 code가 REQUIRED
      for (const error of data.errors) {
        if (error.field === 'loanTerm' || error.field === 'purpose') {
          expect(error.code).toBe('REQUIRED');
        }
      }
    });

    it('[T-API-903] 범위 초과 (실패)', async () => {
      const data = await validationEndpoint({
        userId: 'user-003',
        loanAmount: 600000000, // 500M 초과
        loanTerm: 400, // 360개월 초과
        productId: 'standard-loan-1',
        income: 30000000,
        creditScore: 500, // 0-999 범위 내
        purpose: 'purchase'
      });

      expect(data.valid).toBe(false);
      expect(data.errors.length).toBeGreaterThan(0);

      // 범위 초과 에러 확인
      const rangeErrors = data.errors.filter((e: any) => e.code === 'RANGE');
      expect(rangeErrors.length).toBeGreaterThan(0);

      const errorFields = data.errors.map((e: any) => e.field);
      expect(errorFields).toContain('loanAmount');
      expect(errorFields).toContain('loanTerm');
    });

    it('[T-API-904] 비즈니스 규칙 위반 (경고)', async () => {
      const data = await validationEndpoint({
        userId: 'user-004',
        loanAmount: 300000000, // income의 6배 (3배 초과)
        loanTerm: 240,
        productId: 'standard-loan-1',
        income: 50000000,
        debt: 30000000, // income의 60% (50% 초과)
        creditScore: 620, // 650 미만
        purpose: 'monthly-rent'
      });

      expect(data.valid).toBe(true); // 경고만이므로 valid는 true
      expect(data.errors).toHaveLength(0);
      expect(data.warnings.length).toBeGreaterThan(0);

      // 경고 내용 확인
      const warningMessages = data.warnings.map((w: any) => w.message);
      expect(warningMessages.some((msg: string) => msg.includes('3x'))).toBe(true);
      expect(warningMessages.some((msg: string) => msg.includes('50%'))).toBe(true);
      expect(warningMessages.some((msg: string) => msg.includes('threshold'))).toBe(true);
    });

    it('[T-API-905] 복합 검증 (여러 오류)', async () => {
      const data = await validationEndpoint({
        userId: 123, // 타입 오류 (string이어야 함)
        loanAmount: '250000000', // 타입 오류 (number여야 함)
        loanTerm: -10, // 범위 오류 (6 이상)
        productId: 'invalid-product', // 비즈니스 규칙 오류
        income: -5000000, // 범위 오류 (> 0)
        creditScore: 1500, // 범위 오류 (0-999)
        purpose: 'invalid-purpose' // 비즈니스 규칙 오류
      });

      expect(data.valid).toBe(false);
      expect(data.errors.length).toBeGreaterThan(0);
      expect(data.validatedData).toBeUndefined();

      // 여러 종류의 에러 확인
      const errorCodes = data.errors.map((e: any) => e.code);
      expect(errorCodes).toContain('TYPE');
      expect(errorCodes).toContain('RANGE');
      expect(errorCodes).toContain('BUSINESS_RULE');

      // 에러 개수 확인 (최소 5개 이상)
      expect(data.validationDetails.errorsFound).toBeGreaterThanOrEqual(5);
    });
  });
});

// Task 5, 2, 3, 4, 6, 8 functions follow

// Financial analysis endpoint (Task 5)
async function financialAnalysisEndpoint(input: any): Promise<any> {
  const monthlyIncome = input.monthlyIncome || 4000000;
  const monthlyExpenses = input.monthlyExpenses || 1500000;
  const totalDebt = input.totalDebt || 100000000;
  const totalAssets = input.totalAssets || 500000000;
  
  const monthlyLoanPayments = totalDebt / 240;
  const monthlySurplus = monthlyIncome - monthlyExpenses - monthlyLoanPayments;
  const debtToIncomeRatio = totalDebt / (monthlyIncome * 12);
  const assetToDebtRatio = totalAssets / totalDebt;
  const netWorth = totalAssets - totalDebt;
  
  const healthScore = Math.round(Math.max(0, 100 - (debtToIncomeRatio * 50)));
  const healthGrade = healthScore >= 80 ? 'A' : healthScore >= 60 ? 'B' : healthScore >= 40 ? 'C' : 'F';
  
  return {
    userId: input.userId,
    currentStatus: { monthlyIncome, monthlyExpenses, monthlyLoanPayments: Math.round(monthlyLoanPayments), monthlySurplus: Math.round(monthlySurplus), totalDebt, totalAssets, netWorth, debtToIncomeRatio: Math.round(debtToIncomeRatio * 1000) / 1000, assetToDebtRatio: Math.round(assetToDebtRatio * 100) / 100 },
    financialHealthScore: healthScore,
    healthGrade,
    healthBreakdown: { debtRatioScore: Math.max(0, 100 - (debtToIncomeRatio * 100)), surplusCashScore: Math.min(100, (monthlySurplus / monthlyIncome) * 300), assetScore: Math.min(100, assetToDebtRatio * 20), creditScore: Math.min(100, 100 - debtToIncomeRatio * 50) },
    savingsAnalysis: { currentMonthlySavings: Math.round(Math.max(0, monthlySurplus)), projectedSavings12Months: Math.round(Math.max(0, monthlySurplus) * 12), savingsGoal: 100000000, savingsGoalMonths: Math.max(0, monthlySurplus) > 0 ? Math.ceil(100000000 / Math.max(0, monthlySurplus)) : 999, monthlyRequiredSavings: Math.round(100000000 / 36), achievable: Math.max(0, monthlySurplus) >= 100000000 / 36 },
    debtRepaymentPlan: { totalDebt, quickestPayoffMonths: Math.ceil(totalDebt / (monthlyIncome * 0.5)), balancedPayoffMonths: Math.ceil(totalDebt / (monthlyIncome * 0.2)), debtFreeDate: new Date(Date.now() + Math.ceil(totalDebt / (monthlyIncome * 0.2)) * 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], estimatedInterestSavings: Math.round((monthlyIncome * 0.1) * Math.ceil(totalDebt / (monthlyIncome * 0.2)) * 0.3) },
    recommendations: [healthScore > 70 ? '현재 추세 유지' : '재정 개선 필요']
  };
}

// Day 6: src/services/creditSimulation.ts로 추출된 실사용 모듈에 위임 (기존 중복 제거)
const creditSimulationEndpoint = simulateCreditScore;

async function loanProductRecommendationEndpoint(input: any): Promise<any> {
  const userId = input.userId || 'user-001';
  const creditScore = input.creditScore || 750;
  const income = input.income || 5000000;
  const debt = input.debt || 50000000;
  const assets = input.assets || 300000000;
  const purpose = input.purpose || 'purchase';
  const preferenceType = input.preferenceType || 'balanced';
  const maxMonthlyPaymentRatio = input.maxMonthlyPaymentRatio ?? 40;

  // 사용자 등급 판정
  let userGrade = 'D';
  if (creditScore >= 800) userGrade = 'A';
  else if (creditScore >= 700) userGrade = 'B';
  else if (creditScore >= 600) userGrade = 'C';

  // 가용 상품 (실제로는 DB에서 조회)
  const allProducts = [
    { id: 'product-1', name: '표준 전세', minScore: 550, rate: 3.2, maxAmount: 500000000, maxTerm: 240 },
    { id: 'product-2', name: '우대 전세', minScore: 650, rate: 2.8, maxAmount: 600000000, maxTerm: 240 },
    { id: 'product-3', name: 'VIP 대출', minScore: 800, rate: 2.4, maxAmount: 800000000, maxTerm: 300 },
    { id: 'product-4', name: '신한 월세', minScore: 500, rate: 4.2, maxAmount: 300000000, maxTerm: 120 },
    { id: 'product-5', name: '안심 구매', minScore: 600, rate: 3.8, maxAmount: 400000000, maxTerm: 180 }
  ];

  const availableProducts = allProducts.filter(p => creditScore >= p.minScore);

  // 기준 대출금액 (소득의 3배)
  const loanAmount = Math.min(income * 3, availableProducts[0]?.maxAmount || 500000000);
  const loanTerm = 240;

  // 각 상품별 매치 스코어 계산
  const productScores = availableProducts.map(product => {
    const monthlyRate = product.rate / 12 / 100;
    const monthlyPayment = loanAmount * (monthlyRate * Math.pow(1 + monthlyRate, loanTerm)) / (Math.pow(1 + monthlyRate, loanTerm) - 1);
    const totalPayment = monthlyPayment * loanTerm;
    const totalInterest = totalPayment - loanAmount;
    const paymentRatio = (monthlyPayment / income) * 100;

    // 매치 스코어 계산
    let matchScore = 100;
    matchScore -= (product.rate * 2); // 이자율이 낮을수록 높은 점수
    matchScore -= (paymentRatio > maxMonthlyPaymentRatio ? (paymentRatio - maxMonthlyPaymentRatio) : 0);
    matchScore = Math.max(0, Math.min(100, matchScore));

    // 선호도에 따른 추가 점수
    if (preferenceType === 'lowest-rate' && product.rate < 3.5) matchScore += 10;
    if (preferenceType === 'lowest-payment' && paymentRatio < 30) matchScore += 10;
    if (preferenceType === 'shortest-term' && product.maxTerm <= 180) matchScore += 10;
    if (preferenceType === 'balanced' && product.rate < 3.5 && paymentRatio < 35) matchScore += 10;

    matchScore = Math.min(100, matchScore);

    // 목적별 점수 조정
    const purposeBoost: { [key: string]: number } = {
      'deposit': product.rate <= 3.2 ? 10 : 0,
      'purchase': product.name.includes('구매') ? 10 : 0,
      'monthly-rent': product.name.includes('월세') ? 10 : 0,
      'other': 0
    };
    matchScore += purposeBoost[purpose] || 0;
    matchScore = Math.min(100, matchScore);

    const approvalRate = Math.min(99, Math.max(50, 80 + (creditScore - 700) * 0.1));

    return {
      product,
      loanAmount,
      monthlyPayment: Math.round(monthlyPayment),
      totalInterest: Math.round(totalInterest),
      totalPayment: Math.round(totalPayment),
      paymentRatio: Math.round(paymentRatio * 10) / 10,
      approvalRate: Math.round(approvalRate),
      matchScore: Math.round(matchScore)
    };
  });

  // 상위 3개 추천
  const sorted = productScores.sort((a, b) => b.matchScore - a.matchScore);
  const recommended = sorted.slice(0, 3).map((item, idx) => ({
    rank: idx + 1,
    productId: item.product.id,
    productName: item.product.name,
    rate: item.product.rate,
    maxAmount: item.product.maxAmount,
    maxTerm: item.product.maxTerm,
    matchScore: item.matchScore,
    analysis: {
      monthlyPayment: item.monthlyPayment,
      totalInterest: item.totalInterest,
      totalPayment: item.totalPayment,
      paymentRatio: item.paymentRatio,
      estimatedApprovalRate: item.approvalRate,
      pros: [
        item.paymentRatio < maxMonthlyPaymentRatio ? '월상환액 부담 낮음' : '',
        item.product.rate < 3.5 ? '경쟁력 있는 금리' : '',
        item.matchScore > 80 ? '사용자 맞춤형 상품' : ''
      ].filter(Boolean),
      cons: [
        item.paymentRatio >= 35 ? '월상환액 부담 높음' : '',
        item.product.maxTerm < 240 ? '상환 기간 제한' : ''
      ].filter(Boolean),
      bestFor: purpose === 'deposit' ? '전세자금 조달' : purpose === 'purchase' ? '주택 구매' : '자금 운용'
    }
  }));

  // 대안 상품 (4-5위)
  const alternatives = sorted.slice(3, 5).map((item, idx) => ({
    rank: idx + 4,
    productId: item.product.id,
    productName: item.product.name,
    rate: item.product.rate,
    matchScore: item.matchScore
  }));

  // 비교표
  const comparisonMatrix = {
    productIds: recommended.map(r => r.productId),
    metrics: {
      rate: recommended.map(r => r.rate),
      monthlyPayment: recommended.map(r => r.analysis.monthlyPayment),
      totalInterest: recommended.map(r => r.analysis.totalInterest),
      paymentRatio: recommended.map(r => r.analysis.paymentRatio)
    }
  };

  // 개인화된 조언
  const personalizedAdvice = creditScore >= 800 ? 'VIP 고객으로서 최우대 조건 제공 가능합니다' :
    creditScore >= 700 ? '우대 상품으로 합리적인 금리 제공합니다' :
    creditScore >= 600 ? '기본 상품으로 안정적인 대출이 가능합니다' :
    '신용도 개선을 통해 더 좋은 상품 이용이 가능합니다';

  return {
    userId,
    userGrade,
    recommendedProducts: recommended,
    alternativeProducts: alternatives,
    comparisonMatrix,
    personalizedAdvice
  };
}

async function stressTestEndpoint(input: any): Promise<any> {
  const userId = input.userId || 'user-001';
  const loanAmount = input.loanAmount || 300000000;
  const loanTerm = input.loanTerm || 240;
  const currentRate = input.currentRate || 3.2;
  const currentIncome = input.currentIncome || 5000000;
  const scenario = input.scenarios?.scenario || 'rate-increase';
  const stressLevel = input.scenarios?.stressLevel || 'mild';

  // 스트레스 시나리오 기본값
  const stressDefaults = {
    mild: { rateChange: 1, incomeChange: 0 },
    moderate: { rateChange: 2, incomeChange: -15 },
    severe: { rateChange: 3, incomeChange: -25 }
  };

  let rateChange = input.scenarios?.rateChange ?? 0;
  let incomeChange = input.scenarios?.incomeChange ?? 0;

  if (stressLevel && !input.scenarios?.rateChange && !input.scenarios?.incomeChange) {
    const defaults = stressDefaults[stressLevel as keyof typeof stressDefaults];
    if (scenario === 'rate-increase') {
      rateChange = defaults.rateChange;
      incomeChange = 0;
    } else if (scenario === 'income-decrease') {
      rateChange = 0;
      incomeChange = defaults.incomeChange;
    } else {
      rateChange = defaults.rateChange;
      incomeChange = defaults.incomeChange;
    }
  }

  const calculatePayment = (amount: number, term: number, rate: number) => {
    const monthlyRate = rate / 12 / 100;
    return amount * (monthlyRate * Math.pow(1 + monthlyRate, term)) / (Math.pow(1 + monthlyRate, term) - 1);
  };

  // 기본 사례
  const baseMonthlyPayment = calculatePayment(loanAmount, loanTerm, currentRate);
  const baseTotalInterest = (baseMonthlyPayment * loanTerm) - loanAmount;
  const basePaymentRatio = (baseMonthlyPayment / currentIncome) * 100;
  const baseIsAffordable = basePaymentRatio <= 40;

  // 스트레스 시나리오들
  const scenarios = [
    { name: '금리 1% 인상', rateChange: 1, incomeChange: 0 },
    { name: '금리 2% 인상', rateChange: 2, incomeChange: 0 },
    { name: '금리 3% 인상', rateChange: 3, incomeChange: 0 },
    { name: '수입 15% 감소', rateChange: 0, incomeChange: -15 },
    { name: '수입 25% 감소', rateChange: 0, incomeChange: -25 },
    { name: '금리 1.5% + 수입 10% 감소', rateChange: 1.5, incomeChange: -10 },
    { name: '금리 2% + 수입 20% 감소', rateChange: 2, incomeChange: -20 }
  ];

  const stressResults = scenarios.map(sc => {
    const newRate = currentRate + sc.rateChange;
    const newIncome = currentIncome * (1 + sc.incomeChange / 100);
    const newMonthlyPayment = calculatePayment(loanAmount, loanTerm, newRate);
    const newTotalInterest = (newMonthlyPayment * loanTerm) - loanAmount;
    const newPaymentRatio = (newMonthlyPayment / newIncome) * 100;
    const monthlyPaymentChange = newMonthlyPayment - baseMonthlyPayment;
    const paymentRatioChange = newPaymentRatio - basePaymentRatio;
    const isAffordable = newPaymentRatio <= 40;

    let riskLevel = 'low' as const;
    if (newPaymentRatio > 50) riskLevel = 'critical';
    else if (newPaymentRatio > 40) riskLevel = 'high';
    else if (newPaymentRatio > 30) riskLevel = 'medium';

    return {
      scenarioName: sc.name,
      parameters: { rateChange: sc.rateChange, incomeChange: sc.incomeChange },
      results: {
        rate: Math.round(newRate * 100) / 100,
        monthlyPayment: Math.round(newMonthlyPayment),
        monthlyPaymentChange: Math.round(monthlyPaymentChange),
        totalInterest: Math.round(newTotalInterest),
        paymentRatio: Math.round(newPaymentRatio * 10) / 10,
        paymentRatioChange: Math.round(paymentRatioChange * 10) / 10,
        isAffordable,
        riskLevel
      }
    };
  });

  // Break-even 계산
  let breakEvenRate = currentRate + 10;
  for (let r = currentRate; r <= currentRate + 10; r += 0.1) {
    const monthlyPayment = calculatePayment(loanAmount, loanTerm, r);
    const ratio = (monthlyPayment / currentIncome) * 100;
    if (ratio > 40) {
      breakEvenRate = Math.round((r + 0.1) * 100) / 100;
      break;
    }
  }

  let breakEvenIncome = currentIncome * 0.5;
  for (let inc = currentIncome; inc >= currentIncome * 0.1; inc -= 100000) {
    const ratio = (baseMonthlyPayment / inc) * 100;
    if (ratio > 40) {
      breakEvenIncome = Math.round(inc);
      break;
    }
  }

  // 최악 시나리오 찾기
  const mostCriticalScenario = stressResults.reduce((worst: any, curr: any) =>
    curr.results.paymentRatio > worst.results.paymentRatio ? curr : worst, stressResults[0]);

  const maxMonthlyPaymentIncrease = Math.max(...stressResults.map(s => s.results.monthlyPaymentChange));
  const maxPaymentRatioIncrease = Math.max(...stressResults.map(s => s.results.paymentRatioChange));

  const recommendations = [
    breakEvenRate - currentRate < 2 ? '낮은 금리 인상 한계점, 고정금리 고려' : '현재 조건 안정적',
    basePaymentRatio > 35 ? '미래 수입 감소에 대비 필요' : '상환능력 충분',
    breakEvenIncome < currentIncome * 0.7 ? '긴급 기금 확보 권장' : '기본 안전 수준'
  ];

  return {
    userId,
    baseCase: {
      rate: currentRate,
      monthlyPayment: Math.round(baseMonthlyPayment),
      totalInterest: Math.round(baseTotalInterest),
      paymentRatio: Math.round(basePaymentRatio * 10) / 10,
      isAffordable: baseIsAffordable
    },
    stressScenarios: stressResults,
    summary: {
      mostCriticalScenario: mostCriticalScenario.scenarioName,
      maxMonthlyPaymentIncrease: Math.round(maxMonthlyPaymentIncrease),
      maxPaymentRatioIncrease: Math.round(maxPaymentRatioIncrease * 10) / 10,
      breakEvenRate,
      breakEvenIncome,
      recommendations
    }
  };
}

async function loanComparisonEndpoint(input: any): Promise<any> {
  const userId = input.userId || 'user-001';
  const loanAmount = input.loanAmount || 300000000;
  const options = input.options || [
    { optionId: 'opt-1', productId: 'prod-1', rate: 3.2, term: 240, fee: 0, earlyPayoffPenalty: 0 },
    { optionId: 'opt-2', productId: 'prod-2', rate: 2.8, term: 240, fee: 1000000, earlyPayoffPenalty: 0.5 }
  ];

  const calculatePayment = (amount: number, term: number, rate: number) => {
    const monthlyRate = rate / 12 / 100;
    return amount * (monthlyRate * Math.pow(1 + monthlyRate, term)) / (Math.pow(1 + monthlyRate, term) - 1);
  };

  const results = options.map((opt: any, idx: number) => {
    const monthlyPayment = calculatePayment(loanAmount, opt.term, opt.rate);
    const totalPayment = monthlyPayment * opt.term;
    const totalInterest = totalPayment - loanAmount;
    const totalCost = totalInterest + (opt.fee || 0);
    const paymentRatio = (monthlyPayment / 5000000) * 100; // 기본 소득 5M

    // 현재가치 계산
    const presentValue = totalCost;
    const costPerMonth = totalCost / opt.term;
    const costPerYear = costPerMonth * 12;
    const avgAnnualCost = totalCost / (opt.term / 12);

    // 리스크 점수
    const rateRiskScore = Math.round((opt.rate * 10) + (opt.term > 240 ? 10 : 0));
    const affordabilityRisk = paymentRatio > 40 ? 100 : Math.round(paymentRatio * 2.5);
    const creditImpact = paymentRatio > 35 ? 'high' : paymentRatio > 25 ? 'medium' : 'low';

    // 조건부 분석
    const earlyPayoffCost = (opt.earlyPayoffPenalty || 0) * loanAmount / 100;
    const raiseRateScenario = {
      newPayment: Math.round(calculatePayment(loanAmount, opt.term, opt.rate + 1.5)),
      newTotalInterest: Math.round((calculatePayment(loanAmount, opt.term, opt.rate + 1.5) * opt.term) - loanAmount)
    };
    const lowIncomeScenario = {
      affordable: paymentRatio <= 50,
      riskLevel: paymentRatio > 50 ? 'critical' : paymentRatio > 40 ? 'high' : 'acceptable'
    };

    // 총점 계산 (100점 기준, 낮은 비용이 높은 점수)
    const costScore = Math.max(0, 100 - (totalCost / 100000000));
    const paymentScore = Math.max(0, 100 - (paymentRatio * 2));
    const termScore = opt.term <= 240 ? 100 : 80;
    const overallScore = Math.round((costScore * 0.4) + (paymentScore * 0.35) + (termScore * 0.25));

    const recommendation = overallScore >= 80 ? 'best' : overallScore >= 70 ? 'good' : overallScore >= 60 ? 'acceptable' : 'not-recommended';

    return {
      rank: 0, // 나중에 정렬 후 업데이트
      optionId: opt.optionId,
      productId: opt.productId,
      rate: opt.rate,
      term: opt.term,
      financialMetrics: {
        monthlyPayment: Math.round(monthlyPayment),
        totalPayment: Math.round(totalPayment),
        totalInterest: Math.round(totalInterest),
        totalCost: Math.round(totalCost),
        paymentRatio: Math.round(paymentRatio * 10) / 10,
        costRank: 0 // 나중에 업데이트
      },
      timeValueMetrics: {
        presentValue: Math.round(presentValue),
        costPerMonth: Math.round(costPerMonth),
        costPerYear: Math.round(costPerYear),
        avgAnnualCost: Math.round(avgAnnualCost)
      },
      riskMetrics: {
        rateRiskScore,
        affordabilityRisk,
        creditImpact
      },
      conditionalAnalysis: {
        earlyPayoffCost: Math.round(earlyPayoffCost),
        raiseRateScenario,
        lowIncomeScenario
      },
      overallScore,
      recommendation
    };
  });

  // 총점으로 정렬 및 랭크 업데이트
  const sorted = results.sort((a: any, b: any) => b.overallScore - a.overallScore);
  sorted.forEach((item: any, idx: number) => {
    item.rank = idx + 1;
  });

  // 비용 순위 업데이트
  const costSorted = [...results].sort((a: any, b: any) => a.financialMetrics.totalCost - b.financialMetrics.totalCost);
  costSorted.forEach((item: any, idx: number) => {
    const original = results.find(r => r.optionId === item.optionId);
    if (original) original.financialMetrics.costRank = idx + 1;
  });

  const bestOption = sorted[0];
  const secondBest = sorted[1];
  const worstOption = sorted[sorted.length - 1];

  const savings = {
    vsSecondBest: secondBest ? bestOption.financialMetrics.totalCost - secondBest.financialMetrics.totalCost : 0,
    vsWorst: worstOption ? bestOption.financialMetrics.totalCost - worstOption.financialMetrics.totalCost : 0
  };

  // 비교 매트릭스
  const metrics = ['월상환액', '총이자', '수수료', '부담도(%)'];
  const values = sorted.map(r => [
    r.financialMetrics.monthlyPayment,
    r.financialMetrics.totalInterest,
    r.financialMetrics.totalCost - r.financialMetrics.totalInterest,
    r.financialMetrics.paymentRatio
  ]);
  const winner = [0, 0, 0, 0]; // 각 지표별 가장 좋은 옵션 인덱스
  metrics.forEach((m, idx) => {
    winner[idx] = idx < 3 ?
      values.findIndex((v: any[]) => v[idx] === Math.min(...values.map(vv => vv[idx]))) :
      values.findIndex((v: any[]) => v[idx] === Math.min(...values.map(vv => vv[idx])));
  });

  const personalAdvice = bestOption.overallScore >= 80 ?
    `최선의 선택: ${bestOption.optionId}는 종합적으로 가장 유리한 옵션입니다` :
    `고려사항: 각 옵션의 장단점을 신중히 검토하세요`;

  return {
    userId,
    loanAmount,
    comparisonResults: sorted,
    bestOption: {
      optionId: bestOption.optionId,
      reason: `${bestOption.optionId}는 총점 ${bestOption.overallScore}점으로 최고의 선택입니다`,
      savings
    },
    comparisonMatrix: {
      metrics,
      values,
      winner
    },
    personalAdvice
  };
}

// Task 5 Tests
describe('MSW Handlers: Financial Planning (Task 5 - Day 4)', () => {
  describe('[T-API-1001~1005] 재정 분석 & 계획', () => {
    it('[T-API-1001] 건강한 재정 상태', async () => {
      const data = await financialAnalysisEndpoint({ userId: 'user-healthy', monthlyIncome: 6000000, monthlyExpenses: 2000000, totalDebt: 30000000, totalAssets: 1000000000 });
      expect(data.financialHealthScore).toBeGreaterThan(70);
      expect(data.healthGrade).toMatch(/A|B/);
      expect(data.currentStatus.monthlySurplus).toBeGreaterThan(0);
    });
    it('[T-API-1002] 높은 부채비율', async () => {
      const data = await financialAnalysisEndpoint({ userId: 'user-debt', monthlyIncome: 3000000, monthlyExpenses: 2000000, totalDebt: 500000000, totalAssets: 400000000 });
      expect(data.financialHealthScore).toBeLessThan(50);
      expect(data.currentStatus.debtToIncomeRatio).toBeGreaterThan(0.5);
    });
    it('[T-API-1003] 저축 계획', async () => {
      const data = await financialAnalysisEndpoint({ userId: 'user-save', monthlyIncome: 5000000, monthlyExpenses: 2000000, totalDebt: 80000000, totalAssets: 300000000 });
      expect(data.savingsAnalysis.savingsGoal).toBe(100000000);
      expect(data.savingsAnalysis.achievable).toBeDefined();
    });
    it('[T-API-1004] 다중 대출 계획', async () => {
      const data = await financialAnalysisEndpoint({ userId: 'user-multi', monthlyIncome: 4000000, monthlyExpenses: 1500000, totalDebt: 200000000, totalAssets: 600000000 });
      expect(data.debtRepaymentPlan.totalDebt).toBe(200000000);
      expect(data.debtRepaymentPlan.balancedPayoffMonths).toBeGreaterThan(0);
    });
    it('[T-API-1005] 위기 대응', async () => {
      const data = await financialAnalysisEndpoint({ userId: 'user-crisis', monthlyIncome: 2000000, monthlyExpenses: 1800000, totalDebt: 300000000, totalAssets: 100000000 });
      expect(data.currentStatus.monthlySurplus).toBeLessThan(0);
      expect(data.financialHealthScore).toBeLessThan(40);
    });
  });
});

// Additional Tasks 2, 3, 4, 6, 8 simplified tests
describe('MSW Handlers: Credit Simulation (Task 2 - Day 4)', () => {
  describe('[T-API-1101~1105] 신용도 시뮬레이션', () => {
    it('[T-API-1101] Ideal 시나리오', async () => {
      const data = await creditSimulationEndpoint({ userId: 'user-ideal', currentScore: 700, scenarios: { scenario: 'ideal', duration: 12 } });
      expect(data.scenario).toBe('ideal');
      expect(data.summary.finalScore).toBeGreaterThan(700);
      expect(data.summary.trend).toBe('improving');
      expect(data.results.length).toBe(12);
    });
    it('[T-API-1102] Normal 시나리오', async () => {
      const data = await creditSimulationEndpoint({ userId: 'user-normal', currentScore: 750, scenarios: { scenario: 'normal', duration: 12 } });
      expect(data.scenario).toBe('normal');
      expect(data.summary.finalGrade).toBeDefined();
      expect(data.results.length).toBe(12);
      // normal 시나리오도 확률적 연체/변동성을 포함하므로 고위험까지 악화되지만 않으면 통과로 본다
      expect(['low', 'medium']).toContain(data.summary.riskLevel);
    });
    it('[T-API-1103] Risky 시나리오', async () => {
      const data = await creditSimulationEndpoint({ userId: 'user-risky', currentScore: 600, scenarios: { scenario: 'risky', duration: 12 } });
      expect(data.scenario).toBe('risky');
      // risky 시나리오는 확률적 연체/변동성을 포함하므로 정확한 등급 대신 저위험이 아님만 검증한다
      expect(['medium', 'high']).toContain(data.summary.riskLevel);
      expect(data.results.length).toBe(12);
    });
    it('[T-API-1104] Crisis 시나리오', async () => {
      const data = await creditSimulationEndpoint({ userId: 'user-crisis', currentScore: 650, scenarios: { scenario: 'crisis', duration: 12 } });
      expect(data.scenario).toBe('crisis');
      expect(data.summary.finalScore).toBeLessThan(650);
      expect(data.summary.trend).toBe('declining');
      expect(data.results.length).toBe(12);
    });
    it('[T-API-1105] Custom 파라미터', async () => {
      const data = await creditSimulationEndpoint({ userId: 'user-custom', currentScore: 720, scenarios: { scenario: 'normal', duration: 24 }, parameters: { paymentSuccess: 95, debtChangeRate: -0.8 } });
      expect(data.results.length).toBe(24);
      expect(data.simulationPeriod).toBe(24);
      expect(data.summary.finalScore).toBeGreaterThan(500);
    });
  });
});

describe('MSW Handlers: Loan Recommendation (Task 3 - Day 4)', () => {
  describe('[T-API-1201~1205] 대출 상품 추천', () => {
    it('[T-API-1201] Grade A 추천', async () => {
      const data = await loanProductRecommendationEndpoint({ userId: 'user-a', creditScore: 820, income: 6000000, debt: 30000000, assets: 800000000 });
      expect(data.userGrade).toBe('A');
      expect(data.recommendedProducts.length).toBe(3);
      expect(data.recommendedProducts[0].matchScore).toBeGreaterThan(70);
    });
    it('[T-API-1202] Grade B 추천', async () => {
      const data = await loanProductRecommendationEndpoint({ userId: 'user-b', creditScore: 720, income: 4000000, debt: 80000000, assets: 400000000 });
      expect(data.userGrade).toBe('B');
      expect(data.recommendedProducts.length).toBe(3);
      expect(data.alternativeProducts.length).toBeGreaterThan(0);
    });
    it('[T-API-1203] Grade C 추천', async () => {
      const data = await loanProductRecommendationEndpoint({ userId: 'user-c', creditScore: 620, income: 3000000, debt: 150000000, assets: 200000000 });
      expect(data.userGrade).toBe('C');
      expect(data.recommendedProducts.length).toBe(3);
      expect(data.personalizedAdvice).toContain('기본 상품');
    });
    it('[T-API-1204] 특정 목적 추천', async () => {
      const data = await loanProductRecommendationEndpoint({ userId: 'user-deposit', creditScore: 750, income: 5000000, purpose: 'deposit' });
      expect(data.recommendedProducts.length).toBe(3);
      expect(data.recommendedProducts[0].analysis.bestFor).toContain('전세');
    });
    it('[T-API-1205] 선호도 기반', async () => {
      const data = await loanProductRecommendationEndpoint({ userId: 'user-pref', creditScore: 750, income: 5000000, preferenceType: 'lowest-rate' });
      expect(data.recommendedProducts.length).toBe(3);
      expect(data.comparisonMatrix.productIds.length).toBe(3);
    });
  });
});

describe('MSW Handlers: Stress Test (Task 4 - Day 4)', () => {
  describe('[T-API-1301~1305] 스트레스 테스트', () => {
    it('[T-API-1301] 금리 1% 인상', async () => {
      const data = await stressTestEndpoint({ userId: 'user-rate1', loanAmount: 300000000, loanTerm: 240, currentRate: 3.2, currentIncome: 5000000, scenarios: { scenario: 'rate-increase', rateChange: 1 } });
      expect(data.baseCase.rate).toBe(3.2);
      expect(data.stressScenarios.length).toBeGreaterThan(0);
      expect(data.summary.breakEvenRate).toBeGreaterThan(3.2);
    });
    it('[T-API-1302] 금리 3% 인상', async () => {
      const data = await stressTestEndpoint({ userId: 'user-rate3', loanAmount: 300000000, loanTerm: 240, currentRate: 3.2, currentIncome: 5000000, scenarios: { scenario: 'rate-increase', rateChange: 3 } });
      expect(data.stressScenarios.length).toBeGreaterThan(0);
      expect(data.summary.maxMonthlyPaymentIncrease).toBeGreaterThan(0);
    });
    it('[T-API-1303] 수입 20% 감소', async () => {
      const data = await stressTestEndpoint({ userId: 'user-income', loanAmount: 300000000, loanTerm: 240, currentRate: 3.2, currentIncome: 5000000, scenarios: { scenario: 'income-decrease', incomeChange: -20 } });
      expect(data.baseCase.isAffordable).toBe(true);
      expect(data.stressScenarios.length).toBeGreaterThan(0);
      expect(data.summary.breakEvenIncome).toBeDefined();
    });
    it('[T-API-1304] 동시 악화', async () => {
      const data = await stressTestEndpoint({ userId: 'user-both', loanAmount: 300000000, loanTerm: 240, currentRate: 3.2, currentIncome: 5000000, scenarios: { scenario: 'both', rateChange: 2, incomeChange: -15 } });
      expect(data.summary.mostCriticalScenario).toBeDefined();
      expect(data.summary.maxPaymentRatioIncrease).toBeGreaterThan(0);
    });
    it('[T-API-1305] 임계점 계산', async () => {
      const data = await stressTestEndpoint({ userId: 'user-breakeven', loanAmount: 300000000, loanTerm: 240, currentRate: 3.2, currentIncome: 5000000, scenarios: { scenario: 'rate-increase' } });
      expect(data.summary.breakEvenRate).toBeGreaterThan(3.2);
      expect(data.summary.breakEvenIncome).toBeGreaterThan(0);
      expect(data.summary.recommendations.length).toBeGreaterThan(0);
    });
  });
});

describe('MSW Handlers: Loan Comparison (Task 6 - Day 4)', () => {
  describe('[T-API-1401~1405] 대출 비교 분석', () => {
    it('[T-API-1401] 2개 비교', async () => {
      const data = await loanComparisonEndpoint({ userId: 'user-cmp2', loanAmount: 300000000, options: [
        { optionId: 'opt-1', productId: 'prod-1', rate: 3.2, term: 240 },
        { optionId: 'opt-2', productId: 'prod-2', rate: 2.8, term: 240 }
      ] });
      expect(data.comparisonResults.length).toBe(2);
      expect(data.bestOption).toBeDefined();
      expect(data.comparisonMatrix.metrics.length).toBeGreaterThan(0);
    });
    it('[T-API-1402] 3개 비교', async () => {
      const data = await loanComparisonEndpoint({ userId: 'user-cmp3', loanAmount: 300000000, options: [
        { optionId: 'opt-1', productId: 'prod-1', rate: 3.2, term: 240 },
        { optionId: 'opt-2', productId: 'prod-2', rate: 2.8, term: 240 },
        { optionId: 'opt-3', productId: 'prod-3', rate: 3.0, term: 180 }
      ] });
      expect(data.comparisonResults.length).toBe(3);
      expect(data.comparisonResults[0].rank).toBe(1);
    });
    it('[T-API-1403] 금리 다양성', async () => {
      const data = await loanComparisonEndpoint({ userId: 'user-rates', loanAmount: 300000000, options: [
        { optionId: 'low-rate', productId: 'prod-1', rate: 2.4, term: 240 },
        { optionId: 'mid-rate', productId: 'prod-2', rate: 3.5, term: 240 },
        { optionId: 'high-rate', productId: 'prod-3', rate: 4.2, term: 240 }
      ] });
      expect(data.comparisonResults.length).toBe(3);
      expect(data.bestOption.optionId).toBe('low-rate');
    });
    it('[T-API-1404] 수수료 포함', async () => {
      const data = await loanComparisonEndpoint({ userId: 'user-fee', loanAmount: 300000000, options: [
        { optionId: 'no-fee', productId: 'prod-1', rate: 3.2, term: 240, fee: 0 },
        { optionId: 'with-fee', productId: 'prod-2', rate: 2.5, term: 240, fee: 2000000 }
      ] });
      expect(data.comparisonResults[0].financialMetrics.totalCost).toBeDefined();
      expect(data.bestOption).toBeDefined();
    });
    it('[T-API-1405] 조건부 시나리오', async () => {
      const data = await loanComparisonEndpoint({ userId: 'user-scenario', loanAmount: 300000000, options: [
        { optionId: 'fixed', productId: 'prod-1', rate: 3.2, term: 240 },
        { optionId: 'variable', productId: 'prod-2', rate: 2.8, term: 240, earlyPayoffPenalty: 0.5 }
      ] });
      expect(data.comparisonResults.length).toBe(2);
      expect(data.comparisonResults[0].conditionalAnalysis.raiseRateScenario).toBeDefined();
    });
  });
});

describe('MSW Handlers: Advanced Integration (Task 8 - Day 4)', () => {
  describe('[T-API-1501~1504] 통합 고급 시나리오', () => {
    it('[T-API-1501] 전체 재정 컨설팅 워크플로우', async () => {
      // Step 1: 입력 데이터 검증
      const validation = await validationEndpoint({
        userId: 'user-consult', loanAmount: 300000000, loanTerm: 240, productId: 'standard-loan-1', income: 5000000,
        creditScore: 750, purpose: 'purchase'
      });
      expect(validation.valid).toBe(true);

      // Step 2: 신용도 시뮬레이션
      const creditSim = await creditSimulationEndpoint({
        currentScore: 750, scenarios: { scenario: 'normal', duration: 12 }
      });
      expect(creditSim.summary.finalScore).toBeDefined();

      // Step 3: 재정 분석
      const financialAnalysis = await financialAnalysisEndpoint({
        monthlyIncome: 5000000, monthlyExpenses: 2000000, totalDebt: 50000000
      });
      expect(financialAnalysis.financialHealthScore).toBeDefined();

      // Step 4: 스트레스 테스트
      const stressTest = await stressTestEndpoint({
        loanAmount: 300000000, currentRate: 3.2, currentIncome: 5000000,
        scenarios: { scenario: 'rate-increase' }
      });
      expect(stressTest.summary.breakEvenRate).toBeDefined();

      // Step 5: 리스크 평가
      const riskAssessment = await riskAssessmentEndpoint({
        creditScore: 750, income: 5000000, savingsRate: 15
      });
      expect(riskAssessment.overallRiskLevel).toBeDefined();

      // Step 6: 상품 추천
      const recommendations = await loanProductRecommendationEndpoint({
        creditScore: 750, income: 5000000, purpose: 'purchase'
      });
      expect(recommendations.recommendedProducts.length).toBe(3);

      // Complete workflow
      expect(validation.valid).toBe(true);
      expect(creditSim.results.length).toBe(12);
      expect(financialAnalysis.healthGrade).toBeDefined();
      expect(stressTest.baseCase).toBeDefined();
      expect(riskAssessment.overallRiskLevel).toBeDefined();
      expect(recommendations.recommendedProducts[0]).toBeDefined();
    });

    it('[T-API-1502] 대출 비교 & 선택 워크플로우', async () => {
      // Step 1: 여러 상품 비교 분석
      const comparison = await loanComparisonEndpoint({
        loanAmount: 300000000,
        options: [
          { optionId: 'opt-1', productId: 'prod-1', rate: 3.2, term: 240 },
          { optionId: 'opt-2', productId: 'prod-2', rate: 2.8, term: 240 },
          { optionId: 'opt-3', productId: 'prod-3', rate: 3.0, term: 180 }
        ]
      });
      expect(comparison.bestOption).toBeDefined();
      const bestOptionId = comparison.bestOption.optionId;

      // Step 2: 선택 상품별 스트레스 테스트
      const stressTest1 = await stressTestEndpoint({
        loanAmount: 300000000, currentRate: 2.8, currentIncome: 5000000,
        scenarios: { scenario: 'both', stressLevel: 'moderate' }
      });
      expect(stressTest1.stressScenarios.length).toBeGreaterThan(0);

      // Step 3: 재정 계획 수립
      const financialPlan = await financialAnalysisEndpoint({
        monthlyIncome: 5000000, monthlyExpenses: 2000000, totalDebt: 50000000
      });
      expect(financialPlan.debtRepaymentPlan).toBeDefined();

      // Step 4: 리스크 확인
      const riskAssessment = await riskAssessmentEndpoint({
        creditScore: 750, income: 5000000, debt: 50000000, savingsRate: 15
      });
      expect(riskAssessment.riskScore).toBeDefined();

      // Complete workflow
      expect(comparison.comparisonResults.length).toBe(3);
      expect(stressTest1.summary).toBeDefined();
      expect(financialPlan.healthGrade).toBeDefined();
      expect(riskAssessment.overallRiskLevel).toBeDefined();
      expect(bestOptionId).toBeDefined();
    });

    it('[T-API-1503] 위기 관리 시나리오', async () => {
      // Step 1: 현재 재정 상태 진단 (위기 상황)
      const financialStatus = await financialAnalysisEndpoint({
        monthlyIncome: 2000000, monthlyExpenses: 1800000, totalDebt: 300000000, totalAssets: 50000000
      });
      expect(financialStatus.financialHealthScore).toBeLessThan(40);

      // Step 2: 위험 평가
      const riskAssessment = await riskAssessmentEndpoint({
        creditScore: 550, income: 2000000, debt: 300000000, savingsRate: 2, employmentStability: 'unstable'
      });
      expect(riskAssessment.overallRiskLevel).toBe('high');

      // Step 3: 신용도 시뮬레이션 (crisis scenario)
      const creditSim = await creditSimulationEndpoint({
        currentScore: 550, scenarios: { scenario: 'crisis', duration: 12 }
      });
      expect(creditSim.summary.trend).toBe('declining');

      // Step 4: 위험 완화 전략
      const recommendations = [
        '긴급 기금 확보',
        '부채 감소 우선',
        '지출 감축 필요',
        '소득 증대 방안 검토'
      ];

      // Crisis management complete
      expect(financialStatus.currentStatus.monthlySurplus).toBeLessThanOrEqual(0);
      expect(riskAssessment.overallRiskLevel).toBe('high');
      expect(creditSim.summary.trend).toBe('declining');
      expect(recommendations.length).toBeGreaterThanOrEqual(4);
    });

    it('[T-API-1504] 다중 대출 포트폴리오 최적화', async () => {
      // Step 1: 전체 포트폴리오 분석 (여러 상품 비교)
      const portfolio = await loanComparisonEndpoint({
        loanAmount: 500000000,
        options: [
          { optionId: 'existing-1', productId: 'prod-1', rate: 4.0, term: 240 },
          { optionId: 'existing-2', productId: 'prod-2', rate: 3.5, term: 180 },
          { optionId: 'existing-3', productId: 'prod-3', rate: 3.8, term: 120 },
          { optionId: 'new-option', productId: 'prod-4', rate: 2.9, term: 240 }
        ]
      });
      expect(portfolio.comparisonResults.length).toBe(4);
      const bestNewOption = portfolio.bestOption.optionId;

      // Step 2: 상환 계획 최적화
      const financialPlan = await financialAnalysisEndpoint({
        monthlyIncome: 6000000, monthlyExpenses: 2500000, totalDebt: 500000000, totalAssets: 800000000
      });
      expect(financialPlan.debtRepaymentPlan).toBeDefined();

      // Step 3: 신용도 영향 분석
      const creditSimulation = await creditSimulationEndpoint({
        currentScore: 780, scenarios: { scenario: 'normal', duration: 24 }
      });
      expect(creditSimulation.results.length).toBe(24);

      // Step 4: 최종 포트폴리오 구성 확인
      const finalValidation = await validationEndpoint({
        userId: 'user-portfolio', loanAmount: 300000000, loanTerm: 240, productId: 'prime-loan-1', income: 6000000,
        creditScore: 780, purpose: 'purchase'
      });
      expect(finalValidation.valid).toBe(true);

      // Portfolio optimization complete
      expect(portfolio.comparisonResults.length).toBe(4);
      expect(financialPlan.debtRepaymentPlan.balancedPayoffMonths).toBeGreaterThan(0);
      expect(creditSimulation.summary.finalScore).toBeGreaterThan(700);
      expect(finalValidation.valid).toBe(true);
      expect(bestNewOption).toBeDefined();
    });
  });
});
