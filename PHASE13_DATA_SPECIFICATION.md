# Phase 13 데이터 명세서

**문서 ID**: SPEC-2026-08-04-001  
**버전**: 1.0  
**작성일**: 2026-08-04  
**상태**: 진행 중  

---

## 1. API 명세

### 1.1 VWorld API 전수 목록

#### Layer 1: Search API 2.0
```
엔드포인트: https://api.vworld.kr/req/search
메서드:     GET
요청:       
  service=search&request=search&version=2.0
  &query={address}&type=address&category=road
  &format=json&key={API_KEY}
응답:       JSON
  {
    "response": {
      "result": {
        "items": [
          {
            "id": "string",
            "name": "string",
            "address": {"full": "string", "name": "string"},
            "point": {"x": float, "y": float}
          }
        ]
      }
    }
  }
데이터타입: JSON
타임아웃:   30초
재시도:     3회 (1, 2, 4초)
QPS 제한:   제한 없음 (확인 필요)
키 상태:    ✅ 정상 (테스트됨)
현황:       ✅ 186개 수집 완료
```

#### Layer 2: Geocoder API 2.0
```
엔드포인트: https://api.vworld.kr/req/address
메서드:     GET
요청:
  service=address&request=getcoord&version=2.0
  &address={address}&type=road&crs=epsg:4326
  &format=json&key={API_KEY}
응답:       JSON
  {
    "response": {
      "result": [
        {
          "point": {"x": float, "y": float},
          "level": "string",
          "accuracy": "string"
        }
      ]
    }
  }
타임아웃:   30초
재시도:     3회
키 상태:    🟡 부분 작동 (권한 문제)
현황:       🟡 1개 레이어만 성공
```

#### Layer 3: WFS (Web Feature Service)
```
엔드포인트: https://api.vworld.kr/req/wfs
메서드:     GET
요청:
  service=WFS&request=GetFeature&version=2.0.0
  &typename={typename}&bbox={bbox}&srsname=EPSG:4326
  &output=application/json&maxfeatures={maxfeatures}
  &key={API_KEY}&domain=localhost

WFS 레이어 목록:
  lp_pa_cbnd_bubun    (연속지적도 - 필지)
  lp_pa_bldg          (건물 - 용도별)
  lp_pa_bldg_geom     (GIS 건물일반)
  lp_pa_bldg_intgr    (GIS 건물통합)
  lp_pa_cco           (지형)
  lp_pa_lnd           (토지)

응답:       GeoJSON
  {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {...},
        "properties": {...}
      }
    ]
  }
타임아웃:   30초
재시도:     3회
키 상태:    🔴 실패 (JSON 파싱 에러)
현황:       🔴 186개 주소 모두 실패
```

#### Layer 11: data.go.kr 아파트 거래
```
엔드포인트: http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev
메서드:     GET
요청:
  serviceKey={KEY}&LAWD_CD={광역시도코드}
  &DEAL_YMD={거래년월}&pageNo=1&numOfRows=10

응답:       XML (한국 공공API 표준)
  <?xml version="1.0" encoding="UTF-8"?>
  <response>
    <body>
      <items>
        <item>
          <아파트이름>...</아파트이름>
          <거래금액>...</거래금액>
          <거래년월일>...</거래년월일>
        </item>
      </items>
    </body>
  </response>

키 상태:    🟡 타임아웃 (네트워크 지연)
현황:       🟡 0개 (재시도 필요)
```

### 1.2 대체 API (우회용)

#### NGIS (국토정보플랫폼) WFS
```
엔드포인트: https://map.ngis.go.kr/ws/wfs
메서드:     GET
인증:       없음 (공개 API)

사용 가능 레이어:
  - LT_C_LULC_07: 토지이용계획
  - SD_TOPO_CONTOUR: 지형 (등고선)
  - WC_MappingDataBox: 지적 테이터

장점: 인증 불필요, 타임아웃 낮음
단점: 정확도/세밀도 낮을 수 있음

현황: 샘플 테스트 예정 (Day 8+)
```

#### 주소정보제공 공식 API
```
엔드포인트: https://business.juso.go.kr/addrlink/addrLinkApi.do
메서드:     GET
요청:
  confmKey={KEY}&keyword={address}
  &currentPage=1&countPerPage=1&resultType=json

응답:       JSON
  {
    "results": {
      "juso": [
        {
          "admCd": "11110",
          "bdMgtSn": "0000110000",
          "roadFullAddr": "서울특별시 종로구 세종대로..."
        }
      ]
    }
  }

기능: 주소 → PNU 변환
키 상태:    ✅ 정상
현황:       🔄 PNU 매핑 진행 중
```

---

## 2. 데이터베이스 스키마

### 2.1 SQLite 전체 테이블

