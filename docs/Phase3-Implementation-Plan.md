# Phase 3: Framework 마이그레이션 + jQuery 완전 제거 — 상세 구현 계획서

**작성일**: 2026-07-01  
**담당**: FE Lead (김은경) + Architect Lead (이동욱)  
**기간**: 12주 (2026-10-01 ~ 2027-01-31)  
**목표 델타**: 40% 감소 (52 → 12), jQuery 완전 제거  
**팀 규모**: 5명 (FE 3 + QA 1 + Architect 1)  
**예산**: €150K

---

## 📑 목차

1. Phase 3 비전 & 전략
2. Strangler Fig 아키텍처
3. Week별 상세 일정 (12주)
4. 각 Tier별 마이그레이션 상세
5. jQuery 플러그인 대체 전략
6. TypeScript 도입 계획
7. E2E 테스트 60% 달성
8. 리소스 할당 & 예산
9. 리스크 & 완화책

---

## 1. Phase 3 비전 & 전략

### 1.1 목표

```
현황:
├─ jQuery v1.9.0 (2013년, 13년 된 라이브러리)
├─ Bootstrap v5.1.3 (jQuery 없이 설계됨, 모순)
├─ 플러그인 3개 (ion.rangeSlider, dropzone, metisMenu)
├─ 테스트 60% 미달
└─ TypeScript 없음

6개월 후:
├─ React 19 Server Components로 완전 마이그레이션
├─ jQuery 0개 제거 (CVE-2012-6708 노출 완전 제거)
├─ 플러그인 3개 → HTML5 + React로 대체
├─ 단위테스트 40% + E2E 60% = 100% 커버리지
├─ TypeScript strict mode 적용 (금융도메인 타입안전성)
└─ Storybook 컴포넌트 문서화 완료
```

### 1.2 핵심 원칙: Strangler Fig 패턴

**왜 Strangler Fig인가?**
- Big Bang 마이그레이션은 위험 (jQuery 종속 플러그인 많음)
- 점진적 전환으로 회귀 테스트 가능
- 6개월 병행운영 중 문제 즉시 대응
- 최종 jQuery 제거는 신뢰도 높음

**패턴**:
```
초기 (2026-10-01):
├─ 레거시 jQuery 페이지 100% 운영
└─ React 개발 환경 준비

중기 (2026-11-01 ~ 2027-01-01):
├─ Tier 1 지도/마커 → React (10%)
├─ Tier 2 검색/필터 → React (30%)
├─ Tier 3 거래흐름 → React (60%)
└─ jQuery 단계적 축소

후기 (2027-01-31):
├─ jQuery 완전 제거
├─ React 100% 운영
└─ v1.0.0 릴리스
```

---

## 2. Strangler Fig 아키텍처

### 2.1 구조

```
┌─────────────────────────────────────────────────────────┐
│                    사용자 브라우저                         │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        v              v              v
   ┌─────────┐   ┌──────────┐   ┌──────────┐
   │ Legacy  │   │  New     │   │ Shared   │
   │ jQuery  │   │ React    │   │ Components
   │ (축소)  │   │ (성장)   │   │ (Bridge) │
   └─────────┘   └──────────┘   └──────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        v              v              v
   ┌──────────┐  ┌──────────┐  ┌────────────┐
   │ jQuery   │  │ React 19 │  │ Shared API │
   │ 런타임   │  │ 런타임   │  │ (프록시)   │
   └──────────┘  └──────────┘  └────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
                ┌──────────────┐
                │ API Gateway  │
                │ (D04 프록시) │
                └──────────────┘
```

### 2.2 마이그레이션 경로 (화면별)

