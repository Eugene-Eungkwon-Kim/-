# Phase 12 국제 시장 진출 상세 명세서
## Global Market Entry & International Expansion

**프로젝트**: Loan4U QC v1.1  
**기간**: 2026-07-01 ~ 2026-12-31 (6개월)  
**목표**: 글로벌 월 매출 3.46B ~ 5.0B 원 달성, 국제 사용자 1,500-2,000명 확보  
**우선순위**: 델타값 기반 (ROI/비용, 진출 난이도, 즉시성)

---

## Executive Summary

Phase 12는 Loan4U AVM을 **8개국 국제 시장**으로 확장하는 전략적 단계입니다.

### 기본 전략
```
1단계 (Month 1-3): Quick Win 3개국
   - 영국 (R²=0.90+, 월 4-6천만 원)
   - 싱가포르 (R²=0.90+, 월 2.5-4천만 원, Southeast Asia 거점)
   - 일본 (R²=0.90+, 월 5-7천만 원)

2단계 (Month 4-6): 확장 3개국
   - 독일 (월 4.5-6천만 원, EU 표준화)
   - 호주 (월 3.5-5천만 원)
   - 캐나다 (월 3-4.5천만 원)

3단계 (Month 7-12): 전략적 확장
   - 태국 (Southeast Asia 본격화, 월 1.5-2.5천만 원)
   - 홍콩 (East Asia 거점, 월 2.5-4천만 원)
```

### Phase 12 최종 성과
- **월 누적 매출**: 24,000-36,500만 원 (2.4-3.65억 원)
- **국제 B2B 파트너**: 25-30개 (국내 11개 + 국제 14-19개)
- **글로벌 활성 사용자**: 1,500-2,000명 (국내 480명 + 국제)
- **운영 국가**: 8개국
- **API 거래량**: 월 50-100만 건
- **평균 R² 점수**: 0.87 (국가별 0.82-0.92)

---

## Task 12.1: 영국 진출 (UK Market Entry)

### 1.1 목표 및 기대효과

| 항목 | 목표 | 측정 단위 |
|------|------|----------|
| 월 매출 | 4,000-6,000만 원 | 원/월 |
| 사용자 수 | 150-200명 | 활성 사용자 |
| B2B 파트너 | 3-5개 | 기관 |
| R² 점수 | 0.90+ | 모델 성능 |
| API 거래 | 월 8-12만 건 | 건/월 |
| 진출 기간 | 2-3개월 | 개월 |
| 개발 비용 | $200-250K | USD |

### 1.2 데이터 수집 및 전처리

#### 1.2.1 HM Land Registry API 연동
```python
API 엔드포인트:
- Official Copy Service: /api/property/{uprn}/official-copy
- Price Paid Data: /api/transactions/bulk?date_from=YYYY-MM-DD
- Property Address Data: /api/addresses/search?postcode=XX###XX

데이터 필드 (25개):
  - UPRN (Unique Property Reference Number)
  - Property Type (Detached/Semi/Terraced/Flat/Bungalow)
  - Address Components (Number, Road, Postcode)
  - Transaction Price & Date
  - Land Registry Title Details
  - Building Area (m²)
  - Number of Rooms
  - Council Tax Band
  - Local Authority
  - Latitude/Longitude
  - Distance to Station/School/Hospital
  - Council Tax Value
  - EPC Rating (Energy Performance Certificate)
  - Flood Risk Level
  - Listed Building Status
  - Conservation Area Status
  - Multiple Occupancy Status
  - Lease Term (years)
  - Ground Rent (£/년)
  
주간 업데이트 빈도: 매주 목요일 22:00 UTC
```

#### 1.2.2 추가 데이터소스 통합
```
1. Rightmove/Zoopla Price History API (선택적 상업용)
   - 3년 거래 이력
   - 유사 물건 비교 데이터

2. UK Land Value Assessments (정부 공개)
   - 지가 변동 추세
   - 지역별 가치 분포

3. Flood Risk Data Integration (Environment Agency)
   - 홍수 위험 지역 식별
   - 보험료 영향 분석

4. Schools/Amenities Data (Ordnance Survey)
   - 인근 학교 품질 등급
   - 공원, 병원, 쇼핑센터 거리
```

