# AVM 실거래 데이터 수집 & 모델 재학습 - WBS (작업 분해도)

**프로젝트**: NPL AVM 실거래 데이터 수집  
**총 소요시간**: 10.5일 (84시간)  
**예산**: 약 16시간/명 × 5명  

---

## 1. 프로젝트 구조 (최상위)

```
AVM 실거래 데이터 수집 & 모델 재학습
├── 1. 준비 단계 (2시간)
├── 2. Pilot 수집 (4시간)
├── 3. 전국 데이터 수집 (72시간)
├── 4. 모델 재학습 (48시간)
├── 5. 배포 준비 (16시간)
└── 6. 최종 검증 & 보고 (4시간)
   
총 합계: 146시간 (약 18일, 병렬처리로 10.5일)
```

---

## 2. 상세 WBS 트리

### **1. 준비 단계 (1.0) [2시간]**

#### 1.1 API 키 신청 (1.1) [0.5시간]
```
담당자: Data Engineer
대상: https://www.data.go.kr/
프로세스:
  ├─ (1.1.1) 사이트 접속 및 회원 로그인
  ├─ (1.1.2) "아파트매매 실거래자료" 검색
  ├─ (1.1.3) 국토교통부 데이터셋 선택
  ├─ (1.1.4) [활용신청] 클릭
  └─ (1.1.5) 신청 완료 (승인 대기)
성과물: 신청 증명 스크린샷
```

#### 1.2 환경 설정 (1.2) [0.5시간]
```
담당자: DevOps Engineer
작업:
  ├─ (1.2.1) API 키 발급 확인
  ├─ (1.2.2) .env 파일 수정
  │   └─ KOREA_API_KEY=발급받은_키
  ├─ (1.2.3) 환경변수 로드 테스트
  └─ (1.2.4) API 연결 확인
  
검증 스크립트:
  python -c "
  import os; from dotenv import load_dotenv
  load_dotenv()
  key = os.getenv('KOREA_API_KEY')
  print('✓ API 키 설정 확인' if key and key != 'your_api_key_here' else '✗ API 키 미설정')
  "
성과물: .env 파일 업데이트
```

#### 1.3 의존성 검증 (1.3) [1시간]
```
담당자: QA Engineer
체크리스트:
  ├─ (1.3.1) requirements.txt 확인
  │   └─ requests, pandas, sqlalchemy, dotenv
  ├─ (1.3.2) DB 연결 테스트
  │   python -c "from app.db.database import SessionLocal; print('✓ DB 연결 가능')"
  ├─ (1.3.3) 파서 모듈 로드 테스트
  │   python -c "from app.integrations.korea_api import KoreaLandAPI; print('✓ API 클라이언트 로드 가능')"
  ├─ (1.3.4) 디렉토리 구조 확인
  │   └─ scripts/, data/, logs/ 디렉토리 존재
  └─ (1.3.5) 로깅 설정 확인
      └─ logs/ 디렉토리 쓰기 권한
성과물: 환경 준비 체크리스트
```

---

### **2. Pilot 수집 (2.0) [4시간]**

#### 2.1 파일럿 계획 (2.1) [1시간]
```
담당자: Project Manager
작업:
  ├─ (2.1.1) 대상 지역 선정: 경기도 (31개 시군구)
  ├─ (2.1.2) 대상 기간: 2026년 6월 (1개월)
  ├─ (2.1.3) 예상 데이터: ~7,000건
  ├─ (2.1.4) 예상 소요시간: 30분
  └─ (2.1.5) 실행 계획서 작성
  
기대효과:
  ├─ API 정상 작동 확인
  ├─ 데이터 품질 초차 검증
  ├─ DB 적재 프로세스 검증
  └─ 성능 기준선 수립
성과물: 파일럿 계획서
```

#### 2.2 파일럿 수집 실행 (2.2) [2시간]
```
담당자: Data Engineer
커맨드:
  cd F:\NPL전례\avm_project
  python scripts/fetch_transactions.py --year 2026 --month 6 --sido 경기도

모니터링:
  ├─ (2.2.1) 수집 진도 실시간 모니터링
  ├─ (2.2.2) API 호출 성공률 기록
  ├─ (2.2.3) 오류 로그 수집
  └─ (2.2.4) 예상 완료시간 vs 실제 완료시간 비교

예상 로그:
  [INFO] ▶ 2026-06 수집 시작 (SGG: 31개, 유형: 3가지)
  [INFO] 진도: 10/31 | 삽입 2,341 / 중복 156
  [INFO] ✓ 2026-06 완료: 삽입 7,234 / 중복 423 / 오류 0

성과물: fetch_transactions.log
```