```
Week 1-2:  아키텍처 설계 & 환경 구성
  ├─ Vite + React 19 + Astro 5 환경
  ├─ React 라우팅 (React Router v6)
  ├─ TypeScript 설정 (strict mode)
  └─ Storybook 초기화

Week 3-7:  Tier 1 지도/마커 마이그레이션 (가장 쉬움)
  ├─ React 컴포넌트 작성 (MapContainer, MarkerList)
  ├─ 상태 관리 (React useState, React Query)
  ├─ Astro Island 통합 (부분 하이드레이션)
  ├─ E2E 테스트 (Playwright 3개)
  └─ jQuery 코드 제거 (map.js 삭제)

Week 8-12: Tier 2 검색/필터 마이그레이션 (복잡도 중)
  ├─ SearchBar, FilterPanel, ResultsList (React)
  ├─ ion.rangeSlider → HTML5 <input type="range">
  ├─ 상태 동기화 (Zustand 또는 Context API)
  ├─ E2E 테스트 (Playwright 5개)
  └─ 레거시 필터 코드 제거

Week 13-18: Tier 3 거래흐름 마이그레이션 (가장 복잡)
  ├─ LoanApplication, TradeContract, PaymentProcessing (React)
  ├─ TypeScript 도메인 타입 (Loan, Trade, Payment)
  ├─ dropzone → react-dropzone (파일 업로드)
  ├─ 금융 로직 통합 (Phase 2 테스트 활용)
  ├─ E2E 테스트 (Playwright 전체 거래 흐름)
  └─ 오래된 거래 코드 제거

Week 19-24: jQuery 플러그인 제거 & 완성
  ├─ metisMenu → React Router + custom nav
  ├─ 모든 <script> 태그 정리
  ├─ jQuery 런타임 완전 제거
  ├─ 번들 크기 최종 검증 (150KB 목표)
  └─ v1.0.0 릴리스 준비
```

---

## 3. Week별 상세 일정

### 📅 Week 1-2: 아키텍처 설계 & 환경 (2026-10-01 ~ 2026-10-14)

#### 주요 산출물

**2.1 Strangler Fig 아키텍처 문서**
```markdown
docs/Phase3-Architecture.md (200줄)
├─ 마이그레이션 경로 정의 (Tier 1-3)
├─ 컴포넌트 간 통신 (Props drilling, Context, React Query)
├─ 번들 전략 (code splitting, dynamic import)
└─ 데이터 흐름 (API 프록시, 상태 관리)
```

**2.2 환경 설정**
```
vite.config.ts
├─ Vite 6 설정 (번들러)
├─ React 19 플러그인 추가
├─ Code splitting 규칙
│  ├─ pages/*/index.tsx → 자동 청크
│  └─ shared/components → 공유 청크
└─ Astro 5 통합 (부분 하이드레이션)

tsconfig.json
├─ strict: true (모든 타입 검사 활성화)
├─ noImplicitAny: true
├─ strictNullChecks: true
└─ lib: ["ES2021", "DOM", "DOM.Iterable"]

src/types/
├─ loan.ts (Loan, LoanProduct, LoanFilter)
├─ credit.ts (CreditScore, CreditAssessment)
├─ trade.ts (TradeContract, TradeParty)
├─ payment.ts (Payment, PaymentMethod)
└─ property.ts (Property, PropertyMarker)
```

**2.3 Storybook 초기화**
```bash
npx storybook@latest init

.storybook/
├─ main.ts (메타 설정)
├─ preview.ts (글로벌 데코레이터)
└─ manager.ts (사이드바 커스터마이징)

src/components/
├─ Button.stories.tsx (예시)
└─ ...
```

**2.4 라우팅 설계**
```typescript
// src/App.tsx
<BrowserRouter>
  <Routes>
    {/* Legacy (단계적 제거) */}
    <Route path="/old/*" element={<LegacyPageWrapper />} />
    
    {/* New React 페이지 */}
    <Route path="/map" element={<MapPage />} />
    <Route path="/search" element={<SearchPage />} />
    <Route path="/trade/*" element={<TradeFlow />} />
    
    {/* 404 */}
    <Route path="*" element={<NotFound />} />
  </Routes>
</BrowserRouter>
```