#### 1.2.3 데이터 품질 기준
```
결측값 처리:
  - Price Paid: <0.1% (필수 필드)
  - Building Area: <5% (중위값으로 보간)
  - Postcode: <0.05% (레코드 제거)
  
아웃라이어 탐지:
  - Price: IQR × 3배 규칙
  - Building Area: 10-500m² 범위
  - Ground Rent: 연 £0-5,000 범위
  
좌표 정확도:
  - 표준 오차: <10m
  - 좌표계: OSGB36 → WGS84 변환
  
데이터 신선도:
  - 연령: <3개월 (실시간 거래는 6개월 지연)
  - 갱신: 주 1회
```

### 1.3 모델 개발

#### 1.3.1 회귀 모델 스택
```python
Base Models (4개):
  1. Linear Regression (기준선)
  2. Decision Tree (깊이=8, min_samples_leaf=10)
  3. Random Forest (n_estimators=200, max_depth=12)
  4. Gradient Boosting (n_estimators=100, learning_rate=0.1)

Advanced Models (2개):
  1. XGBoost (max_depth=6, eta=0.1, subsample=0.8)
  2. LightGBM (num_leaves=31, learning_rate=0.05)

Ensemble:
  - Voting Regressor (가중치: XGBoost 40%, LightGBM 35%, GBR 25%)
  - 목표 R²: 0.90+
  - RMSE: £30,000 이하
```

#### 1.3.2 특성 엔지니어링 (25 → 40개 특성)
```
원본 특성 (25개):
  - Property Type, Area, Rooms, Price, Date, Location...

파생 특성 (15개):
  1. Price per m²
  2. Age (거래 시점 기준)
  3. Time Since Transaction
  4. Log Transformation (Price, Area)
  5. Distance to Amenities (School/Hospital/Station)
  6. Postcode Sector Median Price
  7. Council Tax Band Encoded
  8. EPC Rating Score (A=10 → G=1)
  9. Lease Remaining Ratio (Lease Term / Original Term)
  10. Ground Rent to Price Ratio
  11. Flood Risk Level Score (Low=1 → High=5)
  12. Listed Building Premium (1.15x)
  13. Conservation Area Impact (1.08x)
  14. Multiple Occupancy Penalty (0.92x)
  15. Season Encoding (Q1-Q4 가격 변동)
```

#### 1.3.3 모델 검증
```
Cross-Validation:
  - Strategy: Time Series Split (과거→현재 방향)
  - Folds: 5개
  - Test Size: 20% (최근 3개월)
  
성능 지표:
  - R² Score: 목표 0.90+
  - RMSE: <£30,000
  - MAE: <£20,000
  - MAPE: <8%
  
실패 임계값:
  - R² < 0.85: 모델 거부, 특성 재검토
  - RMSE > £50,000: 데이터 정제 재실행
  - MAPE > 12%: 아웃라이어 재분석
```

### 1.4 API 게이트웨이 및 프로덕션 배포

#### 1.4.1 REST API 엔드포인트
```
POST /api/v1/uk/predict
  입력: {
    "postcode": "SW1A 1AA",
    "property_type": "Flat",
    "area_sqm": 85,
    "rooms": 2,
    "building_age_years": 25,
    "lease_remaining_years": 125,
    "distance_to_station_km": 0.5
  }
  
  응답: {
    "predicted_price": 750000,
    "confidence_interval": {
      "lower": 720000,
      "upper": 780000
    },
    "confidence_level": 0.90,
    "comparable_properties": 45,
    "market_trend": "stable",
    "region": "Westminster",
    "valuation_date": "2026-07-15",
    "model_version": "uk_v1.1"
  }

GET /api/v1/uk/market/{postcode}
  응답: {
    "postcode": "SW1A 1AA",
    "median_price": 1050000,
    "price_trend_3m": 2.1,  # % 변화
    "active_listings": 12,
    "avg_time_on_market": 45,  # 일
    "price_range": {
      "min": 450000,
      "max": 3500000,
      "q1": 650000,
      "q3": 1200000
    }
  }
```

#### 1.4.2 인프라 요구사항
```
서버 구성:
  - API 서버: 4vCPU, 16GB RAM (t3.xlarge)
  - 모델 캐시: 100GB SSD
  - 응답 목표: <100ms (95 percentile)

데이터베이스:
  - PostgreSQL: 거래 이력 저장 (3년 × ~2M 거래 = 6GB)
  - Redis: 예측 캐시 (TTL 24시간, 50K entries)

모니터링:
  - API 응답시간 (목표: <100ms)
  - 모델 정확도 (월간 R² 점수)
  - API 가용성 (목표: 99.9%)
  - 거래 거절률 (목표: <1%)
```