#### 2.3 파일럿 검증 (2.3) [1시간]
```
담당자: QA Engineer
검증 항목:

(2.3.1) 데이터 건수 확인
  SELECT COUNT(*) FROM transactions;
  → 예상: ~7,234건

(2.3.2) 샘플 데이터 조회
  SELECT * FROM transactions LIMIT 10;
  → 데이터 형식 정상 확인

(2.3.3) 중복 검사
  SELECT COUNT(*) FROM transactions 
  WHERE transaction_key IN (
    SELECT transaction_key FROM transactions 
    GROUP BY transaction_key HAVING COUNT(*) > 1
  );
  → 예상: 0건 (고유 키 유효성)

(2.3.4) 데이터 범위 검사
  - 계약일: 2026-06-01 ~ 2026-06-30 ✓
  - 거래금액: 10,000만원 ~ 5억원 범위 ✓
  - 면적: 10㎡ ~ 300㎡ 범위 ✓

(2.3.5) 성능 지표 기록
  - API 호출: 93회
  - 소요시간: 28분 (기대값: 30분)
  - 성공률: 100%
  - 삽입률: 94.4% (7,234 / 7,657)

성과물: 파일럿 검증 보고서
```

---

### **3. 전국 데이터 수집 (3.0) [72시간 → 병렬: 15시간]**

#### 3.1 수집 전략 수립 (3.1) [2시간]
```
담당자: Data Engineer + Project Manager
작업:

(3.1.1) 병렬 처리 전략 결정
  옵션 A: 순차 처리 (safe, 72시간)
    └─ 지역별 순차 (243 SGG × 12개월)
  
  옵션 B: 병렬 처리 (fast, 15시간) ← 권장
    ├─ 동시 작업 수: 5 (지역별)
    ├─ rate limit: 0.3초/요청 유지
    └─ 모니터링: 실시간 대시보드

(3.1.2) 데이터 수집 순서 결정
  ├─ 우선순위: 서울 → 경기 → 인천 → 강원 → ...
  └─ 이유: 대량 거래 지역 우선 수집 (조기 타당성 검증)

(3.1.3) 체크포인트 전략
  ├─ 월별 체크포인트 (매월 말 중간 저장)
  ├─ 재개 메커니즘 (중단 시 마지막 위치에서 재개)
  └─ 백업 전략 (6시간마다 DB 백업)

(3.1.4) 리소스 할당
  ├─ CPU: 4 cores (병렬 5개 프로세스)
  ├─ 메모리: 4GB
  ├─ 네트워크: 안정적인 연결 필요
  └─ 저장소: 2GB 확보

성과물: 수집 전략 문서
```

#### 3.2 병렬 수집 스크립트 작성 (3.2) [4시간]
```
담당자: Data Engineer
파일: scripts/fetch_transactions_parallel.py (신규 작성)

기능:
  ├─ (3.2.1) 멀티프로세싱 풀 생성 (workers=5)
  ├─ (3.2.2) 지역별 수집 태스크 분배
  ├─ (3.2.3) 진행률 추적 (tqdm)
  ├─ (3.2.4) 오류 복구 (자동 재시도, 최대 3회)
  ├─ (3.2.5) 체크포인트 저장 (JSON)
  └─ (3.2.6) 실시간 통계 출력

예상 코드 구조:
  ```python
  from multiprocessing import Pool
  from app.integrations.korea_api import KoreaLandAPI
  
  def collect_region(sgg_code, year_months):
      api = KoreaLandAPI(...)
      for year, month in year_months:
          records = api.fetch_apt_transactions(sgg_code, year, month)
          bulk_ingest_transactions(session, records)
  
  pool = Pool(5)
  results = pool.map(collect_region, region_tasks)
  ```

성과물: scripts/fetch_transactions_parallel.py
```

