# Phase 13.2: GPU-가속 모델 훈련 상세 구현 계획

**시작일**: 2026-07-10  
**완료목표**: 2026-07-23 (13일)  
**목표**: RTX 5050으로 6개국 모델 훈련 (35분→5분 가속)

---

## 📋 구현 구성 (4개 모듈)

### 1️⃣ 13.2.1: GPU 환경 설정 (2시간)
**목표**: RTX 5050 최적화, 성능 벤치마크 수집

**산출물**:
- `avm_project/scripts/phase13_2_gpu_setup.py` (50줄)
- `avm_project/scripts/phase13_2_gpu_benchmark.py` (80줄)
- `GPU_SETUP_REPORT_2026_07_10.md`

**체크리스트**:
```python
def check_gpu_environment() -> Dict[str, bool]:
    """GPU 환경 검증 (각 항목 PASS/FAIL)"""
    checks = {
        'cuda_available': torch.cuda.is_available(),  # ✓ 필수
        'rtx_5050': 'RTX 5050' in torch.cuda.get_device_name(0),  # ✓ 확인
        'cuda_version': '11.8+',  # ✓ 확인
        'cudnn_version': '8.6+',  # ✓ 확인
        'xgboost_gpu': check_xgboost_gpu(),  # ✓ 필수
        'lightgbm_gpu': check_lightgbm_gpu(),  # ✓ 필수
        'memory_available': torch.cuda.get_device_properties(0).total_memory > 6e9,  # ✓ 필수
    }
    return checks

def benchmark_gpu_vs_cpu():
    """CPU vs GPU 성능 비교"""
    # KR 데이터: 10,000행, XGBoost 학습
    # 예상: CPU 35분 → GPU 5분 (7배 가속)
```

**의존성**:
```
numpy>=1.21.0
pandas>=1.3.0
scikit-learn>=0.24.0
xgboost[gpu]>=1.7.0          # ← GPU 활성화
lightgbm[gpu]>=3.3.0          # ← GPU 활성화
torch>=2.0.0                  # CUDA 확인용
onnx>=1.12.0
```

---

### 2️⃣ 13.2.2: 국가별 모델 훈련 (6시간, 병렬)
**목표**: 6개국 × 3 모델 = 18개 모델 훈련

**산출물**:
- `avm_project/scripts/phase13_2_gpu_trainer.py` (150줄)
- `avm_project/scripts/train_*_model_gpu.py` (6개, 각 60줄)
- `output/trained_models_gpu/` (18개 pkl 파일)

**구현 흐름**:

```python
class GPUModelTrainer:
    """국가별 병렬 모델 훈련 엔진"""
    
    def __init__(self, country_config: CountryConfig) -> None:
        self.config = country_config
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    def train_xgboost_gpu(self, X_train: np.ndarray, y_train: np.ndarray) -> Dict:
        """XGBoost GPU 훈련 (tree_method='gpu_hist')"""
        model = xgb.XGBRegressor(
            tree_method='gpu_hist',           # ← GPU 활성화
            gpu_id=0,
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            n_jobs=-1,
        )
        model.fit(X_train, y_train, verbose=10)
        
        r2 = model.score(X_test, y_test)
        return {
            'model': model,
            'r2': r2,
            'type': 'xgboost_gpu',
            'device': 'cuda',
        }
    
    def train_lightgbm_gpu(self, X_train: np.ndarray, y_train: np.ndarray) -> Dict:
        """LightGBM GPU 훈련 (device_type='gpu')"""
        model = lgb.LGBMRegressor(
            device_type='gpu',                # ← GPU 활성화
            gpu_platform_id=0,
            gpu_device_id=0,
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            num_leaves=31,
            n_jobs=-1,
        )
        model.fit(X_train, y_train, verbose=10)
        
        r2 = model.score(X_test, y_test)
        return {
            'model': model,
            'r2': r2,
            'type': 'lightgbm_gpu',
            'device': 'cuda',
        }
    
    def train_gradient_boosting(self, X_train, y_train) -> Dict:
        """Gradient Boosting (scikit-learn, CPU 호환)"""
        model = GradientBoostingRegressor(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
        )
        model.fit(X_train, y_train)
        
        r2 = model.score(X_test, y_test)
        return {
            'model': model,
            'r2': r2,
            'type': 'gradient_boosting',
            'device': 'cpu',
        }
    
    def train_all(self, data: Dict) -> Dict[str, Dict]:
        """3개 모델 병렬 훈련"""
        results = {}
        
        # 병렬 훈련 (3개 프로세스)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                'xgboost': executor.submit(self.train_xgboost_gpu, ...),
                'lightgbm': executor.submit(self.train_lightgbm_gpu, ...),
                'gb': executor.submit(self.train_gradient_boosting, ...),
            }
            
            for name, future in futures.items():
                results[name] = future.result()
        
        return results

# 병렬 훈련: 6개국
for country_code in ['KR', 'SG', 'HK', 'UK', 'AU', 'TH']:
    config = get_country_config(country_code)
    data = generate_dataset(config, n_rows=10_000)
    
    trainer = GPUModelTrainer(config)
    models = trainer.train_all(data)
    
    # 모델 저장
    for model_type, model_info in models.items():
        path = f'output/trained_models_gpu/{model_type}_{country_code}.pkl'
        joblib.dump(model_info['model'], path)
        log_performance(country_code, model_type, model_info['r2'])
```