```sql
-- Layer 1-3: 지리정보
CREATE TABLE layer1_search20 (
  id INTEGER PRIMARY KEY,
  api_id TEXT UNIQUE,          -- 검색 객체 ID
  name TEXT,                   -- 이름
  address TEXT,                -- 주소 (문자열로 변환됨)
  lat REAL, lon REAL,          -- 좌표
  search_type TEXT,            -- 검색 타입
  category TEXT,               -- 카테고리
  data_json TEXT,              -- 원본 API 응답
  collected_at TIMESTAMP
);

CREATE TABLE layer2_geocoder20 (
  id INTEGER PRIMARY KEY,
  address TEXT UNIQUE,         -- 조회 주소
  lat REAL, lon REAL,          -- 결과 좌표
  level TEXT,                  -- 정확도 레벨
  accuracy TEXT,               -- 정확도 판정
  data_json TEXT,
  collected_at TIMESTAMP
);

CREATE TABLE layer3_wfs_reference (
  id INTEGER PRIMARY KEY,
  layer_name TEXT UNIQUE,      -- WFS 레이어 이름
  layer_id TEXT,               -- 레이어 ID
  geom_type TEXT,              -- 지오메트리 타입
  feature_count INTEGER,       -- 피처 개수
  data_json TEXT,
  collected_at TIMESTAMP
);

-- Layer 4-7: 건물/토지 (WFS)
CREATE TABLE layer4_cadastral_map (
  id INTEGER PRIMARY KEY,
  quad_id TEXT UNIQUE,         -- 사각형 ID (연속지적도)
  lot_number TEXT,             -- 지번
  area REAL,                   -- 면적 (m²)
  owner TEXT,                  -- 소유자
  zoning TEXT,                 -- 용도지역
  geom TEXT,                   -- WKT 형식 지오메트리
  data_json TEXT,
  collected_at TIMESTAMP
);

CREATE TABLE layer5_building_by_use (
  id INTEGER PRIMARY KEY,
  building_id TEXT UNIQUE,     -- 건물 ID
  use_code TEXT,               -- 용도 코드
  use_name TEXT,               -- 용도 이름
  count INTEGER,               -- 개수
  data_json TEXT,
  collected_at TIMESTAMP
);

CREATE TABLE layer6_gis_building_general (
  id INTEGER PRIMARY KEY,
  building_id TEXT UNIQUE,
  geom TEXT,                   -- GIS 지오메트리
  height REAL,                 -- 높이 (m)
  stories INTEGER,             -- 층수
  material TEXT,               -- 재질
  address TEXT,
  data_json TEXT,
  collected_at TIMESTAMP
);

CREATE TABLE layer7_gis_building_integrated (
  id INTEGER PRIMARY KEY,
  building_id TEXT UNIQUE,
  address TEXT,
  geom TEXT,
  attributes TEXT,            -- 통합 속성 (JSON)
  data_json TEXT,
  collected_at TIMESTAMP
);

-- Layer 8-10: 토지특성
CREATE TABLE layer8_land_characteristics (
  id INTEGER PRIMARY KEY,
  lot_id TEXT UNIQUE,          -- PNU
  slope TEXT,                  -- 경사도
  soil_type TEXT,              -- 토양 타입
  water_accessibility TEXT,    -- 수접근성
  data_json TEXT,
  collected_at TIMESTAMP
);

CREATE TABLE layer9_land_use_plan (
  id INTEGER PRIMARY KEY,
  area_id TEXT UNIQUE,         -- PNU
  plan_zone TEXT,              -- 용도지역
  height_limit REAL,           -- 높이 제한 (m)
  coverage_rate REAL,          -- 건폐율
  data_json TEXT,
  collected_at TIMESTAMP
);

CREATE TABLE layer10_land_right_register (
  id INTEGER PRIMARY KEY,
  lot_id TEXT,                 -- PNU
  right_type TEXT,             -- 권리 타입 (소유권, 전세권 등)
  owner TEXT,                  -- 소유자/권리자
  registration_date TEXT,      -- 등기일
  data_json TEXT,
  collected_at TIMESTAMP,
  UNIQUE(lot_id, right_type, owner)
);

-- Layer 11-14: 공시가격
CREATE TABLE layer11_apart_housing_price (
  id INTEGER PRIMARY KEY,
  apt_id TEXT,                 -- 아파트 ID
  address TEXT,                -- 주소
  price_per_m2 REAL,           -- m² 당 가격 (원)
  price_total REAL,            -- 총 가격 (원)
  price_date TEXT,             -- 공시 기준일 (YYYYMM)
  data_json TEXT,
  collected_at TIMESTAMP,
  UNIQUE(apt_id, price_date)
);

CREATE TABLE layer12_individual_house_price (
  id INTEGER PRIMARY KEY,
  house_id TEXT,
  address TEXT,
  price_per_m2 REAL,
  price_total REAL,
  price_date TEXT,
  data_json TEXT,
  collected_at TIMESTAMP,
  UNIQUE(house_id, price_date)
);

CREATE TABLE layer13_land_price_region (
  id INTEGER PRIMARY KEY,
  region_code TEXT,            -- 지역 코드 (5자리)
  year INTEGER,                -- 연도
  change_rate REAL,            -- 변동률 (%)
  price_index REAL,            -- 가격지수 (100=기준연도)
  data_json TEXT,
  collected_at TIMESTAMP,
  UNIQUE(region_code, year)
);

CREATE TABLE layer14_land_price_usage (
  id INTEGER PRIMARY KEY,
  use_code TEXT,               -- 용도 코드
  year INTEGER,
  change_rate REAL,
  price_index REAL,
  data_json TEXT,
  collected_at TIMESTAMP,
  UNIQUE(use_code, year)
);

-- 메타데이터
CREATE TABLE api_call_log (
  id INTEGER PRIMARY KEY,
  api_name TEXT,               -- API 이름
  layer TEXT,                  -- 레이어
  http_status INTEGER,         -- HTTP 상태코드
  rows_fetched INTEGER,        -- 수집 행 수
  error_message TEXT,          -- 에러 메시지
  call_time_ms INTEGER,        -- 응답 시간 (ms)
  called_at TIMESTAMP
);

CREATE TABLE data_quality_metrics (
  id INTEGER PRIMARY KEY,
  layer TEXT UNIQUE,
  total_rows INTEGER,
  null_count INTEGER,
  duplicate_count INTEGER,
  null_rate REAL,              -- Null 비율 (%)
  quality_score REAL,          -- 품질점수 (0-100)
  measured_at TIMESTAMP
);

CREATE TABLE address_pnu_mapping (
  id INTEGER PRIMARY KEY,
  address TEXT UNIQUE,         -- 주소
  pnu TEXT,                    -- 부동산고유번호 (19자리)
  converted_at TIMESTAMP
);
```

