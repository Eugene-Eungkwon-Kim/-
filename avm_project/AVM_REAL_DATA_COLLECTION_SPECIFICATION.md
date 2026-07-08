# AVM 실거래 데이터 수집 & 모델 재학습 사양서

**프로젝트**: NPL AVM (자동평가 모델)  
**작성일**: 2026-07-03  
**버전**: 1.0  
**상태**: 진행 예정  

---

## 1. 프로젝트 개요

### 목표
현재 **합성 데이터(synthetic) 기반 AVM 모델**을 **실거래 데이터 기반 모델**로 전환하여 실제 대출 심사에 투입 가능한 수준으로 검증

### 문제 정의
```
현재 상태:
  ├─ 데이터: 100% 합성 데이터 (실거래 0건)
  ├─ 성능: R² = 0.949, MAPE = 11.2% (목표 <10.5% → FAIL)
  └─ 신뢰도: 미검증 (합성 데이터 환경에서만 유효)

목표 상태:
  ├─ 데이터: 실거래 데이터 기반
  ├─ 성능: R² > 0.94, MAPE < 10.5%
  └─ 신뢰도: 실제 거래 환경에서 검증됨
```

### 성공 기준
| 항목 | 목표 | 현재 | 검증방법 |
|------|------|------|---------|
| 실거래 데이터 건수 | ≥50,000건 | 0건 | DB 행 수 확인 |
| R² (결정계수) | >0.94 | 0.949 | 모델 평가 스크립트 |
| MAPE (평균절대백분율) | <10.5% | 11.2% | 모델 평가 스크립트 |
| 데이터 시간범위 | 12개월 이상 | N/A | 날짜 범위 확인 |
| API 수집률 | >95% | N/A | 로그 분석 |

---

## 2. 기술 사양

### 2.1 데이터 소스

#### 국토부 공공 API
```
서비스명: 아파트매매 실거래자료 (오픈API)
제공처: 국토교통부 (data.go.kr)
데이터종류:
  ├─ 아파트 (APT_DEAL_TBL)
  ├─ 다세대/연립 (MULTI_DEAL_TBL)
  └─ 오피스텔 (OFFICE_DEAL_TBL)

수집 범위:
  ├─ 지역: 전국 (243개 시군구)
  ├─ 기간: 최근 12개월 (2025-07 ~ 2026-06)
  └─ 정렬: 월별, 시군구별

API 특성:
  ├─ Rate Limit: ~0.3초/요청 (안전한계)
  ├─ 응답형식: XML
  └─ 인증: API 키 기반
```

#### 필수 API 키 설정
```bash
# .env 파일에 추가
KOREA_API_KEY=<발급받은 키>
```

### 2.2 데이터 스키마

#### transactions 테이블 (신규 생성)
```sql
CREATE TABLE transactions (
  id INTEGER PRIMARY KEY,
  sgg_code VARCHAR(10),            -- 시군구 코드
  property_type VARCHAR(20),        -- 아파트/다세대/오피스텔
  complex_name VARCHAR(255),        -- 단지명
  address_dong VARCHAR(255),        -- 주소(동)
  address_jibun VARCHAR(255),       -- 주소(지번)
  
  contract_year INTEGER,            -- 계약연도
  contract_month INTEGER,           -- 계약월
  contract_day INTEGER,             -- 계약일
  
  price_manwon INTEGER,             -- 거래금액(만원)
  exclusive_area FLOAT,             -- 전용면적(㎡)
  floor INTEGER,                    -- 층수
  
  build_year INTEGER,               -- 건축연도
  seller_type VARCHAR(50),          -- 판매자 유형
  buyer_type VARCHAR(50),           -- 구매자 유형
  
  transaction_key VARCHAR(255) UNIQUE,  -- 중복 방지 해시
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sgg_code ON transactions(sgg_code);
CREATE INDEX idx_contract_date ON transactions(contract_year, contract_month);
CREATE INDEX idx_property_type ON transactions(property_type);
```

### 2.3 데이터 처리 파이프라인