### 1.5 B2B 파트너십 및 수익 모델

#### 1.5.1 Target Partners (3-5개)
```
1. Major Banks
   - HSBC, Barclays, Lloyds
   - 용도: Mortgage Underwriting, Risk Assessment
   - 거래량: 월 2-3만 건
   - 가격: £0.5/건 (월 100-150만 원)

2. Property Tech Companies
   - Rightmove, Zoopla, Purplebricks
   - 용도: Valuation Estimates, Market Analysis
   - 거래량: 월 5-10만 건
   - 가격: £0.2/건 (월 100-200만 원)

3. Real Estate Agencies
   - UK Property Networks (100+ 에이전시)
   - 용도: Seller Valuation Guides, CMA Reports
   - 거래량: 월 3-5만 건
   - 가격: £0.3/건 (월 90-150만 원)

4. Insurance Companies
   - Aviva, Direct Line, Churchill
   - 용도: Property Risk Assessment
   - 거래량: 월 1-2만 건
   - 가격: £0.8/건 (월 80-160만 원)

5. Government Agencies (선택적)
   - HM Revenue & Customs (지가세 평가)
   - 거래량: 월 5-10만 건 (비용)
   - 용도: Tax Assessment Support
```

#### 1.5.2 수익 모델
```
Primary Revenue Streams:

1. API 거래 기반 (월 8-12만 건)
   - 단가: £0.3-0.8/건
   - 월 수익: 240-960만 엔 (평균 480만 엔)
   - 파트너별 약정: 월 20-30만 건 × £0.5

2. License Fee (Premium Features)
   - Confidence Interval API: £500/월
   - Market Analytics Dashboard: £1,000/월
   - Batch Processing (일 1M 건): £2,000/월
   - 월 수익: 150-300만 원

3. Consulting Services
   - Property Portfolio Valuation (1-time): £5,000-20,000
   - Market Study Reports (월간): £2,000-5,000
   - Model Customization: £10,000-50,000

Combined Monthly: £30-50K (₩4,000-6,000만)
```

### 1.6 일정 및 마일스톤

```
Week 1-2: 데이터 수집 및 검증
  ☐ HM Land Registry API 키 승인
  ☐ 3개월 × 2M 거래 데이터 수집 (6GB)
  ☐ 데이터 품질 평가 (결측값 <1%, 아웃라이어 <2%)

Week 3-4: 모델 개발
  ☐ 특성 엔지니어링 (25 → 40개)
  ☐ 4개 Base 모델 학습
  ☐ 앙상블 모델 튜닝
  ☐ R² ≥ 0.90 달성 검증

Week 5-6: API 개발 및 테스트
  ☐ FastAPI 엔드포인트 구현
  ☐ 응답시간 <100ms 달성
  ☐ 2K 건/일 부하 테스트 통과

Week 7-8: 파트너십 및 배포
  ☐ 3-5개 B2B 파트너 계약 체결
  ☐ 프로덕션 배포
  ☐ 첫 거래 처리 (Week 8 말)

Month 2-3: 안정화 및 확장
  ☐ 월 8-12만 건 거래 달성
  ☐ 월 수익 4,000-6,000만 원 달성
  ☐ 사용자 확보: 150-200명
```

---

## Task 12.2: 싱가포르 진출 (Singapore Market Entry)

### 2.1 목표 및 기대효과

| 항목 | 목표 | 측정 단위 |
|------|------|----------|
| 월 매출 | 2,500-4,000만 원 | 원/월 |
| 사용자 수 | 100-120명 | 활성 사용자 |
| B2B 파트너 | 3-4개 | 기관 |
| R² 점수 | 0.90+ | 모델 성능 |
| API 거래 | 월 5-8만 건 | 건/월 |
| 진출 기간 | 1.5-2개월 | 개월 |
| 개발 비용 | $150-200K | USD |

### 2.2 전략적 가치

