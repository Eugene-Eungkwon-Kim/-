# Phase 13 통합 코드 개발 실행 계획서
## Python 구현 및 병렬 개발 스케줄

**작성일**: 2026-07-01  
**상태**: 🚀 코드 개발 즉시 시작  
**기간**: 2026-07-01 ~ 2026-08-06 (37일)  
**팀**: Claude Agent (1명, 병렬 개발 최적화)

---

## Executive Summary

**목표**: Phase 13.1-KR부터 13.5까지의 모든 Python 코드 구현 완료 → 한국 부동산 자동가치평가 시스템 (AVM) 운영화

**개발 전략**: 
- **병렬 개발**: Week 2-3에서 13.3-13.5 코드 작성 (13.1 진행 중)
- **순차 검증**: 각 phase 완료 후 통합 테스트
- **점진적 배포**: 13.1 데이터 → 13.2 학습 → 13.3 검증 → 13.4 API → 13.5 자동화

**성공 기준**:
- ✅ 모든 phase 코드 <50 lines/function
- ✅ 100% type hints
- ✅ Unit test >80% coverage
- ✅ 최종 운영화 가능 상태

---

## 1. 전체 일정 개요

```
Week 1 (Jul 1-7):    Phase 13.1-KR (데이터 수집)
Week 2 (Jul 8-14):   Phase 13.2 (GPU 모델 학습) + Phase 13.3 코드 작성 병렬
Week 3 (Jul 15-21):  Phase 13.3 (검증) + Phase 13.4 코드 작성 병렬
Week 3-4 (Jul 19-28): Phase 13.4 (API 배포) + Phase 13.5 코드 작성 병렬
Week 4-5 (Jul 24-Aug 6): Phase 13.5 (자동화) + 통합 테스트 & 운영화

Timeline:
  Phase 13.1-KR: ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ (7 days, Week 1)
  Phase 13.2:    ░███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ (7 days, Week 2)
  Phase 13.3:    ░░░░████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ (4 days, Week 3 early)
  Phase 13.4:    ░░░░░░░███░░░░░░░░░░░░░░░░░░░░░░░░░░░ (5 days, Week 3 late)
  Phase 13.5:    ░░░░░░░░░░████░░░░░░░░░░░░░░░░░░░░░░░ (14 days, Week 4-5)
```

---

## 2. Phase별 코드 개발 계획

### Phase 13.1-KR: 데이터 수집 (Week 1, Jul 1-7)

**목표 코드 완성**:
```
✅ scripts/phase13_kr_data_collector.py (신규)
   ├─ class KoreanRealEstateCollector
   │  ├─ collect_from_datagokr(api_key, months)
   │  ├─ collect_from_molit(csv_paths)
   │  ├─ merge_and_validate()
   │  └─ save_to_parquet()
   │
   └─ main() function for CLI execution
```

**구현 세부사항**:
```python
# phase13_kr_data_collector.py (약 150 lines)

from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd
import requests
import logging

class KoreanRealEstateCollector:
    """Collect Korean real estate data from data.go.kr and MOLIT"""
    
    def __init__(self, output_dir: str = 'data/raw'):
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
    
    def collect_from_datagokr(
        self,
        api_key: str,
        start_month: str,  # '202404'
        end_month: str     # '202406'
    ) -> pd.DataFrame:
        """Collect from data.go.kr API (1000 req/day limit)"""
        # Implementation: rate-limited requests, pagination handling
        # Returns: DataFrame with 26 columns
    
    def collect_from_molit(
        self,
        csv_paths: List[str]  # ['seoul.csv', 'gyeonggi.csv', 'incheon.csv']
    ) -> pd.DataFrame:
        """Load MOLIT CSV files (EUC-KR → UTF-8)"""
        # Implementation: encoding conversion, schema normalization
        # Returns: unified DataFrame
    
    def merge_and_validate(
        self,
        datagokr_df: pd.DataFrame,
        molit_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge data, handle duplicates, validate quality"""
        # Implementation: concat, dedup, null handling, outlier removal
        # Returns: 50K validated DataFrame
    
    def save_to_parquet(self, df: pd.DataFrame, path: str) -> None:
        """Save with compression and metadata"""

if __name__ == '__main__':
    collector = KoreanRealEstateCollector()
    # Execution logic
```

**코드 리뷰 기준**:
- [ ] 각 함수 <50 lines
- [ ] Type hints 100%
- [ ] Error handling (API errors, encoding issues)
- [ ] Logging (progress, metrics)
- [ ] Unit test 포함

