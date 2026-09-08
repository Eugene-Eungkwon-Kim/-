# Loan4U QC v1.1 Excel 완성 프로젝트
## 세부 명세서 (DETAILED_SPECIFICATION_DOCUMENT)
## 2026-06-24

---

## 📋 문서 개요

**명세 항목**:
1. 데이터 소스 명세
2. 데이터 스키마 정의
3. API 명세
4. 처리 알고리즘 명세
5. Excel 파일 포맷 명세
6. QC 검증 규칙

---

## 1️⃣ 데이터 소스 명세

### 1.1 Primary Source: LG 외장하드 D:\ 드라이브

#### 1.1.1 디렉토리 구조
```
D:\loan4u_avm_data\
├── Database/
│   ├── building_registry.db              (건축물 정보)
│   ├── real_estate_transactions.db       (거래 정보)
│   ├── loan_portfolio.db                 (대출 포트폴리오)
│   └── market_indicators.db              (시장 지표)
│
├── Manifest/
│   ├── data_catalog.json                 (데이터 카탈로그)
│   ├── schema_definition.json            (스키마 정의)
│   └── data_dictionary.json              (데이터 딕셔너리)
│
├── CSV/
│   ├── building_attributes.csv           (건물 속성)
│   ├── transaction_history.csv           (거래 이력)
│   └── market_data.csv                   (시장 데이터)
│
└── Runbook/
    ├── data_processing_guide.md          (처리 가이드)
    └── validation_rules.json             (검증 규칙)
```

#### 1.1.2 주요 테이블 및 필드

**building_registry.db**
```
테이블: buildings
필드:
  - pnu (PK): 부동산 고유번호 (19자리)
  - address: 주소
  - city: 시
  - district: 구/군
  - neighborhood: 동
  - lot_number: 지번
  - complex_name: 단지명
  - building_code: 건축물 번호
  - total_area: 전체면적 (㎡)
  - exclusive_area: 전용면적 (㎡)
  - build_year: 준공연도 (YYYY)
  - floor: 층수
  - total_units: 세대수
  - building_type: 건축물 용도
  - zoning: 용도지역
  - created_at: 생성일
  - updated_at: 수정일
```

**real_estate_transactions.db**
```
테이블: transactions
필드:
  - transaction_id (PK): 거래 ID
  - pnu (FK): 부동산 고유번호
  - transaction_date: 매매일자 (YYYYMMDD)
  - transaction_price: 거래가격 (원)
  - buyer: 구매자 구분 (개인/법인)
  - seller: 판매자 구분
  - contract_type: 매매/전세/월세
  - days_to_contract: 계약 소요일 (일)
  - created_at: 등록일
```

**market_indicators.db**
```
테이블: market_indicators
필드:
  - indicator_date: 지표 기준일 (YYYYMM)
  - region: 지역
  - avg_price: 평균가격 (원)
  - price_upper: 시세상단 (원)
  - price_lower: 시세하단 (원)
  - jeonse_upper: 전세시세상단 (원)
  - jeonse_lower: 전세시세하단 (원)
  - cofix: COFIX 금리
  - market_trend: 시장 추세 (상승/보합/하락)
```

### 1.2 Secondary Source: Data.go.kr API

#### 1.2.1 API 엔드포인트

**공시가격 조회 API**
```
EndPoint: /openapi/service/rest/RealEstateOpenapiService/getRealEstateStatistics
Method: GET
인증: API 키 (발급받음)

파라미터:
  - serviceKey: API 키 [필수]
  - LAWD_CD: 지역 코드 (11110 = 서초구) [필수]
  - DEAL_YMD: 거래 년월 (YYYYMM) [필수]
  - numOfRows: 조회 건수 (기본 10, 최대 100)
  - pageNo: 페이지 번호

응답:
{
  "response": {
    "body": {
      "items": [
        {
          "거래금액": "500000000",
          "거래기간": "2024-06",
          "등기이전일자": "20240615",
          "도로명": "서울특별시 서초구 강남대로 38길",
          "건축년도": "2015",
          "아파트": "갤러리 포레스타",
          "전용면적": "110",
          "지역코드": "11650",
          "층": "5"
        }
      ]
    }
  }
}

성공 코드: 200
오류 처리: 403 (API 키 오류), 500 (서버 오류)
```

