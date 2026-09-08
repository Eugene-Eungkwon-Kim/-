# AVM 프로젝트 세부명세서
## 2026-06-24

---

## 1️⃣ 데이터 명세

### 1.1 입력 데이터 명세

#### 데이터 소스
```
원본 위치: D:\loan4u_avm_data
├── Database 파일
│   ├── real_estate_transactions.db (부동산 거래 정보)
│   ├── building_registry.db (건물 정보)
│   ├── loan_portfolio.db (대출 포트폴리오)
│   └── market_indicators.db (시장 지표)
│
├── Manifest 파일
│   ├── data_catalog.json (데이터 카탈로그)
│   ├── schema_definition.json (스키마 정의)
│   └── relationship_mapping.json (테이블 관계)
│
└── Runbook 파일
    ├── data_processing_guide.md (처리 가이드)
    ├── validation_rules.json (검증 규칙)
    └── error_handling.md (오류 처리)
```

#### 주요 테이블 명세

##### real_estate_transactions 테이블
```
컬럼명                  | 타입      | 길이 | NULL | 설명
거래ID                 | VARCHAR   | 20   | NO   | 거래 고유 ID
거래일자               | DATE      | -    | NO   | 거래 발생 일자
거래금액               | DECIMAL   | 15,2 | NO   | 실제 거래가 (원)
주소                   | VARCHAR   | 200  | NO   | 부동산 주소
주소_정규화            | VARCHAR   | 200  | YES  | 정규화된 주소
위도                   | DECIMAL   | 10,6 | YES  | GPS 위도
경도                   | DECIMAL   | 10,6 | YES  | GPS 경도
거래_유형              | VARCHAR   | 20   | NO   | 매매/전세/월세
매도_가격              | DECIMAL   | 15,2 | YES  | 매도가 (전세/월세)
추가_수수료            | DECIMAL   | 10,2 | YES  | 거래 수수료
매매_유형              | VARCHAR   | 30   | YES  | 신축/중고/토지
거래_구분              | VARCHAR   | 20   | YES  | 개별/집단 거래
매수자_유형            | VARCHAR   | 20   | YES  | 개인/법인/기관
매도자_유형            | VARCHAR   | 20   | YES  | 개인/법인/기관
```

##### building_registry 테이블
```
컬럼명                  | 타입      | 길이 | NULL | 설명
건물ID                 | VARCHAR   | 20   | NO   | 건물 고유 ID
건축년도               | YEAR      | -    | NO   | 건축 연도
건물_용도              | VARCHAR   | 50   | NO   | 용도 (주택/상업 등)
건물_분류              | VARCHAR   | 30   | NO   | 분류 (아파트/주택 등)
연면적                 | DECIMAL   | 10,2 | YES  | 연 건축 면적 (㎡)
대지면적               | DECIMAL   | 10,2 | YES  | 대지 면적 (㎡)
층수                   | INTEGER   | -    | YES  | 현재 건물 층수
총층수                 | INTEGER   | -    | YES  | 전체 건물 층수
방개수                 | INTEGER   | -    | YES  | 방 개수
욕실개수               | INTEGER   | -    | YES  | 욕실 개수
주차장                 | VARCHAR   | 30   | YES  | 주차 정보
엘리베이터             | VARCHAR   | 10   | YES  | 엘리베이터 여부
난방방식               | VARCHAR   | 30   | YES  | 난방 방식
건물_등급              | VARCHAR   | 20   | YES  | 건물 등급 (A/B/C 등)
재건축가능             | VARCHAR   | 10   | YES  | 재건축 가능 여부
```

##### loan_portfolio 테이블
```
컬럼명                  | 타입      | 길이 | NULL | 설명
대출ID                 | VARCHAR   | 20   | NO   | 대출 고유 ID
부동산ID               | VARCHAR   | 20   | NO   | 해당 부동산 ID
대출금액               | DECIMAL   | 15,2 | NO   | 대출 금액 (원)
감정가격               | DECIMAL   | 15,2 | NO   | 감정 가격 (원)
대출기간_개월          | INTEGER   | -    | NO   | 대출 기간 (개월)
금리                   | DECIMAL   | 5,2  | NO   | 금리 (%)
담보인정비율_LTV        | DECIMAL   | 5,2  | NO   | LTV (%)
부실여부               | VARCHAR   | 10   | NO   | 부실 여부 (Yes/No)
감정날짜               | DATE      | -    | NO   | 감정 실시 일자
상환상태               | VARCHAR   | 30   | YES  | 상환 상태
연체개월수             | INTEGER   | -    | YES  | 연체 개월 수
```