**산출물**:
- ✅ data/raw/datagokr_transactions.csv (10K)
- ✅ data/processed/kr_validated.parquet (50K)
- ✅ output/collection_metrics.json

---

### Phase 13.2: GPU 모델 학습 (Week 2, Jul 8-14)

**기존 코드 검증 + 개선**:
```
✅ scripts/phase13_model_trainer.py (검증 및 개선)
   ├─ class GPUModelTrainer
   │  ├─ load_training_data()
   │  ├─ feature_engineering(45 features)
   │  ├─ train_xgboost(gpu_hist)
   │  ├─ train_lightgbm(gpu)
   │  ├─ train_gradient_boosting(cpu fallback)
   │  └─ evaluate_models(cv=5)
   │
   └─ main() function for CLI execution

✅ scripts/phase13_gpu_config.py (기존)
   └─ GPU 환경 설정, RTX 5050 타겟팅
```

**구현 개선사항**:
```python
# phase13_model_trainer.py (개선)

from typing import Dict, Tuple, List
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
import pickle

class GPUModelTrainer:
    """Train 3 models on GPU with cross-validation"""
    
    def __init__(self, data_path: str):
        self.data = self._load_data(data_path)  # 50K records
        self.models = {}
        self.cv_results = {}
    
    def feature_engineering(self) -> Tuple[np.ndarray, np.ndarray]:
        """10 base → 45 features, StandardScaler normalization"""
        # Already implemented, verify
        # Returns: X_train (40K×45), X_test (10K×45)
    
    def train_xgboost(self) -> float:
        """XGBoost on GPU (gpu_hist, 15 min expected)"""
        params = {
            'tree_method': 'gpu_hist',
            'objective': 'reg:squarederror',
            'max_depth': 8,
            'learning_rate': 0.05,
            'n_estimators': 500,
        }
        # Training + cross-validation
        # Returns: R² score
    
    def train_lightgbm(self) -> float:
        """LightGBM on GPU (8 min, fastest)"""
        params = {
            'device_type': 'gpu',
            'objective': 'regression',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'n_estimators': 500,
        }
        # Training + cross-validation
        # Returns: R² score
    
    def train_gradient_boosting(self) -> float:
        """Gradient Boosting on CPU (30 min, fallback)"""
        params = {
            'n_estimators': 200,
            'learning_rate': 0.05,
            'max_depth': 8,
        }
        # Training + cross-validation
        # Returns: R² score
    
    def evaluate_models(self) -> Dict[str, Dict]:
        """5-fold cross-validation for all 3 models"""
        # Parallel evaluation
        # Returns: {'xgboost': {...}, 'lightgbm': {...}, 'gb': {...}}

if __name__ == '__main__':
    trainer = GPUModelTrainer('data/processed/kr_validated.parquet')
    # Execution logic
```

**코드 리뷰 기준**:
- [ ] GPU 메모리 최적화 확인
- [ ] Cross-validation 검증
- [ ] 모델 저장 경로 확인
- [ ] Error handling (OOM, training failure)

**산출물**:
- ✅ models/xgboost_kr.pkl (100-150MB)
- ✅ models/lightgbm_kr.pkl (50-80MB)
- ✅ models/gb_kr.pkl (150-200MB)
- ✅ output/training_metrics.json

---

### Phase 13.3: 모델 검증 (Week 3 early, Jul 15-18)

**신규 코드 작성** (병렬 진행, Week 2 중 시작):
```
✅ scripts/phase13_model_validator.py (신규)
   ├─ class ModelValidator
   │  ├─ cross_validate_models() [5-fold CV]
   │  ├─ hyperparameter_tuning() [GridSearchCV]
   │  ├─ extract_feature_importance() [3가지 방법]
   │  ├─ analyze_shap() [해석가능성]
   │  └─ select_best_model() [가중치 기반]
   │
   ├─ class FeatureImportanceAnalyzer
   │  ├─ extract_builtin_importance()
   │  ├─ extract_permutation_importance()
   │  └─ extract_shap_importance()
   │
   └─ main() function
```