#### 3.3 전국 수집 실행 (3.3) [66시간 실제, 병렬: 13시간]
```
담당자: Data Engineer (자동화 실행)
커맨드:

# 순차 방식 (안전하지만 느림)
python scripts/fetch_transactions.py --months 12

# 병렬 방식 (권장, 빠름)
python scripts/fetch_transactions_parallel.py \
  --months 12 \
  --workers 5 \
  --checkpoint data/collection_checkpoint.json \
  --log-level DEBUG

모니터링 대시보드:
  ├─ (3.3.1) 실시간 진도 표시
  │   진도: [████████░░] 243/243 (SGG) × 12/12 (월)
  │   처리율: 125 건/분
  │   남은시간: 4시간 22분
  │
  ├─ (3.3.2) 5분마다 진행상황 저장
  │   └─ data/collection_checkpoint.json
  │
  ├─ (3.3.3) 실시간 통계
  │   삽입: 847,392건
  │   중복: 24,608건
  │   오류: 0건
  │   성공률: 100%
  │
  └─ (3.3.4) 로그 순환 저장
      └─ logs/collection_*.log (1시간 단위)

예상 완료 메시지:
  [INFO] ✓ 전국 12개월 수집 완료
  [INFO] 총 삽입: 847,392건
  [INFO] 총 중복: 24,608건
  [INFO] 소요시간: 13시간 45분
  [INFO] 평균 속도: 61,000건/시간

성과물: 
  ├─ data/npl_avm.db (확장)
  ├─ logs/collection_complete.log
  └─ data/collection_checkpoint.json (최종)
```

#### 3.4 수집 후 검증 (3.4) [4시간]
```
담당자: QA Engineer
검증 스크립트: scripts/validate_collection.py (신규 작성)

(3.4.1) 기본 통계
  SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT sgg_code) as unique_regions,
    MIN(contract_year) || '-' || MIN(contract_month) as earliest_month,
    MAX(contract_year) || '-' || MAX(contract_month) as latest_month,
    COUNT(DISTINCT property_type) as property_types
  FROM transactions;
  
  예상 결과:
  ├─ total_records: ≥ 800,000건
  ├─ unique_regions: = 243개
  ├─ earliest_month: 2025-07
  ├─ latest_month: 2026-06
  └─ property_types: = 3개 (아파트, 다세대, 오피스텔)

(3.4.2) 데이터 품질 검사
  ├─ NULL 값 비율: < 5%
  ├─ 음수 가격: 0건
  ├─ 0 면적: 0건
  ├─ 이상 높이 (> 100층): < 1% (필터링 검토)
  └─ 중복 레코드: 0건 (unique constraint 확인)

(3.4.3) 지역별 분포 검사
  SELECT 
    sgg_code,
    COUNT(*) as cnt,
    ROUND(AVG(price_manwon/10000), 2) as avg_price_eok,
    ROUND(AVG(exclusive_area), 1) as avg_area
  FROM transactions
  GROUP BY sgg_code
  ORDER BY cnt DESC
  LIMIT 20;
  
  예상: 서울, 경기, 인천이 상위 (거래량 많음)

(3.4.4) 시계열 분포 검사
  SELECT 
    contract_year,
    contract_month,
    COUNT(*) as cnt
  FROM transactions
  GROUP BY contract_year, contract_month
  ORDER BY contract_year, contract_month;
  
  예상: 모든 월이 균등하게 데이터 보유

(3.4.5) 성과 지표 기록
  - 데이터 취득률: 99.2% (예상 vs 실제)
  - 저장 공간: DB 파일 크기 = ~150MB
  - 저장소 효율: 847K건 ÷ 150MB = 5.65KB/건

성과물: validate_collection_report.md
```

---

### **4. 모델 재학습 (4.0) [48시간]**

#### 4.1 데이터 전처리 (4.1) [4시간]
```
담당자: Data Engineer
스크립트: scripts/p6_extract_prepare_data.py (기존, 조정)

(4.1.1) 대상 데이터 선정
  SELECT * FROM transactions
  WHERE price_manwon > 10000     -- 최소 1억원
    AND price_manwon < 50000     -- 최대 5억원
    AND exclusive_area > 10      -- 최소 10㎡
    AND exclusive_area < 300     -- 최대 300㎡
    AND build_year > 1950        -- 건축연도 합리적 범위
  ORDER BY contract_year, contract_month;
  
  예상: 약 750,000건 (전체의 88%)

(4.1.2) 이상값 처리
  ├─ 극단값 제거 (1%, 99% 범위 외)
  ├─ NULL 값 처리 (행 제거 vs 중앙값 대체 검토)
  └─ 중복 확인 (transaction_key 기반)

(4.1.3) 학습/테스트 분할
  ├─ Train: 70% (525,000건)
  ├─ Validation: 15% (112,500건)
  └─ Test: 15% (112,500건)
  
  분할 방식: 시간 기반 (최신 15% = 테스트)
  이유: 시계열 성능 평가 가능

(4.1.4) 데이터 저장
  output: data/training_data.csv (750K행 × 15열)
  
  파일 구조:
  sgg_code, property_type, exclusive_area, build_year,
  contract_year, contract_month,
  price_manwon, floor, seller_type, buyer_type, ...

성과물: data/training_data.csv (~120MB)
```