### 1.2 출력 데이터 명세

#### 마스터 데이터셋 명세
```
파일명: master_real_estate_operational_YYYYMMDD.csv
위치: /mnt/avm_data/Cleansed_Data/
크기: 예상 500MB+ (행 수 미정)
인코딩: UTF-8-SIG
구분자: ,

컬럼: 19개 (10개 원본 + 9개 파생)

원본 컬럼 (10개):
1. transaction_id: 거래 고유 ID
2. transaction_date: 거래 일자 (YYYY-MM-DD)
3. price: 실제 거래가 (원)
4. area_sqm: 건물 면적 (㎡)
5. year_built: 건축 년도 (YYYY)
6. floor: 현재 층수 (정수)
7. rooms: 방 개수 (정수)
8. bathrooms: 욕실 개수 (정수)
9. parking: 주차장 여부 (0/1)
10. elevator: 엘리베이터 여부 (0/1)

파생 컬럼 (9개):
11. price_per_sqm: 면적당 가격 = price / area_sqm
12. age_years: 건물 나이 = 2024 - year_built
13. total_floor: 전체 층수 (건물 정보)
14. debt_to_price_ratio: 대출금/가격 = debt / price
15. transaction_count_1y: 1년 거래 건수
16. days_on_market: 시장 일수
17. ltv: LTV (담보인정비율) = loan / price
18. loan_term_months: 대출 기간 (개월)
19. appraisal_rounds: 감정 횟수

데이터 품질 요구사항:
- 완정성: ≥95% (NULL 값 <5%)
- 정확성: ≥98% (검증 규칙 통과)
- 일관성: ≥99% (논리적 모순 <1%)
```

---

## 2️⃣ 모델 명세

### 2.1 입력 특성(Features) 명세

#### 수치형 특성 (12개)
```
1. price_per_sqm: 면적당 가격 (원/㎡)
   범위: 1,000 ~ 100,000 원/㎡
   단위: 원/㎡
   
2. age_years: 건물 나이 (연도)
   범위: 0 ~ 120 년
   단위: 년
   
3. area_sqm: 건물 면적 (㎡)
   범위: 10 ~ 500 ㎡
   단위: ㎡
   
4. floor: 현재 층수
   범위: 1 ~ 100 층
   단위: 층
   
5. rooms: 방 개수
   범위: 1 ~ 10 개
   단위: 개
   
6. bathrooms: 욕실 개수
   범위: 1 ~ 5 개
   단위: 개
   
7. debt_to_price_ratio: 대출금/가격
   범위: 0 ~ 1.5 (150%)
   단위: 비율
   
8. ltv: LTV (담보인정비율)
   범위: 0 ~ 100 %
   단위: %
   
9. loan_term_months: 대출 기간
   범위: 12 ~ 360 개월
   단위: 개월
   
10. transaction_count_1y: 1년 거래 건수
    범위: 0 ~ 100 건
    단위: 건
    
11. days_on_market: 시장 일수
    범위: 0 ~ 1000 일
    단위: 일
    
12. appraisal_rounds: 감정 횟수
    범위: 1 ~ 10 회
    단위: 회
```

#### 범주형 특성 (7개)
```
1. building_type: 건물 타입
   범주: 아파트, 주택, 상업, 토지
   인코딩: One-Hot
   
2. heating_type: 난방 방식
   범주: 중앙, 개별, 지역, 기타
   인코딩: One-Hot
   
3. transaction_type: 거래 유형
   범주: 매매, 전세, 월세
   인코딩: One-Hot
   
4. seller_type: 매도자 유형
   범주: 개인, 법인, 기관
   인코딩: One-Hot
   
5. buyer_type: 매수자 유형
   범주: 개인, 법인, 기관
   인코딩: One-Hot
   
6. region_level1: 광역시도
   범주: 서울, 부산, 대구, ... (17개)
   인코딩: One-Hot
   
7. region_level2: 시군구
   범주: 강남구, 서초구, ... (250+ 개)
   인코딩: Target Encoding (과도한 원-핫 방지)
```

### 2.2 출력 명세