**부동산 실거래 정보 조회 API**
```
EndPoint: /openapi/service/rest/RealEstateService/getRealEstateTransactionReport
Method: GET
인증: API 키

파라미터:
  - serviceKey: API 키 [필수]
  - LAWD_CD: 지역 코드 [필수]
  - DEAL_YMD: 거래 년월 [필수]

응답: 위와 동일
```

#### 1.2.2 API 호출 정책

- **Rate Limit**: 0.5초/요청 (분당 120건)
- **Timeout**: 30초
- **Retry 정책**: 3회 재시도 (지수 백오프: 1s, 2s, 4s)
- **캐싱**: 일일 결과 메모리 캐시

### 1.3 Tertiary Source: 부동산 공개 데이터 포털

- 공시가격 공개 시스템 (공개용 CSV)
- 국토교통부 부동산 시장 정보 (월간 리포트)
- 신용보증기금 시장 지표

---

## 2️⃣ 데이터 스키마 정의

### 2.1 Master Schema (기초 정보)

```json
{
  "master_info": {
    "unique_id": {
      "type": "string",
      "format": "pnu (19자리)",
      "example": "1165010100101190000",
      "required": true,
      "description": "부동산 고유번호"
    },
    "property_type": {
      "type": "enum",
      "values": ["아파트", "빌라", "단독주택", "오피스텔"],
      "example": "아파트",
      "required": true
    },
    "location": {
      "address": {
        "type": "string",
        "example": "서울특별시 서초구 강남대로 38길",
        "required": true
      },
      "city": {
        "type": "string",
        "example": "서울특별시",
        "required": true
      },
      "district": {
        "type": "string",
        "example": "서초구",
        "required": true
      },
      "neighborhood": {
        "type": "string",
        "example": "방배동",
        "required": true
      }
    },
    "building_info": {
      "complex_name": {
        "type": "string",
        "example": "갤러리 포레스타",
        "required": true
      },
      "unit_number": {
        "type": "integer",
        "example": 1205,
        "required": true
      },
      "exclusive_area": {
        "type": "number",
        "format": "float",
        "unit": "㎡",
        "range": [50, 500],
        "example": 110.5,
        "required": true
      },
      "build_year": {
        "type": "integer",
        "format": "YYYY",
        "range": [1950, 2025],
        "example": 2015,
        "required": true
      },
      "floor": {
        "type": "integer",
        "range": [1, 60],
        "example": 5,
        "required": false
      },
      "total_units": {
        "type": "integer",
        "range": [1, 5000],
        "example": 500,
        "required": false
      }
    }
  }
}
```

### 2.2 Price Schema (가격 정보)

```json
{
  "price_info": {
    "official_price": {
      "year_2023": {
        "type": "integer",
        "unit": "원",
        "range": [10000000, 10000000000],
        "example": 650000000,
        "required": true,
        "source": "공시가격공개시스템"
      },
      "year_2022": {
        "type": "integer",
        "unit": "원",
        "example": 620000000,
        "required": true
      }
    },
    "transaction_price": {
      "recent_price": {
        "type": "integer",
        "unit": "원",
        "example": 680000000,
        "description": "최근 3개월 평균 매매가"
      },
      "transaction_date": {
        "type": "string",
        "format": "YYYYMMDD",
        "example": "20240615"
      }
    },
    "market_indicators": {
      "price_upper": {
        "type": "integer",
        "unit": "원",
        "description": "매매시세 상단",
        "example": 700000000
      },
      "price_lower": {
        "type": "integer",
        "unit": "원",
        "description": "매매시세 하단",
        "example": 650000000
      },
      "jeonse_upper": {
        "type": "integer",
        "unit": "원",
        "description": "전세시세 상단"
      },
      "jeonse_lower": {
        "type": "integer",
        "unit": "원",
        "description": "전세시세 하단"
      }
    }
  }
}
```

### 2.3 Prediction Schema (AI 예측)