#### 4.2 특성 공학 (4.2) [8시간]
```
담당자: Data Engineer
스크립트: scripts/p6_feature_engineering.py (기존, 확장)

(4.2.1) 시간 기반 특성 (2시간)
  ├─ contract_age = 2026-06 - contract_month (거래 경과 시간)
  ├─ season = 1,2,3,4 (겨울, 봄, 여름, 가을)
  ├─ is_year_end = 1 if month in [11,12] else 0
  ├─ is_spring_market = 1 if month in [3,4,5] else 0
  └─ year_effect = 선형 시간 추세 계수

(4.2.2) 공간 기반 특성 (2시간)
  ├─ sido (시도 인코딩, 예: 서울=1, 경기=2, ...)
  ├─ sgg_cluster = K-means (243개 지역을 10개 클러스터로)
  ├─ distance_to_seoul (서울역까지 거리, 추정)
  └─ metro_accessible = 1 if 지하철 근처 else 0 (sgg_code 기반)

(4.2.3) 건물 특성 (2시간)
  ├─ building_age = 2026 - build_year
  ├─ is_new = 1 if building_age < 5 else 0
  ├─ is_old = 1 if building_age > 30 else 0
  ├─ price_per_area = price_manwon / exclusive_area (기존)
  └─ floor_level = floor 구간화 (저층 1-3, 중층 4-10, 고층 11+)

(4.2.4) 인접 통계 특성 (2시간)
  ├─ neighborhood_median_price = 같은 sgg, 같은 월의 중앙값
  ├─ neighborhood_std = 표준편차
  ├─ price_ratio = 개별 가격 / 이웃 중앙값
  └─ area_quantile = 면적 분위수 (0.1, 0.5, 0.9)

(4.2.5) 결과 저장
  output: data/training_engineered.csv (750K행 × 35열)
  
  특성 목록:
  - 원본: 15개
  - 시간: 5개
  - 공간: 4개
  - 건물: 5개
  - 인접: 4개
  - 파생: 2개
  = 총 35개 특성

성과물: data/training_engineered.csv (~200MB)
```

#### 4.3 비교사례 쌍 생성 (4.3) [8시간]
```
담당자: Data Engineer
스크립트: scripts/p6_pairing_engine.py (기존, 최적화)

(4.3.1) 쌍 생성 전략
  핵심: 비슷한 물건 2개를 비교 (예: 가격 차이 설명)
  
  매칭 조건:
  ├─ 같은 시군구 (sgg_code)
  ├─ 같은 물건 유형 (property_type)
  ├─ 건축연도 차이 ≤ 3년
  ├─ 면적 유사도 ≥ 90% (larger/smaller ≥ 0.9)
  └─ 계약 시간 간격: 1개월 ~ 12개월
  
  유사도 계산:
  similarity = min(area1, area2) / max(area1, area2)

(4.3.2) 쌍 생성 실행
  for each transaction A in training_data:
      matching_B = find all transactions that satisfy matching_conditions(A)
      for each B in matching_B:
          create_pair(A, B)
          pair_features = [A.features, B.features, abs_diff, ratio]
  
  예상 결과: 2,500,000 ~ 5,000,000 쌍
  (한 transaction 당 평균 3.3~6.7개 매칭 쌍)

(4.3.3) 쌍 데이터 구조
  columns:
  ├─ pair_id (고유 ID)
  ├─ transaction_a_id (첫 거래)
  ├─ transaction_b_id (비교 거래)
  ├─ feature_a_* (거래 A의 특성)
  ├─ feature_b_* (거래 B의 특성)
  ├─ price_diff_manwon (거래 B - A)
  ├─ price_ratio (B / A)
  ├─ area_diff (B - A)
  └─ target (학습 대상: price_diff 또는 price_ratio)

(4.3.4) 결과 저장
  output: data/training_pairs.csv (4M행 × 75열)
  
  행 수 이론:
  - 원본: 750K 거래
  - 평균 매칭: 5.3쌍/거래
  = 약 3,975,000쌍

성과물: data/training_pairs.csv (~800MB)
```

#### 4.4 모델 학습 (4.4) [20시간 / 하드웨어 사양에 따라 변동]

**담당자**: ML Engineer  
**스크립트**: scripts/p5_unified_training.py (기존, 재실행)

#### (4.4.0) 하드웨어 사양 확인 (필수 선결 조건) [1시간]

