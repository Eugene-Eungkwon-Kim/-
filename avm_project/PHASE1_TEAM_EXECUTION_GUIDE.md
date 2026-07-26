# Phase 1 실행 가이드: 병렬 준비 (07-03 ~ 07-13)

**시작**: 2026-07-03 09:00  
**기간**: 11일 (07-03 ~ 07-13)  
**팀**: AVM 6명 + VWorld 2명 = 8명  
**상태**: 🔴 LIVE EXECUTION  

---

## 📍 **팀 배치 (총 8명)**

### **AVM Team (6명)**

| 역할 | 이름 | 책임 | 우선순위 |
|------|------|------|---------|
| **PM** | TBD | 일정/진행 관리, daily standup | 1순위 |
| **DE Lead** | TBD | 데이터 엔지니어 팀장, API 키 신청 | 1순위 |
| **DE 1** | TBD | 파일럿 수집, 검증 | 1순위 |
| **DE 2** | TBD | 전국 수집 모니터링 | 1순위 |
| **MLE** | TBD | 모델 준비 (대기 중) | 2순위 |
| **DevOps** | TBD | 배포 환경 준비 | 2순위 |

### **VWorld Team (2명)**

| 역할 | 이름 | 책임 | 우선순위 |
|------|------|------|---------|
| **Data Engineer** | TBD | Registry 설계, endpoint probe | 1순위 |
| **Data Engineer 2** | TBD | 초기 parser 코드, 테스트 | 1순위 |

---

## 🔔 **Daily Standup (매일 09:30 AM)**

**장소**: Slack/Teams  
**시간**: 5분  
**항목**:
- AVM: 수집 상태 (row count, 에러율)
- VWorld: 구현 진행률 (%)
- 블로커 (있으면)

---

## 📅 **Day-by-Day 상세 일정**

### **DAY 1: 2026-07-03 (목) - 킥오프 & 준비**

#### AM 09:00~10:00: **킥오프 미팅** (전체 8명)

```
의제:
  1. 프로젝트 목표 재확인
  2. 팀 역할 분담 확정
  3. 위험 요소 공유
  4. Daily standup 규칙
  5. Slack 채널 (#avm-vworld-phase1)

산출물: 
  └─ 팀 명단 + 연락처 문서
```

#### AM 10:00~11:00: **AVM 준비** (AVM Team)

```
장소: F:\NPL전례\avm_project

작업:
  1. .env 파일 확인
     python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✓' if os.getenv('KOREA_API_KEY') else '✗')"
  
  2. fetch_transactions_parallel.py 검토
     - 체크포인트 시스템 확인
     - 재시도 로직 검증
     - 로깅 설정 확인
  
  3. 명령어 최종 검증
     python scripts/fetch_transactions_parallel.py --help

산출물:
  └─ AVM 준비 완료 체크리스트
```

#### AM 10:00~11:00: **VWorld 설계** (VWorld Team)

```
장소: C:\Users\eungk\OneDrive\Documents\AVM\docs

작업:
  1. Rev.4 기획서 검토
     - 14개 레이어 목록 확인
     - endpoint 분류 (확정/후보/대체)
     - parser 요구사항 분석
  
  2. registry seed 구조 설계
     - api_kind 분류 (search, geocoder, wfs, wms, reference)
     - 필수/선택 파라미터 정의
     - probe 상태 분류 (ok, no_features, image_only, blocked)
  
  3. Python 프로젝트 구조 설계
     vworld_multi_layer_collector/
       ├─ scripts/
       │  └─ vworld_multi_layer_collector.py
       ├─ parsers/
       │  ├─ search_parser.py
       │  ├─ geocoder_parser.py
       │  └─ wfs_parser.py
       └─ config/
          └─ rev4_registry.seed.json

산출물:
  └─ registry_schema.json (skeleton)
```

#### AM 11:00~12:00: **API 키 신청** (AVM DE Lead)

```
작업:
  1. https://www.data.go.kr/ 접속
  2. 회원 로그인
  3. "아파트매매 실거래자료" 검색
  4. "국토교통부_아파트매매 실거래자료" → [활용신청]
  5. 신청 완료 스크린샷 저장
  6. Slack에 진행 상황 보고

예상: 24시간 내 승인
백업: 2개 계정으로 동시 신청 (병렬 승인)
```

#### PM 13:00~14:00: **환경 최종 검증** (모든 팀)

```
AVM:
  - 패키지 설치 확인: pip list | grep -E "tqdm|pandas|sqlalchemy"
  - DB 연결 테스트: python -c "from app.db.database import SessionLocal; print('✓')"
  - 스크립트 테스트: python scripts/fetch_transactions_parallel.py --help

VWorld:
  - Python 버전: python --version (3.8+)
  - 필요 패키지: pip install requests tqdm
  - 기획서 다운로드 및 오프라인 저장
```

