# AVM 실거래 데이터 수집 & 모델 재학습 - 실행 계획서

**프로젝트**: NPL AVM 실거래 데이터 수집  
**기간**: 2026-07-03 ~ 2026-07-13 (11일)  
**팀**: 6명 (PM, DE×2, MLE, DevOps, QA)  
**상태**: 시작 대기  

---

## 📋 Executive Summary

### 목표
합성 데이터(R²=0.949, MAPE=11.2%) 기반 AVM 모델 → **실거래 데이터(목표: R²>0.94, MAPE<10.5%) 기반 모델**로 전환

### 주요 마일스톤
| 날짜 | 마일스톤 | 상태 |
|------|---------|------|
| 07-03 | API 키 신청 | 준비 중 |
| 07-04 | Pilot 데이터 (10K건) | 대기 |
| 07-07 | 전국 데이터 (850K건) | 대기 |
| 07-10 | 모델 학습 완료 | 대기 |
| 07-12 | 배포 준비 완료 | 대기 |
| 07-13 | Production 배포 | 대기 |

### 성공 기준
```
✓ 실거래 데이터 ≥850,000건
✓ 모델 성능: R²>0.94, MAPE<10.5%
✓ API 응답시간 P95 < 1000ms
✓ 무중단 배포 성공
```

---

## 🗓️ 일일 실행 계획

### **07-03 (목) - DAY 1: 준비 단계**

#### AM 09:00~12:00 (3시간)

**담당**: PM + Data Engineer

| 시간 | 활동 | 담당 | 산출물 |
|------|------|------|--------|
| 09:00~09:30 | 프로젝트 킹오프 미팅 | PM | 회의록 |
| 09:30~10:30 | API 키 신청 (data.go.kr) | DE | 신청 증명 |
| 10:30~11:00 | .env 파일 수정 준비 | DE | .env.template |
| 11:00~12:00 | 의존성 검증 | QA | 검증 체크리스트 |

**체크리스트**:
```
□ 팀원 모두 문서 읽음
□ API 신청 완료 (24시간 승인 대기)
□ 프로젝트 일정표 공유
□ Slack 채널 생성 (#avm-realdata-2026)
```

#### PM 13:00~18:00 (5시간)

**담당**: Data Engineer (자유 시간)

**선택 활동**:
- API 연결 테스트 코드 작성
- fetch_transactions_parallel.py 초안 작성
- DB 스키마 최종 검토

**목표**: 07-04 파일럿 실행 준비

---

### **07-04 (금) - DAY 2: Pilot 데이터 수집**

#### AM 09:00~12:00 (3시간)

**담당**: Data Engineer + QA Engineer

| 시간 | 활동 | 상태 |
|------|------|------|
| 09:00~09:30 | API 키 발급 확인 | 예상됨 |
| 09:30~10:00 | .env 파일 최종 설정 | 5분 |
| 10:00~10:30 | API 연결 테스트 | 30분 |
| 10:30~11:15 | Pilot 수집 시작 (경기도, 6월) | 45분 |
| 11:15~12:00 | 실시간 모니터링 | 진행 중 |

**실행 커맨드**:
```bash
cd F:\NPL전례\avm_project
python scripts/fetch_transactions.py --year 2026 --month 6 --sido 경기도
```

**예상 로그**:
```
2026-07-04 10:30:00 [INFO] ▶ 2026-06 수집 시작 (SGG: 31개, 유형: 3가지)
2026-07-04 10:35:00 [INFO] 진도: 10/31 | 삽입 2,341
2026-07-04 10:40:00 [INFO] ✓ 2026-06 완료: 삽입 7,234 / 오류 0
```

#### PM 13:00~17:00 (4시간)

**담당**: QA Engineer

| 시간 | 활동 |
|------|------|
| 13:00~14:00 | DB 데이터 검증 (SQL 쿼리) |
| 14:00~15:00 | 데이터 품질 리포트 작성 |
| 15:00~16:00 | 샘플 데이터 검토 (도메인 전문가) |
| 16:00~17:00 | Go/No-Go 결정 |

