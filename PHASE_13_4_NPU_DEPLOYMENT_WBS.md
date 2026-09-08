# Phase 13.4 WBS (Work Breakdown Structure)
## NPU 배포 & API 서비스 최적화

**기간**: 2026-07-19 ~ 2026-07-23 (5일, Week 3 후반)  
**팀**: Claude Agent (1명)  
**주요 마일스톤**: 모델 변환 (Day 1), NPU 엔진 (Day 2-3), API 배포 (Day 4), 성능 검증 (Day 5)

---

## 1. 전체 작업 분해

```
Phase 13.4 (5일 × 9h = 45시간)
│
├─ 1. 모델 변환 (4h)
│  ├─ 1.1 ONNX 변환 (LightGBM → ONNX) (1h)
│  ├─ 1.2 OpenVINO IR 변환 (ONNX → XML/BIN) (1h)
│  ├─ 1.3 정확도 검증 (<0.5% loss) (1h)
│  └─ 1.4 성능 벤치마크 (1h)
│
├─ 2. NPU 추론 엔진 (8h)
│  ├─ 2.1 NPUInferenceEngine 클래스 구현 (3h)
│  ├─ 2.2 Unit test & 1000샘플 추론 (2h)
│  ├─ 2.3 Device fallback 테스트 (CPU/GPU) (1.5h)
│  └─ 2.4 성능 프로파일링 (1.5h)
│
├─ 3. REST API 개발 (8h)
│  ├─ 3.1 FastAPI 애플리케이션 구축 (2h)
│  ├─ 3.2 Request/Response 모델 정의 (1h)
│  ├─ 3.3 엔드포인트 구현 (/api/valuation) (2h)
│  ├─ 3.4 Error handling & validation (1h)
│  ├─ 3.5 Rate limiting & 모니터링 (1.5h)
│  └─ 3.6 API 문서 생성 (0.5h)
│
├─ 4. 서비스 배포 (6h)
│  ├─ 4.1 Docker 컨테이너화 (2h)
│  ├─ 4.2 docker-compose 설정 (1h)
│  ├─ 4.3 로컬 배포 & 테스트 (1.5h)
│  ├─ 4.4 Prometheus/Grafana 모니터링 설정 (1.5h)
│  └─ 4.5 로깅 시스템 통합 (0.5h)
│
├─ 5. 성능 검증 (12h)
│  ├─ 5.1 부하 테스트 (1000 req/min) (2h)
│  ├─ 5.2 지연시간 측정 (p50, p99) (2h)
│  ├─ 5.3 메모리/CPU 프로파일링 (2h)
│  ├─ 5.4 정확도 재확인 (R² > 0.85) (2h)
│  ├─ 5.5 Device fallback 성능 평가 (2h)
│  └─ 5.6 벤치마크 보고서 작성 (2h)
│
├─ 6. 문서 & QA (5h)
│  ├─ 6.1 API 문서 (Swagger/OpenAPI) (1h)
│  ├─ 6.2 배포 가이드 (1h)
│  ├─ 6.3 운영 매뉴얼 (1.5h)
│  ├─ 6.4 트러블슈팅 가이드 (1h)
│  └─ 6.5 최종 QA 검사 (0.5h)
│
└─ 7. 이관 및 아카이빙 (2h)
   ├─ 7.1 성능 SLA 정의 (0.5h)
   ├─ 7.2 알림 규칙 설정 (0.5h)
   ├─ 7.3 롤백 계획 수립 (0.5h)
   └─ 7.4 Phase 13.5 이행조건 확인 (0.5h)
```

---

## 2. 일일 진행 계획

### Day 1 (2026-07-19): 모델 변환

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
09:00   1.1 ONNX 변환                Claude  ✓      best_model_kr.onnx
10:00   1.2 OpenVINO IR 변환         Claude  ✓      .xml + .bin
11:00   1.3 정확도 검증              Claude  ✓      <0.5% loss 확인
12:00   Lunch (1h)
13:00   1.4 성능 벤치마크            Claude  ✓      latency 측정
14:00   모델 변환 완료 검수          Claude  ✓      파일 크기 확인
14:30   Daily Standup & Log
15:00   End of Day 1
```

**Day 1 산출물**:
- ✅ best_model_kr.onnx (~18MB)
- ✅ OpenVINO IR (3MB XML + 8MB bin)
- ✅ 정확도 검증 결과 (<0.5% loss 달성)
- 📊 변환 성능 보고서

---

### Day 2 (2026-07-20): NPU 엔진 구현

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
09:00   2.1 NPUInferenceEngine 작성   Claude  ⏳     phase13_npu_inference.py
11:00   2.2 Unit test 및 1000샘플     Claude  ⏳     테스트 결과
12:00   Lunch (1h)
13:00   2.3 Device fallback 테스트    Claude  ⏳     CPU/GPU 동작 확인
14:30   2.4 성능 프로파일링          Claude  ✓      latency 분포
15:30   NPU 엔진 QA 검증             Claude  ✓      최종 확인
16:00   Daily Standup & Log
16:30   End of Day 2
```

