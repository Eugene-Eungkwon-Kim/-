# D09: 금융로직 단위테스트 40% 커버리지 — 상세 구현 계획서

**작성일**: 2026-07-01  
**담당**: FE Dev #1 (테스트 작성) + QA Lead (검증)  
**기간**: Week 3-6 (4주), 40개 테스트, 40% 커버리지 목표  
**상태**: Implementation Ready

---

## 📋 목차

1. 프로젝트 구조 & 파일 생성 순서
2. Week별 상세 작업 계획
3. 각 테스트 파일 상세 스펙
4. Mock 데이터 Fixture
5. Vitest 설정 최종 버전
6. 팀 협업 & 코드 리뷰 가이드
7. CI/CD 통합
8. 일일 체크리스트

---

## 1. 프로젝트 구조 & 파일 생성 순서

### 1.1 디렉토리 구조 (생성 예상)

```
project-root/
├── src/
│   ├── services/
│   │   ├── loan-service.ts                    (기존)
│   │   ├── loan-service.spec.ts               (NEW, Week 3)
│   │   ├── interest-calculator.ts             (기존)
│   │   ├── interest-calculator.spec.ts        (NEW, Week 3)
│   │   ├── credit-assessment.ts               (기존)
│   │   ├── credit-assessment.spec.ts          (NEW, Week 3-4)
│   │   ├── document-validator.ts              (기존)
│   │   ├── document-validator.spec.ts         (NEW, Week 4)
│   │   ├── trade-orchestrator.ts              (기존, Phase 3)
│   │   └── payment-processor.ts               (기존, Phase 3)
│   │
│   ├── types/
│   │   ├── loan.ts                            (기존)
│   │   ├── credit.ts                          (기존)
│   │   └── document.ts                        (기존)
│
├── test/
│   ├── setup.ts                               (NEW, 전역 설정)
│   ├── vitest.config.ts                       (신규 또는 수정)
│   │
│   ├── fixtures/
│   │   ├── loans.json                         (NEW, 대출상품)
│   │   ├── credit-scores.json                 (NEW, 신용점수)
│   │   ├── documents.json                     (NEW, 서류 샘플)
│   │   └── trades.json                        (NEW, 거래)
│   │
│   └── mocks/
│       ├── server.ts                          (기존, 확장)
│       ├── handlers.ts                        (기존, 확장)
│       └── seed-data.ts                       (NEW, 초기 데이터)
│
├── vitest.config.ts                           (기존, 검토 후 수정)
├── package.json                               (검토 후 수정)
└── tsconfig.json                              (검토, TypeScript strict mode)
```

### 1.2 파일 생성 순서 (우선순위)

| 우선순위 | 파일 | 라인수 | 예상 시간 | 담당 |
|---------|------|--------|---------|------|
| 1️⃣ | test/fixtures/loans.json | 50 | 0.5h | QA |
| 2️⃣ | test/mocks/handlers.ts (확장) | +100 | 1h | FE Dev #1 |
| 3️⃣ | test/setup.ts | 40 | 0.5h | FE Dev #1 |
| 4️⃣ | src/services/loan-service.spec.ts | 120 | 3h | FE Dev #1 |
| 5️⃣ | test/fixtures/credit-scores.json | 40 | 0.5h | QA |
| 6️⃣ | src/services/interest-calculator.spec.ts | 180 | 4h | FE Dev #1 |
| 7️⃣ | src/services/credit-assessment.spec.ts | 140 | 3.5h | FE Dev #1 + QA pair |
| 8️⃣ | test/fixtures/documents.json | 30 | 0.5h | QA |
| 9️⃣ | src/services/document-validator.spec.ts | 100 | 2.5h | FE Dev #1 |
| 🔟 | 엣지 케이스 추가 테스트 x 23개 | 200 | 5h | FE Dev #1 |

**총 공수**: 20.5인시 (약 2.5인주 또는 1명 기준 5일)

---

## 2. Week별 상세 작업 계획

### 📅 Week 3: 핵심 테스트 뼈대 (17개 테스트, ~25% 커버리지)

#### 월요일 (2026-07-15)

**오전**: 환경 설정 (1.5h)
```bash
# 1. vitest 기본 설정 검토
cd project-root
npm run test --version  # vitest 설치 확인

# 2. test/setup.ts 작성
cat > test/setup.ts << 'EOF'
import { vi } from 'vitest';
import { server } from './mocks/server';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// 전역 모킹
global.fetch = vi.fn();
EOF

# 3. vitest.config.ts 수정
# - coverage threshold: 40% 설정
# - setupFiles: ['./test/setup.ts']

# 4. npm install 확인
npm ci
npm run test -- --run  # 기본 테스트 실행 (제로 상태)
```

**오후**: Mock 데이터 준비 (2h)
```bash
# test/fixtures/loans.json 작성 (아래 섹션 참고)
# test/mocks/handlers.ts 확장 (MSW GET /api/v1/loans/products)

# 검증
npm run test -- mocks.test.ts  # 모킹 동작 확인
```

#### 화요일-수요일 (2026-07-16 ~ 07-17)

**loan-service.spec.ts 작성** (5개 테스트, ~120줄)