```
API 요청
  ↓ [XML 응답]
파싱 (KoreaLandAPI)
  ↓ [TransactionRecord 객체]
검증 & 정제 (품질 기준 적용)
  ├─ NULL 값 제거
  ├─ 범위 검사 (면적, 가격, 건축연도)
  ├─ 중복 확인 (transaction_key)
  └─ 이상값 필터링
  ↓ [정제된 레코드]
DB 적재 (bulk_ingest_transactions)
  ├─ 삽입 (INSERT)
  ├─ 중복 무시 (UNIQUE 제약)
  └─ 통계 기록 (삽입/중복/오류 건수)
  ↓
DB 저장
```

### 2.4 데이터 품질 기준 (정량화)

#### 필수 품질 기준
```
모든 거래는 다음 조건을 만족해야 포함:

1. 거래금액 (price_manwon)
   ├─ 최소: 10,000만원 (1억원)
   ├─ 최대: 500,000만원 (5억원)
   └─ 범위 외 제거: 거래이상 또는 금융상품

2. 전용면적 (exclusive_area)
   ├─ 최소: 10㎡ (오피스텔/다세대)
   ├─ 최대: 300㎡ (일반 주택)
   └─ 범위 외 제거: 개별공시지가 아님

3. 건축연도 (build_year)
   ├─ 최소: 1950년 (한국전쟁 이후)
   ├─ 최대: 2026년 (현재)
   ├─ NULL 허용: 아니오 (결측은 제거)
   └─ 건축 예정: 제거 (미완성 건물)

4. 거래일자 (contract_year, month, day)
   ├─ NULL 허용: 아니오
   ├─ 유효 범위: 2025-07 ~ 2026-06 (12개월)
   └─ 미래일: 제거

5. 중복 제거
   ├─ 고유 키: transaction_key (해시)
   ├─ 계산식: MD5(sgg_code|property_type|complex_name|area|date|price)
   └─ 중복 기준: 정확히 같은 키 = 중복
```

#### 검증 쿼리
```sql
-- 수집 후 검증
SELECT
  COUNT(*) as total_records,
  COUNT(DISTINCT sgg_code) as unique_regions,
  COUNT(DISTINCT property_type) as property_types,
  MIN(price_manwon) as min_price,
  MAX(price_manwon) as max_price,
  MIN(exclusive_area) as min_area,
  MAX(exclusive_area) as max_area,
  MIN(build_year) as min_build_year,
  MAX(build_year) as max_build_year,
  SUM(CASE WHEN price_manwon < 10000 OR price_manwon > 500000 THEN 1 ELSE 0 END) as price_outliers,
  SUM(CASE WHEN exclusive_area < 10 OR exclusive_area > 300 THEN 1 ELSE 0 END) as area_outliers,
  SUM(CASE WHEN build_year < 1950 OR build_year > 2026 THEN 1 ELSE 0 END) as year_outliers
FROM transactions;

-- 중복 확인
SELECT COUNT(*) as duplicate_count
FROM (
  SELECT transaction_key
  FROM transactions
  GROUP BY transaction_key
  HAVING COUNT(*) > 1
);
-- 기대값: 0 (UNIQUE 제약으로 보장)
```

#### 품질 목표
```
✓ 결측률: < 5% (NULL 또는 범위 외)
✓ 이상값 비율: < 3% (범위 외)
✓ 중복 비율: 0% (고유 키로 보장)
✓ 데이터 수용률: > 95% (수집 대비 실제 저장)
```

### 2.5 API 호출 최적화 전략