**성능 목표**:
```
각 국가별 모든 모델:
✓ R² > 0.84 (기준)
✓ MAPE < 10.5% (기준)

예상 훈련 시간:
- KR: 5분 (GPU) vs 35분 (CPU) → 7배 가속
- SG: 4분 (병렬)
- HK: 4분 (병렬)
- UK: 4분 (병렬)
- AU: 4분 (병렬)
- TH: 4분 (병렬)
────────────────
합계: 25분 (병렬) vs 210분 (순차) → 8배 가속
```

---

### 3️⃣ 13.2.3: 하이퍼파라미터 튜닝 (3시간)
**목표**: GridSearchCV로 최적 파라미터 찾기 (GPU 가속)

**산출물**:
- `avm_project/scripts/phase13_2_hyperparameter_tuning.py` (120줄)
- `output/hyperparameter_tuning_results/` (6개 국가별 결과)

**구현**:

```python
def tune_xgboost_gpu(X_train, y_train, country_code: str) -> Dict:
    """GridSearchCV + GPU"""
    param_grid = {
        'max_depth': [5, 6, 7],
        'learning_rate': [0.03, 0.05, 0.07],
        'subsample': [0.7, 0.8, 0.9],
    }
    
    base_model = xgb.XGBRegressor(
        tree_method='gpu_hist',
        n_estimators=500,
        gpu_id=0,
    )
    
    grid = GridSearchCV(
        base_model,
        param_grid,
        cv=5,  # 5-fold cross-validation
        scoring='r2',
        n_jobs=-1,
    )
    
    grid.fit(X_train, y_train)
    
    return {
        'best_params': grid.best_params_,
        'best_score': grid.best_score_,
        'cv_results': grid.cv_results_,
    }
```

---

### 4️⃣ 13.2.5: ONNX 모델 변환 (2시간)
**목표**: pkl → ONNX (OpenVINO NPU 배포용)

**산출물**:
- `avm_project/scripts/phase13_2_onnx_converter.py` (100줄)
- `output/trained_models_onnx/` (18개 ONNX 파일)
- `ONNX_CONVERSION_VALIDATION_2026_07_23.md`

**구현**:

```python
def convert_to_onnx(pkl_model, model_type: str, country_code: str) -> Dict:
    """pkl → ONNX 변환"""
    
    # 샘플 입력 준비
    sample_input = np.random.randn(1, 5).astype(np.float32)
    
    if model_type == 'xgboost':
        # XGBoost → ONNX
        initial_types = [('float_input', FloatTensorType([None, 5]))]
        onnx_model = convert_sklearn(pkl_model, initial_types=initial_types)
        
    elif model_type == 'lightgbm':
        # LightGBM → ONNX
        onnx_model = convert_lightgbm(pkl_model, initial_types=initial_types)
        
    else:
        # Gradient Boosting → ONNX (sklearn 호환)
        onnx_model = convert_sklearn(pkl_model, initial_types=initial_types)
    
    # 저장
    onnx_path = f'output/trained_models_onnx/{model_type}_{country_code}.onnx'
    onnx.save_model(onnx_model, onnx_path)
    
    # 검증
    sess = rt.InferenceSession(onnx_path)
    pred_onnx = sess.run(None, {'float_input': sample_input})
    pred_pkl = pkl_model.predict(sample_input)
    
    assert np.allclose(pred_onnx, pred_pkl, rtol=1e-5), "ONNX 변환 오류"
    
    return {
        'onnx_path': onnx_path,
        'status': 'success',
        'validation': 'passed',
    }
```