#### 예측 값
```
컬럼명: predicted_price
타입: 정수 (원)
범위: 100,000,000 ~ 5,000,000,000 (1억 ~ 50억 원)
단위: 원

신뢰도: confidence_score
범위: 0 ~ 100 (%)
기준:
- 90~100%: 매우 높음 (예측 신뢰)
- 75~90%: 높음
- 60~75%: 중간
- <60%: 낮음 (재검토 권장)

오차율: discrepancy_rate
범위: -50% ~ +50%
계산식: (predicted - actual) / actual × 100
```

### 2.3 모델 성능 기준

#### 회귀 성능 지표
```
R² (결정계수):
- 목표: ≥ 0.85
- 의미: 변동성의 85% 이상 설명

RMSE (평균제곱근오차):
- 목표: ≤ 50,000,000 원
- 의미: 평균 오차 5천만 원 이하

MAE (평균절대오차):
- 목표: ≤ 30,000,000 원
- 의미: 절대 오차 평균 3천만 원 이하

MAPE (평균절대백분오차):
- 목표: ≤ 3%
- 의미: 상대 오차 3% 이하
```

#### 괴리율 검증
```
±3% 범위 내 달성율:
- 목표: ≥ 90%
- 의미: 1,000건 중 900건 이상

±5% 범위 내 달성율:
- 목표: ≥ 95%
- 의미: 1,000건 중 950건 이상

±10% 범위 내 달성율:
- 목표: ≥ 99%
- 의미: 1,000건 중 990건 이상

가격대별 성능:
- 저가(100-300M): ≤ 5% 오차
- 중가(300-700M): ≤ 3% 오차
- 고가(700M+): ≤ 2% 오차
```

### 2.4 모델 재학습 명세

#### 스케줄
```
주기: 월 1회 (매월 첫째 주 월요일 11:00)
시간대: 야간 (11:00 ~ 13:00)

단계:
1. 데이터 수집 (30분)
   - 신규 거래 데이터 추출
   - 마스터 데이터셋 업데이트

2. 전처리 (30분)
   - 결측치 처리
   - 정규화/표준화

3. 모델 학습 (60분)
   - 7개 모델 재학습
   - 하이퍼파라미터 튜닝

4. 검증 (30분)
   - 성능 평가
   - 모델 비교

5. 배포 (30분)
   - 최적 모델 선정
   - 프로덕션 배포
```

---

## 3️⃣ API 명세

### 3.1 가격 예측 API

#### 엔드포인트
```
POST /api/v1/predict
Content-Type: application/json

기본 URL: https://avm-api.example.com/api/v1
```

#### 요청 명세
```json
{
  "property_id": "PROP_12345",           // 선택 (감시용)
  "area_sqm": 85.5,                      // 필수
  "year_built": 2010,                    // 필수
  "floor": 5,                            // 필수
  "total_floor": 15,                     // 필수
  "rooms": 3,                            // 필수
  "bathrooms": 2,                        // 필수
  "parking": 1,                          // 필수 (0 또는 1)
  "elevator": 1,                         // 필수 (0 또는 1)
  "building_type": "아파트",              // 필수
  "heating_type": "중앙",                 // 필수
  "transaction_type": "매매",             // 필수
  "seller_type": "개인",                  // 필수
  "buyer_type": "개인",                   // 필수
  "region_code": "11620",                // 필수 (5자리 지역 코드)
  "transaction_count_1y": 3,             // 선택
  "debt_to_price_ratio": 0.7,            // 선택
  "ltv": 70.0                            // 선택
}
```

#### 응답 명세
```json
{
  "request_id": "REQ_20260624_001234",
  "timestamp": "2026-06-24T10:30:45Z",
  "status": "success",
  
  "prediction": {
    "predicted_price": 850000000,        // 예측 가격 (원)
    "confidence_score": 87.5,            // 신뢰도 (%)
    "price_range": {
      "lower_bound": 808500000,          // 하한 (±5%)
      "upper_bound": 891500000           // 상한 (±5%)
    },
    "percentile": 55,                    // 지역 내 백분위 (1~100)
    "comparable_properties": 342         // 비교 가능 부동산 수
  },
  
  "analysis": {
    "key_factors": [
      {
        "factor": "area_sqm",
        "contribution": 35.2,             // 기여도 (%)
        "direction": "positive"            // 긍정/부정
      },
      {
        "factor": "year_built",
        "contribution": 28.1,
        "direction": "negative"
      }
    ],
    "similar_properties": [
      {
        "id": "PROP_98765",
        "price": 840000000,
        "similarity_score": 0.92,
        "area_sqm": 86.0,
        "year_built": 2011
      }
    ]
  },
  
  "metadata": {
    "model_version": "2.1.0",
    "model_name": "XGBoost_Ensemble",
    "training_date": "2026-06-24",
    "data_version": "v20260624",
    "execution_time_ms": 125
  }
}
```