```typescript
// src/services/loan-service.spec.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { filterLoanProducts } from './loan-service';

describe('LoanService.filterLoanProducts()', () => {
  // 5개 테스트 (아래 상세 스펙 참고)
  it('신용등급 A(800+)는 프리미엄 + 표준 상품', async () => { ... });
  it('신용등급 B(700-799)는 표준만', async () => { ... });
  it('신용등급 C(650-699)는 조건부', async () => { ... });
  it('신용등급 D(650 미만)는 결과 없음', async () => { ... });
  it('필터 조건 적용 확인', async () => { ... });
});
```

**목표**: 5개 테스트 pass, 커버리지 ~20%

#### 목요일 (2026-07-18)

**interest-calculator.spec.ts 작성** (8개 테스트, ~180줄)

```typescript
// src/services/interest-calculator.spec.ts
import { describe, it, expect } from 'vitest';
import { calculateMonthlyPayment } from './interest-calculator';

describe('InterestCalculator.calculateMonthlyPayment()', () => {
  // 8개 테스트
  it('기본 계산: 원금 3억, 이율 3%, 기간 20년', async () => { ... });
  it('이율이 높을수록 월 납부금 증가', async () => { ... });
  it('기간이 길수록 월 납부금 감소', async () => { ... });
  it('0이율 조건 처리', async () => { ... });
  it('음수 입력 검증(에러)', async () => { ... });
  it('극단적으로 높은 이율(20%+) 처리', async () => { ... });
  it('초단기(6개월) vs 초장기(30년) 비교', async () => { ... });
  it('실제 금리 인상 시나리오', async () => { ... });
});
```

**목표**: 8개 테스트 pass, 누적 커버리지 ~25%

#### 금요일 (2026-07-19)

**주간 정산 & 리뷰** (1h)
```bash
# 현황 확인
npm run test:coverage
# 예상 결과:
# ✅ loan-service.spec.ts: 5/5 passed
# ✅ interest-calculator.spec.ts: 8/8 passed
# 📊 Coverage: ~25% (loan-service 45%, interest-calc 50%, 기타 <20%)

# 이슈 정리
npm run test -- --reporter=verbose
# 실패한 테스트가 있다면 기록

# 다음주 준비
# - credit-assessment 복잡도 검토
# - credit-scores.json fixture 사전 준비
```

---

### 📅 Week 4: credit-assessment + document-validator (10개 테스트 추가)

#### 월요일-수요일 (2026-07-22 ~ 07-24)

**credit-assessment.spec.ts** (6개 테스트, ~140줄)
- Pair programming: FE Dev #1 + QA Lead (신용도 로직 검증)
- 복잡한 조건 분기 (부채비율, 신용점수, 자산) 테스트

**목표**: 6개 테스트 pass, 누적 25% → 30%

#### 목요일-금요일 (2026-07-25 ~ 07-26)

**document-validator.spec.ts** (4개 테스트, ~100줄)
- 파일 유형 검증 (PDF, JPG, PNG)
- 빈 파일, 지원하지 않는 타입 에러 처리

**목표**: 4개 테스트 pass, 누적 커버리지 30%

---

### 📅 Week 5: 엣지 케이스 + 추가 테스트 (23개, ~40% 커버리지)

#### 월요일-수요일 (2026-07-29 ~ 07-31)

**추가 테스트 작성** (23개, ~200줄):

**loan-service.spec.ts 확장**:
- 다양한 부동산 유형(아파트, 원룸, 상가) 필터링
- 대출금액 범위별 필터링
- 복합 조건(부동산유형 + 신용도 + 금액) 테스트
- API 응답 에러 처리
- 총 ~15개 추가

**interest-calculator.spec.ts 확장**:
- 소수점 이율 (3.25%, 2.875% 등)
- 비표준 기간 (13개월, 121개월 등)
- 초고액 대출 (10억 이상)
- 초저액 대출 (100만 미만)
- 총 ~5개 추가

**credit-assessment.spec.ts 확장**:
- 다양한 부채비율 조합
- 자산 없음 시나리오
- 소수점 신용점수
- 총 ~3개 추가

#### 목요일-금요일 (2026-08-01 ~ 08-02)

**최종 통합 & 커버리지 검증**:

```bash
npm run test:coverage

# 예상 결과:
# ✅ 총 40개 테스트 통과
# 📊 Coverage:
#   loan-service.ts: 50%
#   interest-calculator.ts: 55%
#   credit-assessment.ts: 48%
#   document-validator.ts: 40%
#   평균: 40% ✓

npm run test:ui  # UI 대시보드 확인

# CI 통합 테스트
git push origin D09-tests
# GitHub Actions 파이프라인 실행 확인
```

---

### 📅 Week 6: 최적화 & 문서화 (CI 통합)

#### 월요일-화요일 (2026-08-05 ~ 08-06)

**테스트 최적화**:
- 느린 테스트 식별 및 개선 (목표: 전체 < 5초)
- Mock 데이터 크기 최적화
- 병렬 실행 설정 확인

**문서화**:
- `TEST-GUIDE.md` 작성 (테스트 작성 표준)
- 각 테스트 파일 주석 추가
- 팀 온보딩 문서