**Southeast Asia 허브 역할:**
```
싱가포르 진출 → 5개국 추가 진출 기반
├─ 태국 (Thailand)
├─ 베트남 (Vietnam)
├─ 인도네시아 (Indonesia)
├─ 말레이시아 (Malaysia)
└─ 필리핀 (Philippines)

공통점:
  - 싱가포르 표준 통화 (SGD 기준)
  - 영어 기반 시스템 호환
  - 아세안 데이터 규제 유사성
  - 현지 팀 및 인프라 공유 가능
```

### 2.3 데이터 수집 및 전처리

#### 2.3.1 URA & HDB 공식 데이터
```python
데이터소스:
1. URA (Urban Redevelopment Authority)
   - 엔드포인트: /api/udc/v1/transaction
   - 데이터: 민간 부동산 거래 (주택, 상업, 산업)
   - 갱신: 월 1회 (매월 15일)
   - 거래 수: 월 8,000-12,000건

2. HDB (Housing & Development Board)
   - 공공주택 거래 이력
   - 데이터: 가격, 거래량, 지역
   - 거래 수: 월 5,000-8,000건

3. Singapore Property Market Association
   - 시장 지표 및 트렌드
   - 감정사 데이터 (선택적)

데이터 필드 (22개):
  - Property ID
  - Transaction Type (Sale/Rent)
  - Property Type (HDB/Condo/Landed House)
  - Location (Postal Code, Planning Area)
  - Unit Type (HDB: 1-5 room, Condo: 1-5 bed)
  - Area (sqm)
  - Price/Rent
  - Transaction Date
  - Floor Level
  - Age (Lease Remaining for HDB)
  - Latitude/Longitude
  - MRT Distance (km)
  - School/Hospital/Mall Distance
  - Crime Rate (Planning Area)
  - Planning Area Code
```

#### 2.3.2 데이터 품질 기준
```
결측값:
  - Price: <0.05% (필수)
  - Location: <0.1% (필수)
  - Area: <2% (보간)
  
아웃라이어:
  - Price: SGD 150K-8M 범위
  - Area: 35-300 sqm 범위 (HDB), 50-500 (Condo/Landed)
  
좌표 정확도:
  - SVY21 → WGS84 변환
  - 표준 오차: <5m
```

### 2.4 모델 개발

#### 2.4.1 이원성 모델 구조 (Dual Model Architecture)
```python
Model Set A: HDB 공공주택 (월 5-8천 건)
  - 특성: Lease Remaining (중요도 매우 높음), Room Type, Area
  - 목표: R² 0.92+
  - RMSE: SGD 30,000 이하

Model Set B: 민간 부동산 (월 8-12천 건)
  - 특성: Age, Location Prestige, Finishes, Amenities
  - 목표: R² 0.88+
  - RMSE: SGD 50,000 이하

앙상블:
  - Request Type에 따라 자동 선택
  - 혼합 거래의 경우 가중 평균
```

#### 2.4.2 특성 엔지니어링 (22 → 38개)
```
추가 파생 특성 (16개):
  1. Price per sqm
  2. Lease Remaining Ratio (HDB only)
  3. MRT Accessibility Score
  4. Central Location Premium (CBD distance)
  5. School Quality Index
  6. Area (log 변환)
  7. Age (log 변환)
  8. Neighborhood Price Median
  9. Market Trend (3개월)
  10. Transaction Season
  11. Crime Rate Impact
  12. New MRT Opening Impact (Upcoming 프로젝트)
  13. Planning Area Code Encoded (22개 지역)
  14. Amenities Density Score
  15. Flood Risk (일부 지역)
  16. Freehold vs Leasehold Premium (일부 부동산)
```

### 2.5 B2B 파트너십

#### 2.5.1 Target Partners (3-4개)
```
1. Major Banks (2개)
   - DBS Bank, OCBC Bank, UOB
   - 용도: Mortgage Valuation, Risk Assessment
   - 거래: 월 2-3만 건
   - 가격: SGD 0.3-0.5/건

2. Property Portals (1-2개)
   - PropertyGuru Singapore, 99.co
   - 용도: Valuation Estimates, Market Data
   - 거래: 월 5-10만 건
   - 가격: SGD 0.15-0.25/건

3. Real Estate Agencies (1개 네트워크)
   - Singapore Real Estate Agency Association
   - 거래: 월 3-5만 건
```