```
작업: 학습 실행 전 시스템 사양 검증

최소 사양 (Minimum):
  ├─ CPU: 4코어 이상 (Intel i5 또는 동급)
  ├─ 메모리: 8GB RAM 이상
  ├─ 저장소: SSD 2GB 여유 공간
  ├─ Python: 3.8+
  └─ 예상 학습시간: 20시간
  
권장 사양 (Recommended):
  ├─ CPU: 8코어 이상 (Intel i7 또는 동급)
  ├─ 메모리: 16GB RAM 이상
  ├─ 저장소: SSD 5GB 여유 공간
  ├─ GPU: NVIDIA RTX 4060 이상 (선택사항)
  └─ 예상 학습시간: 10시간

최적 사양 (Optimal, GPU 포함):
  ├─ CPU: 8코어 + RTX 4060 Ti
  ├─ 메모리: 16GB RAM
  ├─ GPU 메모리: 6GB 이상
  └─ 예상 학습시간: 5시간

검증 체크리스트:
  □ CPU 코어 수 확인
    # Windows
    wmic cpu get NumberOfCores
    # Linux/Mac
    nproc
  
  □ 메모리 확인
    # Windows
    wmic OS get TotalVisibleMemorySize
    # Linux
    free -h
    # Mac
    sysctl -a | grep hw.memsize
  
  □ 저장소 여유 확인
    # Windows
    dir D: (수집 드라이브)
    # Linux
    df -h
  
  □ GPU 확인 (있으면 좋음)
    python -c "import torch; print(torch.cuda.is_available())"

조치사항:
  ├─ 최소 사양 미달: 클라우드 인스턴스 사용 (AWS EC2, 예상 비용: $50~100)
  ├─ 메모리 부족: 배치 크기 감소 (256 → 128)
  ├─ CPU 부족: 병렬 워커 감소 (4 → 2)
  └─ GPU 있음: XGBoost GPU 버전 사용 (3배 고속화)

성과물: hardware_check_report.txt
```

(4.4.1) 모델 아키텍처
  
  앙상블 모델:
  ├─ 모델 1: XGBoost (트리 기반)
  │   ├─ n_estimators: 200
  │   ├─ max_depth: 8
  │   ├─ learning_rate: 0.05
  │   └─ 장점: 범주형 특성, 비선형 관계 포착
  │
  ├─ 모델 2: Ridge Regression (선형)
  │   ├─ alpha: 1.0 (정규화)
  │   └─ 장점: 해석가능성, 외삽
  │
  └─ 앙상블: Voting Regressor
      ├─ XGBoost 가중치: 0.6
      └─ Ridge 가중치: 0.4

(4.4.2) 하이퍼파라미터 튜닝 (8시간)
  
  방식: Randomized Search + 5-fold Cross Validation
  
  파라미터 그리드:
  {
    'xgb__max_depth': [6, 8, 10],
    'xgb__learning_rate': [0.01, 0.05, 0.1],
    'xgb__n_estimators': [100, 200, 300],
    'xgb__subsample': [0.8, 0.9, 1.0],
    'ridge__alpha': [0.1, 1.0, 10.0]
  }
  
  평가 지표:
  ├─ 주요: R² (Cross-validation)
  ├─ 보조: RMSE, MAPE
  └─ 목표: 최대 R² 달성
  
  CV 프로세스:
  ```
  fold 1: train on data[80:100], test on data[0:20]
  fold 2: train on data[0:20] + data[60:100], test on data[20:40]
  fold 3: train on data[0:40] + data[80:100], test on data[40:60]
  fold 4: train on data[0:60] + data[80:100], test on data[60:80]
  fold 5: train on data[0:80], test on data[80:100]
  
  → 평균 CV 점수 계산
  ```

(4.4.3) 최종 모델 학습 (12시간)
  
  최적 파라미터로 전체 훈련셋(train + validation)에서 학습
  
  코드:
  ```python
  best_model = VotingRegressor(
      estimators=[
          ('xgb', XGBRegressor(**best_params['xgb'])),
          ('ridge', Ridge(**best_params['ridge']))
      ],
      weights=[0.6, 0.4]
  )
  best_model.fit(X_train_val, y_train_val)
  
  # 모델 저장
  joblib.dump(best_model, 'models/trained_model.pkl')
  ```

(4.4.4) 예상 성능 (정성적)
  
  CV 점수 (훈련 중):
  ├─ Fold 1: R² = 0.938
  ├─ Fold 2: R² = 0.940
  ├─ Fold 3: R² = 0.942
  ├─ Fold 4: R² = 0.941
  ├─ Fold 5: R² = 0.939
  └─ 평균 CV R²: 0.940
  
  목표 달성: ✓ (목표 >0.94)