#### 주간 산출물 체크리스트

```
월: 아키텍처 설계 리뷰
  ☐ Strangler Fig 다이어그램 검토
  ☐ Tier 1-3 화면 우선순위 확정
  ☐ 팀 아키텍처 설계 승인

화-수: 환경 구성
  ☐ npm install (Vite 6, React 19, Astro 5, Storybook)
  ☐ vite.config.ts + tsconfig.json 완성
  ☐ src/types/* 모든 도메인 타입 정의
  ☐ .github/workflows/build.yml (빌드 파이프라인)

목-금: 라우팅 & 통합
  ☐ React Router 설정 (path routing)
  ☐ Storybook 실행 확인
  ☐ 개발 서버 npm start (Vite 핫 리로드)
  ☐ TypeScript strict mode 통과 (에러 0)
```

**예상 완료 상태**: 
- ✅ 개발 환경 구성 100%
- ✅ 도메인 타입 정의 100%
- ✅ Tier 1 개발 준비 완료

---

### 📅 Week 3-7: Tier 1 지도/마커 마이그레이션 (2026-10-15 ~ 2026-11-18)

#### 3.1 컴포넌트 설계

**MapContainer.tsx** (지도 표시)
```typescript
interface MapContainerProps {
  center?: [lat: number, lng: number];
  zoom?: number;
  onMarkerClick?: (marker: PropertyMarker) => void;
}

const MapContainer: React.FC<MapContainerProps> = ({
  center = [37.5, 126.9],
  zoom = 13,
  onMarkerClick
}) => {
  const [markers, setMarkers] = useState<PropertyMarker[]>([]);
  const mapRef = useRef<kakao.maps.Map>(null);
  
  useEffect(() => {
    // 지도 초기화
    const map = new kakao.maps.Map(mapRef.current, {
      center: new kakao.maps.LatLng(center[0], center[1]),
      level: zoom
    });
    mapRef.current = map;
    
    // 마커 렌더링
    markers.forEach(marker => {
      new kakao.maps.Marker({
        position: new kakao.maps.LatLng(marker.lat, marker.lng),
        title: marker.title,
        map: map,
        onClick: () => onMarkerClick?.(marker)
      });
    });
  }, [markers, center, zoom]);
  
  return <div ref={mapRef} style={{ width: '100%', height: '500px' }} />;
};
```

**MarkerList.tsx** (목록 표시)
```typescript
interface MarkerListProps {
  markers: PropertyMarker[];
  selectedId?: string;
  onSelect: (id: string) => void;
}

const MarkerList: React.FC<MarkerListProps> = ({
  markers,
  selectedId,
  onSelect
}) => {
  return (
    <ul className="marker-list">
      {markers.map(marker => (
        <li
          key={marker.id}
          className={selectedId === marker.id ? 'selected' : ''}
          onClick={() => onSelect(marker.id)}
        >
          {marker.title} - {marker.address}
        </li>
      ))}
    </ul>
  );
};
```

**PropertyDetail.tsx** (상세 팝업)
```typescript
interface PropertyDetailProps {
  property: Property;
  onClose: () => void;
}

const PropertyDetail: React.FC<PropertyDetailProps> = ({
  property,
  onClose
}) => {
  return (
    <div className="detail-popup">
      <h2>{property.name}</h2>
      <p>{property.address}</p>
      <p>가격: {property.price.toLocaleString()}원</p>
      <p>면적: {property.area}m²</p>
      <button onClick={onClose}>닫기</button>
    </div>
  );
};
```

#### 3.2 페이지 통합