#### PM 14:00~17:00: **작업 착수**

```
AVM:
  - fetch_transactions_parallel.py 코드 리뷰 (1시간)
  - Pilot 수집 스크립트 최종 테스트 (1시간)
  - 07-04 수집 일정 최종 확인 (30분)
  - 대기 중 문서 정리 (1시간)

VWorld:
  - registry seed 초안 작성 (1시간)
  - endpoint probe CLI skeleton (2시간)
  - 초기 parser 구조 설계 (1시간)
```

#### 📊 **Day 1 체크리스트**

```
✅ 팀 8명 모두 준비 완료
✅ Slack 채널 생성 (#avm-vworld-phase1)
✅ AVM: .env 설정, 스크립트 검증
✅ AVM: API 키 신청 (24시간 대기)
✅ VWorld: 기획서 숙독, 설계 시작
✅ Daily standup 09:30 AM 예약됨
```

---

### **DAY 2: 2026-07-04 (금) - Pilot & 설계**

#### 09:30: **Daily Standup**
```
AVM: API 키 신청 진행, Pilot 준비 중
VWorld: registry seed 90% 완료
```

#### 10:00~11:00: **Pilot 수집** (AVM DE)

```
명령어:
cd F:\NPL전례\avm_project
python scripts/fetch_transactions_parallel.py \
  --year 2026 --month 6 \
  --sido 경기도 \
  --workers 3 \
  --checkpoint data/collection_checkpoint.json

모니터링:
  - 진행 상황 (tqdm 표시)
  - 오류 로그 (data/fetch_transactions_parallel.log)
  - 예상 완료: 30분

검증:
  - DB 행 수: SELECT COUNT(*) FROM transactions;
  - 기대값: ~7,234건
```

#### 11:00~12:00: **Pilot 검증** (AVM QA)

```
SQL 쿼리:
1. 데이터 건수
   SELECT COUNT(*) FROM transactions;
   → 7,000~8,000건 예상

2. 시간 범위
   SELECT MIN(contract_year||'-'||contract_month), 
          MAX(contract_year||'-'||contract_month) 
   FROM transactions;
   → 2026-06-* 범위

3. 데이터 샘플
   SELECT * FROM transactions LIMIT 10;
   → 정상 형식 확인

4. 중복 검사
   SELECT COUNT(*) FROM transactions 
   WHERE transaction_key IN (
     SELECT transaction_key FROM transactions 
     GROUP BY transaction_key HAVING COUNT(*) > 1);
   → 0건

GO/NO-GO 결정:
  ✓ GO: 진행 (07-05 전국 수집)
  ✗ NO-GO: 분석 후 재시도
```

#### PM 13:00~15:00: **endpoint probe 초안** (VWorld)

```
작업:
1. probe CLI skeleton 작성 (1시간)
   vworld_multi_layer_collector.py probe-endpoints \
     --profile rev4 \
     --key-prompt \
     --write

2. 14개 레이어 probe 순서 정의 (30분)
   a) Search (1개)
   b) Geocoder (1개)
   c) reference contract (1개)
   d) WFS (7개)
   e) WMS (2개)
   f) NED list (1개)
   g) NED WFS (3개)

3. 첫 3개 (Search, Geocoder, reference) 코드 (30분)
```

#### PM 15:00~17:00: **문서화 & 대기**

```
AVM:
  - Pilot 결과 보고서 작성
  - 07-05 전국 수집 계획 최종 확인
  - 모델 학습 환경 준비

VWorld:
  - registry seed v1 완성
  - probe CLI v1 코드 완성
```

#### 📊 **Day 2 체크리스트**

```
✅ Pilot 수집 완료 (~7,234건)
✅ Pilot 검증 완료 (GO/NO-GO 결정)
✅ VWorld registry seed v1 완성
✅ VWorld probe CLI skeleton 완성
✅ API 키 승인 대기 (최악의 경우 내일)
```

---

### **DAY 3-5: 2026-07-05~07 (토~월) - 전국 수집**

#### 07-05 (토) 10:00: **전국 수집 시작** (AVM)

```
명령어:
python scripts/fetch_transactions_parallel.py \
  --months 12 \
  --workers 3 \
  --checkpoint data/collection_checkpoint.json

실행 모드: 백그라운드
  → screen 또는 nohup으로 실행
  → 24시간 연속 실행

모니터링:
  - 1시간마다 진도 확인
  - 로그: tail -f data/fetch_transactions_parallel.log
  - 예상 완료: 07-06 일요일 오전
```

#### 07-05 (토): **VWorld 병렬 개발** (VWorld)

