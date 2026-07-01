import { http, HttpResponse } from 'msw';

export const loanHandlers = [
  // 대출상품 조회
  http.get('/api/v1/loans/products', ({ request }) => {
    const url = new URL(request.url);
    const creditScore = parseInt(url.searchParams.get('creditScore') || '700');

    // 신용점수에 따라 다른 상품 반환
    if (creditScore >= 800) {
      return HttpResponse.json({
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
      });
    } else if (creditScore >= 700) {
      return HttpResponse.json({
        products: [
          {
            id: 'standard-loan-1',
            name: '표준 전세',
            rate: 3.2,
            maxAmount: 300000000
          }
        ]
      });
    } else if (creditScore >= 650) {
      return HttpResponse.json({
        products: [
          {
            id: 'conditional-loan-1',
            name: '조건부 대출',
            rate: 4.5,
            maxAmount: 150000000
          }
        ]
      });
    } else {
      return HttpResponse.json(
        { error: '조건에 맞는 상품이 없습니다.' },
        { status: 400 }
      );
    }
  }),

  // 이자율 계산
  http.post('/api/v1/loans/calculate', async ({ request }) => {
    const body = await request.json() as {
      principal: number;
      rate: number;
      term: number;
    };

    const monthlyRate = body.rate / 12 / 100;
    const monthlyPayment = body.principal *
      (monthlyRate * Math.pow(1 + monthlyRate, body.term)) /
      (Math.pow(1 + monthlyRate, body.term) - 1);

    return HttpResponse.json({
      monthlyPayment: Math.round(monthlyPayment),
      totalPayment: Math.round(monthlyPayment * body.term),
      totalInterest: Math.round(monthlyPayment * body.term - body.principal)
    });
  }),
];
