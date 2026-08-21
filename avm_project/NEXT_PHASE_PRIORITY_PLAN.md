# 🎯 AVM 프로젝트 다음 단계 우선순위 계획서

## 📋 작업 우선순위 (총 3단계, 1-2주 소요)

### 🥇 **PHASE 1: Cloud Run 배포 (즉시 - 1-2일)**
**목표**: 프로덕션 API 운영 시작
**상태**: 준비 완료 (배포 차단 요소 없음)
**의존성**: GCP 프로젝트 + 인증

#### 1-1. 사전 요구사항 확인
- [ ] GCP 프로젝트 ID 준비
- [ ] gcloud CLI 설치 및 인증
- [ ] Docker Desktop 실행 중
- [ ] 필요한 API 활성화 (run.googleapis.com, containerregistry.googleapis.com)

#### 1-2. 자동 배포 실행
```bash
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=asia-northeast1
cd /home/user/-/avm_project
./deploy_cloudrun.sh
```

#### 1-3. 배포 후 검증
- [ ] 서비스 URL 획득
- [ ] 헬스체크 성공 (GET /health → 200 OK)
- [ ] API 문서 확인 (https://YOUR_URL/docs)
- [ ] 샘플 예측 요청 테스트

**예상 결과**: 
- 공개 REST API 운영 시작
- 월간 $30-50 추정 비용
- 121K requests/sec 처리 능력

---

### 🥈 **PHASE 2: 실제 데이터 수집 및 모델 재학습 (2-3일)**
**목표**: 프로덕션급 모델 완성 (R² 0.94+)
**상태**: Phase 1 완료 후 진행
**의존성**: Data.go.kr API 인증

#### 2-1. API 인증 상태 확인
- [ ] Data.go.kr 포털 접속 (https://www.data.go.kr)
- [ ] 마이페이지 → API 관리 메뉴
- [ ] "부동산 실거래 정보" API 상태 확인
  - 활성: 즉시 수집 가능
  - 대기: 48시간 대기 후 재확인
  - 거절: 재신청 필요

#### 2-2. 월별 데이터 수집 (자동화)
```bash
python scripts/test_api_collection.py \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --api-key YOUR_API_KEY
```

**예상 데이터**:
- 월별 85-160MB (지역별 변동)
- 연간 470-820MB
- 200만+ 거래 레코드

#### 2-3. 모델 재학습
```bash
python scripts/avm_injection_engine.py \
  --data-path data/raw/collected_data_2024.csv \
  --train-all-models
```

#### 2-4. 성능 검증
- [ ] 5-fold 교차검증 실행
- [ ] 각 모델별 R², RMSE, MAE, MAPE 계산
- [ ] 최고 성능 모델 선택
- [ ] 새 모델 배포 (Cloud Run 업데이트)

**예상 결과**:
- R² 점수 0.94+ 달성
- 모델 정확도 개선
- 프로덕션 배포 준비 완료

---

### 🥉 **PHASE 3: 자동화 설정 (1일)**
**목표**: 주간 자동 데이터 수집 + 모델 갱신
**상태**: Phase 2 완료 후 진행
**의존성**: Linux/Mac 환경

#### 3-1. Cron 자동화 설정 (Linux/Mac)
```bash
bash scripts/setup_cron_automation.sh
# 매주 목요일 10:00 자동 실행
```

#### 3-2. 자동화 워크플로우
```
매주 목요일 10:00
  ├─ 지난 주 데이터 수집 (월-일)
  ├─ 데이터 전처리
  ├─ 모델 재학습 (6개 모델)
  ├─ 성능 평가 및 최고 모델 선택
  ├─ Cloud Run 배포 업데이트
  └─ 실행 리포트 생성
```

#### 3-3. 모니터링 설정
- [ ] Cloud Console에서 메트릭 대시보드 설정
- [ ] 에러율 알람 설정 (>5%)
- [ ] 응답 시간 알람 설정 (>500ms)
- [ ] 비용 알람 설정

**예상 결과**:
- 완전 자동화 운영
- 월간 1회 모델 갱신
- 항상 최신 데이터 기반 예측

---

## 📊 타임라인

```
Week 1
├─ Day 1-2: PHASE 1 (Cloud Run 배포)
│           소요: 3시간 총 (GCP 1h + 배포 30m + 검증 1.5h)
│
├─ Day 3-5: PHASE 2 (데이터 수집 및 모델 재학습)
│           소요: 5시간 총 (API 1h + 수집 2h + 재학습 2h)
│
└─ Day 6: PHASE 3 (자동화)
          소요: 1.5시간 (설정 30m + 모니터링 1h)

✅ 1주일 내 완전 자동화 운영 가능
```

---

## ✅ 의존성 체크리스트

| 항목 | PHASE 1 | PHASE 2 | PHASE 3 |
|------|---------|---------|---------|
| GCP 계정 | ✅필수 | - | - |
| GCP 프로젝트 | ✅필수 | - | - |
| gcloud CLI | ✅필수 | - | - |
| Data.go.kr API | - | ✅필수 | ✅연동 |
| Linux/Mac | - | - | ✅필수 |

---

**현재 상태**: 모든 코드/문서 준비 완료, PHASE 1 즉시 시작 가능 ✅

