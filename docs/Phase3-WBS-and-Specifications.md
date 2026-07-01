# Phase 3: Framework 마이그레이션 — WBS & 명세서

**작성일**: 2026-07-01  
**기간**: 12주 (2026-10-01 ~ 2027-01-31)  
**목표**: jQuery 완전 제거 + React 100% 마이그레이션  
**팀**: 5명 (60인주)  
**예산**: €150K

---

## 1. Phase 3 계층적 WBS (5단계)

```
PHASE 3: Framework 마이그레이션 (12주)
│
├─ [L1] PHASE 3 전체 (jQuery 제거, React 도입)
│   ├─ [L2] WEEK 1-2: 아키텍처 & 환경 (2주)
│   │   ├─ [L3] D24: Strangler Fig 설계
│   │   │   ├─ [L4] 24.1: 아키텍처 문서 (200줄)
│   │   │   ├─ [L4] 24.2: 마이그레이션 경로 (Tier 1-3)
│   │   │   └─ [L4] 24.3: 팀 아키텍처 리뷰 승인
│   │   │
│   │   ├─ [L3] D25: TypeScript 기초
│   │   │   ├─ [L4] 25.1: tsconfig.json (strict mode)
│   │   │   ├─ [L4] 25.2: src/types/* (모든 도메인)
│   │   │   ├─ [L4] 25.3: ESLint/Biome TypeScript 규칙
│   │   │   └─ [L4] 25.4: 타입 에러 0 달성
│   │   │
│   │   └─ [L3] D26: Biome + 개발 환경
│   │       ├─ [L4] 26.1: Vite 6 설정
│   │       ├─ [L4] 26.2: React 19 플러그인
│   │       ├─ [L4] 26.3: Code splitting 규칙
│   │       └─ [L4] 26.4: npm start (핫 리로드)
│   │
│   ├─ [L2] WEEK 3-7: Tier 1 지도/마커 (5주)
│   │   ├─ [L3] Tier 1 진행
│   │   │   ├─ [L4] Week 3: 컴포넌트 설계 & Story
│   │   │   │   ├─ [L5] MapContainer.tsx (100줄)
│   │   │   │   ├─ [L5] MarkerList.tsx (60줄)
│   │   │   │   ├─ [L5] PropertyDetail.tsx (50줄)
│   │   │   │   └─ [L5] 3개 Story 작성
│   │   │   ├─ [L4] Week 4: 페이지 통합 & 테스트
│   │   │   │   ├─ [L5] MapPage.tsx (80줄)
│   │   │   │   ├─ [L5] API 연동 (프록시)
│   │   │   │   └─ [L5] Unit 테스트 5개
│   │   │   ├─ [L4] Week 5: E2E & 배포
│   │   │   │   ├─ [L5] E2E 테스트 3개
│   │   │   │   ├─ [L5] 성능 최적화 (번들 < 50KB)
│   │   │   │   └─ [L5] 스테이징 배포
│   │   │   └─ [L4] Week 6-7: 정리 & 제거
│   │   │       ├─ [L5] map.js (jQuery) 삭제
│   │   │       ├─ [L5] 회귀 테스트
│   │   │       └─ [L5] Tier 1 완료
│   │   │
│   │   └─ [L3] 산출물
│   │       ├─ 3개 React 컴포넌트 (210줄)
│   │       ├─ MapPage 통합 (80줄)
│   │       ├─ E2E 테스트 3개
│   │       └─ jQuery map.js 완전 제거
│   │
│   ├─ [L2] WEEK 8-12: Tier 2 검색/필터 (5주)
│   │   ├─ [L3] Tier 2 진행
│   │   │   ├─ [L4] Week 8-9: 컴포넌트 (복잡한 상태관리)
│   │   │   │   ├─ [L5] SearchBar.tsx (80줄)
│   │   │   │   ├─ [L5] FilterPanel.tsx (120줄)
│   │   │   │   │   └─ ion.rangeSlider → HTML5 range
│   │   │   │   ├─ [L5] ResultsList.tsx (100줄)
│   │   │   │   └─ [L5] 3개 Story
│   │   │   ├─ [L4] Week 10-11: 상태 동기화 & E2E
│   │   │   │   ├─ [L5] Zustand/Context API 구현
│   │   │   │   ├─ [L5] E2E 테스트 5개
│   │   │   │   └─ [L5] 성능 검증
│   │   │   └─ [L4] Week 12: 정리 & ion.rangeSlider 제거
│   │   │
│   │   └─ [L3] 산출물
│   │       ├─ 4개 React 컴포넌트 (300줄)
│   │       ├─ E2E 테스트 5개
│   │       ├─ ion.rangeSlider 완전 제거
│   │       └─ SearchPage 통합
│   │
│   ├─ [L2] WEEK 13-18: Tier 3 거래흐름 (6주) ⭐ 가장 복잡
│   │   ├─ [L3] 금융로직 + 문서 처리
│   │   │   ├─ [L4] Week 13-14: 대출/거래 컴포넌트
│   │   │   │   ├─ [L5] LoanApplication.tsx (200줄)
│   │   │   │   ├─ [L5] TradeContract.tsx (180줄)
│   │   │   │   ├─ [L5] PaymentProcessing.tsx (150줄)
│   │   │   │   ├─ [L5] DocumentUpload.tsx (80줄)
│   │   │   │   │   └─ dropzone → react-dropzone
│   │   │   │   ├─ [L5] TypeScript 도메인 타입 (완전)
│   │   │   │   └─ [L5] 4개 Story
│   │   │   ├─ [L4] Week 15-16: 통합 & 플러그인 제거
│   │   │   │   ├─ [L5] TradeFlow.tsx (100줄)
│   │   │   │   ├─ [L5] dropzone 제거
│   │   │   │   ├─ [L5] metisMenu → React nav 대체
│   │   │   │   └─ [L5] Unit 테스트 15개
│   │   │   └─ [L4] Week 17-18: E2E & 배포
│   │   │       ├─ [L5] E2E 1개 (전체 거래 흐름)
│   │   │       ├─ [L5] 회귀 테스트
│   │   │       └─ [L5] 프로덕션 배포
│   │   │
│   │   └─ [L3] 산출물
│   │       ├─ 5개 React 컴포넌트 (710줄)
│   │       ├─ TradeFlow 통합 (100줄)
│   │       ├─ E2E 테스트 1개 (전체 흐름)
│   │       ├─ dropzone, metisMenu 완전 제거
│   │       └─ jQuery 런타임 완전 제거
│   │
│   └─ [L2] WEEK 19-24: jQuery 완전 제거 & 완성 (6주)
│       ├─ [L3] 모든 jQuery 제거
│       │   ├─ [L4] 모든 <script> 태그 정리
│       │   ├─ [L4] jQuery 런타임 제거 (npm uninstall jquery)
│       │   ├─ [L4] 모든 plugin 제거 완료 확인
│       │   └─ [L4] 번들 크기 최종 검증 (150KB 목표)
│       │
│       ├─ [L3] Storybook 문서화
│       │   ├─ [L4] 20개 이상 Story 작성
│       │   ├─ [L4] Design Token 통합
│       │   └─ [L4] npm run storybook 배포
│       │
│       ├─ [L3] 최종 통합 & 테스트
│       │   ├─ [L4] 모든 페이지 E2E 통과 (15개+)
│       │   ├─ [L4] 성능 최종 검증
│       │   ├─ [L4] 접근성 재스캔 (axe 0)
│       │   └─ [L4] 보안 감사
│       │
│       └─ [L3] v1.0.0 릴리스
│           ├─ [L4] 모든 변경사항 병합
│           ├─ [L4] 릴리스 노트 작성
│           ├─ [L4] 프로덕션 배포
│           └─ [L4] 모니터링 대시보드 확인
```

