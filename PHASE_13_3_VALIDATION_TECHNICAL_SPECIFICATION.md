# Phase 13.3 기술 명세서
## 모델 검증 & 성능 최적화

**작성일**: 2026-07-01  
**버전**: 1.0  
**상태**: 📋 설계 중  
**대상**: XGBoost, LightGBM, Gradient Boosting 3개 모델  

---

## 1. 시스템 아키텍처

### 1.1 데이터 흐름

```
Phase 13.2 Output:
├── xgboost_kr.pkl (학습됨)
├── lightgbm_kr.pkl (학습됨)
├── gb_kr.pkl (학습됨)
└── training_data (50K × 45 features)
     ├── X_train: 40K × 45
     ├── X_test: 10K × 45
     └── y_train, y_test: 레이블

     │
     ▼

Phase 13.3 Processing:
┌─────────────────────────────┐
│ 1. Model Loading            │
│ (pickle → model objects)    │
└──────────┬──────────────────┘
           │
     ┌─────▼─────┐
     │           │
     ▼           ▼
┌──────────┐  ┌──────────┐
│ Cross-   │  │Hyper-    │
│Validation│  │parameter │
│(5-fold)  │  │Tuning    │
└────┬─────┘  └────┬─────┘
     │             │
     └─────┬───────┘
           │
           ▼
    ┌─────────────────┐
    │ Feature         │
    │Importance       │
    │+ SHAP Analysis  │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Model Selection │
    │ (Best Model)    │
    └────────┬────────┘
             │
             ▼
    ┌──────────────────┐
    │ Report Generation│
    │ (Performance     │
    │  Summary)        │
    └──────────────────┘
```

### 1.2 모듈 구조

```python
phase13_model_validator.py
├── ModelValidator (main class)
│   ├── load_models() -> Dict[str, Model]
│   ├── cross_validate_models() -> Dict[str, CVResults]
│   ├── hyperparameter_tuning() -> Dict[str, BestParams]
│   ├── extract_feature_importance() -> Dict[str, FeatureImportance]
│   ├── analyze_shap() -> Dict[str, SHAPExplanation]
│   └── select_best_model() -> BestModel
│
├── CVResults (dataclass)
│   ├── model_name: str
│   ├── r2_scores: List[float]  # 5-fold values
│   ├── mape_scores: List[float]
│   ├── rmse_scores: List[float]
│   ├── r2_mean: float
│   ├── r2_std: float
│   └── mape_mean: float
│
├── FeatureImportance (dataclass)
│   ├── model_name: str
│   ├── top_10_features: Dict[str, float]  # feature_name -> importance
│   └── timestamp: str
│
└── BestModel (dataclass)
    ├── model_name: str
    ├── r2_score: float
    ├── mape: float
    ├── params: Dict[str, any]
    └── model_path: str
```

---

## 2. 5-Fold Cross-Validation 명세

### 2.1 CV 설정

```python
class CrossValidationConfig:
    n_splits: int = 5
    method: str = "TimeSeriesSplit"  # 시간 순서 유지
    shuffle: bool = False  # 시계열 데이터이므로 shuffling 없음
    random_state: int = 42
    
    # 분할 방식 (40K records)
    # Fold 1: train [0:32K], val [32K:40K]
    # Fold 2: train [0:24K] + [32K:40K], val [24K:32K]
    # Fold 3: train [0:16K] + [24K:40K], val [16K:24K]
    # Fold 4: train [0:8K] + [16K:40K], val [8K:16K]
    # Fold 5: train [8K:40K], val [0:8K]
```

### 2.2 평가 지표 계산

```python
def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calculate R², MAPE, RMSE, MAE for each fold
    """
    metrics = {
        'r2': r2_score(y_true, y_pred),
        'mape': mean_absolute_percentage_error(y_true, y_pred),
        'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
        'mae': mean_absolute_error(y_true, y_pred),
    }
    return metrics

# 최종 리포트 포맷
CV_Report = {
    'model_name': 'XGBoost',
    'fold_results': [
        {'fold': 1, 'r2': 0.851, 'mape': 0.092, 'rmse': 1850000},
        ...  # 5 folds
    ],
    'mean': {'r2': 0.847, 'mape': 0.091, 'rmse': 1875000},
    'std': {'r2': 0.012, 'mape': 0.008, 'rmse': 45000},
}
```