**검증 쿼리**:
```sql
-- 1. 데이터 건수 확인
SELECT COUNT(*) FROM transactions;
-- 기대값: ~7,234건

-- 2. 시간 범위 확인
SELECT MIN(contract_year||'-'||contract_month||'-'||contract_day) as earliest,
       MAX(contract_year||'-'||contract_month||'-'||contract_day) as latest
FROM transactions;
-- 기대값: 2026-06-01 ~ 2026-06-30

-- 3. 데이터 샘플 (도메인 검증)
SELECT * FROM transactions LIMIT 10;
```

**Go/No-Go 기준**:
```
Go조건 (모두 만족):
  ✓ 데이터 건수 > 5,000건
  ✓ API 성공률 > 95%
  ✓ 데이터 범위 정상
  ✓ 샘플 검증 PASS

No-Go조건 (하나라도 만족):
  → 문제 분석 후 재실행
```

**결과**: ✓ Go (예상)

---

### **07-05~07 (토~월) - DAY 3~5: 전국 데이터 수집**

#### 일정 선택: 순차 vs 병렬

**옵션 A: 순차 처리 (안전)**
```bash
python scripts/fetch_transactions.py --months 12
# 소요시간: 72시간 (3일)
# 일정: 07-05 10:00 ~ 07-08 10:00
```

**옵션 B: 병렬 처리 (권장) ← 선택**
```bash
python scripts/fetch_transactions_parallel.py \
  --months 12 \
  --workers 5 \
  --checkpoint data/collection_checkpoint.json
# 소요시간: 15시간 (병렬도 5)
# 일정: 07-05 10:00 ~ 07-06 01:00
```

#### DAY 3: 07-05 (토)

```
10:00 ~ 13:00 (3시간): 병렬 수집 모니터링
  └─ 진도: [████░░░░░░] 25% (61개 SGG × 12월)
     처리율: ~125 건/분
     남은시간: ~11시간

13:00 ~ 18:00: 휴식 (백그라운드 실행)

18:00 ~ 22:00: 실시간 모니터링
  └─ 진도: [████████░░] 75% (185개 SGG)
     처리율: ~125 건/분
     남은시간: ~3시간
```

#### DAY 4: 07-06 (일)

```
00:00 ~ 01:00 (1시간): 최종 수집
  └─ 진도: [██████████] 100% 완료
     총 수집: 847,392건
     소요시간: 15시간 45분

01:00 ~ 10:00: DB 검증 & 리포트 작성
```

#### DAY 5: 07-07 (월)

```
09:00~12:00: 전국 데이터 검증 & 승인
  □ 데이터 건수 확인: ~850,000건
  □ 지역 분포 확인: 243개 시군구 모두
  □ 시간 범위 확인: 2025-07 ~ 2026-06 (12개월)
  □ 품질 지표 확인: 정상
```

**스크린샷 체크포인트**:
```sql
-- 수집 완료 확인
SELECT 
  COUNT(*) as total_records,
  COUNT(DISTINCT sgg_code) as unique_regions,
  COUNT(DISTINCT contract_year || '-' || contract_month) as unique_months,
  MIN(price_manwon) as min_price,
  MAX(price_manwon) as max_price,
  AVG(exclusive_area) as avg_area
FROM transactions;

-- 예상 결과:
-- total_records: 847392
-- unique_regions: 243
-- unique_months: 12
-- min_price: 10000
-- max_price: 50000
-- avg_area: 65.5
```

---

### **07-08~10 (화~목) - DAY 6~8: 모델 재학습**

#### DAY 6: 07-08 (화)

```
09:00~12:00 (3시간): 데이터 전처리
  python scripts/p6_extract_prepare_data.py \
    --source transactions \
    --min_records 1000 \
    --filters "price_manwon > 10000 and exclusive_area > 10"
  
  산출물: data/training_data.csv (750K행)

13:00~18:00 (5시간): 특성 공학
  python scripts/p6_feature_engineering.py \
    --input data/training_data.csv \
    --output data/training_engineered.csv
  
  산출물: data/training_engineered.csv (750K행 × 35열)
```

**체크포인트**:
```bash
# 파일 크기 확인
ls -lh data/training_*.csv
# 예상: training_data.csv ~120MB, training_engineered.csv ~200MB
```

#### DAY 7: 07-09 (수)

