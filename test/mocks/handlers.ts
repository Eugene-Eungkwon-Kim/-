import { rest } from 'msw';

export const loanHandlers = [
  // 상환 일정 조회
  rest.get('/api/v1/loans/:loanId/repayment-schedule', (req, res, ctx) => {
    const { loanId } = req.params;
    const format = req.url.searchParams.get('format') || 'summary';
    const currency = req.url.searchParams.get('currency') || 'KRW';

    // 모의 대출 정보
    const loanInfo: { [key: string]: any } = {
      'loan-001': {
        principal: 300000000,
        rate: 3.2,
        term: 240,
        startDate: '2026-01-01',
        productName: '표준 전세'
      },
      'loan-002': {
        principal: 150000000,
        rate: 4.5,
        term: 180,
        startDate: '2026-02-01',
        productName: '조건부 대출'
      }
    };

    const loan = loanInfo[loanId];
    if (!loan) {
      return res(ctx.status(404), ctx.json({ error: 'Loan not found' }));
    }

    // 상환 일정 생성
    const monthlyRate = loan.rate / 12 / 100;
    const monthlyPayment = loan.principal *
      (monthlyRate * Math.pow(1 + monthlyRate, loan.term)) /
      (Math.pow(1 + monthlyRate, loan.term) - 1);

    const schedule = [];
    let balance = loan.principal;

    for (let i = 1; i <= loan.term; i++) {
      const interestPayment = Math.round(balance * monthlyRate);
      const principalPayment = Math.round(monthlyPayment - interestPayment);
      balance = Math.max(0, balance - principalPayment);

      if (i <= 12 || i % 12 === 0 || i === loan.term) {
        const dueDate = new Date(new Date(loan.startDate).getTime() + i * 30 * 24 * 60 * 60 * 1000).toISOString();
        schedule.push({
          period: i,
          dueDate: dueDate.split('T')[0],
          payment: Math.round(monthlyPayment),
          principal: principalPayment,
          interest: interestPayment,
          remainingBalance: balance,
          status: i <= 3 ? 'paid' : i === 4 ? 'pending' : 'pending'
        });
      }
    }

    // 환율 적용
    const exchangeRate = currency === 'USD' ? 0.00075 : 1;

    const summary = {
      monthlyPayment: Math.round(monthlyPayment * exchangeRate),
      totalPayment: Math.round(monthlyPayment * loan.term * exchangeRate),
      totalInterest: Math.round((monthlyPayment * loan.term - loan.principal) * exchangeRate),
      paidAmount: Math.round(monthlyPayment * 3 * exchangeRate),
      remainingAmount: Math.round((monthlyPayment * loan.term - monthlyPayment * 3) * exchangeRate),
      remainingInterest: Math.round(((monthlyPayment * loan.term - loan.principal) - (monthlyPayment * 3)) * exchangeRate)
    };

    return res(ctx.json({
      loanId,
      productName: loan.productName,
      principal: loan.principal,
      rate: loan.rate,
      term: loan.term,
      startDate: loan.startDate,
      endDate: new Date(new Date(loan.startDate).getTime() + loan.term * 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      summary,
      schedule,
      earlyRepaymentOptions: {
        prepaymentPenalty: 0,
        prepaymentAllowedAfter: 12,
        estimatedSavings: Math.round(summary.totalInterest * 0.3 * exchangeRate)
      }
    }));
  }),

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

  // 포트폴리오 조회
  rest.get('/api/v1/users/:userId/loans', (req, res, ctx) => {
    const { userId } = req.params;
    const status = req.url.searchParams.get('status');
    const sortBy = req.url.searchParams.get('sortBy') || 'date';
    const limit = parseInt(req.url.searchParams.get('limit') || '10');
    const offset = parseInt(req.url.searchParams.get('offset') || '0');

    // 모의 사용자 대출 포트폴리오
    let userLoans: any[] = [];
    if (userId === 'user-001') {
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
    } else if (userId === 'user-002') {
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

    // 필터링
    let filtered = userLoans;
    if (status) {
      filtered = userLoans.filter(loan => loan.status === status);
    }

    // 정렬
    if (sortBy === 'amount') {
      filtered.sort((a, b) => b.principal - a.principal);
    } else if (sortBy === 'rate') {
      filtered.sort((a, b) => a.rate - b.rate);
    } else {
      filtered.sort((a, b) => new Date(b.startDate).getTime() - new Date(a.startDate).getTime());
    }

    // 페이징
    const total = filtered.length;
    const paginated = filtered.slice(offset, offset + limit);
    const hasMore = offset + limit < total;

    // 포트폴리오 분석
    const totalPrincipal = userLoans.reduce((sum, loan) => sum + loan.principal, 0);
    const totalMonthlyPayment = userLoans.reduce((sum, loan) => sum + loan.monthlyPayment, 0);
    const estimatedMonthlyIncome = 4000000;
    const debtRatio = (totalMonthlyPayment / estimatedMonthlyIncome) * 100;
    const delinquencyCount = userLoans.filter(loan => loan.delinquencyDays > 0).length;

    return res(ctx.json({
      userId,
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
    }));
  }),

  // 신용도 이력 조회
  rest.get('/api/v1/users/:userId/credit-history', (req, res, ctx) => {
    const { userId } = req.params;
    const months = parseInt(req.url.searchParams.get('months') || '12');
    const format = req.url.searchParams.get('format') || 'summary';

    const history: any[] = [];
    const startDate = new Date('2025-08-01');

    for (let i = 0; i < Math.min(months, 12); i++) {
      const date = new Date(startDate);
      date.setMonth(date.getMonth() - i);
      const baseScore = userId === 'user-001' ? 750 : 700;
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

    return res(ctx.json({
      userId,
      currentScore,
      trend,
      averageScore,
      scoreChange,
      history: format === 'detailed' ? history : history.slice(0, 3),
      composition,
      recommendations
    }));
  }),

  // 고급 리스크 분석
  rest.post('/api/v1/analysis/risk-assessment', async (req, res, ctx) => {
    const body = await req.json() as any;

    const creditScore = body.creditScore || 700;
    const income = body.income || 4000000;
    const debt = body.debt || 0;
    const loanAmount = body.loanAmount || 300000000;
    const loanTerm = body.loanTerm || 240;
    const employmentStability = body.employmentStability || 'stable';

    // 신용 리스크 (30%)
    let creditRiskScore = 50;
    if (creditScore >= 800) creditRiskScore = 10;
    else if (creditScore >= 700) creditRiskScore = 25;
    else if (creditScore >= 650) creditRiskScore = 40;
    else creditRiskScore = 70;

    // 소득 리스크 (25%)
    let incomeRiskScore = 30;
    if (employmentStability === 'stable') incomeRiskScore = 15;
    else if (employmentStability === 'moderate') incomeRiskScore = 40;
    else incomeRiskScore = 70;

    // 상환 리스크 (25%)
    const monthlyRate = 3.2 / 12 / 100;
    const monthlyPayment = loanAmount *
      (monthlyRate * Math.pow(1 + monthlyRate, loanTerm)) /
      (Math.pow(1 + monthlyRate, loanTerm) - 1);
    const paymentRatio = (monthlyPayment / income) * 100;
    let repaymentRiskScore = paymentRatio > 50 ? 70 : paymentRatio > 40 ? 50 : 30;

    // 시스템 리스크 (10%) - 경제 상황
    const systemRiskScore = 25;

    // 행동 리스크 (10%)
    const savingsRate = body.savingsRate || 15;
    let behavioralRiskScore = savingsRate < 10 ? 60 : savingsRate < 20 ? 40 : 20;

    // 종합 리스크 점수
    const overallRiskScore = Math.round(
      (creditRiskScore * 0.3) +
      (incomeRiskScore * 0.25) +
      (repaymentRiskScore * 0.25) +
      (systemRiskScore * 0.1) +
      (behavioralRiskScore * 0.1)
    );

    // 부도 확률 (PD) 계산
    const basePD = creditScore >= 800 ? 0.5 : creditScore >= 700 ? 1.5 : creditScore >= 650 ? 3.5 : 8.0;
    const pdAdjustment = (overallRiskScore / 100) * 5;
    const probabilityOfDefault = Math.min(100, basePD + pdAdjustment);

    // 리스크 레벨 판정
    let riskLevel: string;
    if (overallRiskScore < 20) riskLevel = 'very-low';
    else if (overallRiskScore < 35) riskLevel = 'low';
    else if (overallRiskScore < 55) riskLevel = 'medium';
    else if (overallRiskScore < 75) riskLevel = 'high';
    else riskLevel = 'very-high';

    // 완화 전략
    const mitigations = {
      immediate: [] as string[],
      shortTerm: [] as string[],
      mediumTerm: [] as string[]
    };

    if (paymentRatio > 40) {
      mitigations.immediate.push('월상환액 감소 검토 (기간 연장)');
    }
    if (debt > income * 0.3) {
      mitigations.immediate.push('기존 부채 정리');
    }
    if (creditScore < 700) {
      mitigations.shortTerm.push('신용점수 개선 노력');
      mitigations.shortTerm.push('정시 결제 습관 형성');
    }
    if (savingsRate < 15) {
      mitigations.mediumTerm.push('월 저축률 15% 이상 목표 설정');
    }

    return res(ctx.json({
      userId: body.userId,
      overallRiskLevel: riskLevel,
      probabilityOfDefault: Math.round(probabilityOfDefault * 100) / 100,
      riskScore: overallRiskScore,
      riskComponents: {
        creditRisk: {
          score: creditRiskScore,
          assessment: creditScore >= 800 ? 'Excellent' : creditScore >= 700 ? 'Good' : 'Poor',
          factors: [`Credit Score: ${creditScore}`]
        },
        incomeRisk: {
          score: incomeRiskScore,
          stabilityIndex: employmentStability === 'stable' ? 0.9 : 0.5,
          factorsOfConcern: []
        },
        repaymentRisk: {
          score: repaymentRiskScore,
          paymentRatio,
          affordabilityIndex: paymentRatio <= 40 ? 0.8 : 0.4
        },
        systemRisk: {
          score: systemRiskScore,
          macroFactors: ['경제 성장률', '금리 환경'],
          industryFactors: [body.industry || '금융']
        },
        behavioralRisk: {
          score: behavioralRiskScore,
          savingsRate,
          creditDiscipline: savingsRate > 20 ? 'Excellent' : 'Moderate'
        }
      },
      scenarioAnalysis: {
        bestCase: {
          description: '신용도 개선 + 수입 증가 시나리오',
          probabilityOfDefault: Math.max(0, probabilityOfDefault * 0.5)
        },
        baseCase: {
          description: '현재 추세 유지',
          probabilityOfDefault
        },
        worstCase: {
          description: '경제 악화 + 실직 시나리오',
          probabilityOfDefault: Math.min(100, probabilityOfDefault * 2)
        }
      },
      mitigationStrategies: mitigations,
      loanDecision: {
        recommendation: riskLevel === 'very-low' || riskLevel === 'low' ? 'approve' : riskLevel === 'medium' ? 'approve-with-conditions' : 'decline',
        reasoning: riskLevel === 'very-low' ? 'Excellent credit profile' : riskLevel === 'low' ? 'Good credit profile' : 'High risk factors',
        conditions: riskLevel === 'medium' ? {
          requiredCollateral: Math.round(loanAmount * 0.3),
          coApplicantRequired: true,
          rateAdjustment: 1.5,
          maxLoanAmount: loanAmount
        } : undefined
      },
      monitoringPlan: {
        checkpoints: [
          {
            period: 6,
            metrics: ['Credit Score', 'Payment Status'],
            triggers: ['Score drop > 50점', 'Payment delay']
          }
        ]
      }
    }));
  }),

  // 입력 검증 강화
  rest.post('/api/v1/validation/check', async (req, res, ctx) => {
    const body = await req.json() as any;
    const startTime = Date.now();

    const errors: any[] = [];
    const warnings: any[] = [];

    // 필드 존재성 검증
    const requiredFields = ['userId', 'loanAmount', 'loanTerm', 'productId', 'income', 'creditScore', 'purpose'];
    for (const field of requiredFields) {
      if (body[field] === undefined || body[field] === null) {
        errors.push({
          field,
          message: `${field} is required`,
          code: 'REQUIRED'
        });
      }
    }

    // 타입 검증
    if (body.userId && typeof body.userId !== 'string') {
      errors.push({
        field: 'userId',
        message: 'userId must be a string',
        code: 'TYPE'
      });
    }
    if (body.loanAmount && typeof body.loanAmount !== 'number') {
      errors.push({
        field: 'loanAmount',
        message: 'loanAmount must be a number',
        code: 'TYPE'
      });
    }
    if (body.loanTerm && typeof body.loanTerm !== 'number') {
      errors.push({
        field: 'loanTerm',
        message: 'loanTerm must be a number',
        code: 'TYPE'
      });
    }
    if (body.income && typeof body.income !== 'number') {
      errors.push({
        field: 'income',
        message: 'income must be a number',
        code: 'TYPE'
      });
    }
    if (body.creditScore && typeof body.creditScore !== 'number') {
      errors.push({
        field: 'creditScore',
        message: 'creditScore must be a number',
        code: 'TYPE'
      });
    }

    // 범위 검증
    if (body.loanAmount !== undefined && (body.loanAmount < 10000000 || body.loanAmount > 500000000)) {
      errors.push({
        field: 'loanAmount',
        message: 'loanAmount must be between 10M and 500M',
        code: 'RANGE'
      });
    }
    if (body.loanTerm !== undefined && (body.loanTerm < 6 || body.loanTerm > 360)) {
      errors.push({
        field: 'loanTerm',
        message: 'loanTerm must be between 6 and 360 months',
        code: 'RANGE'
      });
    }
    if (body.creditScore !== undefined && (body.creditScore < 0 || body.creditScore > 999)) {
      errors.push({
        field: 'creditScore',
        message: 'creditScore must be between 0 and 999',
        code: 'RANGE'
      });
    }
    if (body.income !== undefined && body.income <= 0) {
      errors.push({
        field: 'income',
        message: 'income must be greater than 0',
        code: 'RANGE'
      });
    }

    // 비즈니스 규칙 검증
    const debt = body.debt || 0;
    if (body.loanAmount && body.income && body.loanAmount > body.income * 3) {
      warnings.push({
        field: 'loanAmount',
        message: 'Loan amount is more than 3x annual income'
      });
    }
    if (body.income && debt > body.income * 0.5) {
      warnings.push({
        field: 'debt',
        message: 'Debt exceeds 50% of annual income'
      });
    }
    if (body.creditScore && body.creditScore < 650) {
      warnings.push({
        field: 'creditScore',
        message: 'Credit score is below recommended threshold'
      });
    }

    // 제품 유효성 검증
    const validProducts = ['prime-loan-1', 'standard-loan-1', 'conditional-loan-1'];
    if (body.productId && !validProducts.includes(body.productId)) {
      errors.push({
        field: 'productId',
        message: 'Invalid productId',
        code: 'BUSINESS_RULE'
      });
    }

    // 목적 검증
    const validPurposes = ['deposit', 'purchase', 'monthly-rent', 'other'];
    if (body.purpose && !validPurposes.includes(body.purpose)) {
      errors.push({
        field: 'purpose',
        message: 'Invalid purpose',
        code: 'BUSINESS_RULE'
      });
    }

    // 일관성 검증
    if (body.loanAmount && body.loanTerm && body.productId) {
      const products: { [key: string]: { maxAmount: number; maxTerm: number } } = {
        'prime-loan-1': { maxAmount: 500000000, maxTerm: 360 },
        'standard-loan-1': { maxAmount: 300000000, maxTerm: 240 },
        'conditional-loan-1': { maxAmount: 150000000, maxTerm: 180 }
      };

      const product = products[body.productId];
      if (product) {
        if (body.loanAmount > product.maxAmount) {
          errors.push({
            field: 'loanAmount',
            message: `Loan amount exceeds product maximum (${product.maxAmount})`,
            code: 'CONSISTENCY'
          });
        }
        if (body.loanTerm > product.maxTerm) {
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

    return res(ctx.json({
      valid,
      errors,
      warnings,
      validatedData: valid ? {
        userId: body.userId,
        loanAmount: body.loanAmount,
        loanTerm: body.loanTerm,
        productId: body.productId,
        income: body.income,
        debt: body.debt,
        creditScore: body.creditScore,
        purpose: body.purpose
      } : undefined,
      validationDetails: {
        fieldsChecked: requiredFields.length,
        errorsFound: errors.length,
        warningsFound: warnings.length,
        validationTime
      }
    }));
  }),

  // 재정 분석 & 계획
  rest.post('/api/v1/planning/financial-analysis', async (req, res, ctx) => {
    const body = await req.json() as any;
    const monthlyIncome = body.monthlyIncome || 4000000;
    const monthlyExpenses = body.monthlyExpenses || 1500000;
    const totalDebt = body.totalDebt || 100000000;
    const totalAssets = body.totalAssets || 500000000;
    const savingsGoal = body.savingsGoal || 100000000;
    const savingsDuration = body.savingsDuration || 36;

    const monthlyLoanPayments = totalDebt / 240; // 240개월 평균
    const monthlySurplus = monthlyIncome - monthlyExpenses - monthlyLoanPayments;
    const debtToIncomeRatio = totalDebt / (monthlyIncome * 12);
    const assetToDebtRatio = totalAssets / totalDebt;
    const netWorth = totalAssets - totalDebt;

    // 재정 건강도 점수 (0-100)
    const debtRatioScore = Math.max(0, 100 - (debtToIncomeRatio * 100));
    const surplusScore = monthlySurplus > 0 ? Math.min(100, (monthlySurplus / monthlyIncome) * 300) : 0;
    const assetScore = Math.min(100, (assetToDebtRatio) * 20);
    const creditScore = Math.min(100, 100 - debtToIncomeRatio * 50);
    const healthScore = Math.round(
      (debtRatioScore * 0.3) +
      (surplusScore * 0.3) +
      (assetScore * 0.2) +
      (creditScore * 0.2)
    );

    let healthGrade = 'A';
    if (healthScore >= 80) healthGrade = 'A';
    else if (healthScore >= 60) healthGrade = 'B';
    else if (healthScore >= 40) healthGrade = 'C';
    else if (healthScore >= 20) healthGrade = 'D';
    else healthGrade = 'F';

    const monthlyRequiredSavings = savingsGoal / savingsDuration;
    const currentMonthlySavings = Math.max(0, monthlySurplus);
    const monthsToGoal = currentMonthlySavings > 0 ? savingsGoal / currentMonthlySavings : Infinity;

    const quickestPayoffMonths = totalDebt > 0 ? Math.ceil(totalDebt / Math.max(monthlyIncome * 0.5, 1)) : 0;
    const balancedPayoffMonths = totalDebt > 0 ? Math.ceil(totalDebt / (monthlyIncome * 0.2)) : 0;

    return res(ctx.json({
      userId: body.userId,
      currentStatus: {
        monthlyIncome,
        monthlyExpenses,
        monthlyLoanPayments: Math.round(monthlyLoanPayments),
        monthlySurplus: Math.round(monthlySurplus),
        totalDebt,
        totalAssets,
        netWorth,
        debtToIncomeRatio: Math.round(debtToIncomeRatio * 1000) / 1000,
        assetToDebtRatio: Math.round(assetToDebtRatio * 100) / 100
      },
      financialHealthScore: healthScore,
      healthGrade,
      healthBreakdown: {
        debtRatioScore: Math.round(debtRatioScore),
        surplusCashScore: Math.round(surplusScore),
        assetScore: Math.round(assetScore),
        creditScore: Math.round(creditScore)
      },
      savingsAnalysis: {
        currentMonthlySavings: Math.round(currentMonthlySavings),
        projectedSavings12Months: Math.round(currentMonthlySavings * 12),
        savingsGoal,
        savingsGoalMonths: monthsToGoal === Infinity ? 999 : Math.round(monthsToGoal),
        monthlyRequiredSavings: Math.round(monthlyRequiredSavings),
        achievable: currentMonthlySavings >= monthlyRequiredSavings
      },
      debtRepaymentPlan: {
        totalDebt,
        quickestPayoffMonths,
        balancedPayoffMonths,
        debtFreeDate: new Date(Date.now() + balancedPayoffMonths * 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        estimatedInterestSavings: Math.round((monthlyIncome * 0.1) * balancedPayoffMonths * 0.3)
      },
      recommendations: [
        monthlySurplus > 0 ? '긍정적인 월 여유금 유지' : '지출 감소 필요',
        debtToIncomeRatio > 0.5 ? '부채 감소 우선' : '균형잡힌 저축',
        healthScore > 70 ? '현재 추세 유지' : '재정 개선 필요'
      ]
    }));
  }),

  // 신용도 시뮬레이션
  rest.post('/api/v1/simulation/credit-score', async (req, res, ctx) => {
    const body = await req.json() as any;
    const userId = body.userId || 'user-001';
    const currentScore = body.currentScore || 750;
    const scenario = body.scenarios?.scenario || 'normal';
    const duration = body.scenarios?.duration || 12;
    const params = body.parameters || {};

    const scenarioDefaults = {
      ideal: { paymentSuccess: 100, debtChangeRate: -1 },
      normal: { paymentSuccess: 90, debtChangeRate: -0.5 },
      risky: { paymentSuccess: 70, debtChangeRate: 0.5 },
      crisis: { paymentSuccess: 50, debtChangeRate: 1.5 }
    };

    const defaults = scenarioDefaults[scenario as keyof typeof scenarioDefaults] || scenarioDefaults.normal;
    const paymentSuccess = params.paymentSuccess ?? defaults.paymentSuccess;
    const debtChangeRate = params.debtChangeRate ?? defaults.debtChangeRate;
    const inquiryFrequency = params.inquiryFrequency ?? 2;

    const getGrade = (score: number): string => {
      if (score >= 900) return 'A+';
      if (score >= 800) return 'A';
      if (score >= 700) return 'B+';
      if (score >= 600) return 'B';
      if (score >= 500) return 'C';
      if (score >= 400) return 'D';
      return 'F';
    };

    const results = [];
    let score = currentScore;
    const scores = [score];

    for (let month = 1; month <= duration; month++) {
      let monthScore = score;
      const events: string[] = [];
      let scoreChange = 0;
      let debtChange = debtChangeRate;

      const paymentSuccess_ = scenario === 'ideal' ? true : scenario === 'crisis' ? false : Math.random() * 100 < paymentSuccess;
      if (paymentSuccess_) {
        monthScore += 5;
        events.push('결제 성공');
        debtChange -= 1;
      } else {
        monthScore -= 20;
        events.push('연체 발생');
        debtChange += 0.5;
      }

      let inquiries = 0;
      if (scenario === 'ideal') inquiries = 0;
      else if (scenario === 'crisis') inquiries = 4;
      else inquiries = Math.floor(inquiryFrequency * (Math.random() + 0.5));

      if (inquiries > 0) {
        monthScore -= inquiries * 2;
        events.push(`신용조회 ${inquiries}회`);
      }

      const volatility = scenario === 'ideal' || scenario === 'crisis' ? 0 : (Math.random() - 0.5) * 10;
      monthScore += volatility;

      monthScore = Math.max(300, Math.min(999, Math.round(monthScore)));
      scoreChange = monthScore - score;
      score = monthScore;
      scores.push(score);

      results.push({
        month,
        score: monthScore,
        grade: getGrade(monthScore),
        debtChange: Math.round(debtChange * 10) / 10,
        events,
        scoreChange
      });
    }

    const bestMonth = results.reduce((best: any, r: any) => r.score > best.score ? r : best, results[0]);
    const worstMonth = results.reduce((worst: any, r: any) => r.score < worst.score ? r : worst, results[0]);
    const averageScore = Math.round(scores.reduce((a: number, b: number) => a + b) / scores.length);
    const finalScoreChange = score - currentScore;

    let trend = 'stable';
    if (finalScoreChange > 30) trend = 'improving';
    else if (finalScoreChange < -30) trend = 'declining';

    const riskLevel = score < 500 ? 'high' : score < 700 ? 'medium' : 'low';

    const recommendations = [
      trend === 'declining' ? '신용도 회복에 집중하세요' : '현재 추세를 유지하세요',
      riskLevel === 'high' ? '우발적 부채 발생 자제' : '신용도 관리 지속',
      score < 700 ? '정기적인 신용보험료 검토' : '우수 고객 혜택 활용'
    ];

    return res(ctx.json({
      userId,
      currentScore,
      simulationPeriod: duration,
      scenario,
      results,
      summary: {
        finalScore: score,
        finalGrade: getGrade(score),
        scoreChange: finalScoreChange,
        bestMonth,
        worstMonth,
        averageScore,
        trend,
        riskLevel
      },
      recommendations
    }));
  }),

  // 대출 상품 추천
  rest.post('/api/v1/recommendations/loan-products', async (req, res, ctx) => {
    const body = await req.json() as any;
    const userId = body.userId || 'user-001';
    const creditScore = body.creditScore || 750;
    const income = body.income || 5000000;
    const debt = body.debt || 50000000;
    const assets = body.assets || 300000000;
    const purpose = body.purpose || 'purchase';
    const preferenceType = body.preferenceType || 'balanced';
    const maxMonthlyPaymentRatio = body.maxMonthlyPaymentRatio ?? 40;

    let userGrade = 'D';
    if (creditScore >= 800) userGrade = 'A';
    else if (creditScore >= 700) userGrade = 'B';
    else if (creditScore >= 600) userGrade = 'C';

    const allProducts = [
      { id: 'product-1', name: '표준 전세', minScore: 550, rate: 3.2, maxAmount: 500000000, maxTerm: 240 },
      { id: 'product-2', name: '우대 전세', minScore: 650, rate: 2.8, maxAmount: 600000000, maxTerm: 240 },
      { id: 'product-3', name: 'VIP 대출', minScore: 800, rate: 2.4, maxAmount: 800000000, maxTerm: 300 },
      { id: 'product-4', name: '신한 월세', minScore: 500, rate: 4.2, maxAmount: 300000000, maxTerm: 120 },
      { id: 'product-5', name: '안심 구매', minScore: 600, rate: 3.8, maxAmount: 400000000, maxTerm: 180 }
    ];

    const availableProducts = allProducts.filter(p => creditScore >= p.minScore);
    const loanAmount = Math.min(income * 3, availableProducts[0]?.maxAmount || 500000000);
    const loanTerm = 240;

    const productScores = availableProducts.map(product => {
      const monthlyRate = product.rate / 12 / 100;
      const monthlyPayment = loanAmount * (monthlyRate * Math.pow(1 + monthlyRate, loanTerm)) / (Math.pow(1 + monthlyRate, loanTerm) - 1);
      const totalPayment = monthlyPayment * loanTerm;
      const totalInterest = totalPayment - loanAmount;
      const paymentRatio = (monthlyPayment / income) * 100;

      let matchScore = 100;
      matchScore -= (product.rate * 2);
      matchScore -= (paymentRatio > maxMonthlyPaymentRatio ? (paymentRatio - maxMonthlyPaymentRatio) : 0);
      matchScore = Math.max(0, Math.min(100, matchScore));

      if (preferenceType === 'lowest-rate' && product.rate < 3.5) matchScore += 10;
      if (preferenceType === 'lowest-payment' && paymentRatio < 30) matchScore += 10;
      if (preferenceType === 'shortest-term' && product.maxTerm <= 180) matchScore += 10;
      if (preferenceType === 'balanced' && product.rate < 3.5 && paymentRatio < 35) matchScore += 10;

      matchScore = Math.min(100, matchScore);

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

    const alternatives = sorted.slice(3, 5).map((item, idx) => ({
      rank: idx + 4,
      productId: item.product.id,
      productName: item.product.name,
      rate: item.product.rate,
      matchScore: item.matchScore
    }));

    const comparisonMatrix = {
      productIds: recommended.map(r => r.productId),
      metrics: {
        rate: recommended.map(r => r.rate),
        monthlyPayment: recommended.map(r => r.analysis.monthlyPayment),
        totalInterest: recommended.map(r => r.analysis.totalInterest),
        paymentRatio: recommended.map(r => r.analysis.paymentRatio)
      }
    };

    const personalizedAdvice = creditScore >= 800 ? 'VIP 고객으로서 최우대 조건 제공 가능합니다' :
      creditScore >= 700 ? '우대 상품으로 합리적인 금리 제공합니다' :
      creditScore >= 600 ? '기본 상품으로 안정적인 대출이 가능합니다' :
      '신용도 개선을 통해 더 좋은 상품 이용이 가능합니다';

    return res(ctx.json({
      userId,
      userGrade,
      recommendedProducts: recommended,
      alternativeProducts: alternatives,
      comparisonMatrix,
      personalizedAdvice
    }));
  }),
];