---

## 3. 하이퍼파라미터 튜닝 명세

### 3.1 GridSearchCV 설정

```python
# XGBoost
param_grid_xgb = {
    'max_depth': [6, 7, 8, 9],
    'learning_rate': [0.01, 0.05, 0.1],
    'subsample': [0.6, 0.8, 1.0],
    'colsample_bytree': [0.7, 0.8, 0.9],
}

grid_search_config = {
    'cv': 5,  # 5-fold
    'scoring': 'r2',
    'n_jobs': 4,  # 병렬 처리
    'verbose': 1,
    'return_train_score': True,
}

# 예상 실행 시간: 108 × 5 = 540 fold 실행
# GPU 병렬화 (4 cores): 540 / 4 = 135분
```

### 3.2 LightGBM Tuning

```python
param_grid_lgb = {
    'num_leaves': [20, 31, 50],
    'learning_rate': [0.01, 0.05, 0.1],
    'max_depth': [8, 10, 12],
    'feature_fraction': [0.7, 0.8, 0.9],
}

# 예상 실행 시간: 81 × 5 = 405 fold 실행
# GPU 병렬화 (4 cores): 405 / 4 = 101분
```

### 3.3 Gradient Boosting Tuning

```python
param_grid_gb = {
    'n_estimators': [100, 200, 300],
    'learning_rate': [0.01, 0.05, 0.1],
    'max_depth': [6, 8, 10],
}

# 예상 실행 시간: 27 × 5 = 135 fold 실행
# CPU: 135분 (병렬화 없음, 순차)
```

---

## 4. Feature Importance 추출 명세

### 4.1 방법론

```python
class FeatureImportanceExtractor:
    """
    3가지 방법으로 특성 중요도 분석
    """
    
    def extract_builtin_importance(model) -> Dict[str, float]:
        """
        모델 내장 중요도 (빠름)
        - XGBoost: model.feature_importances_
        - LightGBM: model.feature_importances_
        - GB: estimator_.feature_importances_
        """
        pass
    
    def extract_permutation_importance(model, X, y) -> Dict[str, float]:
        """
        Permutation importance (해석가능성 높음)
        - 각 특성을 무작위로 섞고 성능 변화 측정
        - 중요도 = (원본 성능 - 섞인 성능) / 원본 성능
        """
        pass
    
    def extract_shap_importance(model, X_sample) -> Dict[str, float]:
        """
        SHAP value 분석 (가장 해석가능)
        - X_sample: 1000개 샘플로 대표성 확보
        - 평균 |SHAP value| = 특성 중요도
        """
        pass

# Top 10 특성 추출 및 저장
top_10_output = {
    'rank': [1, 2, 3, ..., 10],
    'feature_name': ['old_price', 'area_sqm', ...],
    'importance': [0.342, 0.281, ...],
    'cumulative_importance': [0.342, 0.623, ...],  # 상위 10개 누적 기여도
}
```

### 4.2 시각화

```python
# 1. Feature Importance Bar Chart (상위 10)
#    ├─ X축: importance 값
#    ├─ Y축: feature name
#    └─ 컬러: 모델별 다른 색상

# 2. SHAP Summary Plot
#    ├─ 각 샘플의 SHAP value 시각화
#    ├─ X축: SHAP value (음수 = 감소, 양수 = 증가)
#    └─ Y축: top 10 features

# 3. Cumulative Importance (누적 곡선)
#    ├─ X축: feature rank (1~45)
#    ├─ Y축: cumulative importance (0~1)
#    └─ 상위 10개가 전체의 ~70% 차지 예상
```

---

## 5. 모델 선택 기준

### 5.1 평가 매트릭스

| 지표 | XGBoost 기대값 | LightGBM 기대값 | GB 기대값 | 가중치 |
|------|---|---|---|---|
| **R² Score** | 0.850 | 0.851 | 0.835 | 40% |
| **MAPE** | 0.091 | 0.090 | 0.104 | 30% |
| **RMSE** | 1.9M | 1.85M | 2.1M | 20% |
| **Training Time** | 8min (GPU) | 5min (GPU) | 25min (CPU) | 10% |

### 5.2 선택 로직