```
작업:
1. endpoint probe CLI v1 실행 (Search/Geocoder/reference)
   → 3개 endpoint 상태 확인
   → registry에 결과 기록

2. WFS parser skeleton (4개 병렬)
   - continuous_cadastral_map
   - building_by_use
   - gis_building_general
   - land_use_plan

3. 초기 테스트
   - 각 parser가 XML/GML 파싱 가능 확인
```

#### 07-06 (일): **수집 검증** (AVM)

```
예상 상태:
  ├─ 수집 완료: ~850,000건
  ├─ 소요시간: 14-16시간 (병렬도 3)
  ├─ 성공률: >99%
  └─ 중복: 자동 제거됨

검증 SQL:
  SELECT COUNT(*) FROM transactions;
  → 850,000건 이상

기록:
  - 최종 통계 저장
  - 체크포인트 백업 (data/collection_checkpoint.final.json)
```

#### 07-07 (월): **수집 완료 확인**

```
최종 검증:
  ✓ 데이터 건수: 850K+ 확인
  ✓ 지역 분포: 243개 시군구 모두 포함
  ✓ 시간 범위: 2025-07 ~ 2026-06 (12개월)
  ✓ 품질: 이상값 <3%

승인: GO (모델 학습 진행)
```

#### 📊 **DAY 3-5 체크리스트**

```
✅ 전국 12개월 데이터 850K+ 건 수집
✅ 수집 완료 검증 (모든 기준 충족)
✅ VWorld 4개 WFS parser 초안 완성
✅ 10개 endpoint probe 결과 기록
```

---

### **DAY 6-8: 2026-07-08~10 (화~목) - 모델 학습**

#### 07-08 (화): **데이터 전처리** (AVM MLE)

```
작업:
python scripts/p6_extract_prepare_data.py \
  --source transactions \
  --output data/training_data.csv \
  --min_records 1000 \
  --filters "price_manwon > 10000 and exclusive_area > 10"

산출물: 
  └─ data/training_data.csv (750K행)

시간: ~4시간
```

#### 07-08 (화): **VWorld WMS 조사** (VWorld)

```
작업:
1. WMS endpoint probe CLI 작성 (1시간)
2. 지역별/이용상황별 지가변동률 WMS probe (2시간)
3. 결과 분류 (image_only vs feature_info 가능)
```

#### 07-09 (수): **특성 공학** (AVM MLE)

```
작업:
python scripts/p6_feature_engineering.py \
  --input data/training_data.csv \
  --output data/training_engineered.csv

산출물:
  └─ data/training_engineered.csv (750K행 × 35열)

시간: ~8시간
```

#### 07-09 (수): **VWorld 병렬화** (VWorld)

```
작업:
1. WFS saturation splitter 설계 (1시간)
   - maxfeatures 1000 기준
   - 포화 시 4분할 로직
   
2. 3-4개 layer 병렬 parser 테스트 (2시간)
   - 실제 데이터로 parsing
   - geometry 추출 확인
```

#### 07-10 (목): **비교사례 쌍 생성 & 모델 학습 시작** (AVM MLE)

```
작업 1: 쌍 생성 (4시간)
python scripts/p6_pairing_engine.py \
  --input data/training_engineered.csv \
  --output data/training_pairs.csv

산출물:
  └─ data/training_pairs.csv (4M행 × 75열)

작업 2: 모델 학습 시작 (4시간+)
python scripts/p5_unified_training.py \
  --input data/training_pairs.csv \
  --output models/trained_model.pkl \
  --cv_folds 5 \
  --workers 4

예상 완료: 07-11 오전
```

#### 07-10 (목): **VWorld 초기 코드 완성** (VWorld)

```
산출물:
  ✓ vworld_multi_layer_collector.py (스켈레톤)
  ✓ parser/ 디렉토리 (4개 parser)
  ✓ registry seed (14개 레이어 정의)
  ✓ endpoint probe CLI (실행 가능)

상태: "Ready for Phase 2"
```

#### 📊 **DAY 6-8 체크리스트**

```
✅ 데이터 전처리 완료 (750K 행)
✅ 특성 공학 완료 (35개 특성)
✅ 비교사례 쌍 생성 (4M 쌍)
✅ 모델 학습 시작 (20시간 예상)
✅ VWorld 초기 코드 프레임 완성
```

---

### **DAY 9-11: 2026-07-11~13 (금~일) - 배포 준비**

#### 07-11 (금): **모델 검증** (AVM MLE + QA)

```
작업:
python scripts/p7_generate_evaluation_results.py \
  --model models/trained_model.pkl \
  --test_data data/test_pairs.csv

산출물:
  ├─ reports/model_evaluation.json
  ├─ R² score (기대: 0.943)
  ├─ MAPE (기대: 9.8%)
  └─ feature importance

검증:
  ✓ R² > 0.94 확인
  ✓ MAPE < 10.5% 확인
  ✓ 부분군 성능 검증
```