```json
{
  "prediction_info": {
    "model_v1_0": {
      "type": "number",
      "format": "float",
      "unit": "원",
      "range": [10000000, 10000000000],
      "model_type": "XGBoost",
      "r2_score": 0.92,
      "example": 675000000,
      "confidence": {
        "type": "number",
        "format": "float",
        "range": [0, 1],
        "example": 0.85
      }
    },
    "model_v1_1": {
      "type": "number",
      "model_type": "Random Forest",
      "r2_score": 0.90,
      "example": 672000000
    },
    "model_vF": {
      "type": "number",
      "model_type": "Voting Ensemble (XGB+RF+GB)",
      "r2_score": 0.93,
      "example": 678000000
    },
    "master_prediction": {
      "type": "number",
      "description": "3개 모델 가중 평균",
      "formula": "(v1.0 * 0.3 + v1.1 * 0.3 + vF * 0.4)",
      "example": 675500000
    },
    "confidence_score": {
      "type": "integer",
      "unit": "%",
      "range": [0, 100],
      "description": "예측 신뢰도",
      "calculation": "표준편차 기반 계산"
    }
  }
}
```

---

## 3️⃣ API 명세

### 3.1 데이터 수집 API

#### 3.1.1 공시가격 조회

```python
# 메서드
def fetch_official_price(pnu, year):
    """
    부동산 고유번호와 연도로 공시가격 조회
    
    Args:
        pnu (str): 부동산 고유번호 (19자리)
        year (int): 조회 연도 (2022 또는 2023)
    
    Returns:
        dict: {
            "price": 650000000,
            "date": "2023-12-31",
            "currency": "KRW"
        }
    
    Raises:
        APIError: API 호출 실패
        DataNotFoundError: 데이터 없음
    
    Rate Limit: 0.5초/요청
    Timeout: 30초
    """
    pass
```

#### 3.1.2 실거래 데이터 조회

```python
def fetch_transaction_data(pnu, start_date, end_date):
    """
    부동산 거래 데이터 조회
    
    Args:
        pnu (str): 부동산 고유번호
        start_date (str): 시작 날짜 (YYYYMMDD)
        end_date (str): 종료 날짜 (YYYYMMDD)
    
    Returns:
        list: [
            {
                "date": "20240615",
                "price": 680000000,
                "type": "매매",
                "days_to_contract": 5
            }
        ]
    
    Cache: 일일 결과 캐시
    """
    pass
```

#### 3.1.3 건물 정보 조회

```python
def fetch_building_info(pnu):
    """
    건축물관리대장 정보 조회
    
    Args:
        pnu (str): 부동산 고유번호
    
    Returns:
        dict: {
            "exclusive_area": 110.5,
            "build_year": 2015,
            "floor": 5,
            "total_units": 500,
            "zoning": "제1종 주거지역"
        }
    """
    pass
```

### 3.2 데이터 처리 API

#### 3.2.1 데이터 정제

```python
def clean_data(raw_data):
    """
    원본 데이터 정제
    
    1. NULL 처리
       - 필수필드: 오류 발생
       - 선택필드: 중앙값 입력
    
    2. 범위 검증
       - 면적: 50-500 ㎡
       - 가격: 1억 이상
       - 연도: 1950-2025
    
    3. 중복 제거
       - PNU 기준 중복 제거
       - 최신 데이터 우선
    
    Returns:
        dict: 정제된 데이터
    """
    pass
```

#### 3.2.2 특성 생성

```python
def generate_features(building_info, price_info, market_info):
    """
    AVM 모델용 특성 생성
    
    특성 목록:
      - area: 전용면적
      - age: 경과년수 (현재년도 - 준공연도)
      - floor: 층수
      - location_grade: 위치 등급 (신경망 기반)
      - price_ratio: 공시가/평균가격
      - market_trend: 시장 추세 점수
      - cofix: COFIX 금리
    
    Returns:
        array: 특성 벡터
    """
    pass
```

#### 3.2.3 이상치 감지

```python
def detect_outliers(data, method='iqr'):
    """
    이상치 감지
    
    방법:
      - IQR (사분위수): Q1-1.5*IQR ~ Q3+1.5*IQR 범위
      - Z-score: |z| > 3 (표준편차 3배)
    
    Returns:
        list: 이상치 인덱스 리스트
    """
    pass
```