#### 수요일 (2026-08-07)

**CI/CD 통합**:
```yaml
# .github/workflows/test.yml 수정
- name: Unit Tests (D09)
  run: npm run test:coverage
  
- name: Coverage Check
  if: ${{ github.event_name == 'pull_request' }}
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage/lcov.info
    fail_ci_if_error: true
    flags: unit-tests
    thresholds: 40  # Phase 2 목표
```

#### 목요일-금요일 (2026-08-08 ~ 08-09)

**팀 리뷰 & 최종 검증**:
- QA Lead: 테스트 로직 및 커버리지 검증
- FE Lead: 코드 스타일 및 구조 검증
- 승인 후 develop 병합

---

## 3. 각 테스트 파일 상세 스펙

### 3.1 loan-service.spec.ts (핵심 5개 → 최종 15-20개)

**파일 위치**: `src/services/loan-service.spec.ts`  
**최종 라인수**: ~250줄  
**테스트 케이스**: 

```typescript
import { describe, it, expect } from 'vitest';
import { filterLoanProducts, LoanFilter, LoanProduct } from './loan-service';

describe('LoanService', () => {
  
  describe('filterLoanProducts() - 신용도별 필터링', () => {
    it('[T-L001] 신용등급 A(800+): 프리미엄 + 표준 모두 조회', async () => {
      const result = await filterLoanProducts({ creditScore: 820 });
      expect(result).toHaveLength(2);
      expect(result[0].rate).toBeLessThan(result[1].rate);
    });
    
    it('[T-L002] 신용등급 B(700-799): 표준만 조회', async () => {
      const result = await filterLoanProducts({ creditScore: 750 });
      expect(result).toHaveLength(1);
      expect(result[0].name).toContain('표준');
    });
    
    it('[T-L003] 신용등급 C(650-699): 조건부 조회', async () => {
      const result = await filterLoanProducts({ creditScore: 670 });
      expect(result.length).toBeGreaterThan(0);
    });
    
    it('[T-L004] 신용등급 D(650 미만): 결과 없음', async () => {
      const result = await filterLoanProducts({ creditScore: 600 });
      expect(result).toHaveLength(0);
    });
    
    // 추가 테스트 (Week 5)
    it('[T-L005] 신용등급 경계값(800 정확히): 프리미엄 포함', async () => {
      const result = await filterLoanProducts({ creditScore: 800 });
      expect(result.some(p => p.name.includes('프리미엄'))).toBe(true);
    });
    
    it('[T-L006] 신용등급 경계값(700 정확히): 표준만', async () => {
      const result = await filterLoanProducts({ creditScore: 700 });
      expect(result.length).toBeGreaterThan(0);
      expect(result.every(p => !p.name.includes('프리미엄'))).toBe(true);
    });
  });
  
  describe('filterLoanProducts() - 부동산 유형별 필터링', () => {
    it('[T-L101] 아파트 필터링', async () => {
      const result = await filterLoanProducts({
        creditScore: 800,
        propertyType: '아파트'
      });
      expect(result.every(p => p.propertyTypes.includes('아파트'))).toBe(true);
    });
    
    it('[T-L102] 원룸 필터링', async () => {
      const result = await filterLoanProducts({
        creditScore: 750,
        propertyType: '원룸'
      });
      expect(result.length).toBeGreaterThan(0);
    });
    
    it('[T-L103] 상가 필터링 (고리 상품만)', async () => {
      const result = await filterLoanProducts({
        creditScore: 800,
        propertyType: '상가'
      });
      // 상가는 보험료 높음, 제한 많음
      expect(result.some(p => p.type === 'commercial')).toBe(true);
    });
  });
  
  describe('filterLoanProducts() - 금액 범위 필터링', () => {
    it('[T-L201] 최소 금액 이상만 반환', async () => {
      const result = await filterLoanProducts({
        creditScore: 800,
        amountRange: [300000000, 500000000]
      });
      expect(result.every(p => p.maxAmount >= 300000000)).toBe(true);
    });
    
    it('[T-L202] 초고액 대출(10억+) 필터링', async () => {
      const result = await filterLoanProducts({
        creditScore: 900, // 최상위 신용도
        amountRange: [1000000000, 5000000000]
      });
      // VIP 상품만 반환
      expect(result.some(p => p.name.includes('VIP'))).toBe(true);
    });
    
    it('[T-L203] 금액 범위 없을 시 모든 상품', async () => {
      const result = await filterLoanProducts({ creditScore: 750 });
      expect(result.length).toBeGreaterThan(0);
    });
  });
  
  describe('filterLoanProducts() - 에러 처리', () => {
    it('[T-L301] API 응답 에러(429 Too Many Requests)', async () => {
      server.use(
        http.get('/api/v1/loans/products', () => {
          return new HttpResponse(null, { status: 429 });
        })
      );
      
      expect(async () => {
        await filterLoanProducts({ creditScore: 800 });
      }).rejects.toThrow('Rate limit exceeded');
    });
    
    it('[T-L302] 잘못된 신용점수 입력(음수)', async () => {
      expect(() => {
        filterLoanProducts({ creditScore: -100 });
      }).toThrow('Credit score must be between 0 and 999');
    });
  });
});
```