**구현 코드**:
```python
# phase13_model_validator.py (~200 lines)

from dataclasses import dataclass
from typing import Dict, List, Tuple
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import r2_score, mean_absolute_percentage_error
import shap
import numpy as np

@dataclass
class CVResult:
    model_name: str
    r2_scores: List[float]
    mape_scores: List[float]
    r2_mean: float
    r2_std: float
    mape_mean: float

class ModelValidator:
    """Validate and optimize 3 pre-trained models"""
    
    def __init__(self, models: Dict, X_train, X_test, y_train, y_test):
        self.models = models
        self.X_train = X_train
        self.X_test = X_test
        self.y_train = y_train
        self.y_test = y_test
    
    def cross_validate_models(self, n_splits: int = 5) -> Dict[str, CVResult]:
        """5-fold temporal cross-validation"""
        tscv = TimeSeriesSplit(n_splits=n_splits)
        results = {}
        
        for model_name, model in self.models.items():
            cv_scores = cross_val_score(
                model, self.X_train, self.y_train,
                cv=tscv, scoring='r2'
            )
            # Compute statistics
        
        return results
    
    def hyperparameter_tuning(self) -> Dict[str, Dict]:
        """GridSearchCV for 3 models"""
        # XGBoost: 108 combinations
        # LightGBM: 81 combinations
        # GB: 27 combinations
        # Parallel execution
        # Returns: best params for each model
    
    def extract_feature_importance(self) -> Dict[str, List[Tuple]]:
        """Extract top 10 features (3 methods)"""
        # Built-in importance
        # Permutation importance
        # SHAP values
        # Returns: {model_name: [(feature, importance), ...]}
    
    def analyze_shap(self) -> Dict:
        """SHAP analysis for interpretability"""
        # 1000 sample subsets
        # SHAP values computation
        # Returns: SHAP summary
    
    def select_best_model(self) -> str:
        """Weighted scoring (R² 40%, MAPE 30%, time 10%)"""
        # Score each model
        # Returns: best_model_name (expected: 'LightGBM')

if __name__ == '__main__':
    # Load 3 pre-trained models
    # Validate and optimize
    # Select best
```

**코드 리뷰 기준**:
- [ ] CV 결과 통계 검증
- [ ] GridSearch 병렬화
- [ ] Feature importance 시각화
- [ ] SHAP 분석 완성도

**산출물**:
- ✅ models/best_model_kr.pkl (LightGBM, optimized)
- ✅ output/cv_results.json
- ✅ output/feature_importance.json
- ✅ output/shap_analysis.png

---

### Phase 13.4: API 배포 (Week 3 late, Jul 19-23)

**신규 코드 작성** (병렬 진행, Week 3 중 시작):
```
✅ scripts/phase13_api_service.py (개선)
   ├─ class FastAPIService
   │  ├─ @app.post("/api/valuation")
   │  ├─ @app.get("/health")
   │  └─ @app.get("/api/performance")
   │
   └─ Pydantic models: Request, Response

✅ scripts/phase13_npu_inference.py (신규/개선)
   ├─ class NPUInferenceEngine
   │  ├─ predict() [<10ms latency]
   │  └─ batch_predict()
   │
   └─ Device fallback logic (NPU→GPU→CPU)

✅ scripts/phase13_model_converter.py (개선)
   ├─ class ModelConverter
   │  ├─ lightgbm_to_onnx()
   │  ├─ onnx_to_openvino_ir()
   │  └─ quantization_int8()
   │
   └─ main() for deployment
```

**구현 코드**:
```python
# phase13_npu_inference.py (~100 lines)

from openvino.runtime import Core, get_version
from dataclasses import dataclass
from typing import Dict, Any
import numpy as np
import time

@dataclass
class InferenceResult:
    predicted_price: float
    confidence: float
    latency_ms: float
    device: str

class NPUInferenceEngine:
    """OpenVINO IR based NPU inference"""
    
    def __init__(self, model_path: str, device: str = 'NPU'):
        self.core = Core()
        self.model = self.core.read_model(model_path)
        self.compiled = self.core.compile_model(self.model, device)
        self.device = device
    
    def predict(self, features: np.ndarray) -> InferenceResult:
        """Single prediction with timing"""
        start = time.time()
        
        # Set input tensor
        infer_req = self.compiled.create_infer_request()
        # ... inference logic ...
        
        latency_ms = (time.time() - start) * 1000
        
        return InferenceResult(
            predicted_price=prediction,
            confidence=0.95,
            latency_ms=latency_ms,
            device=self.device
        )
    
    def batch_predict(self, features: np.ndarray) -> List[InferenceResult]:
        """Batch prediction (memory-efficient)"""
        # Process in chunks
        # Returns: List[InferenceResult]
```