**pages/MapPage.tsx**
```typescript
export default function MapPage() {
  const [markers, setMarkers] = useState<PropertyMarker[]>([]);
  const [selectedMarker, setSelectedMarker] = useState<PropertyMarker | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // 마커 데이터 로드 (API 프록시 사용)
    setLoading(true);
    fetch('/api/v1/map/markers')
      .then(r => r.json())
      .then(data => setMarkers(data.markers))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="map-page">
      <h1>부동산 지도</h1>
      <div className="map-layout">
        <div className="map-container">
          {loading ? <p>로딩 중...</p> : <MapContainer 
            onMarkerClick={setSelectedMarker} 
          />}
        </div>
        <div className="sidebar">
          <MarkerList 
            markers={markers}
            selectedId={selectedMarker?.id}
            onSelect={(id) => {
              const marker = markers.find(m => m.id === id);
              setSelectedMarker(marker || null);
            }}
          />
        </div>
      </div>
      {selectedMarker && (
        <PropertyDetail 
          property={selectedMarker.property}
          onClose={() => setSelectedMarker(null)}
        />
      )}
    </div>
  );
}
```

#### 3.3 E2E 테스트

**e2e/tier1-map.spec.ts**
```typescript
import { test, expect } from '@playwright/test';

test.describe('Tier 1: 지도 & 마커', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/map');
  });

  test('마커가 지도에 표시된다', async ({ page }) => {
    // Kakaos Maps SDK로 렌더링되는 마커 확인
    const map = page.locator('.kakaomap-container');
    await expect(map).toBeVisible();
    
    // 마커 개수 확인
    const markerElements = page.locator('[data-testid="map-marker"]');
    const count = await markerElements.count();
    expect(count).toBeGreaterThan(0);
  });

  test('마커 클릭 시 상세 팝업 표시', async ({ page }) => {
    const firstMarker = page.locator('[data-testid="map-marker"]').first();
    await firstMarker.click();
    
    const popup = page.locator('.detail-popup');
    await expect(popup).toBeVisible();
    
    // 팝업 내용 검증
    const title = await popup.locator('h2').textContent();
    expect(title).toBeTruthy();
  });

  test('목록에서 항목 선택 시 마커 강조', async ({ page }) => {
    const firstItem = page.locator('.marker-list li').first();
    await firstItem.click();
    
    // 선택된 항목에 'selected' 클래스 확인
    await expect(firstItem).toHaveClass(/selected/);
  });
});
```

#### 3.4 주간 체크리스트

```
Week 3 (10/15-10/21):
  ☐ MapContainer.tsx 완성 (100줄) + Story 작성
  ☐ MarkerList.tsx 완성 (60줄) + Story
  ☐ PropertyDetail.tsx 완성 (50줄) + Story
  ☐ Storybook 3개 컴포넌트 확인
  ☐ TypeScript 에러 0

Week 4 (10/22-10/28):
  ☐ MapPage.tsx 통합 (80줄)
  ☐ API 연동 (프록시 확인)
  ☐ 로컬 개발 서버 정상 동작
  ☐ Unit 테스트 (Vitest) 5개 작성

Week 5 (10/29-11/04):
  ☐ E2E 테스트 3개 작성 + 통과
  ☐ 성능 검증 (번들 크기 < 50KB)
  ☐ 메모리 누수 체크 (DevTools)
  ☐ 스테이징 배포 및 QA 검증

Week 6-7 (11/05-11/18):
  ☐ 회귀 테스트 (기존 지도 기능 동작)
  ☐ 레거시 jQuery 코드 제거 (map.js 삭제)
  ☐ 최종 리뷰 및 승인
  ☐ Tier 1 완료 보고
```

**예상 완료 상태**:
- ✅ Tier 1 React 전환 100%
- ✅ E2E 테스트 3개 통과
- ✅ jQuery 지도 코드 완전 제거
- ✅ 번들 크기 최적화 완료
- 📊 E2E 커버리지: ~20% (3/15 페이지)

---

### 📅 Week 8-12: Tier 2 검색/필터 마이그레이션 (2026-11-19 ~ 2026-12-23)

#### 주요 작업