#### 요청 전략
```
1. 배치 처리
   ├─ 단위: 시군구(SGG) × 월(month) 단위로 분산
   ├─ 병렬도: 3~5개 워커 (동시 요청)
   └─ 이유: 계정 rate limit 회피, 안정성

2. Rate Limiting
   ├─ 최소 지연: 0.3초/요청 (안전)
   ├─ 권장 지연: 0.5초/요청 (안정성 중시)
   └─ 계산: 8,748회 × 0.5초 = 4,374초 = 1.2시간 (순차)
           = ~30분 (병렬도 3, 오버헤드 제외)

3. 재시도 전략 (Exponential Backoff)
   ├─ 최대 재시도: 3회
   ├─ 대기 시간: 2^retry 초
   │   ├─ 재시도 1: 2초
   │   ├─ 재시도 2: 4초
   │   └─ 재시도 3: 8초
   └─ 대상 오류: API 타임아웃, 503 서버 오류, 연결 실패

4. 오류 처리
   ├─ 일시적 오류: 자동 재시도 (위 전략)
   ├─ 영구적 오류: 로깅 후 스킵
   │   ├─ 401 인증 실패 → API 키 검증 필요
   │   ├─ 404 없음 → 데이터 없음 (정상)
   │   └─ 400 잘못된 요청 → SGG 코드 검증
   └─ 타임아웃: 30초 (기본값)
```

#### 병렬 처리 구현
```python
# fetch_transactions_parallel.py 사용
python scripts/fetch_transactions_parallel.py \
  --months 12 \
  --workers 3 \
  --checkpoint data/collection_checkpoint.json

# 파라미터 설명:
# --workers: 병렬 프로세스 수 (권장 2~5)
# --checkpoint: 체크포인트 파일 (중단 시 재개)

# 진행 모니터링:
# - 실시간 진도 표시 (tqdm)
# - 1시간마다 통계 출력
# - 체크포인트 자동 저장 (5분마다)
```

#### 모니터링 지표
```
수집 중:
  ├─ 처리율: 건수/시간 (목표: >15,000건/시간)
  ├─ 성공률: 삽입/(삽입+오류) (목표: >99%)
  ├─ API 응답시간: 평균 < 1초
  └─ 워커 CPU: < 50%

수집 후:
  ├─ 총 수집 건수: >= 850,000건
  ├─ 데이터 수용률: > 95%
  ├─ 소요시간: <= 30시간 (병렬)
  └─ 저장소 사용: ~150MB (DB 파일)
```

### 2.4 모델 재학습 파이프라인

```
실거래 데이터 (transactions 테이블)
  ↓ [특성 공학]
feature_engineering.py
  ├─ 시간 기반 특성 (계약연도, 계약월)
  ├─ 공간 기반 특성 (시도, 시군구)
  ├─ 건물 특성 (건축연도, 건물유형)
  └─ 가격 기반 특성 (㎡당 가격)
  ↓
pairing_engine.py (비교사례 쌍 생성)
  ├─ 같은 시군구 + 같은 건물유형
  ├─ 건축연도 차이 ≤3년
  └─ 면적 유사도 >90%
  ↓
unified_training.py (모델 학습)
  ├─ 모델: XGBoost + Ridge Regression 앙상블
  ├─ 데이터: 80% 훈련, 20% 검증
  ├─ 하이퍼파라미터: 랜덤 서치 (5-fold CV)
  └─ 목표: R² >0.94, MAPE <10.5%
  ↓
trained_model.pkl (저장)
  ↓
validation_script.py (검증)
  ├─ 테스트 세트 성능 평가
  ├─ 잔차 분석
  ├─ 피처 중요도 분석
  └─ 보고서 생성
```

---

## 3. 작업 규모 및 일정

### 3.1 데이터 수집 규모

```
시군구당 예상 데이터:
  ├─ 아파트: ~200~500건/월
  ├─ 다세대: ~50~150건/월
  └─ 오피스텔: ~20~50건/월
  = 약 300~700건/시군구/월

전국 (243개 시군구) × 12개월:
  = 약 872,000 ~ 2,037,600건 (목표: ≥50,000건)

API 호출:
  ├─ 아파트: 243 SGG × 12월 = 2,916회
  ├─ 다세대: 243 SGG × 12월 = 2,916회
  ├─ 오피스텔: 243 SGG × 12월 = 2,916회
  = 총 8,748회 (rate limit: 0.3초/회)
  
예상 소요시간:
  = 8,748회 × 0.3초 = 2,624초 ≈ 44분
```

### 3.2 일정 계획