**Day 2 산출물**:
- ✅ NPUInferenceEngine 클래스 (<50 lines/method)
- ✅ Unit test 100% pass
- ✅ Device fallback 자동 선택 동작 확인
- 📊 성능 프로파일 (p50, p99 latency)

**Day 2 기대 결과**:
```
NPU Latency Profile (1000 predictions):
├─ p50: 6.5ms ✓
├─ p99: 12.0ms ✓
├─ mean: 8.2ms ✓
└─ Max: 15ms ✓
```

---

### Day 3 (2026-07-21): REST API 개발

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
09:00   3.1 FastAPI 애플리케이션      Claude  ✓      app initialization
10:00   3.2 Request/Response 모델     Claude  ✓      Pydantic models
11:00   3.3 /api/valuation 엔드포인트 Claude  ✓      POST endpoint
12:00   Lunch (1h)
13:00   3.4 Error handling 추가       Claude  ✓      HTTP exceptions
14:00   3.5 Rate limiting 구현        Claude  ✓      1000 req/min limiter
14:45   3.6 API 문서 생성             Claude  ✓      Swagger UI
15:30   API 기능 테스트               Claude  ✓      모든 endpoint 검증
16:00   Daily Standup & Log
16:30   End of Day 3
```

**Day 3 산출물**:
- ✅ phase13_api_service.py (완전 구현)
- ✅ Request/Response 모델 (Pydantic)
- ✅ /api/valuation POST endpoint
- ✅ /health GET endpoint
- ✅ Error handling (400/500 responses)
- 📋 Swagger API 문서

---

### Day 4 (2026-07-22): 서비스 배포

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
09:00   4.1 Dockerfile 작성           Claude  ✓      image 빌드
10:00   4.2 docker-compose 설정       Claude  ✓      services 정의
11:00   4.3 로컬 배포                 Claude  ✓      Port 8000 리스닝
12:00   Lunch (1h)
13:00   4.3 배포 후 엔드투엔드 테스트 Claude  ✓      HTTP 요청 검증
14:00   4.4 Prometheus/Grafana 설정   Claude  ✓      메트릭 수집
15:00   4.5 로깅 통합                 Claude  ✓      JSON structured logs
15:30   배포 완료 검증                Claude  ✓      최종 확인
16:00   Daily Standup & Log
16:30   End of Day 4
```

**Day 4 산출물**:
- ✅ Dockerfile (python:3.11 + OpenVINO)
- ✅ docker-compose.yml (npu-api + prometheus + grafana)
- ✅ API 서비스 배포 완료 (localhost:8000)
- ✅ Prometheus 메트릭 수집
- ✅ Grafana 대시보드 (기본)
- 📊 배포 로그

---

### Day 5 (2026-07-23): 성능 검증 & 최종 완료

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
09:00   5.1 부하 테스트               Claude  ⏳     1000 req/min 처리
10:30   5.2 지연시간 측정             Claude  ⏳     p50/p99 기록
11:30   5.3 리소스 프로파일링         Claude  ⏳     메모리/CPU 사용
12:30   Lunch (1h)
13:30   5.4 정확도 재확인             Claude  ✓      R² 검증
14:00   5.5 Fallback 성능 평가        Claude  ✓      CPU/GPU 비교
14:30   5.6 벤치마크 보고서           Claude  ✓      최종 성능 요약
15:30   6.1-6.5 문서 작성             Claude  ✓      모든 가이드
16:30   7.1-7.4 QA & 이관             Claude  ✓      Phase 13.5 준비
17:00   Daily Standup & Final Log
17:30   End of Day 5
```

**Day 5 산출물**:
- ✅ 부하 테스트 결과 (1000 req/min 처리 확인)
- ✅ 성능 벤치마크 (NPU vs GPU vs CPU)
- ✅ R² > 0.85 정확도 재확인
- ✅ API 문서 (Swagger/OpenAPI)
- ✅ 배포 가이드
- ✅ 운영 매뉴얼
- ✅ Phase 13.5 이행조건 확인

---

## 3. 작업 의존성 분석

```
Task Dependency Graph:

1.1 ONNX Conversion
    │
    ├─→ 1.2 OpenVINO IR Conversion
    │    │
    │    ├─→ 1.3 Accuracy Validation
    │    │    │
    │    │    └─→ 1.4 Benchmark
    │    │         │
    │    │         └─→ 2.1 NPU Engine
    │    │              │
    │    │              ├─→ 2.2 Unit Test
    │    │              ├─→ 2.3 Fallback Test
    │    │              └─→ 2.4 Profiling
    │    │                   │
    │    │                   └─→ 3.1 FastAPI App
    │    │                        │
    │    │                        ├─→ 3.2 Models
    │    │                        ├─→ 3.3 Endpoints
    │    │                        ├─→ 3.4 Error Handling
    │    │                        ├─→ 3.5 Rate Limiting
    │    │                        └─→ 3.6 API Docs
    │    │                             │
    │    │                             └─→ 4.1 Dockerfile
    │    │                                  │
    │    │                                  ├─→ 4.2 docker-compose
    │    │                                  ├─→ 4.3 Local Deployment
    │    │                                  ├─→ 4.4 Prometheus
    │    │                                  └─→ 4.5 Logging
    │    │                                       │
    │    │                                       └─→ 5.1-5.6 Performance Test
    │    │                                            │
    │    │                                            └─→ 6.1-6.5 Documentation
    │    │                                                 │
    │    │                                                 └─→ 7.1-7.4 Handover