#### 에러 응답
```json
{
  "request_id": "REQ_20260624_001234",
  "status": "error",
  "error": {
    "code": "INVALID_INPUT",
    "message": "Invalid area_sqm value",
    "details": {
      "field": "area_sqm",
      "provided": -50,
      "expected_range": "10 ~ 500"
    }
  }
}
```

### 3.2 모델 정보 API

#### 엔드포인트
```
GET /api/v1/model/info
```

#### 응답
```json
{
  "model": {
    "name": "XGBoost_Ensemble",
    "version": "2.1.0",
    "training_date": "2026-06-24",
    "last_retrain": "2026-06-24T11:00:00Z"
  },
  "performance": {
    "r2_score": 0.87,
    "rmse": 45000000,
    "mae": 28000000,
    "mape": 2.8,
    "discrepancy_rate_within_3pct": 92.5,
    "discrepancy_rate_within_5pct": 96.2
  },
  "data": {
    "training_samples": 285000,
    "test_samples": 71250,
    "last_update": "2026-06-24T11:00:00Z"
  }
}
```

### 3.3 헬스체크 API

#### 엔드포인트
```
GET /api/v1/health
```

#### 응답
```json
{
  "status": "healthy",
  "timestamp": "2026-06-24T10:30:45Z",
  "components": {
    "api": "up",
    "model": "ready",
    "database": "connected",
    "cache": "operational"
  },
  "version": "2.1.0"
}
```

---

## 4️⃣ 배포 명세

### 4.1 시스템 요구사항

#### 개발 환경
```
Python: 3.11+
OS: Linux (Ubuntu 22.04)
메모리: 16GB RAM
CPU: 4-core
디스크: 100GB
```

#### 프로덕션 환경 (AWS)
```
ECS 클러스터:
- 인스턴스 타입: t3.large
- CPU: 2 vCPU
- 메모리: 8GB
- 개수: 3개 (HA)

RDS:
- 엔진: PostgreSQL 15
- 인스턴스: db.t3.medium
- 스토리지: 100GB SSD
- 백업: 매일 자동

API Gateway:
- Rate Limiting: 1,000 req/sec
- 인증: API Key + JWT
- CORS: 활성화
```

### 4.2 성능 요구사항

```
API 응답 시간:
- p50: <100ms
- p95: <300ms
- p99: <500ms

처리량:
- 동시 요청: 1,000+ req/sec
- 월 처리량: 10억 건/월 (추정)

가용성:
- SLA: 99.9% (월간 허용 다운타임: 43분)
- 재해복구 RTO: 1시간
- 재해복구 RPO: 15분
```

---

## 5️⃣ 테스트 명세

### 5.1 단위 테스트

#### 데이터 검증 테스트
```python
test_validate_input_range()        # 입력값 범위 검증
test_validate_null_handling()      # NULL 값 처리
test_validate_data_types()         # 데이터 타입 검증
test_validate_business_logic()     # 비즈니스 로직 검증
```

#### 모델 테스트
```python
test_model_loading()               # 모델 로드
test_model_prediction()            # 예측 실행
test_prediction_output_format()    # 출력 형식
test_prediction_value_range()      # 출력 범위
```

### 5.2 통합 테스트

```python
test_api_request_response()        # API 요청/응답
test_database_connection()         # DB 연결
test_cache_functionality()         # 캐싱
test_authentication()              # 인증
test_error_handling()              # 에러 처리
```

### 5.3 성능 테스트

```
테스트 시나리오:
1. 기본 부하: 100 concurrent users
2. 최대 부하: 1,000 concurrent users
3. 스파이크: 5,000 requests/sec (30초)

측정 항목:
- 응답 시간
- 에러율
- 처리량
- CPU/메모리 사용률
```

---

**작성 일자**: 2026-06-24  
**버전**: v1.0  
**상태**: 검토 대기
