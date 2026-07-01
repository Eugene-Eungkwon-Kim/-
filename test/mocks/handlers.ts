import { rest } from 'msw';

export const loanHandlers = [
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

  // 대출상품 조회
  rest.get('/api/v1/loans/products', (req, res, ctx) => {
    const creditScore = parseInt(req.url.searchParams.get('creditScore') || '700');

    // 신용점수에 따라 다른 상품 반환
    if (creditScore >= 800) {
      return res(ctx.json({
        products: [
          {
            id: 'prime-loan-1',
            name: '프리미엄 전월세',
            rate: 2.5,
            maxAmount: 500000000
          },
          {
            id: 'standard-loan-1',
            name: '표준 전세',
            rate: 3.2,
            maxAmount: 300000000
          }
        ]
      }));
    } else if (creditScore >= 700) {
      return res(ctx.json({
        products: [
          {
            id: 'standard-loan-1',
            name: '표준 전세',
            rate: 3.2,
            maxAmount: 300000000
          }
        ]
      }));
    } else if (creditScore >= 650) {
      return res(ctx.json({
        products: [
          {
            id: 'conditional-loan-1',
            name: '조건부 대출',
            rate: 4.5,
            maxAmount: 150000000
          }
        ]
      }));
    } else {
      return res(ctx.status(400), ctx.json({
        error: '조건에 맞는 상품이 없습니다.'
      }));
    }
  }),

  // 이자율 계산
  rest.post('/api/v1/loans/calculate', async (req, res, ctx) => {
    const body = await req.json() as {
      principal: number;
      rate: number;
      term: number;
    };

    const monthlyRate = body.rate / 12 / 100;
    const monthlyPayment = body.principal *
      (monthlyRate * Math.pow(1 + monthlyRate, body.term)) /
      (Math.pow(1 + monthlyRate, body.term) - 1);

    return res(ctx.json({
      monthlyPayment: Math.round(monthlyPayment),
      totalPayment: Math.round(monthlyPayment * body.term),
      totalInterest: Math.round(monthlyPayment * body.term - body.principal)
    }));
  }),
];