---

### 3.2 interest-calculator.spec.ts (8개 → 15-20개)

**파일 위치**: `src/services/interest-calculator.spec.ts`  
**최종 라인수**: ~280줄

```typescript
describe('InterestCalculator.calculateMonthlyPayment()', () => {
  
  describe('기본 계산 로직', () => {
    it('[T-I001] 원금 3억, 이율 3%, 기간 20년 = 월 1,426,000원', async () => {
      const result = await calculateMonthlyPayment({
        principal: 300000000,
        rate: 3.0,
        term: 240
      });
      expect(result.monthlyPayment).toBeCloseTo(1426000, -3);
    });
    
    it('[T-I002] 이율이 높을수록 월 납부금 증가', async () => {
      const low = await calculateMonthlyPayment({
        principal: 300000000, rate: 2.0, term: 240
      });
      const high = await calculateMonthlyPayment({
        principal: 300000000, rate: 4.0, term: 240
      });
      expect(high.monthlyPayment).toBeGreaterThan(low.monthlyPayment);
    });
    
    it('[T-I003] 기간이 길수록 월 납부금 감소, 총액 증가', async () => {
      const short = await calculateMonthlyPayment({
        principal: 300000000, rate: 3.0, term: 180
      });
      const long = await calculateMonthlyPayment({
        principal: 300000000, rate: 3.0, term: 240
      });
      expect(long.monthlyPayment).toBeLessThan(short.monthlyPayment);
      expect(long.totalPayment).toBeGreaterThan(short.totalPayment);
    });
  });
  
  describe('특수 조건', () => {
    it('[T-I101] 0% 이율: 월납부 = 원금 / 기간', async () => {
      const result = await calculateMonthlyPayment({
        principal: 300000000, rate: 0, term: 240
      });
      expect(result.monthlyPayment).toBeCloseTo(1250000, -3);
      expect(result.totalInterest).toBe(0);
    });
    
    it('[T-I102] 극도로 높은 이율(20%): 계산 정상 동작', async () => {
      const result = await calculateMonthlyPayment({
        principal: 100000000, rate: 20.0, term: 60
      });
      expect(Number.isFinite(result.monthlyPayment)).toBe(true);
      expect(result.monthlyPayment).toBeGreaterThan(3000000);
    });
    
    it('[T-I103] 소수점 이율(3.25%, 2.875%)', async () => {
      const r325 = await calculateMonthlyPayment({
        principal: 300000000, rate: 3.25, term: 240
      });
      const r287 = await calculateMonthlyPayment({
        principal: 300000000, rate: 2.875, term: 240
      });
      expect(r325.monthlyPayment).toBeGreaterThan(r287.monthlyPayment);
    });
    
    it('[T-I104] 비표준 기간(13개월, 121개월)', async () => {
      const r13 = await calculateMonthlyPayment({
        principal: 100000000, rate: 3.0, term: 13
      });
      const r121 = await calculateMonthlyPayment({
        principal: 100000000, rate: 3.0, term: 121
      });
      expect(r121.monthlyPayment).toBeLessThan(r13.monthlyPayment);
    });
  });
  
  describe('극단값 처리', () => {
    it('[T-I201] 초고액 대출(500억)', async () => {
      const result = await calculateMonthlyPayment({
        principal: 50000000000,
        rate: 3.0,
        term: 240
      });
      expect(result.monthlyPayment).toBeGreaterThan(200000000);
    });
    
    it('[T-I202] 초저액 대출(100만원)', async () => {
      const result = await calculateMonthlyPayment({
        principal: 1000000,
        rate: 5.0,
        term: 60
      });
      expect(result.monthlyPayment).toBeCloseTo(18870, -2);
    });
    
    it('[T-I203] 초단기(6개월)', async () => {
      const result = await calculateMonthlyPayment({
        principal: 100000000,
        rate: 3.0,
        term: 6
      });
      expect(result.monthlyPayment).toBeGreaterThan(16500000);
    });
    
    it('[T-I204] 초장기(30년=360개월)', async () => {
      const result = await calculateMonthlyPayment({
        principal: 300000000,
        rate: 3.0,
        term: 360
      });
      expect(result.monthlyPayment).toBeLessThan(1000000);
    });
  });
  
  describe('에러 처리', () => {
    it('[T-I301] 음수 원금', async () => {
      expect(async () => {
        await calculateMonthlyPayment({
          principal: -300000000, rate: 3.0, term: 240
        });
      }).rejects.toThrow('Principal must be positive');
    });
    
    it('[T-I302] 음수 이율', async () => {
      expect(async () => {
        await calculateMonthlyPayment({
          principal: 300000000, rate: -3.0, term: 240
        });
      }).rejects.toThrow('Rate must be non-negative');
    });
    
    it('[T-I303] 기간 0개월', async () => {
      expect(async () => {
        await calculateMonthlyPayment({
          principal: 300000000, rate: 3.0, term: 0
        });
      }).rejects.toThrow('Term must be at least 1 month');
    });
  });
});
```

