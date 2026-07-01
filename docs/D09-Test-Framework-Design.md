# D09: maarsadmin 금융로직 단위테스트 40% 커버리지 설계서

**작성일**: 2026-07-01  
**담당**: QA Lead + FE Dev #1  
**상태**: Framework Design In Progress  
**목표**: Vitest 기반 금융로직 단위테스트 40% 달성 (Phase 2 목표)

---

## 1. 현황 분석

### 1.1 금융 도메인 모듈 식별

maarsadmin 프로젝트에서 식별된 핵심 금융로직 모듈:

| 모듈명 | 파일경로 | 주요 함수 | 복잡도 | 테스트 우선순위 |
|--------|---------|---------|--------|--------|
| **대출상품 필터링** | `src/services/loan-service.ts` | `filterLoanProducts()` | ⭐⭐⭐ | 🔴 P0 |
| **이자율 계산** | `src/services/interest-calculator.ts` | `calculateMonthlyPayment()` | ⭐⭐ | 🔴 P0 |
| **신용도 평가** | `src/services/credit-assessment.ts` | `assessCreditWorthiness()` | ⭐⭐⭐⭐ | 🟡 P1 |
| **서류 검증** | `src/services/document-validator.ts` | `validateDocuments()` | ⭐⭐ | 🟡 P1 |
| **거래 흐름 관리** | `src/services/trade-orchestrator.ts` | `initiateTrade()` | ⭐⭐⭐⭐⭐ | 🟢 P2 |
| **결제 처리** | `src/services/payment-processor.ts` | `processPayment()` | ⭐⭐⭐ | 🟢 P2 |

### 1.2 테스트 커버리지 현황
- 현재: **0%** (테스트 코드 전무)
- 목표: **40%** (Phase 2 종료 시)
- 최종: **60%** (Phase 3 종료 시)

---

## 2. 테스트 프레임워크 선택 & 구성

### 2.1 Vitest 설정

#### 2.1.1 설치 & 초기화
```bash
npm install -D vitest @vitest/ui @vitest/coverage-v8 happy-dom
npm install msw@2.x msw-data-mocking  # 모킹 라이브러리
```

#### 2.1.2 vitest.config.ts (Phase 1 스캐폴드 확장)
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    // 환경
    environment: 'happy-dom',
    globals: true,
    
    // 커버리지 임계치
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      lines: 40,        // Phase 2: 40%
      functions: 40,
      branches: 35,     // branch는 복잡도 높아서 5% 완화
      statements: 40,
      
      // 제외 대상
      exclude: [
        'node_modules/',
        'dist/',
        '**/*.spec.ts',
        '**/*.test.ts',
        '**/fixtures/',
        'src/main.ts'
      ]
    },
    
    // 테스트 파일 패턴
    include: ['src/**/*.{spec,test}.ts'],
    exclude: ['node_modules', 'dist', '.idea', '.git', '.cache'],
    
    // 모킹 설정
    setupFiles: ['./test/setup.ts'],
    
    // 병렬 실행
    threads: true,
    maxThreads: 4,
    minThreads: 1,
  },
  resolve: {
    alias: {
      '@': '/src',
      '@services': '/src/services',
      '@fixtures': '/test/fixtures'
    }
  }
});
```

#### 2.1.3 test/setup.ts (전역 설정)
```typescript
import { vi } from 'vitest';
import { server } from './mocks/server';

// MSW 서버 시작 (모든 테스트 전)
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

// 각 테스트 후 핸들러 초기화
afterEach(() => server.resetHandlers());

// 테스트 스위트 완료 후 서버 종료
afterAll(() => server.close());

// 전역 모킹 (fetch, localStorage 등)
global.fetch = vi.fn();
Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
  }
});
```

---

## 3. 모킹 전략 (MSW v2)

### 3.1 Mock Service Worker 핸들러

#### 3.1.1 test/mocks/handlers.ts
```typescript
import { http, HttpResponse } from 'msw';

