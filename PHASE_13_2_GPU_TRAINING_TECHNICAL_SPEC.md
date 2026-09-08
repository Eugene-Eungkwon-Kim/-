# Phase 13.2 기술 명세서
## GPU 기반 모델 학습 — 상세 구현 가이드

**버전**: 1.0  
**작성일**: 2026-07-01  
**대상**: ML Engineer / DevOps  
**코드 레퍼런스**: `avm_project/scripts/phase13_model_trainer.py`

---

## 1. 입력/출력 데이터 명세

### 1.1 Input Data (Phase 13.1에서 제공)

**File**: `avm_project/data/processed/kr_features_45.pkl`  
**Format**: pandas DataFrame (pickled)  
**Shape**: (50000, 45)  
**Dtype**: float64 (normalized -3σ to +3σ)

**Schema**:
```python
FEATURE_NAMES = [
    # Base 10 features
    'area_sqm', 'old_price', 'latitude', 'longitude', 'property_type',
    'building_age', 'floor', 'distance_subway_km', 'distance_school_km', 'distance_park_km',
    
    # Temporal 4 features
    'transaction_year', 'transaction_month', 'transaction_quarter', 'building_age_squared',
    
    # Location 6 features
    'location_cluster_id', 'suburb_distance_quartile', 'lat_normalized', 'lon_normalized',
    'elevation_proxy', 'urbanization_score',
    
    # Market 3 features
    'regional_avg_price_monthly', 'regional_price_trend_pct', 'regional_transaction_volume',
    
    # Categorical 12 features (one-hot + target encoding)
    'usage_residential', 'usage_commercial', 'usage_office', 'usage_factory',
    'usage_agricultural', 'usage_other',
    'district_avg_price_encoded', 'district_price_std_encoded',
    'structure_reinforced_concrete', 'structure_wood', 'structure_steel', 'structure_other',
    
    # Interaction 10 features
    'area_x_building_age', 'area_x_latitude', 'price_x_distance_subway',
    'building_age_cubic', 'area_log', 'price_log', 'cluster_x_price',
    'season_indicator', 'market_momentum', 'location_market_fit',
]

TARGET = 'transaction_price_new'  # KRW, range: 50M ~ 5B
```

**Train/Test Split**:
```python
# Temporal split (no leakage)
train_indices = (dates >= '2026-01-01') & (dates <= '2026-03-15')  # 40,000 rows (80%)
test_indices = (dates > '2026-03-15') & (dates <= '2026-04-30')    # 10,000 rows (20%)

X_train = X[train_indices]  # (40000, 45)
X_test = X[test_indices]    # (10000, 45)
y_train = y[train_indices]  # (40000,)
y_test = y[test_indices]    # (10000,)
```

### 1.2 Output Data

**Models** (저장 위치: `avm_project/models/phase13_kr/`):
```
├── xgboost_kr.json          # 100-150 MB (XGBoost native format)
├── lightgbm_kr.txt          # 50-80 MB (LightGBM text format) ⭐
├── gradient_boosting_kr.pkl # 150-200 MB (sklearn joblib)
└── best_model_metadata.json # 메타데이터
```

**Metadata**:
```json
{
  "best_model": "lightgbm",
  "r2_score": 0.8742,
  "mape": 0.0901,
  "rmse_krw": 1850000,
  "mae_krw": 1200000,
  "training_date": "2026-07-11T14:30:00Z",
  "training_time_sec": 420,
  "feature_count": 45,
  "train_size": 40000,
  "test_size": 10000,
  "cross_validation_folds": 5,
  "cv_r2_mean": 0.8720,
  "cv_r2_std": 0.0045,
  "model_version": "phase13_kr_v1.0"
}
```

**Feature Importance** (`best_model_features.csv`):
```
feature,importance,rank
area_log,0.2450,1
price_log,0.1890,2
regional_avg_price_monthly,0.1120,3
location_cluster_id,0.0980,4
building_age,0.0750,5
...
season_indicator,0.0012,43
elevation_proxy,0.0008,44
structure_other,0.0005,45
```

---

## 2. 모델 학습 명세

### 2.1 XGBoost (GPU: gpu_hist)

**Framework Version**: xgboost >=3.0  
**Device**: NVIDIA RTX 5050 (8GB GDDR7) or CPU fallback  

**Hyperparameters**:
```python
xgb_params = {
    # Booster
    'booster': 'gbtree',
    'tree_method': 'gpu_hist',    # GPU acceleration
    'device': 'cuda:0',
    'objective': 'reg:squarederror',
    
    # Architecture
    'max_depth': 8,
    'min_child_weight': 1,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    
    # Learning
    'learning_rate': 0.05,
    'n_estimators': 500,
    'early_stopping_rounds': 50,
    
    # GPU specific
    'gpu_id': 0,
    'max_leaves': 100,
    'grow_policy': 'lossguide',
    'max_bin': 256,
}

training_params = {
    'num_round': 500,
    'evals': [(dtrain, 'train'), (dtest, 'eval')],
    'verbose_eval': 10,
}
```