```python
def select_best_model(cv_results: Dict[str, CVResults]) -> str:
    """
    Weighted scoring system
    """
    scores = {}
    
    for model_name, results in cv_results.items():
        r2_score = (results.r2_mean - 0.80) / (0.95 - 0.80)  # 정규화
        mape_score = (0.15 - results.mape_mean) / (0.15 - 0.08)
        rmse_score = (3.0e6 - results.rmse_mean) / (3.0e6 - 1.5e6)
        time_score = 1.0  # 모두 acceptable
        
        weighted_score = (
            0.40 * r2_score + 
            0.30 * mape_score + 
            0.20 * rmse_score + 
            0.10 * time_score
        )
        scores[model_name] = weighted_score
    
    return max(scores, key=scores.get)  # 예상: LightGBM
```

---

## 6. 출력 파일 명세

### 6.1 저장 경로 및 포맷

```
avm_project/
├── models/
│   ├── best_model_kr.pkl (최적 모델, ~80MB)
│   ├── models_cv_results.json (CV 결과)
│   │   ├── xgboost_cv_scores
│   │   ├── lightgbm_cv_scores
│   │   └── gb_cv_scores
│   └── models_metadata.json
│       ├── model_name: 'LightGBM'
│       ├── r2: 0.851
│       ├── mape: 0.090
│       ├── training_date: '2026-07-18'
│       └── hyperparameters: {...}
│
├── output/
│   └── PHASE_13_3_VALIDATION_REPORT.md
│       ├── 성능 비교표 (3개 모델 × 8개 메트릭)
│       ├── 하이퍼파라미터 튜닝 이력
│       ├── Feature importance (Top 10 × 3 모델)
│       ├── SHAP 분석
│       └── 최종 권장사항
│
└── docs/
    └── PHASE_13_3_FEATURE_ANALYSIS.md
        ├── Feature correlation heatmap (45×45)
        ├── Feature interaction analysis
        └── Domain insights
```

### 6.2 JSON 스키마

```json
{
  "cv_results": {
    "xgboost": {
      "fold_1": {"r2": 0.851, "mape": 0.092, "rmse": 1850000},
      "fold_2": {...},
      "fold_3": {...},
      "fold_4": {...},
      "fold_5": {...},
      "mean": {"r2": 0.847, "mape": 0.091, "rmse": 1875000},
      "std": {"r2": 0.012, "mape": 0.008, "rmse": 45000}
    },
    "lightgbm": {...},
    "gb": {...}
  },
  "hyperparameter_tuning": {
    "xgboost": {
      "best_params": {"max_depth": 8, "learning_rate": 0.05},
      "best_score": 0.851,
      "n_iterations": 108
    }
  },
  "feature_importance": {
    "xgboost": {
      "top_10": [
        {"rank": 1, "name": "old_price", "importance": 0.342},
        {"rank": 2, "name": "area_sqm", "importance": 0.281}
      ]
    }
  }
}
```

---

## 7. 구현 체크리스트

### 7.1 Phase 13.3 구현 항목

```python
✅ phase13_model_validator.py
├─ ModelValidator 클래스 (main orchestrator)
├─ cross_validate_models() - 5-fold CV 실행
├─ hyperparameter_tuning() - GridSearchCV
├─ extract_feature_importance() - 3가지 방법
├─ analyze_shap() - SHAP 분석
└─ select_best_model() - 가중치 기반 선택

✅ 결과 저장
├─ CV results → models/models_cv_results.json
├─ Best model → models/best_model_kr.pkl
├─ Metadata → models/models_metadata.json
└─ Report → output/PHASE_13_3_VALIDATION_REPORT.md

✅ 시각화 (matplotlib/seaborn)
├─ Feature importance bar chart (×3)
├─ SHAP summary plots (×3)
├─ CV score distributions (box plots)
└─ Cumulative importance curves (×3)
```

---

## 8. 의존성 및 라이브러리

```python
# 핵심 라이브러리
import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import r2_score, mean_absolute_percentage_error
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import GradientBoostingRegressor
import shap  # SHAP analysis
import matplotlib.pyplot as plt
import seaborn as sns

# 버전 요구사항
xgboost >= 3.2.0
lightgbm >= 4.6.0
scikit-learn >= 1.6.0
shap >= 0.45.0
```

---

**기술 명세서 작성 완료**  
**다음 문서**: Phase 13.3 WBS (Work Breakdown Structure)