#### 2.5.2 수익 구조
```
API 거래 (월 5-8만 건):
  - 평균 단가: SGD 0.25/건
  - 월 수익: SGD 12.5-20K (₩1,500-2,400만)

Premium Services:
  - Portfolio Analytics: SGD 500/월
  - Batch API: SGD 1,000/월
  - 월 수익: SGD 3-5K (₩350-600만)

총 월 수익: SGD 15-25K (₩1,850-3,000만)
```

### 2.6 전개 일정

```
Week 1-2: 데이터 수집
  ☐ URA/HDB API 승인 및 수집
  ☐ 3개월 데이터 (15-20만 거래)
  ☐ 품질 검증

Week 3: 모델 개발
  ☐ 이원 모델 학습 (HDB/민간)
  ☐ R² 0.88-0.92 달성

Week 4-5: API 개발 및 배포
  ☐ FastAPI 구현
  ☐ 부하 테스트 (1.5K 건/시간)
  ☐ 프로덕션 배포

Week 6-8: 파트너십 및 확장
  ☐ 3-4개 파트너 계약
  ☐ 월 5-8만 건 거래 달성
```

---

## Task 12.3: 일본 진출 (Japan Market Entry)

### 3.1 목표 및 기대효과

| 항목 | 목표 | 측정 단위 |
|------|------|----------|
| 월 매출 | 5,000-7,000만 원 | 원/월 |
| 사용자 수 | 120-150명 | 활성 사용자 |
| B2B 파트너 | 3-4개 | 기관 |
| R² 점수 | 0.90+ | 모델 성능 |
| API 거래 | 월 10-15만 건 | 건/월 |
| 진출 기간 | 2-3개월 | 개월 |
| 개발 비용 | $150-180K | USD |

### 3.2 데이터 수집

#### 3.2.1 공식 데이터소스
```
1. 국토교통성 (Ministry of Land, Infrastructure, Transport and Tourism)
   - 실거래 데이터베이스 (Real Estate Transaction Database)
   - 월 거래: 20-30만 건
   - 갱신: 월 1회
   
2. 부동산 공시가격 (Land Price Appraisal System)
   - 지가 변동 추세
   - 가치평가 기준
   
3. REINS (Real Estate Information System)
   - MLS 수준의 거래 정보
   - 매물 정보

데이터 필드 (28개):
  - 부동산 ID
  - 거래 유형 (매매/임차)
  - 부동산 유형 (주택/상업/토지)
  - 주소 (도도부현/시구정촌)
  - 면적 (㎡)
  - 가격 (￥)
  - 거래일
  - 건물 연식
  - 위도/경도 (Tokyo Datum)
  - 최근역까지 거리
  - 학교/병원까지 거리
  - 지역 특성 (도시/교외/농촌)
```

#### 3.2.2 특수 고려사항
```
좌표계 변환:
  - Tokyo Datum (Japan) → WGS84
  - 반소 (FUDE) 단위 지도 활용

진법/단위:
  - 면적: ㎡ (일반), 평 (전통)
  - 가격: JPY (일본 엔)

지역 특성:
  - 도심 (Tokyo/Osaka/Nagoya 등 3대도시)
  - 교외 (주변 도도부현)
  - 농촌/산림지역 (낮은 거래량)
  
타겟 지역:
  - 도쿄: 월 40-50천 건 (전체의 20%)
  - 오사카/고베: 월 15-20천 건
  - 기타 메이저: 월 50-70천 건
```

### 3.3 모델 개발

#### 3.3.1 다지역 모델 구조 (Multi-Region Architecture)
```
Model Set 1: 도심 (Tokyo/Osaka/Nagoya)
  - 특성: 인근역 거리, 건물 연식, 상권 지수
  - 목표 R²: 0.92+

Model Set 2: 도시 (20+ 인구 50만 이상 도시)
  - 목표 R²: 0.89+

Model Set 3: 지방 (소도시/농촌)
  - 목표 R²: 0.83+

라우팅:
  - 주소에서 지역 자동 분류
  - 해당 모델 선택
```

#### 3.3.2 특성 엔지니어링 (28 → 42개)
```
추가 파생 특성:
  1. Price per ㎡
  2. Nearest Station Distance (m)
  3. Commute Time to CBD (분)
  4. Building Age (로그)
  5. Neighborhood Median Price
  6. Urban Prestige Score (도심 지수)
  7. School Quality Index
  8. Population Density
  9. Commercial District Proximity
  10. Flood Hazard Map Risk
  11. Earthquake Seismic Grade
  12. Accessibility Score (대중교통)
  13. Regional Economic Index
  14. Land Appreciation Trend (3년)
  15. Zoning Type (주거/상업/혼합)
  16. Age (제곱항)
  17. Transaction Season
  18. Building Age × Distance to Station (상호작용항)
```