---

## 2. 델타 항목별 상세 명세서

### 📋 D05: jQuery CVE 노출 제거

| 항목 | 내용 |
|------|------|
| **목표** | CVE-2012-6708 노출 0 (jQuery v1.9.0 완전 제거) |
| **기간** | 12주 (지속적) |
| **검증** | npm list jquery → empty |
| **영향** | HIGH (보안) |

### 📋 D06: jQuery 모듈 완전 제거

| 항목 | 내용 |
|------|------|
| **현황** | 11개 jQuery 의존 JS 모듈 |
| **목표** | 모두 React 또는 Vanilla JS로 대체 |
| **대체 전략** | - Tier 1: 지도 JS → React MapContainer<br>- Tier 2: 검색 JS → React SearchBar<br>- Tier 3: 거래 JS → React TradeFlow<br>- 공통: common.js 삭제 가능 |
| **기간** | 12주 (지속적) |
| **검증** | grep -r "$..*\|jQuery" → 0건 |

### 📋 D07: jQuery 플러그인 3개 제거

| 플러그인 | 현황 | 대체 | 기간 |
|---------|------|------|------|
| **ion.rangeSlider** | 가격 필터 슬라이더 | HTML5 range input | Week 8-10 |
| **dropzone** | 파일 업로드 | react-dropzone | Week 14-15 |
| **metisMenu** | 좌측 메뉴 아코디언 | React Router + custom | Week 15-16 |