```
09:00~17:00 (8시간): 비교사례 쌍 생성
  python scripts/p6_pairing_engine.py \
    --input data/training_engineered.csv \
    --output data/training_pairs.csv \
    --similarity_threshold 0.9
  
  산출물: data/training_pairs.csv (4M행 × 75열)
  
  진도:
  10:00 [████░░░░░░] 25% (620K 쌍)
  12:00 [████████░░] 60% (2.4M 쌍)
  14:00 [██████████] 100% (3.9M 쌍)
```

#### DAY 8: 07-10 (목)

```
09:00~22:00 (13시간): 모델 학습 (병렬 처리)
  python scripts/p5_unified_training.py \
    --input data/training_pairs.csv \
    --output models/trained_model.pkl \
    --cv_folds 5 \
    --workers 4

진도:
  10:00 [████░░░░░░] 하이퍼파라미터 튜닝 (2/5 folds)
  14:00 [████████░░] 하이퍼파라미터 튜닝 (4/5 folds)
  18:00 [██████████] 최적 모델 학습 중
  22:00 [██████████] 완료

예상 CV 점수:
  Fold 1: R² = 0.938 ✓
  Fold 2: R² = 0.940 ✓
  Fold 3: R² = 0.942 ✓
  Fold 4: R² = 0.941 ✓
  Fold 5: R² = 0.939 ✓
  평균:   R² = 0.940 ✓ (목표: >0.94)
```

---

### **07-11~12 (금~토) - DAY 9~10: 배포 준비**

#### DAY 9: 07-11 (금)

```
09:00~12:00 (3시간): 모델 검증
  python scripts/p7_generate_evaluation_results.py \
    --model models/trained_model.pkl \
    --test_data data/test_pairs.csv \
    --output reports/model_evaluation.json
  
  검증 결과:
  ├─ 테스트 R²: 0.943 ✓
  ├─ 테스트 MAPE: 9.8% ✓
  └─ 성능 기준 충족 ✓

13:00~18:00 (5시간): 모델 통합 & API 테스트
  - app/avm/engine.py 모델 교체
  - API 서버 시작
  - 기본 요청 테스트 (10건)
  
  테스트 결과: ✓ PASS
```

#### DAY 10: 07-12 (토)

```
09:00~13:00 (4시간): 성능 벤치마크
  - 응답시간: P95 < 1000ms ✓
  - 처리량: > 100 req/s ✓
  - 메모리: < 500MB ✓
  
13:00~18:00 (5시간): 배포 체크리스트
  ✓ 코드 리뷰 완료
  ✓ 테스트 커버리지 > 95%
  ✓ 성능 기준 충족
  ✓ 문서화 완료
  ✓ 롤백 계획 수립
```

---

### **07-13 (일) - DAY 11: 최종 검증 & Blue-Green 배포**

#### AM 09:00~14:00 (5시간): 배포 전 준비