---

### 3.3 credit-assessment.spec.ts (6개 → 12-15개)

**파일 위치**: `src/services/credit-assessment.spec.ts`  
**최종 라인수**: ~220줄

```typescript
describe('CreditAssessment.assessCreditWorthiness()', () => {
  
  describe('기본 승인 로직', () => {
    it('[T-C001] 양호 신용도: 부채비율 30%, 신용점수 800 = 승인', async () => {
      const result = await assessCreditWorthiness({
        income: 10000000,
        debt: 3000000,
        creditScore: 800,
        assets: 500000000
      });
      expect(result.approved).toBe(true);
      expect(result.recommendation).toBe('APPROVED');
    });
    
    it('[T-C002] 부채비율 높음(60% > 50%): 미승인', async () => {
      const result = await assessCreditWorthiness({
        income: 10000000,
        debt: 6000000,
        creditScore: 800,
        assets: 500000000
      });
      expect(result.approved).toBe(false);
    });
    
    it('[T-C003] 신용점수 낮음(600 < 650): 미승인', async () => {
      const result = await assessCreditWorthiness({
        income: 10000000,
        debt: 2000000,
        creditScore: 600,
        assets: 500000000
      });
      expect(result.approved).toBe(false);
    });
    
    it('[T-C004] 조건부 승인: 부채비율 40%, 신용점수 750', async () => {
      const result = await assessCreditWorthiness({
        income: 10000000,
        debt: 4000000,
        creditScore: 750,
        assets: 500000000
      });
      expect(result.recommendation).toBe('CONDITIONAL');
    });
  });
  
  describe('자산 기반 대출 한도', () => {
    it('[T-C101] 자산 5억 → 최대 대출금 4억(80%)', async () => {
      const result = await assessCreditWorthiness({
        income: 10000000,
        debt: 1000000,
        creditScore: 800,
        assets: 500000000
      });
      expect(result.maxLoanAmount).toBe(400000000);
    });
    
    it('[T-C102] 자산 없음(0원): 대출 불가', async () => {
      expect(async () => {
        await assessCreditWorthiness({
          income: 10000000,
          debt: 1000000,
          creditScore: 800,
          assets: 0
        });
      }).rejects.toThrow();
    });
    
    it('[T-C103] 자산 10억: 최대 대출금 8억', async () => {
      const result = await assessCreditWorthiness({
        income: 10000000,
        debt: 1000000,
        creditScore: 800,
        assets: 1000000000
      });
      expect(result.maxLoanAmount).toBe(800000000);
    });
  });
  
  describe('소수점 신용점수', () => {
    it('[T-C201] 신용점수 650.5 (경계값 직상): 승인', async () => {
      const result = await assessCreditWorthiness({
        income: 10000000,
        debt: 2000000,
        creditScore: 650.5,
        assets: 500000000
      });
      expect(result.approved).toBe(true);
    });
    
    it('[T-C202] 신용점수 799.9 vs 800.0', async () => {
      const r799 = await assessCreditWorthiness({
        income: 10000000, debt: 2000000, creditScore: 799.9, assets: 500000000
      });
      const r800 = await assessCreditWorthiness({
        income: 10000000, debt: 2000000, creditScore: 800.0, assets: 500000000
      });
      // 두 경우 모두 승인이지만 기본값은 다를 수 있음
      expect(r799.approved).toBeDefined();
      expect(r800.approved).toBeDefined();
    });
  });
  
  describe('부채비율 변동 시나리오', () => {
    it('[T-C301] 월급여 1000만원, 부채 100만원 = 10%', async () => {
      const result = await assessCreditWorthiness({
        income: 10000000,
        debt: 1000000,
        creditScore: 800,
        assets: 500000000
      });
      expect(result.debtRatioPercent).toBe(10);
    });
    
    it('[T-C302] 실제 부채 증가 시나리오: 50% → 60%', async () => {
      const before = await assessCreditWorthiness({
        income: 10000000,
        debt: 5000000,
        creditScore: 750,
        assets: 500000000
      });
      const after = await assessCreditWorthiness({
        income: 10000000,
        debt: 6000000,
        creditScore: 750,
        assets: 500000000
      });
      expect(before.approved).toBe(true);
      expect(after.approved).toBe(false);
    });
  });
  
  describe('에러 처리', () => {
    it('[T-C401] 월급여 0원', async () => {
      expect(async () => {
        await assessCreditWorthiness({
          income: 0,
          debt: 1000000,
          creditScore: 800,
          assets: 500000000
        });
      }).rejects.toThrow('Income must be positive');
    });
    
    it('[T-C402] 음수 부채', async () => {
      expect(async () => {
        await assessCreditWorthiness({
          income: 10000000,
          debt: -1000000,
          creditScore: 800,
          assets: 500000000
        });
      }).rejects.toThrow();
    });
  });
});
```

---

### 3.4 document-validator.spec.ts (4개 → 8-10개)

**파일 위치**: `src/services/document-validator.spec.ts`  
**최종 라인수**: ~150줄