**Expected Performance**:
- R² Score: 0.84-0.86
- MAPE: 8.5-9.5%
- RMSE: 1.8-2.1M KRW
- Training Time: ~15 minutes (GPU)

**Output Format**: JSON (native XGBoost)

### 2.2 LightGBM (GPU)

**Framework Version**: lightgbm >=4.0  
**Device**: GPU (OpenCL) or CPU  

**Hyperparameters**:
```python
lgb_params = {
    'objective': 'regression',
    'metric': 'rmse',
    'boosting_type': 'gbdt',
    
    # GPU
    'device_type': 'gpu',
    'gpu_device_id': 0,
    'gpu_platform_id': 0,
    
    # Architecture
    'max_depth': 10,
    'num_leaves': 31,
    'min_data_in_leaf': 20,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    
    # Learning
    'learning_rate': 0.05,
    'num_leaves': 31,
    'verbose': 10,
    
    # Optimization
    'num_boost_round': 500,
    'early_stopping_rounds': 50,
}
```

**Expected Performance**:
- R² Score: 0.85-0.87 ⭐ (Best expected)
- MAPE: 8.5-9.5%
- RMSE: 1.7-2.0M KRW
- Training Time: ~8 minutes (GPU) — **가장 빠름**

**Output Format**: Text (LightGBM native)

### 2.3 Gradient Boosting (CPU)

**Framework**: sklearn.ensemble.GradientBoostingRegressor  
**Device**: CPU only (no GPU support)

**Hyperparameters**:
```python
gb_params = {
    'n_estimators': 200,
    'learning_rate': 0.05,
    'max_depth': 8,
    'min_samples_split': 5,
    'min_samples_leaf': 2,
    'subsample': 0.8,
    'random_state': 42,
    'n_iter_no_change': 50,
    'validation_fraction': 0.1,
}
```

**Expected Performance**:
- R² Score: 0.82-0.84
- MAPE: 9.5-10.5%
- RMSE: 1.9-2.2M KRW
- Training Time: ~30 minutes (CPU) — Fallback only

**Output Format**: Pickle (joblib)

---

## 3. 특성 엔지니어링 코드 스펙

### 3.1 Module: phase13_feature_engineering.py

**Core Class**:
```python
class Phase13FeatureEngineer:
    def __init__(self, df: pd.DataFrame) -> None:
        """Initialize with raw 26-column DataFrame"""
        self.df = df
        self.scaler = StandardScaler()
    
    def build_all_features(self) -> Tuple[np.ndarray, List[str]]:
        """Transform 26 columns → 45 features"""
        self.add_base_features()        # 10
        self.add_temporal_features()    # +4 = 14
        self.add_location_features()    # +6 = 20
        self.add_market_features()      # +3 = 23
        self.add_categorical_features() # +12 = 35
        self.add_interaction_features() # +10 = 45
        
        X = self.df[self.feature_names].values.astype(np.float32)
        X_normalized = self.scaler.fit_transform(X)
        
        return X_normalized, self.feature_names
```

**Key Methods**:
- `add_base_features()`: 원본 컬럼 직접 사용
- `add_temporal_features()`: 거래일 기반 파생
- `add_location_features()`: 위치 기반 인코딩 (K-means clustering)
- `add_market_features()`: 지역/월별 통계
- `add_categorical_features()`: One-hot + target encoding
- `add_interaction_features()`: 다항식, 교차항

**Normalization**: StandardScaler (train fit, test transform)

### 3.2 Train/Test Split Strategy

```python
# Temporal split (no data leakage)
train_mask = df['transaction_date'] <= '2026-03-15'
test_mask = df['transaction_date'] > '2026-03-15'

X_train = X[train_mask]  # 40K
X_test = X[test_mask]    # 10K
y_train = y[train_mask]
y_test = y[test_mask]

# Cross-validation: use temporal folds
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5)
for train_idx, val_idx in tscv.split(X_train):
    X_cv_train, X_cv_val = X_train[train_idx], X_train[val_idx]
    y_cv_train, y_cv_val = y_train[train_idx], y_train[val_idx]
    # train & evaluate each model
```

---

## 4. 평가 지표 명세

### 4.1 Metrics

**Regression Metrics**:
```python
def evaluate_model(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    from sklearn.metrics import r2_score, mean_absolute_percentage_error, mean_squared_error
    
    r2 = r2_score(y_true, y_pred)
    mape = mean_absolute_percentage_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = np.mean(np.abs(y_true - y_pred))
    
    return {
        'r2': r2,
        'mape': mape,
        'rmse': rmse,
        'mae': mae,
        'rmse_in_millions': rmse / 1e6,  # KRW 단위
    }
```