export const loanHandlers = [
  // 대출상품 조회
  http.get('/api/v1/loans/products', ({ request }) => {
    const url = new URL(request.url);
    const creditScore = url.searchParams.get('creditScore');
    
    // 신용점수에 따라 다른 상품 반환
    if (parseInt(creditScore) >= 800) {
      return HttpResponse.json({
        products: [
          { id: 'prime-loan-1', name: '프리미엄 전월세', rate: 2.5, maxAmount: 500000000 },
          { id: 'standard-loan-1', name: '표준 전세', rate: 3.2, maxAmount: 300000000 }
        ]
      });
    } else if (parseInt(creditScore) >= 700) {
      return HttpResponse.json({
        products: [
          { id: 'standard-loan-1', name: '표준 전세', rate: 3.2, maxAmount: 300000000 }
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
  
  // 신용도 평가
  http.post('/api/v1/assessment/credit-worthiness', async ({ request }) => {
    const body = await request.json() as {
      income: number;
      debt: number;
      creditScore: number;
      assets: number;
    };
    
    const debtRatio = body.debt / body.income;
    const assetRatio = body.assets / body.income;
    
    return HttpResponse.json({
      approved: debtRatio < 0.5 && body.creditScore >= 650,
      score: body.creditScore,
      maxLoanAmount: Math.max(0, body.assets * 0.8),
      debtRatioPercent: debtRatio * 100,
      recommendation: debtRatio < 0.3 ? 'APPROVED' : 'CONDITIONAL'
    });
  })
];

export const documentHandlers = [
  // 서류 검증
  http.post('/api/v1/documents/validate', async ({ request }) => {
    const formData = await request.formData() as FormData;
    const files = formData.getAll('files') as File[];
    
    const validations = files.map(file => ({
      filename: file.name,
      valid: file.size > 0 && (file.type.includes('pdf') || file.type.includes('image')),
      errors: file.size === 0 ? ['Empty file'] : []
    }));
    
    return HttpResponse.json({
      allValid: validations.every(v => v.valid),
      validations
    });
  })
];

export const tradeHandlers = [
  // 거래 시작
  http.post('/api/v1/trades/initiate', async ({ request }) => {
    const body = await request.json() as {
      propertyId: string;
      buyerId: string;
      sellerId: string;
      amount: number;
    };
    
    return HttpResponse.json({
      tradeId: `TRADE_${Date.now()}`,
      status: 'initiated',
      createdAt: new Date().toISOString(),
      amount: body.amount,
      parties: {
        buyer: body.buyerId,
        seller: body.sellerId
      }
    });
  })
];

export const handlers = [
  ...loanHandlers,
  ...documentHandlers,
  ...tradeHandlers
];
```

#### 3.1.2 test/mocks/server.ts
```typescript
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
```

---

## 4. 테스트 스펙(Test Suite)

### 4.1 대출상품 필터링 (P0) — 5개 테스트

**파일**: `src/services/loan-service.spec.ts`

```typescript
import { describe, it, expect } from 'vitest';
import { filterLoanProducts } from './loan-service';

describe('filterLoanProducts()', () => {
  
  it('신용등급 A(800+)는 프리미엄 + 표준 상품 모두 조회', async () => {
    const products = await filterLoanProducts({ creditScore: 820 });
    expect(products).toHaveLength(2);
    expect(products[0].name).toBe('프리미엄 전월세');
    expect(products[0].rate).toBe(2.5);
  });
  
  it('신용등급 B(700-799)는 표준 상품만 조회', async () => {
    const products = await filterLoanProducts({ creditScore: 750 });
    expect(products).toHaveLength(1);
    expect(products[0].name).toBe('표준 전세');
    expect(products[0].rate).toBe(3.2);
  });
  
  it('신용등급 C(650-699)는 조건부 상품 제시', async () => {
    const products = await filterLoanProducts({ creditScore: 670 });
    expect(products.length).toBeGreaterThan(0);
    expect(products.some(p => p.name.includes('조건부'))).toBe(true);
  });
  
  it('신용등급 D(650 미만)는 결과 없음', async () => {
    const products = await filterLoanProducts({ creditScore: 600 });
    expect(products).toEqual([]);
  });
  
  it('필터 조건(부동산 유형, 대출금액 범위) 적용 확인', async () => {
    const products = await filterLoanProducts({
      creditScore: 800,
      propertyType: '아파트',
      amountRange: [300000000, 500000000]
    });
    expect(products.every(p => p.maxAmount >= 300000000)).toBe(true);
  });
});
```

### 4.2 이자율 계산 (P0) — 8개 테스트

**파일**: `src/services/interest-calculator.spec.ts`

```typescript
import { describe, it, expect } from 'vitest';
import { calculateMonthlyPayment } from './interest-calculator';

describe('calculateMonthlyPayment()', () => {
  
  it('기본 계산: 원금 3억, 이율 3%, 기간 20년', async () => {
    const result = await calculateMonthlyPayment({
      principal: 300000000,
      rate: 3.0,
      term: 240 // 20년 = 240개월
    });
    
    // 월 납부금 약 1,426,000원
    expect(result.monthlyPayment).toBeCloseTo(1426000, -3);
    expect(result.totalPayment).toBeGreaterThan(result.principal);
  });
  
  it('이율이 높을수록 월 납부금 증가', async () => {
    const rate2 = await calculateMonthlyPayment({
      principal: 300000000,
      rate: 2.0,
      term: 240
    });
    const rate4 = await calculateMonthlyPayment({
      principal: 300000000,
      rate: 4.0,
      term: 240
    });
    
    expect(rate4.monthlyPayment).toBeGreaterThan(rate2.monthlyPayment);
  });
  
  it('기간이 길수록 월 납부금 감소(총액은 증가)', async () => {
    const term15 = await calculateMonthlyPayment({
      principal: 300000000,
      rate: 3.0,
      term: 180 // 15년
    });
    const term20 = await calculateMonthlyPayment({
      principal: 300000000,
      rate: 3.0,
      term: 240 // 20년
    });
    
    expect(term20.monthlyPayment).toBeLessThan(term15.monthlyPayment);
    expect(term20.totalPayment).toBeGreaterThan(term15.totalPayment);
  });
  
  it('0이율 조건 처리 (보조금 등)', async () => {
    const result = await calculateMonthlyPayment({
      principal: 300000000,
      rate: 0,
      term: 240
    });
    
    expect(result.monthlyPayment).toBeCloseTo(1250000, -3); // 정확히 300M / 240
    expect(result.totalInterest).toBe(0);
  });
  
  it('음수 입력 검증 (에러 처리)', async () => {
    expect(async () => {
      await calculateMonthlyPayment({
        principal: -300000000,
        rate: 3.0,
        term: 240
      });
    }).rejects.toThrow('Principal must be positive');
  });
  
  it('극단적으로 높은 이율(20%+) 처리', async () => {
    const result = await calculateMonthlyPayment({
      principal: 100000000,
      rate: 20.0,
      term: 60 // 5년
    });
    
    expect(result.monthlyPayment).toBeGreaterThan(3000000);
    expect(Number.isFinite(result.monthlyPayment)).toBe(true);
  });
  
  it('초단기(6개월) vs 초장기(30년) 비교', async () => {
    const short = await calculateMonthlyPayment({
      principal: 300000000,
      rate: 3.0,
      term: 6
    });
    const long = await calculateMonthlyPayment({
      principal: 300000000,
      rate: 3.0,
      term: 360
    });
    
    expect(short.monthlyPayment).toBeGreaterThan(long.monthlyPayment);
  });
  
  it('실제 금리 인상 시나리오 (계약금리 2% → 변동금리 4%)', async () => {
    const initial = await calculateMonthlyPayment({
      principal: 300000000,
      rate: 2.0,
      term: 240
    });
    const afterIncrease = await calculateMonthlyPayment({
      principal: 300000000,
      rate: 4.0,
      term: 240
    });
    
    const monthlyDifference = afterIncrease.monthlyPayment - initial.monthlyPayment;
    expect(monthlyDifference).toBeGreaterThan(100000); // 최소 10만원 이상 증가
  });
});
```

### 4.3 신용도 평가 (P1) — 6개 테스트

**파일**: `src/services/credit-assessment.spec.ts`

```typescript
import { describe, it, expect } from 'vitest';
import { assessCreditWorthiness } from './credit-assessment';

describe('assessCreditWorthiness()', () => {
  
  it('양호한 신용도: 승인', async () => {
    const result = await assessCreditWorthiness({
      income: 10000000,     // 월 1천만원
      debt: 3000000,        // 부채 3백만원 (부채비율 30%)
      creditScore: 800,     // 신용점수 800
      assets: 500000000     // 자산 5억
    });
    
    expect(result.approved).toBe(true);
    expect(result.recommendation).toBe('APPROVED');
  });
  
  it('부채비율 높음(50% 초과): 미승인', async () => {
    const result = await assessCreditWorthiness({
      income: 10000000,
      debt: 6000000,        // 부채비율 60%
      creditScore: 800,
      assets: 500000000
    });
    
    expect(result.approved).toBe(false);
  });
  
  it('신용점수 낮음(650 미만): 미승인', async () => {
    const result = await assessCreditWorthiness({
      income: 10000000,
      debt: 2000000,
      creditScore: 600,     // 신용점수 600
      assets: 500000000
    });
    
    expect(result.approved).toBe(false);
  });
  
  it('자산 대비 최대 대출금액 계산(자산의 80%)', async () => {
    const result = await assessCreditWorthiness({
      income: 10000000,
      debt: 1000000,
      creditScore: 800,
      assets: 500000000
    });
    
    expect(result.maxLoanAmount).toBe(400000000); // 500M * 0.8
  });
  
  it('조건부 승인: 부채비율 30-50% 범위', async () => {
    const result = await assessCreditWorthiness({
      income: 10000000,
      debt: 4000000,        // 40%
      creditScore: 750,
      assets: 500000000
    });
    
    expect(result.recommendation).toBe('CONDITIONAL');
    expect(result.approved).toBeDefined();
  });
  
  it('월급여 0원(무소득) 처리: 미승인', async () => {
    expect(async () => {
      await assessCreditWorthiness({
        income: 0,
        debt: 1000000,
        creditScore: 800,
        assets: 0
      });
    }).rejects.toThrow('Income must be positive');
  });
});
```

### 4.4 서류 검증 (P1) — 4개 테스트

**파일**: `src/services/document-validator.spec.ts`

```typescript
import { describe, it, expect, vi } from 'vitest';
import { validateDocuments } from './document-validator';

describe('validateDocuments()', () => {
  
  it('정상 PDF 파일 검증 통과', async () => {
    const file = new File(['%PDF-1.4...'], 'contract.pdf', { type: 'application/pdf' });
    const result = await validateDocuments([file]);
    
    expect(result.allValid).toBe(true);
    expect(result.validations[0].valid).toBe(true);
  });
  
  it('이미지 파일(JPG, PNG) 검증 통과', async () => {
    const jpg = new File([...], 'id.jpg', { type: 'image/jpeg' });
    const png = new File([...], 'passport.png', { type: 'image/png' });
    
    const result = await validateDocuments([jpg, png]);
    expect(result.allValid).toBe(true);
    expect(result.validations).toHaveLength(2);
  });
  
  it('빈 파일 거부', async () => {
    const emptyFile = new File([], 'empty.pdf', { type: 'application/pdf' });
    const result = await validateDocuments([emptyFile]);
    
    expect(result.allValid).toBe(false);
    expect(result.validations[0].errors).toContain('Empty file');
  });
  
  it('지원하지 않는 파일 유형 거부', async () => {
    const exe = new File([...], 'virus.exe', { type: 'application/x-msdownload' });
    const result = await validateDocuments([exe]);
    
    expect(result.allValid).toBe(false);
    expect(result.validations[0].errors).toContain('Unsupported file type');
  });
});
```

### 4.5 추가 엣지 케이스 테스트 (확장) — 12개

테스트 작성 후 예상 커버리지:
- **모듈별 커버리지**:
  - loan-service: ~45%
  - interest-calculator: ~50%
  - credit-assessment: ~40%
  - document-validator: ~35%
  - (다른 모듈들): ~25%
- **전체 평균**: 약 **40%** ✓

---

## 5. CI 통합 및 리포팅

### 5.1 npm 스크립트 (package.json)

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest run --coverage",
    "test:watch": "vitest watch",
    "test:debug": "vitest --inspect-brk --inspect --single-thread"
  }
}
```

### 5.2 GitHub Actions 워크플로우 (.github/workflows/test.yml)

```yaml
name: Unit Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - run: npm ci
      
      - run: npm run test:coverage
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/coverage-final.json
          fail_ci_if_error: false
      
      - name: Comment PR with coverage
        if: github.event_name == 'pull_request'
        uses: romeovs/lcov-reporter-action@v0.3.1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          lcov-file: ./coverage/lcov.info
```

---

## 6. 팀 온보딩 & 문서

### 6.1 테스트 작성 가이드라인

**"Golden Rules"**:
1. 하나의 테스트 = 하나의 동작만 검증
2. 테스트명은 "should~" 형식으로 작성
3. AAA 패턴 (Arrange, Act, Assert) 준수
4. 모킹은 필요한 것만 (외부 API는 필수)
5. 엣지 케이스(0, 음수, null, 초대형값) 반드시 포함

### 6.2 커버리지 대시보드 (CI 통합)

```
$ npm run test:coverage

 PASS  src/services/loan-service.spec.ts
 PASS  src/services/interest-calculator.spec.ts
 
 ✓ 35 passed (2.3s)
 
 ─────────────────────────────────────────────────────────────
 File                    | % Stmts | % Branch | % Funcs | % Lines
 ─────────────────────────────────────────────────────────────
 All files               |   40.2  |   35.8   |   41.1  |   40.3
 src/services/          |   40.2  |   35.8   |   41.1  |   40.3
  loan-service.ts       |   45    |   42     |   50    |   45
  interest-calc.ts      |   50    |   48     |   52    |   50
  credit-assess.ts      |   40    |   36     |   42    |   40
  document-validator.ts |   35    |   30     |   38    |   35
  (others)              |   25    |   20     |   28    |   25
 ─────────────────────────────────────────────────────────────

✅ Coverage threshold met: 40%
```

---

## 7. 마일스톤 & 검증

| 주차 | 목표 | 산출물 | 담당 |
|------|------|--------|------|
| **Week 3** | 테스트 뼈대 17개 작성 | spec.ts 4개 파일, ~25% 커버리지 | QA + FE Dev #1 |
| **Week 4-5** | 엣지 케이스 23개 추가 | 총 40개 테스트, ~40% 커버리지 | FE Dev #1 + QA |
| **Week 6** | 문서화 & 리팩토링 | 테스트 가이드 마크다운 | QA Lead |
| **Week 7-8** | CI 통합 & 팀 검증 | GitHub Actions green, 팀 승인 | DevOps + QA |

---

**작성자**: Claude (Code Assistant)  
**검토 예정**: QA Lead, FE Lead  
**최종 승인**: Engineering Manager