**SearchBar & FilterPanel** (복잡한 상태 관리)
```typescript
interface SearchState {
  query: string;
  filters: {
    location?: string;
    priceMin?: number;
    priceMax?: number;
    propertyType?: string[];
    buildingYearMin?: number;
  };
  results: Property[];
  loading: boolean;
  error?: string;
}

const SearchPage: React.FC = () => {
  const [state, dispatch] = useReducer(searchReducer, initialState);
  
  // ion.rangeSlider → HTML5 <input type="range">
  const handlePriceChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const priceMin = parseInt(e.currentTarget.value);
    dispatch({ 
      type: 'SET_FILTER', 
      payload: { priceMin } 
    });
  };
  
  return (
    <div className="search-page">
      <SearchBar 
        value={state.query}
        onChange={(query) => dispatch({ type: 'SET_QUERY', payload: query })}
      />
      <FilterPanel 
        filters={state.filters}
        onPriceChange={handlePriceChange}
        // HTML5 range 슬라이더
      />
      <ResultsList 
        results={state.results}
        loading={state.loading}
      />
    </div>
  );
};
```

**ion.rangeSlider 대체**
```html
<!-- 기존: ion.rangeSlider jQuery 플러그인 -->
<input type="text" class="js-range-slider" data-type="double" ... />

<!-- 신규: HTML5 native range + React state -->
<div className="price-filter">
  <label>최소 가격: {state.filters.priceMin?.toLocaleString()}원</label>
  <input 
    type="range" 
    min="0" 
    max="1000000000" 
    step="100000"
    value={state.filters.priceMin || 0}
    onChange={handlePriceChange}
  />
  
  <label>최대 가격: {state.filters.priceMax?.toLocaleString()}원</label>
  <input 
    type="range" 
    min="0" 
    max="1000000000" 
    step="100000"
    value={state.filters.priceMax || 1000000000}
    onChange={handlePriceMax}
  />
</div>
```

#### 예상 산출물

- SearchBar.tsx (80줄)
- FilterPanel.tsx (120줄)
- ResultsList.tsx (100줄)
- SearchPage.tsx (150줄)
- E2E 테스트 5개 (200줄)
- **Tier 2 jQuery 코드 제거** (800줄 삭제)

---

### 📅 Week 13-18: Tier 3 거래흐름 마이그레이션 (2026-12-24 ~ 2027-01-31)

#### 3.3 복잡한 금융 로직 통합

**LoanApplication.tsx** (금융도메인 타입 활용)
```typescript
import { 
  LoanProduct, 
  CreditAssessment, 
  LoanFilter 
} from '@types';

interface LoanApplicationState {
  step: 'qualification' | 'selection' | 'documents' | 'confirmation';
  creditAssessment?: CreditAssessment;
  selectedProduct?: LoanProduct;
  documents: File[];
}

const LoanApplication: React.FC = () => {
  const [state, dispatch] = useReducer(
    loanApplicationReducer,
    initialState
  );
  
  // Phase 2 테스트에서 정의한 금융 로직 재사용
  const handleQualificationSubmit = async (data: {
    income: number;
    debt: number;
    creditScore: number;
    assets: number;
  }) => {
    const assessment = await assessCreditWorthiness(data);
    dispatch({ 
      type: 'SET_ASSESSMENT', 
      payload: assessment 
    });
  };
  
  return (
    <div className="loan-application">
      {state.step === 'qualification' && (
        <QualificationForm onSubmit={handleQualificationSubmit} />
      )}
      {state.step === 'selection' && (
        <ProductSelection 
          assessment={state.creditAssessment}
          onSelect={(product) => 
            dispatch({ type: 'SET_PRODUCT', payload: product })
          }
        />
      )}
      {/* ... */}
    </div>
  );
};
```