| 단계 | 기간 | 주요활동 | 성과물 |
|------|------|---------|--------|
| **1단계** | 07-03 (Today) | API 키 신청 & 설정 | KOREA_API_KEY 설정 |
| **2단계** | 07-04 | Pilot 수집 (경기도 2개월) | ~10,000건 테스트 데이터 |
| **3단계** | 07-05~07 | 검증 & 확대 (전국 12개월) | ~870,000건 실거래 데이터 |
| **4단계** | 07-08~10 | 모델 재학습 & 검증 | trained_model.pkl + 평가 보고서 |
| **5단계** | 07-11~12 | 배포 준비 & 검증 | 배포 체크리스트 완료 |

---

## 4. 구현 상세

### 4.1 Step 1: API 키 설정 (2시간)

#### 작업 내용
```
1. data.go.kr 접속 (https://www.data.go.kr/)
2. "아파트매매 실거래자료" 검색
3. "국토교통부_아파트매매 실거래자료" 선택
4. [활용신청] 클릭
5. API 키 발급 대기 (~24시간)
6. .env 파일 수정:
   KOREA_API_KEY=발급받은_키
7. 연결 테스트:
   python scripts/test_korea_api.py --sgg 41590 --year 2026 --month 6
```

#### 예상 결과
```
✓ API 연결 성공
✓ 샘플 데이터 5건 수신
✓ 파싱 성공
```

### 4.2 Step 2: Pilot 수집 (4시간)

#### 작업 내용
```bash
# 경기도 (41xxx), 2026년 6월만 수집 (소규모 테스트)
cd F:\NPL전례\avm_project
python scripts/fetch_transactions.py --year 2026 --month 6 --sido 경기도
```

#### 예상 로그
```
2026-07-04 10:00:00 [INFO] ▶ 2026-06 수집 시작 (SGG: 31개, 유형: 아파트,다세대,오피스텔)
2026-07-04 10:05:00 [INFO] 진도: 10/31 | 삽입 2,341 / 중복 156
2026-07-04 10:10:00 [INFO] 진도: 20/31 | 삽입 4,852 / 중복 289
2026-07-04 10:15:00 [INFO] ✓ 2026-06 완료: 삽입 7,234 / 중복 423 / 오류 0
```

#### 검증 항목
```
✓ DB 레코드 확인: SELECT COUNT(*) FROM transactions;
✓ 데이터 샘플 확인: SELECT * FROM transactions LIMIT 10;
✓ 중복 검사: SELECT COUNT(*) FROM transactions GROUP BY transaction_key HAVING COUNT(*) > 1;
```

### 4.3 Step 3: 전국 수집 (72시간)

#### 작업 내용
```bash
# 최근 12개월 전국 전체 수집
python scripts/fetch_transactions.py --months 12
```

#### 병렬 처리 옵션 (권장)
```python
# scripts/fetch_transactions_parallel.py (신규 작성)
# 지역별 병렬 처리로 소요시간 단축
# 병렬도: 5 (동시 5개 시군구)
# 예상 소요시간: 72시간 → 15시간
```

#### 모니터링
```
- 매 10개 시군구마다 진도 표시
- 1시간마다 로그 백업
- 오류 발생 시 자동 재시도 (최대 3회)
```

### 4.4 Step 4: 모델 재학습 (48시간)

#### 작업 1: 데이터 전처리 (4시간)
```bash
python scripts/p6_extract_prepare_data.py \
  --source transactions \
  --output data/training_data.csv \
  --min_records 1000 \
  --filters "price_manwon > 10000 and exclusive_area > 10"
```

#### 작업 2: 특성 공학 (8시간)
```bash
python scripts/p6_feature_engineering.py \
  --input data/training_data.csv \
  --output data/training_engineered.csv \
  --features [time, location, building, price]
```

#### 작업 3: 비교사례 쌍 생성 (8시간)
```bash
python scripts/p6_pairing_engine.py \
  --input data/training_engineered.csv \
  --output data/training_pairs.csv \
  --similarity_threshold 0.9
```

#### 작업 4: 모델 학습 (20시간)
```bash
python scripts/p5_unified_training.py \
  --input data/training_pairs.csv \
  --output models/trained_model.pkl \
  --cv_folds 5 \
  --random_seed 42
```