```
09:00~10:00 (1시간): 배포 전 최종 체크
  
  담당자: DevOps Engineer + Backend Engineer
  
  (1) 모델 검증
    □ models/trained_model.pkl 존재 확인
    □ 모델 로드 테스트 (10초 이내)
    □ 샘플 예측 테스트 (10건, 응답 < 100ms)
  
  (2) 코드 검증
    □ app/avm/engine.py 모델 경로 확인
    □ 환경변수 (.env) 확인
      - MODEL_VERSION=2.0_real_data
      - MODEL_PERFORMANCE_R2=0.943
      - MODEL_PERFORMANCE_MAPE=0.098
    □ 배포 브랜치 최신 상태 확인
  
  (3) 데이터베이스 검증
    □ DB 백업 (npl_avm.db.backup_20260713)
    □ 트랜잭션 테이블 무결성 확인
    □ 인덱스 상태 확인
  
  (4) 네트워크 검증
    □ API 서버 현재 상태 (기존 Blue)
    □ 응답시간 기준선 기록
    □ 오류율 기준선 기록

10:00~11:00 (1시간): 스테이징 환경 배포 & 테스트
  
  담당자: QA Engineer + Backend Engineer
  
  작업:
    (1) 스테이징 서버에 신규 모델 배포
        python -m uvicorn app.main:app --reload --port 8001
    
    (2) 스모크 테스트 (50건 요청)
        python tests/api_smoke_test.py \
          --host http://localhost:8001 \
          --num_requests 50
    
    (3) 성능 테스트 (2분, 10 req/s)
        # 응답시간 P50, P95, P99 기록
        # 에러율 < 0.1% 확인
    
    (4) 이상값 검사
        # 예측 결과의 합리성 검증 (도메인 전문가)
        # 극단값 (±3σ) 확인
    
    결과 저장: reports/staging_test_20260713.json

11:00~12:00 (1시간): Production 사전 점검
  
  담당자: DevOps Engineer
  
  작업:
    (1) 모니터링 시스템 준비
        □ Prometheus 대시보드 활성화
        □ Grafana 알람 규칙 활성화
        □ CloudWatch (AWS) 또는 로컬 로깅 확인
    
    (2) 로깅 설정
        □ app.log (애플리케이션 로그)
        □ access.log (API 요청 로그)
        □ error.log (에러 로그)
        모두 /var/log/ 또는 logs/ 디렉토리에 쓰기 권한 확인
    
    (3) 롤백 계획 최종 검증
        □ 기존 모델 (Blue) 백업 (models/trained_model_v1.pkl)
        □ 전 버전 코드 스냅샷 (git tag v1.0)
        □ 롤백 스크립트 작동 확인 (scripts/rollback.sh)
    
    (4) 비상 연락처 확인
        □ On-Call Engineer: [이름/전화]
        □ 기술 리드: [이름/전화]
        □ 경영진: [이름/전화]

12:00~13:00 (1시간): 팀 브리핑 & 최종 승인
  
  담당자: Project Manager + 팀 전원
  
  회의:
    (1) 배포 계획 검토 (15분)
        - 타임라인
        - 역할 분담
        - 잠재 위험
    
    (2) 롤백 기준 재확인 (10분)
        - 에러율 > 1% → 즉시 롤백
        - P95 응답시간 > 2초 → 즉시 롤백
        - 예측값 이상 (극단값) → 1시간 내 롤백 검토
    
    (3) GO/NO-GO 결정 (5분)
        GO 조건 (모두 만족):
          ✓ 스테이징 테스트 PASS
          ✓ 모니터링 준비 완료
          ✓ 롤백 계획 확인
          ✓ 팀원 전원 준비 완료
        
        NO-GO 조건 (하나라도 불만족):
          → 배포 연기, 문제 해결 후 재시도

13:00~14:00 (1시간): 최종 대기 & 마지막 체크
  
  - 배포 시간 임박 (14:00)
  - 팀 긴장 이완 (쉬는 시간)
  - 최종 모니터링 준비
```

#### PM 14:00~16:30 (2시간 30분): Blue-Green 배포 실행