**Target Thresholds**:
```python
SUCCESS_CRITERIA = {
    'r2_min': 0.84,           # Minimum acceptable
    'r2_target': 0.85,        # Target
    'mape_max': 0.105,        # 10.5% maximum
    'mape_target': 0.10,      # 10% target
    'rmse_max': 2.5e6,        # 250만원
}
```

### 4.2 Cross-Validation Evaluation

```python
# 5-fold time-series cross-validation
cv_scores = {
    'r2_folds': [],
    'mape_folds': [],
    'rmse_folds': [],
}

for fold, (train_idx, val_idx) in enumerate(tscv.split(X_train)):
    X_cv_train, X_cv_val = X_train[train_idx], X_train[val_idx]
    y_cv_train, y_cv_val = y_train[train_idx], y_train[val_idx]
    
    model.fit(X_cv_train, y_cv_train)
    y_pred = model.predict(X_cv_val)
    
    metrics = evaluate_model(y_cv_val, y_pred)
    cv_scores['r2_folds'].append(metrics['r2'])
    cv_scores['mape_folds'].append(metrics['mape'])
    cv_scores['rmse_folds'].append(metrics['rmse'])

# Report
print(f"R² = {np.mean(cv_scores['r2_folds']):.4f} ± {np.std(cv_scores['r2_folds']):.4f}")
print(f"MAPE = {np.mean(cv_scores['mape_folds']):.2%} ± {np.std(cv_scores['mape_folds']):.2%}")
```

---

## 5. 모델 선정 로직

### 5.1 Selection Criteria

```python
def select_best_model(results: Dict[str, ModelResult]) -> Tuple[str, ModelResult]:
    """
    Priority:
    1. R² > 0.84 (필수)
    2. MAPE < 10.5% (필수)
    3. R² 최대값 (1차 정렬)
    4. MAPE 최소값 (2차 정렬)
    5. 학습 시간 최소 (3차 정렬)
    """
    
    # Filter by minimum criteria
    candidates = [
        (name, result)
        for name, result in results.items()
        if result.r2 > 0.84 and result.mape < 0.105
    ]
    
    if not candidates:
        # Fallback: highest R²
        candidates = [(name, result) for name, result in results.items()]
    
    # Sort by (R² descending, MAPE ascending, time ascending)
    best = max(
        candidates,
        key=lambda x: (x[1].r2, -x[1].mape, -x[1].training_time)
    )
    
    return best[0], best[1]

# Expected result:
# "lightgbm" (R²=0.87, MAPE=0.09, time=8min) is likely best
```

---

## 6. 배포 체크리스트

```
Before Training:
- [ ] X_train (40K×45), X_test (10K×45) 준비 완료
- [ ] y_train, y_test 준비 완료
- [ ] 데이터 정규화 검증
- [ ] GPU 메모리 확인 (8GB 확보)
- [ ] 모든 라이브러리 import 가능

During Training:
- [ ] XGBoost training log 모니터 (15 min)
- [ ] LightGBM training log 모니터 (8 min)
- [ ] Gradient Boosting training log 모니터 (30 min)
- [ ] OOM (Out of Memory) 에러 감시

After Training:
- [ ] 3개 모델 파일 저장 확인
- [ ] 모델 파일 크기 검증 (100-200 MB 범위)
- [ ] R², MAPE 점수 확인 (기준 충족)
- [ ] Feature importance 추출 가능
- [ ] Metadata JSON 생성 완료
- [ ] Phase 13.3 진행 가능 확인
```

---

## 7. 에러 처리

### 7.1 Exception Handling

```python
# GPU 초기화 실패 → CPU fallback
try:
    import xgboost as xgb
    dtrain = xgb.DMatrix(X_train, label=y_train)
    model = xgb.train(params_xgboost, dtrain)
except (RuntimeError, xgb.XGBError) as e:
    if 'CUDA' in str(e) or 'GPU' in str(e):
        log.warning(f"GPU error: {e}, switching to CPU")
        params_xgboost['tree_method'] = 'hist'
        params_xgboost['device'] = 'cpu'
        model = xgb.train(params_xgboost, dtrain)

# 메모리 부족 → 배치 학습
except MemoryError:
    log.warning("OOM: reducing batch size and feature count")
    feature_selection_mask = feature_importance > threshold
    X_train_reduced = X_train[:, feature_selection_mask]
    X_test_reduced = X_test[:, feature_selection_mask]
    # Retrain with reduced features
```

---

**최종 체크**: 모든 명세 준수, Phase 13.3 데이터 파이프라인 준비 확인.