#### 작업 5: 검증 & 평가 (8시간)
```bash
python scripts/p7_generate_evaluation_results.py \
  --model models/trained_model.pkl \
  --test_data data/test_pairs.csv \
  --output reports/model_evaluation.json
```

#### 성과물
```
✓ models/trained_model.pkl (학습된 모델)
✓ reports/model_evaluation.json (성능 지표)
✓ reports/feature_importance.csv (피처 중요도)
✓ reports/residual_analysis.json (잔차 분석)
```

### 4.5 Step 5: 배포 준비 (16시간)

#### 작업 1: API 통합 (4시간)
```bash
# app/avm/engine.py에 새 모델 통합
python -c "
import pickle
with open('models/trained_model.pkl', 'rb') as f:
    model = pickle.load(f)
    print(f'모델 로드 성공: {type(model)}')
"
```

#### 작업 2: API 엔드포인트 테스트 (6시간)
```bash
# 서버 실행
uvicorn app.main:app --reload --port 8000

# 테스트 요청 (100건)
python tests/api_smoke_test.py --num_requests 100
```

#### 작업 3: 성능 벤치마크 (4시간)
```
- 응답시간: P95 < 1000ms
- 처리량: > 100 req/s
- 메모리 사용: < 500MB
- CPU 사용률: < 50%
```

#### 작업 4: 배포 체크리스트 (2시간)
```
✓ 코드 리뷰 완료
✓ 단위 테스트 통과 (100%)
✓ 통합 테스트 통과
✓ 성능 기준 충족
✓ 보안 검사 통과
✓ 문서화 완료
```

---

## 5. 리스크 및 대응

| 위험 | 영향 | 확률 | 대응 계획 |
|------|------|------|---------|
| API 키 승인 지연 | 1주 지연 | 중(30%) | - 사전에 2개 계정으로 신청 |
| 네트워크 단절 | 수집 중단 | 낮(5%) | - 체크포인트 기반 재개 가능 |
| 이상 데이터 증가 | 모델 성능 저하 | 중(25%) | - 자동 필터링 강화 |
| 하드웨어 부족 | 학습 실패 | 낮(10%) | - 미니배치 처리 (256개) |

---

## 6. 성공 기준 재정의

### 6.1 데이터 품질
```
✓ 실거래 데이터 ≥50,000건 확보
✓ 데이터 결손률 <5%
✓ 이상값 범위 내 (<3σ)
✓ 시간 범위 12개월 이상
```

### 6.2 모델 성능
```
✓ R² > 0.94 (목표 달성)
✓ MAPE < 10.5% (목표 달성)
✓ RMSE < 100,000,000원
✓ 모든 부분군에서 성능 일관성 유지
```

### 6.3 운영 준비
```
✓ API 응답시간 P95 < 1000ms
✓ 시스템 가용성 > 99.9%
✓ 모니터링 & 로깅 완성
✓ 배포 문서 & 롤백 계획 완성
```

---

## 7. 최종 산출물

```
AVM_PROJECT/
├── data/
│   ├── npl_avm.db (확장됨, 870K건)
│   ├── training_data.csv
│   ├── training_engineered.csv
│   └── training_pairs.csv
├── models/
│   └── trained_model.pkl (신규, 실거래 기반)
├── reports/
│   ├── model_evaluation.json
│   ├── feature_importance.csv
│   ├── residual_analysis.json
│   ├── api_performance_report.json
│   └── FINAL_REPORT.md
├── scripts/
│   ├── fetch_transactions_parallel.py (신규)
│   └── test_korea_api.py (신규)
└── logs/
    ├── data_collection_2026-07-04.log
    ├── data_collection_2026-07-05.log
    └── model_training_2026-07-08.log
```

---

## 승인 및 서명

| 역할 | 이름 | 날짜 | 서명 |
|------|------|------|------|
| Project Manager | - | 2026-07-03 | ☐ |
| Technical Lead | - | 2026-07-03 | ☐ |
| Data Engineer | - | 2026-07-03 | ☐ |