```

**크리티컬 패스**: 1.1 → 1.2 → 1.3 → 1.4 → 2.1 → 2.2 → 2.3 → 2.4 → 3.1 → 3.3 → 4.1 → 4.3 → 5.1 → 5.6 → 6.5 → 7.4

**병렬화 가능 작업**:
- 3.2 (Request models) + 3.4 (Error handling): 30min 단축
- 5.3 (Memory) + 5.5 (Fallback test): 동시 진행 가능
- 6.1 (API docs) + 6.2 (Deployment guide): 병렬 작성

---

## 4. 리소스 할당

### 4.1 총 투입 시간

| 작업군 | 예상시간 | 효율 | 비고 |
|--------|---------|------|------|
| **1. 모델 변환** | 4h | 100% | 순차적 |
| **2. NPU 엔진** | 8h | 100% | 순차적 |
| **3. API 개발** | 8h | 95% | 병렬화 불가 |
| **4. 배포** | 6h | 100% | 순차적 |
| **5. 성능 검증** | 12h | 90% | 부하테스트 병렬 |
| **6. 문서화** | 5h | 95% | 병렬 가능 |
| **7. 이관** | 2h | 100% | 순차적 |
| **TOTAL** | **45h** | **97%** | 4시간 단축 가능 |

### 4.2 컴퓨팅 리소스

```
리소스            사용시간        할당량      비용
────────────────────────────────────────────────
GPU (RTX 5050)    Day 1, 5      일부       $0
CPU (4 cores)     Day 2-5       100%       $0
메모리 (16GB)     Day 4-5       8-12GB     $0
디스크            Day 1-5       500MB      $0
────────────────────────────────────────────────
Total:                                    $0
```

---

## 5. 마일스톤

| 마일스톤 | 날짜 | 목표 | 성공기준 |
|---------|------|------|--------|
| **M1: 모델 변환** | Jul 19 14:00 | ONNX + OpenVINO IR | 정확도 손실 <0.5% ✓ |
| **M2: NPU 엔진** | Jul 20 15:30 | 추론 엔진 구현 | 1000샘플 <10ms ✓ |
| **M3: API 서비스** | Jul 21 16:00 | REST API 배포 | /api/valuation 동작 ✓ |
| **M4: 서비스 배포** | Jul 22 16:30 | Docker 배포 | Port 8000 리스닝 ✓ |
| **M5: 성능 검증** | Jul 23 15:00 | 벤치마크 완료 | 1000 req/min 처리 ✓ |
| **M6: 문서화 완료** | Jul 23 17:00 | 모든 가이드 작성 | API/배포/운영 문서 ✓ |

---

## 6. 위험 및 대응

| 위험 | 확률 | 영향 | 대응책 |
|------|------|------|--------|
| ONNX 변환 실패 | 10% | Day 1 지연 | 수동 그래프 최적화 |
| OpenVINO 드라이버 미설치 | 15% | NPU 불가 | CPU fallback 활용 |
| API 응답 >20ms | 15% | 목표 미달 | Feature 캐싱, batch 처리 |
| Docker 빌드 오류 | 10% | Day 4 지연 | 의존성 최소화 |
| 부하테스트 기기 부하 | 20% | 순시적 | 분산 테스트 또는 재시도 |

---

## 7. 단계별 체크리스트

### Phase 13.4 완료 조건

```
✅ 모델 변환
├─ ONNX 파일 생성 (<20MB)
├─ OpenVINO IR 생성 (<12MB total)
└─ 정확도 손실 <0.5%

✅ NPU 엔진
├─ NPUInferenceEngine 클래스 (<50 lines/method)
├─ 1000샘플 추론 <10ms (p99)
└─ Device fallback 자동 선택

✅ REST API
├─ /api/valuation endpoint 구현
├─ Request/Response 모델 검증
└─ Error handling 완료

✅ 서비스 배포
├─ Docker 이미지 빌드 완료
├─ docker-compose 설정 완료
└─ localhost:8000 서비스 실행

✅ 성능 검증
├─ 1000 req/min 처리 능력 확인
├─ p50 latency <10ms, p99 <20ms
├─ R² > 0.85 유지
└─ 메모리 <500MB

✅ 문서 & 배포
├─ Swagger API 문서 생성
├─ 배포 가이드 작성
├─ 운영 매뉴얼 작성
└─ Phase 13.5 이행조건 확인

└─→ Phase 13.5 시작 가능
```

---

**WBS 완성**  
**총 프로젝트 기간**: 5일 (41-45시간)  
**예상 완료**: 2026-07-23 17:30