**코드 리뷰 기준**:
- [ ] API 엔드포인트 검증
- [ ] ONNX 변환 정확도 (<0.5% loss)
- [ ] NPU 지연시간 확인 (<10ms)
- [ ] Device fallback 동작 검증
- [ ] Docker 이미지 크기 최적화

**산출물**:
- ✅ models/best_model_kr.onnx (18MB)
- ✅ models/openvino_ir/ (XML + BIN)
- ✅ Dockerfile + docker-compose.yml
- ✅ API 실행 중 (localhost:8000)

---

### Phase 13.5: 자동화 & 모니터링 (Week 4-5, Jul 24-Aug 6)

**신규 코드 작성** (병렬 진행, Week 3 말 시작):
```
✅ scripts/phase13_automation_engine.py (신규)
   ├─ class AutomationEngine
   │  ├─ execute_job() [Job orchestration]
   │  ├─ schedule_cron() [Cron integration]
   │  └─ notify() [Slack/Email/SMS]
   │
   └─ main() for daemon

✅ scripts/phase13_model_monitor.py (신규)
   ├─ class ModelMonitor
   │  ├─ track_metrics() [Prometheus]
   │  ├─ detect_drift() [KS-test]
   │  ├─ alert_on_degradation() [>1% R² loss]
   │  └─ automatic_rollback() [Decision logic]
   │
   └─ Metrics: R², latency, accuracy

✅ scripts/phase13_ab_testing.py (신규)
   ├─ class ABTestingManager
   │  ├─ route_prediction() [5% new, 95% old]
   │  ├─ statistical_test() [t-test]
   │  └─ gradual_rollout() [5%→25%→100%]
   │
   └─ Traffic splitting logic
```

**구현 코드**:
```python
# phase13_automation_engine.py (~150 lines)

from dataclasses import dataclass
from enum import Enum
import subprocess
import json
from datetime import datetime
import logging

class JobStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'

@dataclass
class AutomationJob:
    job_id: str
    name: str
    script_path: str
    timeout_seconds: int
    max_retries: int = 2

class AutomationEngine:
    """Orchestrate weekly retraining workflow"""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.logger = logging.getLogger(__name__)
    
    def execute_job(self, job: AutomationJob) -> Dict[str, Any]:
        """Execute with error handling and timeout"""
        try:
            result = subprocess.run(
                [f'bash {job.script_path}'],
                shell=True,
                timeout=job.timeout_seconds,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self._notify(job, 'success', result.stdout)
                return {'status': 'success'}
            else:
                if job.max_retries > 0:
                    job.max_retries -= 1
                    return self.execute_job(job)  # Retry
                else:
                    self._notify(job, 'failure', result.stderr)
                    return {'status': 'failed', 'error': result.stderr}
        
        except subprocess.TimeoutExpired:
            self._notify(job, 'timeout', f"Exceeded {job.timeout_seconds}s")
            return {'status': 'timeout'}
        
        except Exception as e:
            self._notify(job, 'error', str(e))
            return {'status': 'error', 'error': str(e)}
    
    def _notify(self, job: AutomationJob, status: str, message: str):
        """Send notifications (Slack, Email, SMS)"""
        # Implementation

if __name__ == '__main__':
    engine = AutomationEngine('config/automation.json')
    # Execute weekly retraining job
```

**코드 리뷰 기준**:
- [ ] Cron 스크립트 동작 검증
- [ ] 모니터링 메트릭 수집 확인
- [ ] 알림 채널 동작 확인
- [ ] A/B 테스팅 통계 검증
- [ ] 자동 롤백 메커니즘 테스트

**산출물**:
- ✅ scripts/run_weekly_retraining.sh (Cron 실행)
- ✅ Prometheus metrics configuration
- ✅ Grafana dashboard (JSON)
- ✅ AlertManager rules (YAML)

---

## 3. 개발 순서 및 의존성

```
Dependency Graph:

Phase 13.1-KR (Week 1)
    │ 50K parquet data
    ▼
Phase 13.2 (Week 2)
    │ 3 trained models (.pkl)
    ▼
Phase 13.3 (Week 3 early, CV results
    │ best_model + top 10 features
    ▼
Phase 13.4 (Week 3 late)
    │ ONNX + OpenVINO IR + API service
    ▼
Phase 13.5 (Week 4-5)
    │ Automation + monitoring + rollback
    ▼
Production Ready ✅

Parallel Streams (동시 진행 가능):
- Phase 13.1-KR (Week 1): 7 days
- Phase 13.3-13.5 코드 작성 (Week 2-3): 13.2 진행 중 시작
```