```typescript
describe('DocumentValidator.validateDocuments()', () => {
  
  describe('파일 유형 검증', () => {
    it('[T-D001] PDF 파일 통과', async () => {
      const file = new File(['%PDF-1.4'], 'contract.pdf', { type: 'application/pdf' });
      const result = await validateDocuments([file]);
      expect(result.allValid).toBe(true);
      expect(result.validations[0].valid).toBe(true);
    });
    
    it('[T-D002] JPEG 이미지 통과', async () => {
      const file = new File([...], 'id.jpg', { type: 'image/jpeg' });
      const result = await validateDocuments([file]);
      expect(result.allValid).toBe(true);
    });
    
    it('[T-D003] PNG 이미지 통과', async () => {
      const file = new File([...], 'passport.png', { type: 'image/png' });
      const result = await validateDocuments([file]);
      expect(result.allValid).toBe(true);
    });
    
    it('[T-D004] 지원하지 않는 유형 거부(EXE)', async () => {
      const file = new File([...], 'virus.exe', { type: 'application/x-msdownload' });
      const result = await validateDocuments([file]);
      expect(result.allValid).toBe(false);
      expect(result.validations[0].errors).toContain('Unsupported file type');
    });
  });
  
  describe('파일 크기 검증', () => {
    it('[T-D101] 빈 파일(0바이트) 거부', async () => {
      const file = new File([], 'empty.pdf', { type: 'application/pdf' });
      const result = await validateDocuments([file]);
      expect(result.allValid).toBe(false);
      expect(result.validations[0].errors).toContain('Empty file');
    });
    
    it('[T-D102] 정상 크기 파일(1-50MB)', async () => {
      const data = new Uint8Array(5000000); // 5MB
      const file = new File([data], 'large.pdf', { type: 'application/pdf' });
      const result = await validateDocuments([file]);
      expect(result.allValid).toBe(true);
    });
    
    it('[T-D103] 초과 크기 파일(>50MB) 거부', async () => {
      const data = new Uint8Array(60000000); // 60MB
      const file = new File([data], 'huge.pdf', { type: 'application/pdf' });
      const result = await validateDocuments([file]);
      expect(result.allValid).toBe(false);
      expect(result.validations[0].errors).toContain('File size exceeds 50MB');
    });
  });
  
  describe('다중 파일 검증', () => {
    it('[T-D201] 3개 파일 모두 유효', async () => {
      const files = [
        new File(['%PDF-1.4'], 'contract.pdf', { type: 'application/pdf' }),
        new File([...], 'id.jpg', { type: 'image/jpeg' }),
        new File([...], 'passport.png', { type: 'image/png' })
      ];
      const result = await validateDocuments(files);
      expect(result.allValid).toBe(true);
      expect(result.validations).toHaveLength(3);
    });
    
    it('[T-D202] 1개 파일 무효 → 전체 무효', async () => {
      const files = [
        new File(['%PDF-1.4'], 'contract.pdf', { type: 'application/pdf' }),
        new File([], 'empty.pdf', { type: 'application/pdf' })
      ];
      const result = await validateDocuments(files);
      expect(result.allValid).toBe(false);
      expect(result.validations[1].valid).toBe(false);
    });
  });
});
```

---

## 4. Mock 데이터 Fixture

### 4.1 test/fixtures/loans.json

```json
{
  "products": [
    {
      "id": "prime-loan-1",
      "name": "프리미엄 전월세",
      "type": "premium",
      "minCreditScore": 800,
      "rate": 2.5,
      "maxAmount": 500000000,
      "term": [120, 240],
      "propertyTypes": ["아파트", "오피스텔"],
      "requirements": {
        "minIncome": 30000000,
        "maxDebtRatio": 0.3
      }
    },
    {
      "id": "standard-loan-1",
      "name": "표준 전세",
      "type": "standard",
      "minCreditScore": 700,
      "rate": 3.2,
      "maxAmount": 300000000,
      "term": [120, 180, 240],
      "propertyTypes": ["아파트", "원룸", "오피스텔"],
      "requirements": {
        "minIncome": 15000000,
        "maxDebtRatio": 0.5
      }
    },
    {
      "id": "conditional-loan-1",
      "name": "조건부 대출",
      "type": "conditional",
      "minCreditScore": 650,
      "rate": 4.5,
      "maxAmount": 150000000,
      "term": [60, 120, 180],
      "propertyTypes": ["원룸", "전세방"],
      "requirements": {
        "minIncome": 8000000,
        "maxDebtRatio": 0.6,
        "additionalReview": true
      }
    },
    {
      "id": "commercial-loan-1",
      "name": "상가 담보 대출",
      "type": "commercial",
      "minCreditScore": 750,
      "rate": 4.8,
      "maxAmount": 2000000000,
      "term": [120, 180, 240],
      "propertyTypes": ["상가", "오피스"],
      "requirements": {
        "minIncome": 50000000,
        "maxDebtRatio": 0.4,
        "commercialLicense": true
      }
    }
  ]
}
```

### 4.2 test/fixtures/credit-scores.json

