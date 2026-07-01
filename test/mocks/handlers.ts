import { rest } from 'msw';

export const loanHandlers = [
  // 대출 신청
  rest.post('/api/v1/loans/apply', async (req, res, ctx) => {
    const body = await req.json() as {
      userId: string;
      loanAmount: number;
      loanTerm: number;
      productId: string;
      purpose: string;
      collateral?: { type: string; value: number };
      coApplicant?: { name: string; creditScore: number };
    };

    // 입력 검증
    if (!body.userId) {
      return res(ctx.status(400), ctx.json({
        error: 'userId is required'
      }));
    }
    if (body.loanAmount <= 0) {
      return res(ctx.status(400), ctx.json({
        error: 'loanAmount must be greater than 0'
      }));
    }
    if (body.loanTerm <= 0) {
      return res(ctx.status(400), ctx.json({
        error: 'loanTerm must be greater than 0'
      }));
    }

    // 제품별 한도 설정
    const products: { [key: string]: { maxAmount: number; maxTerm: number } } = {
      'prime-loan-1': { maxAmount: 500000000, maxTerm: 360 },
      'standard-loan-1': { maxAmount: 300000000, maxTerm: 240 },
      'conditional-loan-1': { maxAmount: 150000000, maxTerm: 180 }
    };

    const product = products[body.productId];
    if (!product) {
      return res(ctx.status(400), ctx.json({
        error: 'Invalid productId'
      }));
    }

    // 신용도 기반 승인 한도 결정
    const creditScore = body.coApplicant?.creditScore || 750;
    let maxLoanAmount = 0;
    let grade = 'D';

    if (creditScore >= 800) {
      grade = 'A';
      maxLoanAmount = 470000000;
    } else if (creditScore >= 700) {
      grade = 'B';
      maxLoanAmount = 280000000;
    } else if (creditScore >= 650) {
      grade = 'C';
      maxLoanAmount = 130000000;
    } else {
      return res(ctx.json({
        applicationId: `APP-${Date.now()}`,
        status: 'rejected',
        approvedAmount: 0,
        approvedTerm: 0,
        monthlyPayment: 0,
        totalInterest: 0,
        message: 'Credit score too low for loan approval',
        expirationDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        nextSteps: ['Improve your credit score', 'Try again in 3 months']
      }));
    }

    // 신청액이 한도를 초과하는 경우
    if (body.loanAmount > maxLoanAmount) {
      return res(ctx.json({
        applicationId: `APP-${Date.now()}`,
        status: 'rejected',
        approvedAmount: maxLoanAmount,
        approvedTerm: Math.min(body.loanTerm, product.maxTerm),
        monthlyPayment: 0,
        totalInterest: 0,
        message: `Requested amount ${body.loanAmount} exceeds maximum ${maxLoanAmount}`,
        expirationDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        nextSteps: ['Reduce loan amount', 'Apply with lower amount']
      }));
    }

    // 신청 기간이 상품 최대 기간을 초과하는 경우
    if (body.loanTerm > product.maxTerm) {
      return res(ctx.json({
        applicationId: `APP-${Date.now()}`,
        status: 'rejected',
        approvedAmount: body.loanAmount,
        approvedTerm: product.maxTerm,
        monthlyPayment: 0,
        totalInterest: 0,
        message: `Requested term ${body.loanTerm} exceeds maximum ${product.maxTerm}`,
        expirationDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        nextSteps: ['Reduce loan term', 'Apply with shorter term']
      }));
    }

    // 월상환액 계산
    const monthlyRate = 3.2 / 12 / 100; // 기본 3.2% 이자율
    const monthlyPayment = body.loanAmount *
      (monthlyRate * Math.pow(1 + monthlyRate, body.loanTerm)) /
      (Math.pow(1 + monthlyRate, body.loanTerm) - 1);

    // 월상환액 가능성 검증 (월상환 < 월소득의 40%)
    const estimatedMonthlyIncome = 4000000; // 예상 월소득 기본값
    const paymentRatio = (monthlyPayment / estimatedMonthlyIncome) * 100;

    if (paymentRatio > 40) {
      // 조건부 승인
      return res(ctx.json({
        applicationId: `APP-${Date.now()}`,
        status: 'conditional',
        approvedAmount: body.loanAmount,
        approvedTerm: body.loanTerm,
        monthlyPayment: Math.round(monthlyPayment),
        totalInterest: Math.round(monthlyPayment * body.loanTerm - body.loanAmount),
        conditions: ['Provide collateral worth 30% of loan amount', 'Co-applicant approval required'],
        message: 'Conditional approval: requires collateral or co-applicant',
        expirationDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        nextSteps: ['Provide collateral', 'Add co-applicant', 'Verify income documents']
      }));
    }

    // 완전 승인
    return res(ctx.json({
      applicationId: `APP-${Date.now()}`,
      status: 'approved',
      approvedAmount: body.loanAmount,
      approvedTerm: body.loanTerm,
      monthlyPayment: Math.round(monthlyPayment),
      totalInterest: Math.round(monthlyPayment * body.loanTerm - body.loanAmount),
      message: `Loan approved for ${body.loanAmount.toLocaleString()}원 at Grade ${grade}`,
      expirationDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      nextSteps: ['Review loan terms', 'Sign documents', 'Complete verification']
    }));
  }),

  // 신용도 평가
  rest.post('/api/v1/credit/assess', async (req, res, ctx) => {
    const body = await req.json() as {
      income: number;
      debt: number;
      creditScore: number;
      assets: number;
    };

    // 입력 검증
    if (body.income <= 0) {
      return res(ctx.status(400), ctx.json({
        error: 'Income must be greater than 0'
      }));
    }
    if (body.debt < 0) {
      return res(ctx.status(400), ctx.json({
        error: 'Debt cannot be negative'
      }));
    }
    if (body.creditScore < 0 || body.creditScore > 999) {
      return res(ctx.status(400), ctx.json({
        error: 'Credit score must be between 0 and 999'
      }));
    }
    if (body.assets < 0) {
      return res(ctx.status(400), ctx.json({
        error: 'Assets cannot be negative'
      }));
    }

    // 월간 부채 비율 계산
    const monthlyIncome = body.income;
    const monthlyDebtPayment = body.debt / 12;
    const debtRatio = (monthlyDebtPayment / monthlyIncome) * 100;

    // 신용 등급 결정 및 최대 대출액 계산
    let maxLoanAmount = 0;
    let approved = false;
    let recommendation: 'APPROVED' | 'CONDITIONAL' | 'REJECTED' = 'REJECTED';
    let grade = 'D';

    if (body.creditScore >= 800) {
      // Grade A: 신용점수 우수
      grade = 'A';
      maxLoanAmount = Math.min(
        monthlyIncome * 12 * 5,
        500000000
      );
      approved = debtRatio <= 40;
      recommendation = approved ? 'APPROVED' : 'CONDITIONAL';
    } else if (body.creditScore >= 700) {
      // Grade B: 신용점수 양호
      grade = 'B';
      maxLoanAmount = Math.min(
        monthlyIncome * 12 * 3,
        300000000
      );
      approved = debtRatio <= 50;
      recommendation = approved ? 'APPROVED' : 'CONDITIONAL';
    } else if (body.creditScore >= 650) {
      // Grade C: 신용점수 보통
      grade = 'C';
      maxLoanAmount = Math.min(
        monthlyIncome * 12 * 1.5,
        150000000
      );
      approved = debtRatio <= 60;
      recommendation = 'CONDITIONAL';
    } else {
      // Grade D: 신용점수 불량
      grade = 'D';
      maxLoanAmount = 0;
      approved = false;
      recommendation = 'REJECTED';
    }

    // 자산 기반 추가 대출액 계산
    if (body.assets > 0) {
      const assetBasedLoan = body.assets * 0.7;
      maxLoanAmount = Math.max(maxLoanAmount, Math.min(assetBasedLoan, maxLoanAmount * 1.2));
    }

    // 현재 부채를 고려한 최종 대출액 조정
    const adjustedMaxLoan = Math.max(0, maxLoanAmount - body.debt);

    return res(ctx.json({
      approved,
      score: body.creditScore,
      maxLoanAmount: Math.round(adjustedMaxLoan),
      debtRatioPercent: Math.round(debtRatio * 100) / 100,
      recommendation,
      grade,
      message: approved
        ? `Credit assessment approved. Grade ${grade}. Max loan: ${Math.round(adjustedMaxLoan).toLocaleString()}원`
        : `Credit assessment ${recommendation.toLowerCase()}. Grade ${grade}.`
    }));
  }),

  // 대출상품 조회 (고급 기능 포함: 정렬, 페이징, 적합도 점수)
  rest.get('/api/v1/loans/products', (req, res, ctx) => {
    const creditScore = parseInt(req.url.searchParams.get('creditScore') || '700');
    const sortBy = req.url.searchParams.get('sortBy') || 'rate';
    const limit = parseInt(req.url.searchParams.get('limit') || '10');
    const offset = parseInt(req.url.searchParams.get('offset') || '0');

    // 신용점수에 따라 상품 범위 결정
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
      return res(ctx.status(400), ctx.json({
        error: '조건에 맞는 상품이 없습니다.'
      }));
    }

    // 정렬 적용
    let sortedProducts = [...allProducts];
    if (sortBy === 'rate') {
      sortedProducts.sort((a, b) => a.rate - b.rate);
    } else if (sortBy === 'amount') {
      sortedProducts.sort((a, b) => b.maxAmount - a.maxAmount);
    } else if (sortBy === 'term') {
      sortedProducts.sort((a, b) => b.maxTerm - a.maxTerm);
    }

    // 적합도 점수 계산
    const productsWithScore = sortedProducts.map((product, index) => ({
      ...product,
      eligibilityScore: Math.round((creditScore / 10 + (5 - index)) * 10) / 10,
      monthlyPaymentEstimate: Math.round((product.maxAmount * 0.01) / 12),
      competitorCount: Math.max(1, 5 - sortedProducts.length)
    }));

    // 페이징 적용
    const total = productsWithScore.length;
    const paginatedProducts = productsWithScore.slice(offset, offset + limit);
    const hasMore = offset + limit < total;

    return res(ctx.json({
      products: paginatedProducts,
      pagination: {
        total,
        limit,
        offset,
        hasMore
      },
      timestamp: new Date().toISOString()
    }));
  }),

  // 서류 검증
  rest.post('/api/v1/documents/validate', async (req, res, ctx) => {
    const body = await req.json() as {
      files: Array<{
        name: string;
        type: string;
        size: number;
      }>;
    };

    const VALID_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
    const MAX_FILE_SIZE = 50 * 1024 * 1024;
    const MAX_TOTAL_SIZE = 500 * 1024 * 1024;

    const validations = [];
    let totalSize = 0;
    let allValid = true;

    if (!body.files || body.files.length === 0) {
      return res(ctx.json({
        allValid: false,
        documentCount: 0,
        totalSize: 0,
        validations: [{
          filename: 'unknown',
          valid: false,
          errors: ['At least one file is required']
        }],
        message: 'No files provided'
      }));
    }

    for (const file of body.files) {
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

    return res(ctx.json({
      allValid,
      documentCount: body.files.length,
      totalSize,
      validations,
      message: allValid ? 'All documents valid' : 'Some documents failed validation'
    }));
  }),

  // 이자율 계산 (고급 기능 포함)
  rest.post('/api/v1/loans/calculate', async (req, res, ctx) => {
    const body = await req.json() as {
      principal: number;
      rate: number;
      term: number;
      frequency?: 'monthly' | 'quarterly' | 'annual';
      downPayment?: number;
      generateSchedule?: boolean;
    };

    // 기본값 설정
    const frequency = body.frequency || 'monthly';
    const downPayment = body.downPayment || 0;
    const generateSchedule = body.generateSchedule || false;
    const actualPrincipal = Math.max(0, body.principal - downPayment);

    // 상환 주기별 기간 계산
    const periodsPerYear = frequency === 'monthly' ? 12 : frequency === 'quarterly' ? 4 : 1;
    const periodicRate = (body.rate / 100) / periodsPerYear;
    const totalPeriods = Math.round((body.term * 12) / (12 / periodsPerYear));

    // 상환액 계산
    const periodicPayment = actualPrincipal *
      (periodicRate * Math.pow(1 + periodicRate, totalPeriods)) /
      (Math.pow(1 + periodicRate, totalPeriods) - 1);

    const totalPayment = Math.round(periodicPayment * totalPeriods);
    const totalInterest = Math.round(totalPayment - actualPrincipal);

    // 상환 일정 생성 (선택적)
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

    // 조기 상환 정보 계산
    const earlyRepaymentInfo = {
      possibleFrom: 12,
      penaltyPercentage: 0,
      estimatedSavings: Math.round(totalInterest * 0.3)
    };

    return res(ctx.json({
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
      term: body.term
    }));
  }),
];