**dropzone → react-dropzone 대체**
```typescript
import { useDropzone } from 'react-dropzone';

const DocumentUpload: React.FC = () => {
  const { getRootProps, getInputProps, acceptedFiles } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  return (
    <div {...getRootProps()} className="dropzone">
      <input {...getInputProps()} />
      <p>파일을 드래그하거나 클릭하여 업로드</p>
      <ul>
        {acceptedFiles.map(file => (
          <li key={file.name}>{file.name}</li>
        ))}
      </ul>
    </div>
  );
};
```

#### 예상 산출물

- LoanApplication.tsx (200줄)
- TradeContract.tsx (180줄)
- PaymentProcessing.tsx (150줄)
- DocumentUpload.tsx (80줄)
- TradeFlow.tsx (통합, 100줄)
- E2E 테스트 1개 (전체 거래 흐름, 80줄)
- **Tier 3 jQuery + dropzone + metisMenu 제거** (1,200줄)

---

## 4. jQuery 플러그인 제거 전략

### 4.1 ion.rangeSlider 제거

**현황**: Tier 2에서 가격 필터링
**대체**: HTML5 `<input type="range">` + React 상태 관리
**기간**: Week 8-10 (Tier 2 진행 중)
**검증**: E2E 테스트 (필터 변경 → 결과 업데이트)

```typescript
// 제거 전 (jQuery 플러그인)
$(".js-range-slider").ionRangeSlider({
  type: "double",
  min: 0,
  max: 1000000000,
  from: 300000000,
  to: 500000000,
  onFinish: function(data) { updateResults(data); }
});

// 제거 후 (React 네이티브)
const [priceRange, setPriceRange] = useState({ min: 300000000, max: 500000000 });

useEffect(() => {
  updateResults(priceRange);
}, [priceRange]);
```

### 4.2 dropzone 제거

**현황**: 파일 업로드 (서류 검증)
**대체**: react-dropzone (가볍고 모던)
**기간**: Week 14-15 (Tier 3 진행 중)
**검증**: E2E 테스트 (파일 드래그 → 업로드)

```bash
# 제거
npm uninstall dropzone

# 추가
npm install react-dropzone
```

### 4.3 metisMenu 제거

**현황**: 좌측 네비게이션 메뉴 (아코디언)
**대체**: React Router + custom nav component
**기간**: Week 15-16
**검증**: E2E 테스트 (메뉴 클릭 → 페이지 이동)

```typescript
// 제거 후: React Navigation
interface NavItem {
  label: string;
  path: string;
  icon?: string;
  children?: NavItem[];
}

const Navigation: React.FC<{ items: NavItem[] }> = ({ items }) => {
  const [expanded, setExpanded] = useState<string[]>([]);
  
  return (
    <nav>
      {items.map(item => (
        <div key={item.path}>
          <Link to={item.path} onClick={() => {
            if (item.children) {
              setExpanded(prev => 
                prev.includes(item.path)
                  ? prev.filter(p => p !== item.path)
                  : [...prev, item.path]
              );
            }
          }}>
            {item.label}
          </Link>
          {item.children && expanded.includes(item.path) && (
            <ul>
              {item.children.map(child => (
                <li key={child.path}>
                  <Link to={child.path}>{child.label}</Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </nav>
  );
};
```

---

## 5. TypeScript 도입 계획

### 5.1 단계적 도입

**Phase 3 중점 (금융도메인)**:
```typescript
// src/types/finance.ts
export interface Loan {
  id: string;
  principal: number; // KRW
  rate: number; // annual %
  term: number; // months
  status: 'approved' | 'pending' | 'rejected' | 'completed';
  startDate: Date;
  endDate: Date;
}

export interface CreditAssessment {
  approved: boolean;
  score: number; // 0-999
  maxLoanAmount: number;
  debtRatioPercent: number;
  recommendation: 'APPROVED' | 'CONDITIONAL' | 'REJECTED';
}

export interface TradeContract {
  id: string;
  buyerId: string;
  sellerId: string;
  propertyId: string;
  amount: number; // KRW
  signatureDate: Date;
  status: 'draft' | 'signed' | 'completed' | 'cancelled';
  loanId?: string;
  witnesses?: string[]; // 증인 서명
}
```