### 📋 D10: E2E 테스트 60%

| 지표 | 목표 | 검증 |
|------|------|------|
| **커버리지** | 60% | npm run e2e:coverage |
| **시나리오** | 15개 | Playwright 자동 리포트 |
| **회귀 테스트** | 0 failures | 모든 CI 통과 |

### 📋 D24: Strangler Fig 병행운영

| 항목 | 내용 |
|------|------|
| **기간** | 6개월 (2026-10-01 ~ 2027-03-31) |
| **전략** | Tier 1→2→3 단계 전환 |
| **검증** | 최종 jQuery 제거 후 모든 기능 동작 |
| **롤백** | Git tag로 이전 버전 복원 가능 |

### 📋 D25: TypeScript 도입

| 항목 | 내용 |
|------|------|
| **범위** | 금융도메인 우선 (loan, credit, trade, payment) |
| **strict mode** | 100% (모든 에러 제거) |
| **커버리지** | 타입 에러 0건 |
| **기간** | 2주 설정 + 12주 사용 |

### 📋 D26: Biome 자동화

| 항목 | 내용 |
|------|------|
| **도구** | Biome 2 (ESLint + Prettier 통합) |
| **적용** | Phase 1에서 기초 설정, Phase 3에서 React 규칙 추가 |
| **검증** | npm run lint → 0 warnings |

### 📋 D27: Storybook 컴포넌트 문서화

| 항목 | 내용 |
|------|------|
| **컴포넌트** | 20개 이상 (모든 주요 컴포넌트) |
| **Story** | 각 컴포넌트 3-5개 변형 (Default, Interactive, Mobile 등) |
| **배포** | npm run storybook:build → static site |
| **목표** | 새 팀원 온보딩 시 Storybook 참고 가능 |

---

## 3. WBS 매트릭스

| 시퀀스 | 델타 | 작업명 | 담당 | 기간 | 예산 | 의존성 |
|--------|------|--------|------|------|------|--------|
| 1 | D24 | Strangler Fig 설계 | Arch | 3d | €400 | 없음 |
| 2 | D25 | TypeScript 환경 | FE Lead | 5d | €600 | 1 |
| 3 | D26 | Vite + Biome 설정 | FE Dev #1 | 3d | €400 | 1-2 |
| 4 | - | 팀 Kickoff | All | 1d | - | 1-3 |
| 5-8 | Tier 1-3 | 병렬 마이그레이션 | 4명 | 42d | €105K | 4 |
| 9 | D05/06/07 | jQuery 플러그인 제거 | 3명 | 15d | €20K | 5-8 |
| 10 | D10 | E2E 60% 달성 | QA | 30d | €15K | 5-8 |
| 11 | D27 | Storybook 문서화 | 2명 | 10d | €8K | 5-8 |
| 12 | - | v1.0.0 릴리스 | All | 5d | €2K | 9-11 |

---

## 4. 간트 차트

### 📊 12주 진도