### 2.2 인덱스 전략

```sql
-- Layer 1
CREATE INDEX idx_search20_address ON layer1_search20(address);
CREATE INDEX idx_search20_geom ON layer1_search20(lat, lon);

-- Layer 2
CREATE INDEX idx_geocoder20_coords ON layer2_geocoder20(lat, lon);

-- Layer 4
CREATE INDEX idx_cadastral_quad ON layer4_cadastral_map(quad_id);

-- Layer 5
CREATE INDEX idx_building_use ON layer5_building_by_use(use_code);

-- Layer 6-7
CREATE INDEX idx_building_general_addr ON layer6_gis_building_general(address);
CREATE INDEX idx_building_integrated_addr ON layer7_gis_building_integrated(address);

-- Layer 8-10
CREATE INDEX idx_land_char_lot ON layer8_land_characteristics(lot_id);
CREATE INDEX idx_useplan_area ON layer9_land_use_plan(area_id);
CREATE INDEX idx_land_right_lot ON layer10_land_right_register(lot_id);

-- Layer 11-12
CREATE INDEX idx_apart_addr ON layer11_apart_housing_price(address);
CREATE INDEX idx_apart_date ON layer11_apart_housing_price(price_date);
CREATE INDEX idx_house_addr ON layer12_individual_house_price(address);

-- Layer 13-14
CREATE INDEX idx_price_region ON layer13_land_price_region(region_code);
CREATE INDEX idx_price_usage ON layer14_land_price_usage(use_code);

-- PNU 매핑
CREATE INDEX idx_pnu_mapping_pnu ON address_pnu_mapping(pnu);
```

---

## 3. 데이터 수집 명세

### 3.1 수집 규칙

| 규칙 | 정의 | 적용 범위 |
|------|------|---------|
| 중복 제거 | INSERT OR IGNORE (Primary Key) | 모든 Layer |
| Null 처리 | NULL 저장 (필요시 기본값) | 선택 필드 |
| 타입 변환 | 문자열/숫자/JSON으로 변환 | API 응답별 |
| 인코딩 | UTF-8 | 모든 문자 필드 |
| 타임존 | UTC (ISO 8601) | 타임스탐프 |

### 3.2 수집 데이터 샘플

#### Layer 1 Sample
```json
{
  "id": 1,
  "api_id": "search_20260804_001",
  "name": "종로구청",
  "address": "서울특별시 종로구 세종대로 209",
  "lat": 37.5729,
  "lon": 126.9809,
  "search_type": "address",
  "category": "road",
  "data_json": "{...}",
  "collected_at": "2026-08-04T10:37:20+00:00"
}
```