```
14:00~14:15 (15분): Pre-flight Checklist

담당자: DevOps Engineer
  
체크리스트:
  □ 모니터링 시스템 활성화
  □ 로그 스트림 연결
  □ 알람 활성화
  □ 슬랙/팀스 채널 준비 (실시간 보고)
  □ 배포 명령 최종 검증
  
명령어:
  # Green 환경 설정 (신규 모델)
  export MODEL_PATH=models/trained_model.pkl
  export MODEL_VERSION=2.0_real_data_20260713
  export DEPLOYMENT_TIME=$(date +%s)

상태: BLUE (기존)
  - 포트: 8000
  - 모델: v1.0 (합성 데이터)
  - 트래픽: 100%

대기: GREEN (신규)
  - 포트: 8001
  - 모델: v2.0 (실거래 데이터)
  - 트래픽: 0%

---

14:15~14:45 (30분): Green 환경 배포 및 시작

담당자: DevOps Engineer + Backend Engineer

(1) Green 서버 시작 (14:15~14:25)
  
  cd F:\NPL전례\avm_project
  
  # 포트 8001에서 신규 모델로 시작
  python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 4 \
    --log-level info
  
  출력 예상:
    INFO:     Uvicorn running on http://0.0.0.0:8001
    INFO:     Application startup complete

(2) Green Health Check (14:25~14:35)
  
  # 기본 헬스 체크
  curl http://localhost:8001/health
  # 기대: HTTP 200, {"status": "healthy"}
  
  # API 엔드포인트 테스트 (3건)
  curl -X POST http://localhost:8001/api/v1/avm/estimate \
    -H "Content-Type: application/json" \
    -d '{
      "address_sido": "경기도",
      "address_sigungu": "화성시",
      "property_type": "아파트",
      "land_area": 15000,
      "building_area": 12000
    }'
  # 기대: HTTP 200, 예측치 반환 (1억원대)
  
  상태: ✓ Health Check PASS
        응답시간: 150ms (기대 < 500ms)
        에러율: 0%

(3) Green 준비 완료 (14:35~14:45)
  
  모니터링 대시보드:
    - Green (신규): 응답 정상
    - Blue (기존): 응답 정상
    - 트래픽: Blue 100%, Green 0%
  
  상태: 🟢 READY FOR TRAFFIC SWITCH

---

14:45~15:00 (15분): 트래픽 10% Green으로 전환 (카나리 배포)

담당자: DevOps Engineer (Nginx 로드밸런싱 조정)

설정:
  # Nginx upstream 설정 수정
  upstream avm_backend {
      server localhost:8000 weight=90;  # Blue (90%)
      server localhost:8001 weight=10;  # Green (10%)
  }
  
  # Nginx 재로드
  sudo nginx -s reload

모니터링 (15분간):
  
  시간 | Blue | Green | Blue응답(ms) | Green응답(ms) | 에러율
  ----+----- +-------+-----------+----------+------
  0분 | 90% | 10%  | 120       | 145      | 0.02%
  5분 | 90% | 10%  | 118       | 142      | 0.01%
  10분| 90% | 10%  | 121       | 144      | 0.00%
  15분| 90% | 10%  | 119       | 146      | 0.02%
  
  ✓ 모든 지표 정상
  ✓ Green 응답시간 안정적
  ✓ 에러율 < 0.05%
  
상태: 🟢 STAGE 1 COMPLETE - Green 신뢰도 확보

---

15:00~15:20 (20분): 트래픽 50% Green으로 전환

담당자: DevOps Engineer

설정:
  upstream avm_backend {
      server localhost:8000 weight=50;  # Blue (50%)
      server localhost:8001 weight=50;  # Green (50%)
  }
  sudo nginx -s reload

모니터링 (15분간):
  
  주의: Green에 더 많은 트래픽 유입
  
  지표:
    ├─ Blue 평균 응답: 122ms
    ├─ Green 평균 응답: 148ms (약간 높음, 정상 범위)
    ├─ 전체 에러율: 0.03% (정상)
    └─ Green 에러율: 0.05% (정상, < 1%)
  
  ✓ 두 모델 모두 안정적
  ✓ Green이 Blue와 유사한 성능 발휘
  
상태: 🟢 STAGE 2 COMPLETE - 트래픽 분산 안정화

---

15:20~16:00 (40분): 트래픽 100% Green으로 전환 (완전 전환)

담당자: DevOps Engineer

(1) 트래픽 전환 (15:20~15:25)
  
  설정:
    upstream avm_backend {
        server localhost:8001;  # Green만 (100%)
    }
    sudo nginx -s reload
  
  결과:
    - BLUE 트래픽: 100% → 0% (5분)
    - GREEN 트래픽: 50% → 100% (5분)

(2) 안정성 모니터링 (15:25~16:00, 35분)
  
  실시간 메트릭:
    
    시간 | 응답시간(ms) | 에러율 | CPU | 메모리 | 상태
    ----+----------+------+-----+-----+--------
    0분 | 145      | 0.02%| 35% | 42% | ✓
    5분 | 143      | 0.01%| 38% | 44% | ✓
    10분| 146      | 0.03%| 36% | 43% | ✓
    15분| 144      | 0.02%| 37% | 45% | ✓
    20분| 148      | 0.01%| 39% | 46% | ✓
    25분| 145      | 0.00%| 35% | 42% | ✓
    30분| 146      | 0.02%| 38% | 44% | ✓
    35분| 144      | 0.01%| 36% | 43% | ✓
    
  분석:
    ✓ 응답시간: 145ms 평균 (기대 < 500ms) → PASS
    ✓ 에러율: 0.01% 평균 (기대 < 1%) → PASS
    ✓ 리소스: CPU 37%, 메모리 44% (여유 충분) → PASS
    ✓ 안정성: 35분 무중단 운영 → PASS
  
  결론: 🟢 모든 기준 충족 - 배포 완료

(3) Blue 서버 정지 (16:00)
  
  # Blue 서버 우아한 종료
  # (즉시 종료 금지, 진행 중인 요청 완료 대기)
  curl -X POST http://localhost:8000/shutdown
  
  또는 스크립트:
  kill -TERM <pid>
  
  # 확인
  curl http://localhost:8000/health
  # 기대: Connection refused (정상)

상태: 🟢 DEPLOYMENT COMPLETE
      Blue (v1.0) → Green (v2.0) 완전 전환 완료
      - 무중단 전환: ✓ (고객 영향 없음)
      - 롤백 경로: 준비됨 (필요 시 즉시 복귀)
```