```json
{
  "scores": [
    {
      "name": "Excellence (900+)",
      "minScore": 900,
      "description": "매우 우수한 신용도"
    },
    {
      "name": "Grade A (800-899)",
      "minScore": 800,
      "description": "우수한 신용도"
    },
    {
      "name": "Grade B (700-799)",
      "minScore": 700,
      "description": "양호한 신용도"
    },
    {
      "name": "Grade C (650-699)",
      "minScore": 650,
      "description": "보통 신용도 (조건부)"
    },
    {
      "name": "Grade D (0-649)",
      "minScore": 0,
      "description": "신용도 부족"
    }
  ]
}
```

### 4.3 test/fixtures/documents.json

```json
{
  "validTypes": [
    {
      "type": "application/pdf",
      "extension": ".pdf",
      "name": "PDF"
    },
    {
      "type": "image/jpeg",
      "extension": ".jpg",
      "name": "JPEG"
    },
    {
      "type": "image/png",
      "extension": ".png",
      "name": "PNG"
    }
  ],
  "limits": {
    "maxFileSize": 52428800,
    "maxFileCount": 10,
    "totalMaxSize": 500000000
  },
  "samples": {
    "validPdf": {
      "content": "%PDF-1.4\n%âãÏó\n1 0 obj\n",
      "filename": "contract.pdf",
      "type": "application/pdf"
    },
    "validJpeg": {
      "content": "JPEG_HEADER_BYTES",
      "filename": "id.jpg",
      "type": "image/jpeg"
    }
  }
}
```

---

## 5. Vitest 최종 설정

### 5.1 vitest.config.ts (수정)

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@services': path.resolve(__dirname, './src/services'),
      '@types': path.resolve(__dirname, './src/types'),
      '@fixtures': path.resolve(__dirname, './test/fixtures'),
      '@mocks': path.resolve(__dirname, './test/mocks'),
    }
  },
  
  test: {
    // 환경
    environment: 'happy-dom',
    globals: true,
    
    // 커버리지 임계치 (Phase 2: 40%)
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov', 'text-summary'],
      
      // 절대값 (%)
      lines: 40,
      functions: 40,
      branches: 35,    // 조건문 복잡도 높아서 5% 완화
      statements: 40,
      
      // 파일별 요구사항
      perFile: true,
      
      exclude: [
        'node_modules/',
        'dist/',
        '**/*.spec.ts',
        '**/*.test.ts',
        '**/fixtures/',
        '**/mocks/',
        'src/main.ts',
        'src/index.html'
      ],
      
      // 상세 리포트
      all: true,
      skipFull: false,
      lines: 40,
    },
    
    // 테스트 파일 패턴
    include: ['src/**/*.{spec,test}.ts', 'test/**/*.{spec,test}.ts'],
    exclude: ['node_modules', 'dist', '.idea', '.git', '.cache'],
    
    // 세트업 파일
    setupFiles: ['./test/setup.ts'],
    
    // 병렬 실행
    threads: true,
    maxThreads: 4,
    minThreads: 1,
    
    // 타임아웃
    testTimeout: 10000,
    hookTimeout: 10000,
    
    // 로깅
    reporter: ['default', 'html'],
    outputFile: {
      html: './coverage/index.html',
    },
    
    // 변경 감지 모드
    watch: process.env.CI !== 'true',
  }
});
```

### 5.2 package.json (scripts 수정)

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest run --coverage",
    "test:watch": "vitest watch",
    "test:debug": "vitest --inspect-brk --inspect --single-thread",
    "test:d09": "vitest run src/services/loan-service.spec.ts src/services/interest-calculator.spec.ts --coverage",
    "test:ci": "vitest run --coverage --reporter=junit --outputFile=test-results.xml"
  }
}
```

---

## 6. 팀 협업 & 코드 리뷰 가이드

### 6.1 Pair Programming 규칙

**언제**: credit-assessment.spec.ts 작성 (신용도 로직 복잡도 높음)

**진행 방식**:
- 운전자(Driver): FE Dev #1 (코드 작성)
- 항법자(Navigator): QA Lead (로직 검증, 실수 지적)
- 15분마다 교대

**체크리스트**:
```
□ 금융 로직 정확성 (부채비율 계산식 검증)
□ 엣지 케이스 포함 (부채 0, 신용도 경계값 등)
□ Mock API 응답 일관성
□ 테스트 네이밍 (T-CXXX 패턴)
□ 코드 가독성 (주석, 변수명)
```

### 6.2 PR 리뷰 체크리스트

**리뷰어**: FE Lead + QA Lead

```markdown
## Test Implementation Review

### Coverage
- [ ] Loan-service.spec.ts 커버리지 > 45%
- [ ] Interest-calculator.spec.ts > 50%
- [ ] Credit-assessment.spec.ts > 45%
- [ ] Document-validator.spec.ts > 40%
- [ ] 전체 평균 > 40%

### Test Quality
- [ ] 각 테스트는 하나의 동작만 검증
- [ ] AAA 패턴 준수 (Arrange, Act, Assert)
- [ ] 테스트명이 명확 (T-XXXX 형식)
- [ ] 모킹이 적절 (외부 API만)
- [ ] 엣지 케이스 포함 (경계값, 0, 음수, null 등)

### Code Quality
- [ ] TypeScript strict mode 통과
- [ ] ESLint/Biome 통과 (npm run lint)
- [ ] 중복 코드 없음
- [ ] 함수 길이 < 30줄
- [ ] 복잡도 < 10 (cyclomatic)

### CI/CD
- [ ] npm run test:coverage 통과
- [ ] GitHub Actions 모든 job green
- [ ] 시간 < 5초 (전체 테스트 수행)

### Documentation
- [ ] 각 테스트 파일에 주석 있음
- [ ] README.md 업데이트됨
- [ ] Fixture 변경 사항 기록됨
```