---

## 4️⃣ 처리 알고리즘 명세

### 4.1 데이터 수집 알고리즘

```
입력: 1,085개 Master List (pnu, address, complex_name, unit)

단계 1: LG 드라이브 DB 쿼리 (병렬 처리)
  for each record in master_list:
    1. building_registry.db에서 pnu 검색
    2. 전용면적, 준공연도, 층수 추출
    3. 매칭 결과 저장

단계 2: API 호출 (미매칭 데이터)
  for each unmatched record:
    1. 주소 기반 검색 (API)
    2. 지역/동 기반 폴백 검색
    3. 정제 및 검증
    4. 캐시에 저장

단계 3: 데이터 통합
  1. DB 결과 (우선도 100%)
  2. API 결과 (우선도 80%)
  3. 중복 제거 및 정합성 확인

출력: 통합 데이터셋 (building_attributes.csv)
```

### 4.2 AI 예측 알고리즘

```
입력: 정제된 데이터셋 (1,085 × 7 특성)

단계 1: 데이터 전처리
  1. 특성 정규화 (StandardScaler)
  2. 범주 변수 인코딩 (LabelEncoder)
  3. NULL 처리 (median imputation)

단계 2: 3개 모델 병렬 실행
  
  Model v1.0: XGBoost
    - 트리 개수: 100
    - max_depth: 6
    - learning_rate: 0.1
    - 예상 R²: 0.92
  
  Model v1.1: Random Forest + Gradient Boosting
    - RF: 50 트리, max_depth 8
    - GB: 50 iterations
    - 예상 R²: 0.90
  
  Model vF: Voting Ensemble
    - 가중치: XGB(0.4) + RF(0.3) + GB(0.3)
    - 예상 R²: 0.93

단계 3: 신뢰도 계산
  1. 예측값 표준편차 계산
  2. 신뢰도 = exp(-std) * 100
  3. 예측 구간: ±1σ (신뢰도 68%), ±2σ (95%)

단계 4: 마스예측가 계산
  master_price = (v1.0 * 0.3) + (v1.1 * 0.3) + (vF * 0.4)

출력: 예측 결과 (predictions.csv)
```

### 4.3 QC 검증 알고리즘

```
입력: 완성된 Excel 파일 (1,085 × 30컬럼)

검증 규칙:

1. 필드 검증
   - NULL 체크: 모든 필수필드 != NULL
   - 범위 검증: 
     * 면적: 50 ≤ area ≤ 500
     * 가격: 10M ≤ price ≤ 10B
     * 연도: 1950 ≤ year ≤ 2025

2. 일관성 검증
   - ACT vs WEB: |area_act - area_web| / area_act < 5%
   - 가격 로직: official_price < transaction_price < upper_bound
   - 시간 로직: build_year < transaction_date (연도)

3. 예측 검증
   - 예측값 범위: lower_bound < prediction < upper_bound
   - 신뢰도: 0 ≤ confidence ≤ 100
   - R² 점수: > 0.85

4. 이상치 검증
   - 가격 편차: |actual - prediction| / actual < 20%
   - 시세 범위: |actual - market_mid| < 10%

출력: QC Report (통과/실패)
```

---

## 5️⃣ Excel 파일 포맷 명세

### 5.1 Sheet: Report

```
Row 1: "LOAN4U QC REPORT"
Row 2: "2026-06-24"
Row 3: "Verified by: [담당자명]"
Row 4: ""
Row 5: "Summary Statistics:"
Row 6: "  Total Records: 1,085"
Row 7: "  Data Completion: 100%"
Row 8: "  Validation Pass Rate: 99%+"
Row 9: "  Model Performance (R²): 0.88"
Row 10: ""
Row 11: "Outliers Identified: N"
Row 12: "Recommendations: ..."
```

### 5.2 Sheet: 아파트 (258행 × 30열)