성과물: models/trained_model.pkl (~50MB)
```

#### 4.5 모델 검증 (4.5) [8시간]
```
담당자: QA Engineer + ML Engineer
스크립트: scripts/p7_generate_evaluation_results.py (기존, 확장)

(4.5.1) 테스트셋 성능 평가 (2시간)
  
  코드:
  ```python
  best_model = joblib.load('models/trained_model.pkl')
  y_pred = best_model.predict(X_test)
  
  # 지표 계산
  r2 = r2_score(y_test, y_pred)
  mape = mean_absolute_percentage_error(y_test, y_pred)
  rmse = np.sqrt(mean_squared_error(y_test, y_pred))
  mae = mean_absolute_error(y_test, y_pred)
  ```
  
  예상 결과:
  ├─ R² (테스트): 0.943 (CV와 유사)
  ├─ MAPE: 9.8% (목표 <10.5% ✓)
  ├─ RMSE: 95,000,000원
  └─ MAE: 52,000,000원

(4.5.2) 부분군 성능 분석 (2시간)
  
  by 물건 유형:
  ├─ 아파트: R² = 0.948, MAPE = 9.2%
  ├─ 다세대: R² = 0.925, MAPE = 11.5%
  └─ 오피스텔: R² = 0.912, MAPE = 13.2%
  
  by 지역:
  ├─ 서울: R² = 0.956, MAPE = 8.1%
  ├─ 경기: R² = 0.941, MAPE = 10.2%
  └─ 지방: R² = 0.925, MAPE = 11.8%
  
  by 건축연도:
  ├─ 신축(5년): R² = 0.952, MAPE = 7.9%
  ├─ 중고(5~20년): R² = 0.943, MAPE = 9.8%
  └─ 노후(20년+): R² = 0.918, MAPE = 12.5%

(4.5.3) 잔차 분석 (2시간)
  
  분석:
  ├─ 잔차 분포: 정규분포 확인 (Q-Q plot)
  ├─ 등분산성: 잔차 vs 예측값 (이상적: 수평 띠)
  ├─ 자기상관: Durbin-Watson 통계량 (목표: 1.5~2.5)
  └─ 이상값: residual > 2σ인 데이터 식별
  
  예상 결과:
  ├─ 잔차 평균: ±1,000,000원 (거의 0)
  ├─ 잔차 표준편차: 95,000,000원 (RMSE와 일치)
  └─ 정상성: ✓ 기각 불가 (Shapiro-Wilk p > 0.05)

(4.5.4) 피처 중요도 분석 (2시간)
  
  상위 10개 특성:
  1. price_per_area (평가: 25%)
  2. building_age (평가: 18%)
  3. sgg_cluster (평가: 15%)
  4. neighborhood_median_price (평가: 12%)
  5. contract_age (평가: 10%)
  6. exclusive_area (평가: 8%)
  7. floor_level (평가: 5%)
  8. distance_to_seoul (평가: 3%)
  9. is_new (평가: 2%)
  10. season (평가: 2%)
  
  해석:
  ├─ ✓ 단가(㎡당 가격)가 가장 중요 (직관적)
  ├─ ✓ 건축연도가 2번째 (경험과 일치)
  ├─ ✓ 지역과 이웃 평가 상위권 (지리적 영향 큼)
  └─ ✓ 계절 효과는 작음 (실제와 일치)

(4.5.5) 성과 보고서 생성 (1시간)
  
  산출물:
  ├─ reports/model_evaluation.json (지표 데이터)
  ├─ reports/feature_importance.csv (피처 기여도)
  ├─ reports/residual_analysis.json (잔차 통계)
  ├─ reports/performance_by_group.csv (부분군 성능)
  └─ reports/MODEL_EVALUATION_REPORT.md (최종 보고서)

성과물: 
  ├─ reports/MODEL_EVALUATION_REPORT.md
  ├─ reports/model_evaluation.json
  ├─ models/trained_model.pkl (검증됨)
  └─ validation_passed.txt
```

---

### **5. 배포 준비 (5.0) [16시간]**

#### 5.1 모델 통합 (5.1) [4시간]
```
담당자: Backend Engineer
작업:

(5.1.1) API 엔드포인트 업데이트 (2시간)
  파일: app/avm/engine.py
  
  변경:
  ├─ 기존 모델 제거 (synthetic data 기반)
  ├─ 새 모델 로드 (real data 기반)
  ├─ 모델 버전 관리 추가
  │   - model_version: "2.0_real_data_20260710"
  │   - trained_date: "2026-07-10"
  │   - training_records: 750000
  │   - r2_score: 0.943
  │   - mape: 0.098
  └─ 로깅 강화 (모델 로드, 추론 시간)
  
  코드:
  ```python
  import joblib
  
  class AVMEngine:
      def __init__(self):
          self.model = joblib.load('models/trained_model.pkl')
          self.model_version = "2.0_real_data_20260710"
          self.created_at = datetime.now()
      
      def estimate(self, features):
          """AVM 추정"""
          prediction = self.model.predict([features])[0]
          return {
              'estimate_price': prediction,
              'model_version': self.model_version,
              'created_at': self.created_at
          }
  ```

(5.1.2) 환경변수 업데이트 (1시간)
  파일: .env
  
  추가:
  ```
  # Model Configuration
  MODEL_VERSION=2.0_real_data_20260710
  MODEL_PATH=models/trained_model.pkl
  MODEL_PERFORMANCE_R2=0.943
  MODEL_PERFORMANCE_MAPE=0.098
  ```

(5.1.3) 호환성 테스트 (1시간)
  - 기존 API 입력 형식 호환성 확인
  - 응답 형식 일관성 확인
  - 에러 처리 검증

성과물: app/avm/engine.py (업데이트됨)
```

#### 5.2 API 테스트 (5.2) [6시간]
```
담당자: QA Engineer
스크립트: tests/api_smoke_test.py (신규 작성)

(5.2.1) 단위 테스트 (1시간)
  ├─ 모델 로드 테스트
  ├─ 예측 결과 형식 테스트
  ├─ 입력 검증 테스트
  └─ 예외 처리 테스트

(5.2.2) 통합 테스트 (2시간)
  
  테스트 케이스:
  ├─ 정상 요청 (100건)
  │   POST /api/v1/avm/estimate
  │   {
  │     "address_sido": "경기도",
  │     "address_sigungu": "화성시",
  │     "property_type": "아파트",
  │     "land_area": 15000,
  │     "building_area": 12000
  │   }
  │   → HTTP 200, 추정치 반환
  │
  ├─ 경계 케이스
  │   ├─ 최소값 (1억원대)
  │   ├─ 최대값 (5억원대)
  │   ├─ 미지 지역
  │   └─ 이상 입력 (음수, 0)
  │   → 적절한 응답 또는 에러
  │
  └─ 병렬 요청
      ├─ 동시 10개 요청
      ├─ 동시 50개 요청
      ├─ 동시 100개 요청
      └─ 성능 기준 충족 확인

(5.2.3) 성능 벤치마크 (2시간)
  
  메트릭:
  ├─ 응답시간 P50: < 500ms
  ├─ 응답시간 P95: < 1000ms
  ├─ 응답시간 P99: < 2000ms
  ├─ 처리량: > 100 req/s
  ├─ 메모리 사용: < 500MB (상주)
  ├─ CPU 사용률: < 50% (1개 코어 기준)
  └─ 에러율: < 0.1%
  
  테스트 방법:
  ```bash
  # locust를 이용한 부하 테스트
  locust -f tests/load_test.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 10m
  ```

(5.2.4) 배포 전 체크리스트 (1시간)
  ├─ ✓ 모든 테스트 통과
  ├─ ✓ 코드 리뷰 완료
  ├─ ✓ 보안 검사 통과
  ├─ ✓ 문서화 완료
  └─ ✓ 배포 계획 수립

성과물: tests/api_smoke_test.log
```

#### 5.3 성능 벤치마크 (5.3) [4시간]
```
담당자: DevOps Engineer
스크립트: scripts/benchmark_model.py (신규 작성)

(5.3.1) 정적 벤치마크 (1시간)
  
  단일 예측 성능:
  ├─ 모델 로드시간: < 2초
  ├─ 예측시간/건: < 50ms
  ├─ 메모리 점유: < 200MB
  └─ 모델 크기: < 100MB

(5.3.2) 동적 벤치마크 (2시간)
  
  동시 요청 처리:
  ├─ 1 req/s: P95 < 100ms
  ├─ 10 req/s: P95 < 200ms
  ├─ 100 req/s: P95 < 500ms
  ├─ 1000 req/s: P95 < 1000ms
  └─ 최대 처리량 측정

(5.3.3) 메모리/CPU 프로파일링 (1시간)
  
  도구: memory_profiler, cProfile
  
  분석:
  ├─ 메모리 누수 확인
  ├─ CPU 핫스팟 식별
  └─ 최적화 기회 발굴