---

## 📊 진행 계획 (일일)

```
Day 1-2 (2026-07-10~11): GPU 환경 설정
├─ GPU 드라이버 확인
├─ XGBoost/LightGBM GPU 확인
├─ 벤치마크 수행
└─ 산출물: GPU_SETUP_REPORT_2026_07_10.md

Day 3-9 (2026-07-12~18): 모델 훈련 (병렬)
├─ KR 기준 훈련 (Day 3)
├─ SG/HK/UK/AU/TH 병렬 훈련 (Day 4-9)
├─ 성능 로그 수집
└─ 산출물: 18개 pkl 파일

Day 10-12 (2026-07-19~21): 하이퍼파라미터 튜닝
├─ GridSearchCV (5-fold CV)
├─ 최적 파라미터 확정
└─ 산출물: 6개국 튜닝 결과

Day 13 (2026-07-22~23): ONNX 변환 & 테스트
├─ 18개 모델 → ONNX 변환
├─ 변환 검증 (pred_pkl ≈ pred_onnx)
├─ 24개 단위 테스트
└─ 산출물: 18개 ONNX 파일 + 테스트 보고서
```

---

## 🧪 테스트 스위트 (24개)

### 데이터 검증 (6개)
- ✓ 각 국가 10,000행 데이터 생성 확인
- ✓ feature_min/max 범위 검증
- ✓ null 값 없음 확인
- ✓ 상관계수 < 0.985 검증
- ✓ 지가 범위 (price_floor/ceiling) 검증
- ✓ 지리좌표 범위 검증

### 모델 성능 (12개)
- ✓ XGBoost R² > 0.84 (6개 국가)
- ✓ LightGBM R² > 0.84 (6개 국가)
- ✓ Gradient Boosting R² > 0.84 (6개 국가)

### ONNX 검증 (6개)
- ✓ 18개 ONNX 파일 생성 확인
- ✓ ONNX 예측 vs 원본 pkl 일치성 (±1e-5)
- ✓ ONNX 파일 크기 타당성 (< 100MB)
- ✓ OpenVINO IR 변환 가능성
- ✓ 추론 시간 측정 (목표: <10ms)
- ✓ 배치 예측 검증

---

## 🎯 완료 기준

```
✓ 모든 테스트 24/24 통과
✓ 6개국 R² > 0.84 (평균 0.87 목표)
✓ ONNX 변환 성공 100%
✓ ONNX 예측 정확도 ≤ 1e-5 오차
✓ 성능 로그 6개국 × 3 모델 = 18개 기록
✓ 구현 코드 CODING_STANDARDS.md 준수
  - 모든 함수 ≤ 50줄
  - 100% type hints
  - docstring 완전
```

---

## 📈 기대 효과

### 성능 개선
```
훈련 시간: 210분 → 25분 (8배 가속)
메모리: CPU 기반 → GPU 병렬 처리
추론 시간: 5-10ms (GPU) → 1-2ms (ONNX+OpenVINO)
```

### 품질 보증
```
Type hints: 100%
테스트 커버리지: 24/24 (완전)
코드 리뷰 체크리스트: 100%
```

---

## 📚 참고 자료

### 기준 구현
- `avm_project/scripts/train_kr_model.py` (기존 CPU 훈련)
- `avm_project/scripts/country_configs.py` (국가 설정)
- `avm_project/scripts/realistic_data_generator.py` (데이터 생성)

### XGBoost GPU 문서
- https://xgboost.readthedocs.io/en/latest/gpu/index.html
- `tree_method='gpu_hist'` 사용

### LightGBM GPU 문서
- https://lightgbm.readthedocs.io/en/latest/GPU-Targets.html
- `device_type='gpu'` 사용

### ONNX 변환
- https://github.com/onnx/sklearn-onnx
- https://github.com/onnx/onnxmltools

---

**계획 작성일**: 2026-07-09  
**구현 시작일**: 2026-07-10  
**완료 예정일**: 2026-07-23  
**담당**: Eugene Eungkwon Kim (또는 팀원)