**헤더**:
```
1. 연번
2. 시, 3. 군, 4. 구, 5. 동
6. 지번
7. 단지명
8. 동.1 (건물번호)
9. 호 (호수)

10. 주택종류ACT, 11. 주택종류WEB
12. 전용면적ACT, 13. 전용면적WEB
14. 준공연도ACT, 15. 준공연도WEB

16. INDEX FOR RAW TABLE
17. INDEX FOR AIpredict

18. 세대수ACT, 19. 세대수WEB
20. 공시가격ACT, 21. 공시가격WEB
22. 실거래일

23. 실거래가격ACT, 24. 실거래가격WEB
25. 마스예측가ACT
26. 마스예측가WEB(구)
27. 마스예측가WEB(신)

28. 건축물대장(O/X)
29. 토지이용계획원(O/X)
30. 등기부등본(O/X)
```

**데이터 타입**:
| 컬럼 | 타입 | 범위 | 포맷 | 예시 |
|------|------|------|------|------|
| 연번 | Integer | 1-258 | # | 1 |
| 시 | String | 한글 | Text | 서울특별시 |
| 구 | String | 한글 | Text | 강남구 |
| 동 | String | 한글 | Text | 청담동 |
| 지번 | Integer | 1-9999 | # | 129 |
| 단지명 | String | - | Text | PH129(더펜트하우스청담) |
| 호 | Float | 1-9999 | #.0 | 1603.0 |
| 주택종류 | String | 아파트/오피스텔 | Text | 아파트 |
| 전용면적 | Float | 50-500 | #.00 | 110.50 |
| 준공연도 | Integer | 1950-2025 | YYYY | 2015 |
| 공시가격 | Integer | 1M-10B | # | 650000000 |
| 실거래가격 | Integer | 1M-10B | # | 680000000 |
| 마스예측가 | Integer | 1M-10B | # | 675500000 |
| O/X | String | O/X | Text | O |

### 5.3 유효성 검사 (Data Validation)

```
연번: 1 ~ 258 (목록)
주택종류: 아파트, 오피스텔 (드롭다운)
전용면적: 50 ≤ x ≤ 500 (숫자)
준공연도: 1950 ≤ x ≤ 2025 (숫자)
가격 필드: 1000000 ≤ x ≤ 10000000000 (숫자)
O/X 필드: O, X, 미조사 (드롭다운)
```

---

## 6️⃣ QC 검증 규칙

### 6.1 검증 기준

| 검증항목 | 기준 | 합격 | 부합 |
|---------|------|------|------|
| 필드 완성도 | 입력률 > 95% | ✅ | |
| 범위 검증 | 이상치 < 2% | ✅ | |
| 일관성 | 편차 < 5% | ✅ | |
| 예측 성능 | R² > 0.85 | ✅ | |
| 신뢰도 | 90% < confidence < 100% | ✅ | |

### 6.2 오류 분류

**Critical**: 데이터 타입 오류, NULL 필수필드
```
→ 수정 필수, 재검증 필요
```

**Major**: 범위 초과, 논리 오류
```
→ 재입력 또는 설명 필요
```

**Minor**: 미세한 편차, 형식 오류
```
→ 기록만 유지, 영향 없음
```

---

## 📝 구현 참고사항

### Python 라이브러리

```python
# 데이터 처리
pandas >= 1.3.0
numpy >= 1.21.0
openpyxl >= 3.7.0

# API 호출
requests >= 2.26.0
aiohttp >= 3.8.0  # 비동기 요청

# 머신러닝
scikit-learn >= 1.0.0
xgboost >= 1.5.0
lightgbm >= 3.3.0

# 데이터베이스
sqlite3  # 내장
sqlalchemy >= 1.4.0

# 로깅 및 모니터링
logging  # 내장
tqdm >= 4.62.0
```

### 에러 처리

```python
class APIError(Exception):
    """API 호출 실패"""
    pass

class DataNotFoundError(Exception):
    """데이터 미발견"""
    pass

class DataValidationError(Exception):
    """데이터 검증 실패"""
    pass

class QCError(Exception):
    """QC 검증 실패"""
    pass
```

---

**명세 작성**: 2026-06-24  
**버전**: 1.0  
**다음 단계**: WBS 작성 → 독립 검토