```
Week 1   [██░░░░░░░░░░░░░░░░░░░░] 8%
├─ D24 설계: [████░░░░░░░░░░░░░░░░░░]
├─ D25 TS 설정: [██████░░░░░░░░░░░░░░░░]
└─ D26 Vite 설정: [████░░░░░░░░░░░░░░░░░░]

Week 2   [████░░░░░░░░░░░░░░░░░░] 17%
├─ D25/D26 완료: [████████████░░░░░░░░░░]
└─ Kickoff: [█░░░░░░░░░░░░░░░░░░░░░]

Week 3-5 [████████░░░░░░░░░░░░░░] 33%
├─ Tier 1 MapContainer: [████░░░░░░░░░░░░░░░░░░]
├─ Tier 1 MarkerList: [████░░░░░░░░░░░░░░░░░░]
├─ Tier 1 E2E: [██░░░░░░░░░░░░░░░░░░░░]
└─ 병렬 Story 작성: [████░░░░░░░░░░░░░░░░░░]

Week 6-7 [██████░░░░░░░░░░░░░░░░] 50%
├─ Tier 1 완료: [████████████░░░░░░░░░░]
└─ jQuery map.js 제거: [████░░░░░░░░░░░░░░░░░░]

Week 8-10 [████████████░░░░░░░░░░] 67%
├─ Tier 2 SearchBar: [████░░░░░░░░░░░░░░░░░░]
├─ Tier 2 FilterPanel: [████░░░░░░░░░░░░░░░░░░]
├─ ion.rangeSlider 제거: [██░░░░░░░░░░░░░░░░░░░░]
└─ E2E 테스트 5개: [████░░░░░░░░░░░░░░░░░░]

Week 11-12 [██████████████░░░░░░░░] 80%
├─ Tier 2 완료: [████████░░░░░░░░░░░░░░]
└─ SearchPage 통합: [████░░░░░░░░░░░░░░░░░░]

Week 13-18 [████████████████░░░░░░] 95%
├─ Tier 3 대출/거래: [████░░░░░░░░░░░░░░░░░░]
├─ Tier 3 문서/결제: [████░░░░░░░░░░░░░░░░░░]
├─ dropzone → react-dropzone: [██░░░░░░░░░░░░░░░░░░░░]
├─ metisMenu → React nav: [██░░░░░░░░░░░░░░░░░░░░]
├─ TypeScript 완성: [████░░░░░░░░░░░░░░░░░░]
└─ E2E 1개 통합: [██░░░░░░░░░░░░░░░░░░░░]

Week 19-24 [██████████████████████] 100%
├─ 모든 jQuery 제거: [████░░░░░░░░░░░░░░░░░░]
├─ Storybook 20개 Story: [████░░░░░░░░░░░░░░░░░░]
├─ E2E 60% 달성: [████░░░░░░░░░░░░░░░░░░]
├─ 최종 통합테스트: [████░░░░░░░░░░░░░░░░░░]
└─ v1.0.0 릴리스: [████████████░░░░░░░░░░] ✅
```

---

## 5. 팀 할당 & 예산

### 👥 5명 팀 (60인주)

```
FE Lead (김은경): 7인주 (100%)
├─ Week 1-2: D24 아키텍처 설계 (1인주)
├─ Week 3-18: Tier 3 금융로직 (5인주)
└─ Week 19-24: 최종 검증 & 릴리스 (1인주)

FE Dev #1 (박준호): 8인주 (100%)
├─ Week 3-7: Tier 1 지도 (5인주)
└─ Week 8-12: Tier 2 검색 (3인주)

FE Dev #2 (이수진): 8인주 (100%)
├─ Week 3-7: Tier 1 Story & 성능 (2인주)
├─ Week 8-12: Tier 2 상태관리 & E2E (4인주)
└─ Week 13-18: Tier 3 지원 (2인주)

QA Lead (박정희): 4인주 (100%)
├─ Week 1-2: E2E 전략 (0.5인주)
├─ Week 3-24: 지속적 E2E 작성 & 검증 (3인주)
└─ Week 19-24: 최종 회귀테스트 (0.5인주)

Architect (이동욱): 3인주 (25%)
├─ Week 1-2: Strangler Fig 설계 (1.5인주)
├─ Week 3-12: 아키텍처 리뷰 (1인주)
└─ Week 13-24: TypeScript/성능 감독 (0.5인주)

────────────────
TOTAL: 30인주 실제 투입 (약 2.5명 × 12주)
```

### 💰 예산 상세