#### Layer 13 Sample
```json
{
  "id": 1,
  "region_code": "11110",
  "year": 2026,
  "change_rate": 0.025,
  "price_index": 135.2,
  "data_json": "{\"region\": \"종로구\"}",
  "collected_at": "2026-08-04T10:40:35+00:00"
}
```

### 3.3 데이터 검증

| 필드 | 타입 | 범위 | 유효성 |
|------|------|------|--------|
| lat | REAL | [-90, 90] | 통과 경우만 저장 |
| lon | REAL | [-180, 180] | 통과 경우만 저장 |
| price | REAL | >0 | Null 또는 양수 |
| year | INTEGER | 2000-2050 | 현실적 연도 |
| address | TEXT | 1-500자 | 공백만 제거 |

---

## 4. 성능 기준

### 4.1 수집 성능

| 메트릭 | 목표 | 현황 |
|--------|------|------|
| Layer당 처리시간 | <10분 | 측정 중 |
| 초당 레코드 | 50+ | 186개/분 ≈ 3개/초 |
| DB 쓰기 시간 | <100ms | 측정 대기 |
| 메모리 사용 | <100MB | 측정 중 |

### 4.2 DB 쿼리 성능

```sql
-- 조회 (1,000행)
SELECT * FROM layer1_search20 WHERE address LIKE '%강남%';
목표: <100ms

-- 집계 (전체 행 수)
SELECT COUNT(*) FROM layer1_search20;
목표: <50ms (인덱스 활용)

-- 조인 (주소-PNU 매핑)
SELECT a.*, p.pnu FROM layer1_search20 a
LEFT JOIN address_pnu_mapping p ON a.address = p.address;
목표: <500ms (1,000행)
```

---

## 5. 데이터 품질 메트릭

### 5.1 현황 (Day 7 기준)

| Layer | 레코드 | Null % | 중복 | 상태 |
|-------|--------|--------|------|------|
| 1 | 186 | 50% (address 필드) | 0 | 🟡 품질 낮음 |
| 2 | 0 | N/A | 0 | 🔴 수집 실패 |
| 3 | 1 | 0% | 0 | ✅ |
| 4-7 | 0 | N/A | 0 | 🔴 API 실패 |
| 8-10 | 11 | 0% | 0 | ✅ 샘플 |
| 11-14 | 45 | 0% | 0 | ✅ |

### 5.2 목표 (Day 21)

- **Null 비율**: <10% (모든 필드)
- **중복**: 0건 (Primary Key)
- **유효성**: 100% (범위 검증)
- **품질점수**: >80/100

---

## 6. 데이터 보안

### 6.1 민감정보 정책

| 정보 | 마스킹 | 기준 |
|------|--------|------|
| 소유자명 | 부분 (성씨만) | GDPR/개인정보보호 |
| 주민번호 | 제거 | 법정 필수 |
| 연락처 | 제거 | 개인정보 |

**현황**: 현재 데이터셋에 민감정보 미포함 (공시 데이터만)

### 6.2 암호화

- DB 파일: 그대로 저장 (로컬 개발)
- 전송: HTTPS (API 통신)
- 백업: TBD (보안 정책 따름)

---

## 7. 데이터 선적 (Data Lineage)

```
VWorld API (Layer 1-3)
    ↓
주소 → PNU 변환 (address_pnu_mapping)
    ↓
NGIS WFS (Layer 8-10)
    ↓
공시가격 API (Layer 11-14)
    ↓
SQLite DB (최종)
    ↓
AVM 학습셋 (10,000 레코드)
```

---

## 부록: 필드 메타데이터

### A.1 Layer 1 필드 정의

| 필드 | 타입 | Null 가능 | 설명 | 예시 |
|------|------|----------|------|------|
| api_id | TEXT | N | API 검색 객체 ID | "search_0001" |
| name | TEXT | Y | 시설/지명 | "종로구청" |
| address | TEXT | Y | 주소 (정제된) | "서울 종로구 세종대로" |
| lat | REAL | Y | 위도 | 37.5729 |
| lon | REAL | Y | 경도 | 126.9809 |
| search_type | TEXT | Y | "address", "place" | "address" |
| category | TEXT | Y | 도로명/지번/POI | "road" |

### A.2 Layer 13 필드 정의

| 필드 | 타입 | Null 가능 | 설명 | 예시 |
|------|------|----------|------|------|
| region_code | TEXT | N | 행정코드 (5자리) | "11110" |
| year | INTEGER | N | 연도 | 2026 |
| change_rate | REAL | Y | 전년대비 변동률 | 0.025 (2.5%) |
| price_index | REAL | Y | 지가지수 (100=기준) | 135.2 |

---

**최종 검수**: (감사자)  
**승인**: (프로젝트 리더)  
**유효 기간**: 2026-08-04 ~ 2026-08-21
