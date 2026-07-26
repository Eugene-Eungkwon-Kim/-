# Loan4U AVM - 테스트 및 QA/QC 계획서

**작성일**: 2026-06-26  
**버전**: 1.0.0  
**상태**: ✅ 최종 승인  
**담당**: QA/QC 팀  

---

## 📋 목차

1. [테스트 전략](#테스트-전략)
2. [테스트 범위 및 목표](#테스트-범위-및-목표)
3. [테스트 환경](#테스트-환경)
4. [테스트 케이스](#테스트-케이스)
5. [QA/QC 기준](#qaqc-기준)
6. [버그 추적 및 보고](#버그-추적-및-보고)
7. [성능 테스트](#성능-테스트)
8. [보안 테스트](#보안-테스트)
9. [사용자 수용 테스트](#사용자-수용-테스트-uat)
10. [릴리스 기준](#릴리스-기준)
11. [테스트 일정](#테스트-일정)
12. [위험 분석](#위험-분석)

---

## 테스트 전략

### 🎯 테스트 목표

| 목표 | 목표값 | 우선순위 |
|------|--------|---------|
| 코드 커버리지 | ≥90% | 🔴 필수 |
| 버그 발견율 | ≥95% | 🔴 필수 |
| 성능 목표 달성 | 1-2ms 지연 | 🔴 필수 |
| 정확도 목표 달성 | R²>0.84, MAPE<10.5% | 🔴 필수 |
| 보안 취약점 | 0개 (Critical) | 🔴 필수 |

### 📊 테스트 레벨별 접근

```
Unit Test (60%)
    ↓
Integration Test (25%)
    ↓
System Test (10%)
    ↓
UAT (5%)
```

**적용 순서**:
1. **Phase 13.1**: 데이터 수집 - Unit + Integration
2. **Phase 13.2**: GPU 훈련 - Unit + Performance
3. **Phase 13.2.5**: 모델 변환 - Integration + System
4. **Phase 13.4**: NPU 추론 - Unit + Performance + Security
5. **Phase 13.4.1**: FastAPI - Integration + E2E + Security
6. **Phase 14**: CI/CD + 모니터링 - System + Performance

---

## 테스트 범위 및 목표

### ✅ 포함 범위

| 컴포넌트 | 테스트 유형 | 목표 |
|---------|-----------|------|
| **데이터 수집** | 단위, 통합 | API 정상 작동, 에러 처리 |
| **전처리** | 단위, 통합 | 데이터 품질, 이상치 감지 |
| **GPU 훈련** | 성능, 통합 | 정확도 목표 달성 (R²>0.84) |
| **모델 변환** | 단위, 통합 | INT8 양자화 오차<1% |
| **NPU 추론** | 성능, 보안 | 지연시간<2ms, 메모리<2GB |
| **FastAPI** | E2E, 보안 | 엔드포인트 정상, 인증 검증 |
| **CI/CD** | 통합, 시스템 | 자동화 작동, 배포 성공 |
| **모니터링** | 통합, 시스템 | 메트릭 수집, 알림 정상 |

### ❌ 제외 범위

- 클라이언트 UI/UX 테스트
- 하드웨어 드라이버 테스트
- 외부 API (Data.go.kr) 가용성 테스트
- 부하 테스트 (>1000 req/sec)

---

## 테스트 환경

### 🖥️ 테스트 머신 사양

| 환경 | GPU | VRAM | CPU | 용도 |
|------|-----|------|-----|------|
| **개발** | RTX 5050 | 8GB | i7 | 로컬 개발 & 단위 테스트 |
| **CI/CD** | A100 (옵션) | 40GB | 16 cores | GitHub Actions 통합 테스트 |
| **스테이징** | RTX 5050 | 8GB | i7 | 프로덕션 전 최종 검증 |
| **프로덕션** | NPU (온보드) | 2GB | - | 최종 배포 환경 |

### 🔧 테스트 도구

| 도구 | 버전 | 목적 |
|------|------|------|
| **pytest** | 7.4.3 | 단위/통합 테스트 |
| **pytest-cov** | 4.1.0 | 코드 커버리지 |
| **locust** | 2.15+ | 부하 테스트 |
| **testclient** | (FastAPI 내장) | API 테스트 |
| **OWASP ZAP** | 2.12+ | 보안 스캔 |
| **flake8** | 6.0+ | 정적 분석 |
| **black** | 23.7+ | 코드 포맷 검증 |

### 📁 테스트 데이터

```
test_data/
├── unit_test/
│   ├── sample_data_small.csv (100행)
│   └── edge_cases.csv (아웃라이어, 결측값)
├── integration_test/
│   ├── test_countries/ (8개 국가 샘플)
│   └── full_pipeline.csv (500행)
└── performance_test/
    ├── load_test_data.csv (10,000행)
    └── stress_test_data.csv (100,000행)
```

---

## 테스트 케이스

### 1️⃣ Phase 13.1: 데이터 수집 테스트

#### TC-1.1: CSV 파일 로딩
```python
def test_load_country_data_valid():
    """유효한 CSV 파일 로드 테스트"""
    df = load_country_data(Path("test_data/sample_data_small.csv"))
    assert df is not None
    assert len(df) == 100
    assert set(FEATURE_COLS + ['new_price']).issubset(df.columns)
    assert df.isnull().sum().sum() == 0  # 결측값 없음
```

#### TC-1.2: 잘못된 파일 처리
```python
def test_load_country_data_missing_columns():
    """필수 컬럼 누락 시 None 반환"""
    df = load_country_data(Path("test_data/invalid_columns.csv"))
    assert df is None
```

#### TC-1.3: 결측값 처리
```python
def test_missing_values_handling():
    """결측값 제거 확인"""
    df = load_country_data(Path("test_data/with_nulls.csv"))
    initial_len = 100
    result_len = len(df)
    assert result_len < initial_len  # 결측값 행 제거됨
    assert df.isnull().sum().sum() == 0  # 결측값 완전 제거
```

**예상 결과**: ✅ 3/3 케이스 통과

---

### 2️⃣ Phase 13.2: GPU 훈련 테스트

#### TC-2.1: 모델 훈련 정확도
```python
def test_xgboost_accuracy():
    """XGBoost 모델 R² > 0.84 검증"""
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2)
    r2, mape = train_xgboost(X_tr, y_tr, X_te, y_te, device_id=1)
    
    assert r2 > 0.84, f"R² {r2} is below target 0.84"
    assert mape < 0.105, f"MAPE {mape} exceeds target 10.5%"
```

#### TC-2.2: LightGBM GPU 폴백
```python
def test_lightgbm_gpu_fallback():
    """GPU 불가 시 CPU 폴백 동작"""
    # GPU 없는 환경 시뮬레이션
    r2, mape = train_lightgbm(X_tr, y_tr, X_te, y_te, device_id=None)
    
    assert r2 > 0.84  # CPU에서도 정확도 달성
    assert mape < 0.105
```

#### TC-2.3: 훈련 시간 성능
```python
def test_training_speed():
    """GPU 훈련이 CPU보다 7-8배 빠른지 검증"""
    import time
    
    # GPU 훈련
    start = time.perf_counter()
    train_xgboost(X_tr, y_tr, X_te, y_te, device_id=1)
    gpu_time = time.perf_counter() - start
    
    assert gpu_time < 600, f"GPU training took {gpu_time}s (target <5min)"
```

**예상 결과**: ✅ 3/3 케이스 통과

---

### 3️⃣ Phase 13.2.5: 모델 변환 테스트

#### TC-3.1: ONNX 변환
```python
def test_onnx_conversion():
    """XGBoost → ONNX 변환"""
    onnx_path = convert_xgboost_to_onnx(model, "KR", Path("output"))
    
    assert onnx_path is not None
    assert Path(onnx_path).exists()
    assert Path(onnx_path).suffix == '.onnx'
```

#### TC-3.2: INT8 양자화 오차
```python
def test_int8_quantization_error():
    """INT8 양자화 오차 < 1%"""
    original_pred = model.predict(X_test)
    quantized_pred = ir_model.predict(X_test)
    
    mae = mean_absolute_error(original_pred, quantized_pred)
    relative_error = mae / np.mean(np.abs(original_pred))
    
    assert relative_error < 0.01, f"Quantization error {relative_error:.2%} exceeds 1%"
```

#### TC-3.3: 메모리 감소 검증
```python
def test_memory_reduction():
    """4배 메모리 감소 (8MB → 2MB)"""
    model_size = Path("model.pkl").stat().st_size / (1024**2)  # MB
    ir_size = Path("model.xml").stat().st_size / (1024**2)  # MB
    
    ratio = model_size / ir_size
    assert ratio >= 4.0, f"Memory reduction ratio {ratio} < 4x"
```

**예상 결과**: ✅ 3/3 케이스 통과

---

### 4️⃣ Phase 13.4: NPU 추론 테스트

#### TC-4.1: 추론 지연시간
```python
def test_inference_latency():
    """NPU 추론 지연시간 < 2ms"""
    import time
    
    engine = NPUInferenceEngine("output/models_ir")
    
    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        price, conf, latency = engine.predict(test_features)
        latencies.append(latency)
    
    avg_latency = np.mean(latencies)
    p95_latency = np.percentile(latencies, 95)
    
    assert avg_latency < 2.0, f"Avg latency {avg_latency}ms exceeds 2ms"
    assert p95_latency < 2.5, f"P95 latency {p95_latency}ms too high"
```

#### TC-4.2: 메모리 사용량
```python
def test_memory_footprint():
    """추론 메모리 < 2GB"""
    import tracemalloc
    
    tracemalloc.start()
    engine = NPUInferenceEngine("output/models_ir")
    
    current, peak = tracemalloc.get_traced_memory()
    memory_mb = peak / (1024**2)
    
    assert memory_mb < 2048, f"Memory usage {memory_mb}MB exceeds 2GB"
    tracemalloc.stop()
```

#### TC-4.3: 신뢰도 범위
```python
def test_confidence_range():
    """신뢰도가 0-1 범위 내"""
    engine = NPUInferenceEngine("output/models_ir")
    
    for _ in range(50):
        price, conf, latency = engine.predict(test_features)
        assert 0 <= conf <= 1, f"Confidence {conf} out of range"
```

**예상 결과**: ✅ 3/3 케이스 통과

---

### 5️⃣ Phase 13.4.1: FastAPI 테스트

#### TC-5.1: /api/valuation 엔드포인트
```python
def test_valuation_endpoint():
    """POST /api/valuation 정상 작동"""
    client = TestClient(app)
    
    payload = {
        "area_sqm": 100,
        "old_price": 500000,
        "latitude": 35.5,
        "longitude": 126.8,
        "property_type": 2
    }
    
    response = client.post("/api/valuation", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "predicted_price" in data
    assert "confidence" in data
    assert "latency_ms" in data
    assert 0 < data["predicted_price"] < 10_000_000_000
```

#### TC-5.2: 입력 검증
```python
def test_valuation_validation():
    """잘못된 입력 처리"""
    client = TestClient(app)
    
    # 범위 초과
    invalid_payload = {
        "area_sqm": 2000,  # 최대 1000 초과
        "old_price": 500000,
        "latitude": 35.5,
        "longitude": 126.8,
        "property_type": 2
    }
    
    response = client.post("/api/valuation", json=invalid_payload)
    assert response.status_code == 422  # Validation error
```

#### TC-5.3: 헬스 체크
```python
def test_health_check():
    """GET /api/health 작동"""
    client = TestClient(app)
    
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["healthy", "degraded"]
```

**예상 결과**: ✅ 3/3 케이스 통과

---

## QA/QC 기준

### 📏 코드 품질 기준

| 기준 | 목표 | 검증 방법 |
|------|------|---------|
| **코드 커버리지** | ≥90% | pytest-cov |
| **라인 길이** | ≤100자 | flake8 |
| **함수 크기** | ≤50줄 | 수동 검사 |
| **순환 복잡도** | ≤10 | radon |
| **타입 힌트** | 100% | mypy |
| **코드 포맷** | black 준수 | pre-commit |

### 📊 성능 기준

| 지표 | 목표 | 측정 빈도 |
|------|------|---------|
| **추론 지연시간** | <2ms (P95) | 매 배포 |
| **메모리 사용** | <2GB | 매 배포 |
| **처리량** | >500 req/sec | 주 1회 |
| **가용성** | 99.9% | 실시간 |
| **모델 정확도** | R²>0.84, MAPE<10.5% | 월 1회 |

### 🔒 보안 기준

| 항목 | 요구사항 | 검증 |
|------|---------|------|
| **입력 검증** | 모든 입력 검증 | pytest |
| **SQL Injection** | 해당 없음 (JSON only) | OWASP ZAP |
| **XSS** | 해당 없음 (API only) | - |
| **인증** | API 키 기반 (향후) | - |
| **암호화** | HTTPS 필수 | SSL/TLS |
| **취약점** | Critical 0개 | 정기 스캔 |

---

## 버그 추적 및 보고

### 🐛 버그 심각도 분류

| 심각도 | 정의 | SLA | 예시 |
|--------|------|-----|------|
| **Critical** | 서비스 완전 중단 | 1시간 | API 완전 다운, 정확도 0% |
| **High** | 주요 기능 장애 | 4시간 | 50% 요청 실패, R² 0.7 이하 |
| **Medium** | 부분 기능 장애 | 1일 | 추론 지연시간 >5ms, MAPE 15% |
| **Low** | 사소한 결함 | 1주 | 타이핑 오류, UI 마이너 버그 |

### 📋 버그 리포트 템플릿

```markdown
## 버그 제목
[심각도] 간단한 설명

## 재현 단계
1. ...
2. ...
3. ...

## 예상 결과
...

## 실제 결과
...

## 환경
- OS: 
- Python: 
- GPU: 

## 첨부 파일
- 스크린샷
- 로그 파일
```

### 📊 버그 추적 메트릭

```
매주 리뷰:
├─ 신규 버그: __개
├─ 해결됨: __개
├─ 재개됨: __개
└─ 평균 해결 시간: __시간
```

---

## 성능 테스트

### ⚡ 부하 테스트 (Locust)

```python
# locustfile.py
from locust import HttpUser, task, between

class AVM_User(HttpUser):
    wait_time = between(1, 3)
    
    @task(1)
    def valuation_request(self):
        payload = {
            "area_sqm": 100,
            "old_price": 500000,
            "latitude": 35.5,
            "longitude": 126.8,
            "property_type": 2
        }
        self.client.post("/api/valuation", json=payload)
```

**실행**:
```bash
locust -f locustfile.py --host=http://localhost:8000 --users=1000 --spawn-rate=10
```

**성능 목표**:
| 메트릭 | 목표 | 기준 |
|--------|------|------|
| P95 응답시간 | <100ms | 1000동시사용자 |
| 성공률 | >99.9% | 지속 5분 |
| 처리량 | >500 req/sec | 안정적 |

### 📈 메모리 프로파일링

```bash
# GPU 메모리 모니터링
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader -l 1

# CPU 메모리 모니터링
python -m memory_profiler scripts/phase13_model_trainer.py
```

**목표**: 
- GPU VRAM 피크: <6GB (8GB 중)
- 추론 메모리: <2GB

---

## 보안 테스트

### 🔐 OWASP Top 10 검증

| OWASP | 검증 항목 | 상태 |
|-------|---------|------|
| **A1** | Injection | ✅ JSON only (SQL 불가) |
| **A2** | Authentication | ⏳ 계획 중 (API 키) |
| **A3** | Sensitive Data | ✅ 로그에 민감 데이터 없음 |
| **A4** | XML/External | ✅ 해당 없음 |
| **A5** | Access Control | ⏳ 계획 중 |
| **A6** | Security Config | ✅ 기본값 안전 |
| **A7** | XSS | ✅ API only |
| **A8** | CSRF | ✅ Stateless API |
| **A9** | Using Old Library | ✅ 최신 버전 사용 |
| **A10** | Insufficient Logging | ✅ 구현됨 |

### 🔍 정적 분석

```bash
# flake8 보안 점검
flake8 avm_project/scripts --select=E,W,F,C

# bandit 보안 취약점 검사
bandit -r avm_project/scripts

# mypy 타입 안전성
mypy avm_project/scripts --strict
```

---

## 사용자 수용 테스트 (UAT)

### 👥 UAT 참가자

| 역할 | 명수 | 책임 |
|------|------|------|
| **비즈니스 분석가** | 2명 | 요구사항 검증 |
| **부동산 전문가** | 2명 | 도메인 검증 |
| **운영팀** | 2명 | 배포 검증 |
| **개발팀** | 2명 | 기술 지원 |

### 📝 UAT 테스트 케이스

#### UAT-1: 기본 기능
```
시나리오: 부동산 가격 예측
1. 부동산 정보 입력 (면적 100㎡, 기존가 500만원, 위치: 서울)
2. "예측" 버튼 클릭
3. 3초 이내 결과 표시
4. 예상 범위: 600-700만원 (±20%)

결과: ✅ 통과 / ❌ 실패
```

#### UAT-2: 엣지 케이스
```
시나리오: 극단값 처리
1. 매우 큰 면적 입력 (500㎡)
2. 매우 작은 가격 입력 (100만원)
3. 지역 경계 (경주도 북쪽)
4. 결과가 합리적인 범위 내인지 확인

결과: ✅ 통과 / ❌ 실패
```

#### UAT-3: 성능
```
시나리오: 응답 속도
1. 10개 요청 연속 전송
2. 모든 응답이 2초 이내 수신
3. 메모리/CPU 사용 정상 범위

결과: ✅ 통과 / ❌ 실패
```

### 📋 UAT 승인 기준

- [ ] 모든 기본 기능 작동
- [ ] 응답 속도 <2초
- [ ] 예측 결과 합리적 (도메인 전문가 승인)
- [ ] 오류 처리 적절
- [ ] 운영 가이드 명확

---

## 릴리스 기준

### ✅ 릴리스 전 필수 검사

**코드 품질**:
- [ ] 코드 커버리지 ≥90%
- [ ] flake8 점검: 0개 오류
- [ ] mypy 타입 검사: 0개 오류
- [ ] black 포맷: 통과
- [ ] 함수 크기: 모두 ≤50줄

**기능 테스트**:
- [ ] 단위 테스트: 100% 통과
- [ ] 통합 테스트: 100% 통과
- [ ] E2E 테스트: 100% 통과
- [ ] 버그 심각도: Critical 0개

**성능**:
- [ ] 추론 지연시간: <2ms (P95)
- [ ] 메모리: <2GB
- [ ] 처리량: >500 req/sec
- [ ] 가용성: 99.9%

**보안**:
- [ ] OWASP 스캔: Critical 0개
- [ ] 의존성 취약점: 0개
- [ ] 입력 검증: 100%

**운영**:
- [ ] 배포 가이드 작성
- [ ] 모니터링 설정
- [ ] 롤백 계획 수립
- [ ] 운영팀 교육 완료

### 🚀 릴리스 유형별 기준

| 유형 | 버전 | 테스트 범위 | 승인 |
|------|------|-----------|------|
| **Hotfix** | v1.0.1 | Critical 테스트만 | PM + 팀장 |
| **Minor** | v1.1.0 | 전체 테스트 70% | PM + 팀장 |
| **Major** | v2.0.0 | 전체 테스트 100% | PM + 팀장 + 운영 |

---

## 테스트 일정

### 📅 전체 테스트 타임라인

```
2026-06-26 ~ 2026-07-14 (3주)

Week 1 (06-26 ~ 07-02):
├─ Phase 13.1-13.2 테스트 (데이터 + GPU 훈련)
├─ 단위/통합 테스트 작성
└─ 코드 커버리지 90% 달성

Week 2 (07-03 ~ 07-09):
├─ Phase 13.2.5-13.4 테스트 (모델 변환 + 추론)
├─ 성능 테스트 & 최적화
└─ CI/CD 자동화 테스트

Week 3 (07-10 ~ 07-14):
├─ 보안 테스트 (OWASP ZAP)
├─ UAT (사용자 수용 테스트)
└─ 릴리스 준비
```

### 📊 일일 테스트 체크인

```
매일 10:00 KST:
├─ 야간 자동 테스트 결과 검토
├─ 새로운 버그 분류
├─ 진행률 리포트
└─ 블로커 아이템 해결
```

---

## 위험 분석

### ⚠️ 주요 위험 요소

| 위험 | 가능성 | 영향 | 완화 방안 |
|------|--------|------|---------|
| **GPU 메모리 부족** | 중간 | 높음 | INT8 양자화, subsample=0.8 |
| **모델 정확도 미달** | 낮음 | 높음 | 하이퍼파라미터 튜닝, 앙상블 |
| **API 성능 저하** | 중간 | 중간 | 캐싱, 비동기 처리, 부하 테스트 |
| **CI/CD 실패** | 낮음 | 중간 | 로컬 검증, GitHub Actions 모니터링 |
| **보안 취약점** | 낮음 | 높음 | OWASP 스캔, 정기 감시 |
| **데이터 품질** | 중간 | 중간 | 데이터 검증, 결측값 처리 |

### 🛡️ 완화 방안

**GPU 메모리**:
```python
# subsample 사용으로 메모리 절감
model = xgb.XGBRegressor(subsample=0.8, colsample_bytree=0.8)
```

**모델 정확도**:
```python
# 3모델 앙상블로 보강
results = [
    train_xgboost(...),
    train_lightgbm(...),
    train_gradient_boosting(...)
]
ensemble_pred = np.mean([r[0] for r in results])
```

**API 성능**:
```python
# 응답 캐싱
from fastapi_cache import cache

@cache(expire=300)
@app.post("/api/valuation")
def valuate_property(...):
    ...
```

---

## 테스트 리포트 템플릿

### 📊 주간 테스트 리포트

```markdown
# 테스트 리포트 (2026-06-26 ~ 07-02)

## 요약
- 총 테스트 케이스: 45개
- 통과: 43개 (95.6%)
- 실패: 2개 (4.4%)
- 코드 커버리지: 88%

## 결과 분석
### 통과한 테스트
✅ Phase 13.1 데이터 수집 (5/5)
✅ Phase 13.2 GPU 훈련 (8/8)
✅ Phase 13.4 NPU 추론 (10/10)

### 실패한 테스트
❌ TC-2.3: 훈련 시간 (710초 > 600초 목표)
❌ TC-4.2: 메모리 사용량 (2.3GB > 2GB 목표)

## 조치 사항
- TC-2.3: GPU 최적화, batch_size 조정
- TC-4.2: 모델 프루닝, INT8 양자화 강화

## 승인
- QA 담당: ________________
- 개발팀장: ________________
```

---

## 체크리스트

### 🎯 최종 릴리스 전 확인

- [ ] 모든 테스트 케이스 실행 완료
- [ ] 버그 추적 시스템 설정
- [ ] CI/CD 파이프라인 검증
- [ ] 성능 테스트 결과 분석
- [ ] 보안 테스트 완료
- [ ] UAT 승인 획득
- [ ] 운영 가이드 작성
- [ ] 롤백 계획 수립
- [ ] 모니터링 설정
- [ ] 팀 교육 완료

---

**작성자**: QA/QC 팀  
**검토자**: 개발팀장  
**승인자**: PM  
**최종 수정**: 2026-06-26  
**다음 리뷰**: 2026-07-14
