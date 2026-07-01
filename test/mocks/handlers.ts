import { rest } from 'msw';

export const loanHandlers = [
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