```
인건비: €140K
  - FE 3명: €84K (€2,500/주 × 12주)
  - QA 1명: €16K (€2,000/주 × 8주)
  - Architect 1명: €12K (€2,000/주 × 6주)

도구/인프라: €5K
  - Storybook 호스팅
  - RUM 대시보드 확장
  - 추가 개발 환경

학습/문서: €5K
  - React 19 교육
  - 마이그레이션 가이드 작성

────────────
합계: €150K
```

---

## 6. 의존성 & 리스크

### 🔗 Critical Path

```
Week 1-2: 아키텍처 설계 (필수)
    ↓
Week 3-7: Tier 1 (기초 확립) ⭐ 28일
    ↓
Week 8-12: Tier 2 (중복도 높음, 35일) ⭐ 가장 오래
    ↓
Week 13-18: Tier 3 (복잡도 높음, 42일) ⭐ 가장 복잡
    ↓
Week 19-24: jQuery 제거 & 릴리스 (30일)

총 Critical Path: Week 1-24 (12주, 모두 순차)
```

### 🚨 주요 리스크

| ID | 리스크 | 영향 | 대응 |
|----|--------|------|------|
| R1 | jQuery 플러그인 제거 복잡 | HIGH | 초기 PoC (1주) |
| R2 | TypeScript 타입 에러 많음 | MEDIUM | 점진적 적용 |
| R3 | E2E 테스트 플레이크 | MEDIUM | 재시도 메커니즘 |
| R4 | React 19 호환성 | LOW | 사전 테스트 |
| R5 | 성능 회귀 (번들 커짐) | MEDIUM | 번들 분석 도구 |

---

## 7. 성공 기준 (Go/No-Go)

### ✅ Phase 3 완료 조건

| 항목 | 기준 | 검증 |
|------|------|------|
| **D05** | jQuery CVE 제거 | npm list jquery → empty |
| **D06** | jQuery 모듈 제거 | grep "\..*\|jQuery" → 0건 |
| **D07** | 플러그인 3개 제거 | ion.range, dropzone, metisMenu 삭제 |
| **D10** | E2E 60% | npm run e2e:coverage ≥ 60 |
| **D24** | Strangler Fig | Tier 1-3 모두 완료 |
| **D25** | TypeScript strict | npm run type-check 에러 0 |
| **D26** | Biome | npm run lint 경고 0 |
| **D27** | Storybook | 20개 이상 Story |
| **v1.0.0** | 릴리스 | 프로덕션 배포 성공 |

### 🎯 주차별 Gate

```
Week 6 Gate:
├─ Tier 1 완료 ✓
├─ E2E 20% 달성 ✓
└─ Decision: Go (Week 7-12 진행) or No-Go

Week 12 Gate:
├─ Tier 2 완료 ✓
├─ E2E 40% 달성 ✓
├─ jQuery 플러그인 2개 제거 (ion.range, dropzone) ✓
└─ Decision: Go (Week 13-24 진행) or No-Go

Week 18 Gate:
├─ Tier 3 완료 ✓
├─ E2E 60% 달성 ✓
├─ 모든 jQuery 제거 ✓
└─ Decision: Go (v1.0.0 릴리스) or No-Go

Week 24 Gate (최종):
├─ v1.0.0 릴리스 ✓
├─ 모든 기능 정상 동작 ✓
├─ Storybook 배포 ✓
└─ CTO 최종 승인 → 프로덕션 배포
```

---

## 8. Phase 2 + Phase 3 누적 효과

### 📊 델타 감소 누적

```
초기상태 (Phase 1 완료): 94.5
    ↓
Phase 2 (45% 감소): 52
    ↓
Phase 3 (40% 감소): 12 ✅ 최종 목표

총 88% 기술부채 제거!
```

### 🏆 최종 상태

```
v1.0.0 (2027-01-31):
├─ jQuery: 0개 제거 ✓
├─ React: 100% 도입 ✓
├─ TypeScript: strict mode ✓
├─ 테스트: Unit 40% + E2E 60% = 100% ✓
├─ 번들 크기: 150KB ✓
├─ 성능: LCP < 1.2s ✓
├─ 접근성: WCAG 2.2 준수 ✓
├─ 보안: API 키 0 노출 ✓
└─ 문서: Storybook 20+ components ✓
```

---

**작성자**: Claude (Code Assistant)  
**검토 예정**: Architecture Lead, CTO  
**최종 승인**: 기술이사