**strict mode 위반 0**:
```bash
npm run type-check
# 출력: ✓ No errors found (모든 파일)
```

---

## 6. E2E 테스트 60% 달성

### 6.1 커버리지 계획

```
Week 3-7:   Tier 1 E2E (3개) = 20%
Week 8-12:  Tier 2 E2E (5개) = 40%
Week 13-18: Tier 3 E2E (1개 통합) = 60%

시나리오:
  1. 지도 표시 & 마커 클릭 (Tier 1)
  2. 검색 & 필터링 & 결과 조회 (Tier 2)
  3. 대출 신청 ~ 계약 ~ 결제 (Tier 3 전체)
  4. 문서 업로드 & 검증 (Tier 3)
  5. 모바일 반응형 (데스크톱 + 모바일)
  ... 총 15개 시나리오, 60% 달성
```

---

## 7. Storybook 문서화

### 7.1 컴포넌트 Story 작성

**MapContainer.stories.tsx**
```typescript
import type { Meta, StoryObj } from '@storybook/react';
import MapContainer from './MapContainer';

const meta = {
  title: 'Pages/MapContainer',
  component: MapContainer,
  parameters: { layout: 'fullscreen' }
} satisfies Meta<typeof MapContainer>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    center: [37.5, 126.9],
    zoom: 13
  }
};

export const HighZoom: Story = {
  args: {
    center: [37.5, 126.9],
    zoom: 18
  }
};
```

**총 20개 이상 Story** (모든 주요 컴포넌트)

---

## 8. 리소스 할당 & 예산

### 8.1 팀 구성 (5명, 60인주)

```
FE Lead (김은경)
├─ Tier 3 거래흐름 구현 (금융로직)
├─ TypeScript 검증
└─ 총 7인주 (100%)

FE Dev #1 (박준호)
├─ Tier 1 지도 (Week 3-7)
├─ Tier 2 검색 (Week 8-12)
└─ 총 8인주 (100%)

FE Dev #2 (이수진)
├─ Tier 2 필터링 & 상태 관리
├─ E2E 테스트 작성
└─ 총 8인주 (100%)

QA Lead (박정희)
├─ E2E 테스트 전략 수립
├─ 회귀 테스트 지휘
├─ 스토리북 검증
└─ 총 4인주 (100%)

Architect Lead (이동욱)
├─ Strangler Fig 설계 감독
├─ TypeScript 아키텍처 리뷰
├─ Week 1-2 아키텍처 설계
└─ 총 3인주 (25%)

────────────────────────
TOTAL: 30인주 (약 15명이 2주 동시 진행)
```

### 8.2 예산

```
인건비: €140K
  - FE 개발: €84K (3명 × €2,500 × 12주)
  - QA: €16K (1명 × €2,000 × 8주)
  - Architecture: €12K (1명 × €2,000 × 6주)

인프라: €5K
  - Storybook 호스팅
  - 추가 개발 환경 (기타)

학습/문서: €5K

────────────
합계: €150K
```

---

## 9. 주요 리스크

| ID | 리스크 | 영향 | 대응 |
|----|--------|------|------|
| R1 | jQuery 플러그인 의존성 복잡 | HIGH | 초기 3주 PoC |
| R2 | React 19 버전 호환성 | MEDIUM | 사전 테스트 |
| R3 | TypeScript 타입 커버리지 | MEDIUM | strict mode 강제 |
| R4 | E2E 테스트 플레이크성 | MEDIUM | Playwright 재시도 |
| R5 | 성능 회귀 (번들 커짐) | MEDIUM | 번들 분석 도구 |

---

**작성자**: Claude (Code Assistant)  
**검토 예정**: Architecture Lead, FE Lead  
**최종 승인**: CTO, 기술이사