---

## 4. 코드 품질 기준

**모든 phase 코드**:
```python
# 1. Function size
def my_function():
    """Brief description"""
    # Max 50 lines (100 for complex logic)
    pass

# 2. Type hints (100%)
def predict(features: np.ndarray) -> Dict[str, float]:
    """Predict with type safety"""
    pass

# 3. Single Responsibility
# ✓ collect_data() - only collects
# ✓ validate_data() - only validates
# ✗ collect_and_train() - violates SRP

# 4. Error handling
try:
    result = api_call()
except RequestException as e:
    logger.error(f"API call failed: {e}")
    raise

# 5. Logging (not print)
logger.info("Processing started")
logger.error("Critical error occurred")
```

**Unit Tests**:
```python
# Test coverage >80%

# Example: test_phase13_data_collector.py
def test_collect_from_datagokr_returns_dataframe():
    collector = KoreanRealEstateCollector()
    df = collector.collect_from_datagokr(api_key='test', ...)
    assert len(df) > 0
    assert all(col in df.columns for col in required_cols)

def test_merge_handles_duplicates():
    # Test duplicate removal
    pass

def test_validate_detects_outliers():
    # Test outlier detection
    pass
```

---

## 5. Git Commit 계획

**주간별 커밋**:
```
Week 1:
  commit: "Phase 13.1-KR: Add Korean data collection pipeline"
  - phase13_kr_data_collector.py
  - Collection metrics & quality report

Week 2:
  commit: "Phase 13.2: Verify GPU model trainer (XGBoost/LightGBM/GB)"
  - phase13_model_trainer.py (검증)
  - 3 trained models

Week 3:
  commit: "Phase 13.3: Add model validator with CV & hyperparameter tuning"
  - phase13_model_validator.py
  - Feature importance analysis

  commit: "Phase 13.4: Add NPU inference engine & FastAPI service"
  - phase13_npu_inference.py
  - phase13_api_service.py (개선)
  - Docker deployment

Week 4-5:
  commit: "Phase 13.5: Add automation engine & monitoring system"
  - phase13_automation_engine.py
  - phase13_model_monitor.py
  - Cron scripts + Prometheus config
```

---

## 6. 리소스 및 병렬화

**CPU/GPU 활용**:
```
Week 1: CPU (데이터 수집 I/O)
Week 2: GPU (모델 학습, RTX 5050)
Week 3: GPU + CPU (검증 + API 개발)
Week 4-5: CPU (자동화 + 모니터링, <20% CPU)
```

**개발 효율**:
```
순차 진행: 37 days
병렬 개발: ~25 days (32% 단축)
  ├─ Week 1: Phase 13.1-KR (7 days, critical path)
  ├─ Week 2: 13.2 + 13.3 코드 작성 (병렬)
  ├─ Week 3: 13.3 실행 + 13.4 코드 작성 (병렬)
  └─ Week 4-5: 13.4 + 13.5 병렬, 통합 테스트
```

---

## 7. 최종 체크리스트

**코드 완성**:
- [ ] Phase 13.1-KR 데이터 수집 완료 (50K parquet)
- [ ] Phase 13.2 모델 학습 완료 (3 pkl 모델)
- [ ] Phase 13.3 모델 검증 완료 (CV + feature analysis)
- [ ] Phase 13.4 API 배포 완료 (FastAPI + NPU)
- [ ] Phase 13.5 자동화 완료 (Cron + 모니터링)

**품질 검증**:
- [ ] 모든 코드 <50 lines/function
- [ ] 100% type hints
- [ ] Unit test >80% coverage
- [ ] PEP 8 compliance
- [ ] 0 debug prints

**배포 준비**:
- [ ] Docker 이미지 빌드 완료
- [ ] API 엔드포인트 동작 확인
- [ ] 성능 벤치마크 검증
- [ ] 모니터링 시스템 작동
- [ ] 자동화 스크립트 테스트

---

**Phase 13 코드 개발 준비 완료**  
**시작일**: 2026-07-01 (Phase 13.1-KR)  
**완료일**: 2026-08-06 (Phase 13.5)  
**예상 코드량**: ~800 lines (모든 phase)  
**예상 테스트 시간**: 40 hours (20% 추가)  

**다음 단계**: Phase 13.1-KR 즉시 실행 시작 🚀