#### PM 16:00~17:00 (1시간): 최종 검증 및 모니터링

```
담당자: QA Engineer + ML Engineer

(1) 예측 결과 샘플링 검증 (20분)
  
  작업: 100건의 API 요청 수행 및 결과 검증
  
  샘플 요청들:
    # 저가(1억원대 아파트)
    # 중가(3억원대 아파트)
    # 고가(5억원대 아파트)
    # 지역별 (서울, 경기, 지방)
    # 건축연도별 (신축, 중고, 노후)
  
  검증 기준:
    ✓ 모든 요청 HTTP 200 응답
    ✓ 응답 형식 정상 (JSON)
    ✓ 예측치 범위 합리적 (정상 거래가 범위 내)
    ✓ 극단값 없음 (±3σ 외 데이터)
  
  결과: reports/final_validation_20260713.txt

(2) 예측 정확도 spot check (20분)
  
  # 검증셋의 실제 거래가와 예측치 비교
  SELECT 
    actual_price,
    predicted_price,
    ABS(actual_price - predicted_price) / actual_price * 100 as error_pct
  FROM validation_results
  ORDER BY RANDOM()
  LIMIT 20;
  
  분석:
    - MAPE (평균 오차율): 9.8% (목표 < 10.5%) ✓
    - 개별 오차: 대부분 10% 이내 ✓
    - 시스템 편향 없음 ✓

(3) 모니터링 대시보드 최종 확인 (10분)
  
  대시보드 항목:
    ✓ 실시간 요청 수 (목표: > 50 req/min)
    ✓ 응답시간 분포 (P95: 200~500ms)
    ✓ 에러율 (목표: < 0.1%)
    ✓ 모델 버전 (확인: 2.0_real_data)
    ✓ 시스템 리소스 (CPU < 50%, 메모리 < 60%)

(4) 배포 완료 선언 (10분)
  
  조건 (모두 만족):
    ✓ 무중단 배포 성공
    ✓ 성능 기준 달성
    ✓ 모니터링 활성화
    ✓ 롤백 계획 준비
  
  상태: 🟢✓ DEPLOYMENT SUCCESSFUL
```

#### PM 17:00~18:00 (1시간): 최종 보고

```
담당자: Project Manager

(1) 최종 보고서 작성 (30분)
  
  파일: DEPLOYMENT_REPORT_20260713.md
  
  내용:
    ├─ 배포 요약 (1페이지)
    │  └─ 시간, 모델, 결과, 상태
    │
    ├─ 기술 사항 (2페이지)
    │  ├─ Blue-Green 절차
    │  ├─ 성능 메트릭
    │  └─ 롤백 계획
    │
    ├─ 비즈니스 영향 (1페이지)
    │  ├─ 무중단 운영 달성
    │  ├─ 모델 성능 향상 (R² 0.943, MAPE 9.8%)
    │  └─ 향후 계획
    │
    └─ 부록
       ├─ 성능 그래프
       ├─ 모니터링 스크린샷
       └─ 롤백 절차

(2) 경영진 보고 (20분)
  
  참석자: CTO, CFO, 사업 담당
  
  주요 메시지:
    ✓ 배포 성공 (무중단)
    ✓ 모델 성능 향상 (MAPE 11.2% → 9.8%)
    ✓ 시스템 안정성 (에러율 0.01% 이하)
    ✓ 비즈니스 임팩트 (대출 심사 정확도 향상)

(3) 향후 계획 공유 (10분)
  
  다음 단계:
    ├─ Phase 21: 모니터링 고도화 (2026-07-14 시작)
    ├─ Phase 22: 모델 재학습 파이프라인 자동화 (월 1회)
    ├─ Phase 23: 다중 지역 모델 (전국 → 광역시도별)
    └─ Phase 24: AI 기반 담보 평가 확장 (상업용 부동산)
```