### 3.4 일정

```
Week 1-2: 데이터 수집
  ☐ 국토교통성 API 신청 및 승인
  ☐ 3개월 × 20-30만 건 수집

Week 3-4: 모델 개발
  ☐ 3개 지역 모델 학습
  ☐ R² 0.83-0.92 달성

Week 5-6: API 및 배포
  ☐ 지역별 라우팅 로직
  ☐ 응답시간 <100ms

Week 7-8: 파트너십
  ☐ 3-4개 파트너 (은행, 증권, 에이전시)
  ☐ 월 10-15만 건 거래
```

---

## Task 12.4: 추가 선진국 진출 (Advanced Markets)

### 4.1 독일 (Germany) - Month 4-5

**목표**: 월 4,500-6,000만 원, 3-4 B2B 파트너

**데이터소스**:
- Catastro (지적청) 부동산 정보
- INE (통계청) 거래
- Bundesinstitut für Berufsbildung (BIBB) DB

**모델**: 3개 지역 (베를린/뮌헨/프랑크푸르트) + 기타

**API 거래**: 월 8-12만 건

### 4.2 호주 (Australia) - Month 5-6

**목표**: 월 3,500-5,000만 원, 3개 B2B 파트너

**데이터소스**:
- CoreLogic RP Data
- NSW/VIC Land Registry

**모델**: 주(State)별 3개 모델 (NSW/VIC/QLD)

**API 거래**: 월 6-9만 건

### 4.3 캐나다 (Canada) - Month 5-6 (병행)

**목표**: 월 3,000-4,500만 원

**데이터소스**:
- Real Estate Board of Canada
- MLS 데이터

**모델**: 주(Province)별 모델 (ON/BC/AB 우선)

---

## Task 12.5: Southeast Asia 본격화

### 5.1 태국 (Thailand) - Month 7-8

**목표**: 월 1,500-2,500만 원, 싱가포르 기반 확장

**진출 순서**: 싱가포르 팀을 활용하여 데이터 수집 및 파트너십

**모델**: 방콕/주요도시 + 기타

### 5.2 후속 진출 (Month 9-12)

- 홍콩 (월 2,500-4,000만 원)
- 베트남 (월 800-1,500만 원, 장기성장)
- 인도네시아 (월 1,000-2,000만 원, 장기성장)

---

## 종합 기대효과 (Month 1-12)

```
Month 1-3 (Quick Win):
  누적 월매출: 11,500-16,000만 원
  활성 사용자: 370-470명
  B2B 파트너: 9-13개

Month 4-6 (확장):
  누적 월매출: 23,000-33,500만 원
  활성 사용자: 590-740명
  B2B 파트너: 15-21개

Month 7-9 (Southeast Asia):
  누적 월매출: 24,500-36,000만 원
  활성 사용자: 690-840명
  B2B 파트너: 18-25개

Month 10-12 (최종):
  누적 월매출: 26,500-40,000만 원
  활성 사용자: 790-940명
  B2B 파트너: 20-28개
```

### 최종 목표 (Month 12 말)
- **월 누적 매출**: 26,500-40,000만 원
- **글로벌 활성 사용자**: 790-940명
- **국제 B2B 파트너**: 20-28개
- **운영 국가**: 8-10개국
- **평균 모델 성능**: R² 0.87

---

## 리스크 관리

### 높은 리스크

1. **규제 준수 위험**
   - GDPR (EU), APPI (일본), CCPA (미국)
   - 대응: 법무팀 고용, DPA 계약

2. **데이터 접근성 위험**
   - API 중단, 정책 변경
   - 대응: 다중 데이터소스, 계약 보장

3. **환율 변동 위험**
   - 신흥시장 통화 변동성
   - 대응: USD 기준 가격, 분기별 재평가

### 중간 리스크

1. 시장 경기 침체
2. 현지 경쟁 업체 출현
3. 기술 통합 복잡도

---

**작성일**: 2026-06-25  
**상태**: Phase 12 명세서 v1.0  
**다음**: WBS 작성, 구현 시작