#### 07-11 (금): **VWorld 최종 점검** (VWorld)

```
작업:
1. 모든 14개 레이어 endpoint probe 완료
2. registry 최종 상태:
   - ok: 8-10개
   - no_features: 0-2개
   - image_only: 1-2개
   - blocked: 0-2개

산출물:
  └─ api_endpoint_registry.json (최종)
```

#### 07-12 (토): **배포 준비** (AVM DevOps + QA)

```
작업:
1. 모델 통합 (1시간)
   - app/avm/engine.py 업데이트
   - 환경변수 설정
   
2. 스테이징 배포 (2시간)
   - 포트 8001에서 신규 모델 실행
   - 50건 스모크 테스트
   - 성능 기준선 기록
   
3. 배포 체크리스트 (1시간)
   - 코드 리뷰 완료
   - 테스트 통과
   - 롤백 계획 확인

산출물:
  └─ DEPLOYMENT_CHECKLIST.md
```

#### 07-12 (토): **VWorld 인수/인계** (VWorld)

```
산출물:
  ├─ vworld_multi_layer_collector.py (완성)
  ├─ parsers/* (5개+ 파서)
  ├─ config/rev4_registry.seed.json
  ├─ 실행 가이드
  └─ Phase 2 인수 문서

상태: "Ready for Phase 2 expansion"
```

#### 07-13 (일): **Production 배포** (AVM DevOps + 모니터링팀)

```
14:00~16:30: Blue-Green 배포 실행

단계별 실행:
  14:00~14:15: Pre-flight 체크
  14:15~14:45: Green (신규) 배포
  14:45~15:00: 트래픽 10% 전환
  15:00~15:20: 트래픽 50% 전환
  15:20~16:00: 트래픽 100% 전환
  16:00~16:30: 최종 검증

모니터링:
  - P95 응답시간: <1000ms
  - 에러율: <0.1%
  - 예측치 범위: 정상

결과:
  ✅ 배포 완료 (무중단)
  ✅ 새 모델 (R² 0.943) 운영 중
  ✅ 롤백 경로 준비됨
```

#### 📊 **DAY 9-11 체크리스트**

```
✅ 모델 검증 완료 (R² 0.943, MAPE 9.8%)
✅ 배포 준비 완료 (체크리스트 100%)
✅ Production 배포 완료 (Blue-Green, 무중단)
✅ VWorld Phase 1 완료 (14개 레이어 프로브)
```

---

## 📊 **Phase 1 최종 성과**

### **AVM 팀**

```
✅ 850,000+ 건 실거래 데이터 수집
✅ 모델 R² 0.943 달성 (목표: >0.94)
✅ MAPE 9.8% 달성 (목표: <10.5%)
✅ Production 배포 완료 (2026-07-13)
✅ 무중단 전환 성공
```

### **VWorld 팀**

```
✅ Rev.4 기획서 기반 14개 레이어 정의
✅ 13개 endpoint probe 완료 (1개 reference)
✅ 5-6개 parser 초안 완성
✅ vworld_multi_layer_collector.py 스켈레톤 완성
✅ Phase 2 준비 완료
```

### **종합**

```
📊 AVM: 배포 완료 (즉시 수익)
📊 VWorld: Phase 2 준비 완료 (대기 중)
📊 팀: 7/10 (AVM 배포로 2명 해제 가능)
📊 다음 단계: Phase 2 (VWorld 집중 개발)
```

---

## 🎯 **Phase 1 위험 요소 & 대응**

| 위험 | 확률 | 영향 | 대응 |
|------|------|------|------|
| API 키 미발급 | 5% | 1일 지연 | 2계정 신청 |
| 데이터 품질 불량 | 10% | 모델 성능 저하 | 필터링 강화 |
| WMS endpoint 실패 | 20% | VWorld 지연 | fallback layer 준비 |
| 배포 실패 | 5% | 롤백 + 재시도 | rollback 스크립트 준비 |

---

## 📞 **긴급 연락처**

```
Project Manager: [TBD]
AVM Team Lead: [TBD]
VWorld Lead: [TBD]
On-Call: [TBD]
```

---

## 🚀 **지금 실행할 것**

```
✅ 1. 09:30 AM: Daily standup 시작
✅ 2. 10:00 AM: 팀 역할 분담 확정
✅ 3. 10:00 AM: AVM API 키 신청
✅ 4. 10:00 AM: VWorld registry 설계 시작
✅ 5. 매일 09:30 AM: standup 계속
```

---

**Phase 1 실행 중... ⏱️**