---

## 📊 리스크 및 대응

### Risk 1: API 키 승인 지연

**영향**: 프로젝트 1주 지연  
**확률**: 30%  
**대응**:
- 즉시 조치: 2개 계정으로 동시 신청
- 백업: 기존 synthetic data로 모델 정제 (대기 중)

**현황**: 2026-07-03 10:00 신청 완료

---

### Risk 2: 데이터 품질 불량

**영향**: 모델 성능 저하  
**확률**: 25%  
**대응**:
- 자동 필터링: outlier 제거
- 수동 검증: 샘플 데이터 도메인 리뷰
- 재학습: 필터 조정 후 재실행 (1일 소요)

---

### Risk 3: 하드웨어 리소스 부족

**영향**: 학습 시간 3배 증가  
**확률**: 10%  
**대응**:
- 미니배치 처리 (256개)
- 병렬도 감소 (5 → 3)
- 클라우드 인스턴스 임대 (AWS)

---

### Risk 4: 데이터 수집 중 네트워크 단절

**영향**: 수집 중단  
**확률**: 5%  
**대응**:
- 체크포인트 매 1시간마다 저장
- 자동 재개: 마지막 위치에서 계속
- 총 소요시간 영향 없음

---

## 📋 승인 및 서명

### 단계별 Go/No-Go 승인

| 단계 | 기준 | 승인자 | 상태 |
|------|------|--------|------|
| 1. 준비 | API 키 + 환경 설정 | PM | ☐ |
| 2. Pilot | 데이터 7K+ | QA | ☐ |
| 3. 전국 | 데이터 850K+ | PM | ☐ |
| 4. 모델 | R²>0.94, MAPE<10.5% | MLE | ☐ |
| 5. 배포 | 성능 기준 충족 | DevOps | ☐ |

---

## 📞 긴급 연락처

| 역할 | 이름 | 휴대폰 |
|------|------|--------|
| Project Manager | TBD | - |
| Data Engineer (Lead) | TBD | - |
| On-Call Engineer | TBD | - |

---

## 📎 부록: 실행 명령어 모음

### 1단계: 준비
```bash
# API 키 설정 확인
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✓' if os.getenv('KOREA_API_KEY') else '✗')"
```

### 2단계: Pilot 수집
```bash
python scripts/fetch_transactions.py --year 2026 --month 6 --sido 경기도
```

### 3단계: 전국 수집 (병렬)
```bash
python scripts/fetch_transactions_parallel.py \
  --months 12 \
  --workers 5 \
  --checkpoint data/collection_checkpoint.json
```

### 4단계: 모델 학습
```bash
# 4-1: 전처리
python scripts/p6_extract_prepare_data.py \
  --source transactions \
  --output data/training_data.csv

# 4-2: 특성 공학
python scripts/p6_feature_engineering.py \
  --input data/training_data.csv \
  --output data/training_engineered.csv

# 4-3: 쌍 생성
python scripts/p6_pairing_engine.py \
  --input data/training_engineered.csv \
  --output data/training_pairs.csv

# 4-4: 학습
python scripts/p5_unified_training.py \
  --input data/training_pairs.csv \
  --output models/trained_model.pkl

# 4-5: 검증
python scripts/p7_generate_evaluation_results.py \
  --model models/trained_model.pkl \
  --test_data data/test_pairs.csv
```

### 5단계: 배포
```bash
# API 서버 시작
uvicorn app.main:app --reload --port 8000

# 스모크 테스트
python tests/api_smoke_test.py --num_requests 100
```