성과물: reports/benchmark_report.json
```

#### 5.4 배포 준비 완료 (5.4) [2시간]
```
담당자: Project Manager + DevOps Engineer

(5.4.1) 배포 체크리스트 작성 (1시간)
  ├─ 코드 리뷰: ✓
  ├─ 테스트 커버리지: ✓ (95%)
  ├─ 성능 기준: ✓
  ├─ 보안 검사: ✓
  ├─ 문서화: ✓
  ├─ 팀 준비: ✓
  └─ 롤백 계획: ✓

(5.4.2) 배포 계획서 (0.5시간)
  ├─ Blue-Green 배포 전략
  ├─ 배포 일정: 2026-07-13 14:00~16:00 (2시간 점검)
  ├─ 담당자: Backend Engineer
  └─ 롤백 절차 명시

(5.4.3) 모니터링 계획 (0.5시간)
  ├─ 메트릭 대시보드 준비
  ├─ 알람 규칙 설정
  ├─ 상시 모니터링 체계 구축
  └─ 24시간 온콜 체계

성과물: DEPLOYMENT_CHECKLIST.md
```

---

### **6. 최종 검증 & 보고 (6.0) [4시간]**

#### 6.1 최종 성능 검증 (6.1) [2시간]
```
담당자: QA Engineer

(6.1.1) 프로덕션 환경 검증
  ├─ API 응답 확인
  ├─ DB 연결 확인
  ├─ 로깅 정상 여부
  └─ 모니터링 대시보드 작동

(6.1.2) 예측 결과 샘플링 검증
  - 100건의 추정 결과 수집
  - 결과의 합리성 검증 (도메인 전문가)
  - 이상값 확인

성과물: production_validation_report.md
```

#### 6.2 최종 보고서 작성 (6.2) [2시간]
```
담당자: Project Manager

산출물:
├─ FINAL_REPORT.md
│  ├─ Executive Summary
│  ├─ 프로젝트 개요
│  ├─ 데이터 수집 결과
│  ├─ 모델 학습 결과
│  ├─ 성능 평가
│  ├─ 배포 결과
│  ├─ 비용/일정 분석
│  └─ 향후 계획
│
├─ DATA_COLLECTION_REPORT.md
│  ├─ 수집 현황
│  ├─ 데이터 품질 지표
│  ├─ 지역별/시간별 분포
│  └─ 통계 요약
│
├─ MODEL_EVALUATION_REPORT.md
│  ├─ 모델 아키텍처
│  ├─ 성능 지표
│  ├─ 부분군 분석
│  ├─ 피처 중요도
│  └─ 검증 결과
│
└─ DEPLOYMENT_REPORT.md
   ├─ 배포 일정
   ├─ 배포 결과
   ├─ 성능 지표
   ├─ 모니터링 현황
   └─ 다음 단계
```

---

## 3. 일정 요약 (Gantt Chart)

```
07-03 (목): [API 신청  ][준비 ........]
07-04 (금): [........][파일럿 수집......]
07-05 (토): [........][파일럿 검증][전국 수집 시작.....................]
07-06 (일): [...전국 수집 진행중........................]
07-07 (월): [...전국 수집 진행중........................]
07-08 (화): [......................][데이터 전처리 시작.....................]
07-09 (수): [....................[특성 공학 + 쌍 생성.....................]
07-10 (목): [....................................][모델 학습...................]
07-11 (금): [...............모델 학습.............][검증...]
07-12 (토): [............검증.............][배포 준비....]
07-13 (일): [배포 준비....][최종 검증......]
```

---

## 4. 리소스 할당

### 인력
```
- Project Manager: 1명 (기획, 관리, 보고)
- Data Engineer: 2명 (수집, 전처리, 파이프라인)
- ML Engineer: 1명 (모델 학습, 튜닝)
- DevOps Engineer: 1명 (환경, 배포, 모니터링)
- QA Engineer: 1명 (검증, 테스트)

총 6명 (풀타임, 10.5일)
```

### 인프라
```
- CPU: 4코어 (병렬 처리)
- 메모리: 8GB (최소)
- 저장소: 2GB (데이터 + 모델)
- 네트워크: 안정적 인터넷 (API 호출)
```

---

## 5. 성공 지표

```
✓ 데이터: 850K+ 건 수집
✓ 성능: R² > 0.94, MAPE < 10.5%
✓ 배포: 무중단 전환, 모니터링 활성화
✓ 문서: 모든 산출물 완성
```