---

## 7. CI/CD 통합

### 7.1 .github/workflows/test-d09.yml (신규)

```yaml
name: D09 Unit Tests

on:
  push:
    branches: [develop, main]
    paths:
      - 'src/services/**'
      - 'test/**'
      - 'package.json'
      - '.github/workflows/test-d09.yml'
  pull_request:
    branches: [develop, main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        node-version: [18.x, 20.x]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm run test:coverage
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
          flags: unit-tests-d09
          fail_ci_if_error: false
      
      - name: Coverage comment on PR
        if: github.event_name == 'pull_request'
        uses: romeovs/lcov-reporter-action@v0.3.1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          lcov-file: ./coverage/lcov.info
      
      - name: Check coverage threshold
        run: |
          coverage=$(grep -o '"lines":{[^}]*"pct":[0-9.]*' coverage/coverage-final.json | grep -o '[0-9.]*$')
          echo "Coverage: $coverage%"
          if (( $(echo "$coverage < 40" | bc -l) )); then
            echo "❌ Coverage below 40%"
            exit 1
          else
            echo "✅ Coverage meets 40% threshold"
          fi

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          cache: 'npm'
      - run: npm ci
      - run: npm run lint -- src/services/**/*.spec.ts
      
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          cache: 'npm'
      - run: npm ci
      - name: Measure test execution time
        run: |
          time npm run test:coverage
          # 예상: < 5초
```

---

## 8. 일일 체크리스트

### 📅 Week 3 월요일 (2026-07-15)

```
오전:
☐ vitest.config.ts 검토 및 수정
☐ test/setup.ts 작성 완료
☐ npm ci 확인
☐ npm run test -- --run 동작 확인 (0개 통과)

오후:
☐ test/fixtures/loans.json 작성
☐ test/mocks/handlers.ts GET /api/v1/loans/products 추가
☐ 모킹 동작 테스트
☐ commit: test(setup): vitest + MSW 초기 설정

체크:
✅ 정상 상태: npm run test 실행 → 0개 테스트 (설정 완료 신호)
```

### 📅 Week 3 화요일-수요일 (2026-07-16 ~ 07-17)

```
목표: loan-service.spec.ts 5개 테스트 완료

화요일:
☐ loan-service.spec.ts 뼈대 작성
☐ T-L001 ~ T-L004 테스트 구현
☐ npm run test:coverage 확인 (예상: 20%)
☐ 실패 테스트 디버깅

수요일:
☐ T-L005 테스트 추가
☐ 모든 테스트 pass 확인
☐ commit: test(D09): loan-service 5개 테스트 (20% 커버리지)

매일:
☐ npm run test (변경 감지 모드)
☐ 에러 수정 및 재실행
```

### 📅 주간 금요일 (주말 전)

```
정산:
☐ npm run test:coverage 최종 리포트 확인
☐ 커버리지 프로세스 문서에 기록
☐ 문제점 이슈 등록 (있으면)
☐ 다음주 준비물 점검
```

---

## 9. 예상 마일스톤 & 검증

| 주차 | 목표 | 테스트 수 | 커버리지 | 상태 |
|------|-----|---------|----------|------|
| Week 3 | 기초 설정 + 17개 | 17/40 | ~25% | ✅ Ready |
| Week 4 | 추가 10개 | 27/40 | ~30% | ✅ Ready |
| Week 5 | 엣지 케이스 13개 | 40/40 | ~40% | ✅ Ready |
| Week 6 | 최적화 + CI | 40/40 | ≥40% | ✅ Phase 2 완료 |

---

## 10. 트러블슈팅 가이드

### 문제: 테스트 타임아웃 (> 1초)

```bash
# 원인: Mock API 응답 지연 또는 계산 복잡도 높음
# 해결:
npm run test:debug  # 느린 부분 식별

# vitest.config.ts:
testTimeout: 10000  # 기본 10초
```

### 문제: 커버리지 40% 미만

```bash
# 원인: 엣지 케이스 미포함 또는 복잡도 높은 함수 누락
# 확인:
npm run test:coverage -- --reporter=html
# coverage/index.html 열어서 노란색(covered) 부분 확인

# 추가 테스트 작성: 미커버된 라인 +3줄마다 1개 테스트
```

### 문제: Mock API 응답 일관성 오류

```bash
# 원인: MSW 핸들러 순서 또는 캐싱
# 해결:
test/setup.ts:
afterEach(() => server.resetHandlers());  # 각 테스트마다 초기화
```

---

**작성자**: Claude (Code Assistant)  
**최종 검토**: QA Lead, FE Lead  
**승인 대기**: Engineering Manager
