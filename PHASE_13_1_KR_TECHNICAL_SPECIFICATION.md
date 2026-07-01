# Phase 13.1-KR 기술 명세서
## 한국 실거래 데이터 수집 & GPU 기반 모델 학습 기술 설계

**버전**: 1.0  
**작성일**: 2026-07-01  
**최종 검토**: TBD  
**상태**: 📋 설계 (구현 대기)

---

## 1. 데이터 수집 API 명세

### 1.1 Data.go.kr API

**Base URL**: `https://www.data.go.kr/api/15054409/V001/`  
**인증**: API Key (Authorization: X-API-Key)  

#### 1.1.1 Real Estate Transaction (부동산 실거래)

**Endpoint**: `/GetRealEstateTradingInfoSvc`  
**Method**: GET  
**Rate Limit**: 1,000 req/day (Free)  

**Request Parameters**:
```python
{
    'serviceKey': str,                    # API Key
    'pageNo': int = 1,                   # Page number
    'numOfRows': int = 100,              # Rows per page (max 100)
    'DEAL_YM': str,                      # YYYYMM (e.g., '202606')
    'REGION_CODE': str = '11110',        # 법정동 코드 (5자리)
    'REAL_ESTATE_TYPE_CODE': str = '01',# '01'=아파트, '02'=단독주택...
}
```

**Response Schema**:
```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL SERVICE."
    },
    "body": {
      "pageNo": 1,
      "numOfRows": 100,
      "totalCount": 12345,
      "items": [
        {
          "거래일": "20260601",
          "거래금액": "350000",
          "건물명": "래미안",
          "도로명": "서울시 강남구 테헤란로",
          "층": "25",
          "건축년도": "2015",
          "평면적": "84.95",
          "건물용도": "주거용",
          "위도": "37.4979",
          "경도": "127.0470"
        },
        ...
      ]
    }
  }
}
```

**Error Handling**:
```python
ERROR_CODES = {
    '01': 'Application Error',
    '02': 'Database Connection Error',
    '03': 'No data',
    '04': 'Http error',
    '05': 'Service Key is not registered',
    '06': 'Deadline has passed',
    '07': 'Service Key has been deactivated',
    '08': 'Service Key info does not exist',
    '09': 'Service Key has not been approved',
    '10': 'API has not been approved',
}
```

#### 1.1.2 Building Information (건축물 정보)

**Endpoint**: `/GetBrExposBldInfoService`  
**Method**: GET  

**Request Parameters**:
```python
{
    'serviceKey': str,
    'pageNo': int = 1,
    'numOfRows': int = 100,
    'sigunguCode': str,              # 시군구 코드 (5자리)
    'bjdongCode': str = '',          # 법정동 코드 (선택)
}
```

**Response Schema**:
```json
{
  "items": [
    {
      "건축년도": "2015",
      "건축면적": "1250.50",
      "연면적": "4520.75",
      "용도": "주거용",
      "구조": "철근콘크리트",
      "거기": "5",
      "도로명주소": "...",
      "법정동": "강남구 역삼동"
    }
  ]
}
```

#### 1.1.3 Standardized Land Price (공시지가)

**Endpoint**: `/GetStandardLandPriceSvc`  
**Method**: GET  

**Request Parameters**:
```python
{
    'serviceKey': str,
    'pageNo': int = 1,
    'numOfRows': int = 100,
    'stdYear': str,                  # YYYY (e.g., '2026')
    'sigunguCode': str,
}
```

**Response Schema**:
```json
{
  "items": [
    {
      "stdYm": "202606",
      "ldCodeVal": "11100101",
      "ldCodeNm": "서울시 종로구 종로 1가",
      "stdLandPrice": "15000000",  # 공시지가 (원/m²)
      "pclsLandCodeVal": "01",
      "pclsLandCodeNm": "주거"
    }
  ]
}
```

### 1.2 MOLIT CSV Downloader

**Source**: 국토교통부 부동산거래 공개시스템  
**URL**: `https://www.molit.go.kr/USR/RLAND/MY/Mydata/...`  
**Method**: CSV 배치 다운로드 (웹 크롤링 또는 FTP)  

**CSV Schema**:
```
거래일자,거래금액,도로명주소,법정동,건물명,건물용도,건축년도,평면적,층,구조,위도,경도
20260601,350000,서울시 강남구 테헤란로 100,강남구 역삼동,래미안,주거용,2015,84.95,25,철근콘크리트,37.4979,127.0470
20260602,420000,서울시 서초구 서초대로 50,서초구 방배동,아크로,주거용,2018,102.30,15,철근콘크리트,37.4850,127.0210
...
```

**Row Count**: 
- 월별 30,000~40,000 건
- 3개월 (서울/경기/인천): 100,000+ 건
- 선택적 확대: 전국 150,000+ 건

---

## 2. 데이터 처리 파이프라인 명세

### 2.1 Input Data Format (API Response)

**Source 1: data.go.kr API** → JSON  
**Source 2: MOLIT CSV** → CSV  
**Source 3: Local Vworld/Opinet** → GeoJSON / JSON  

### 2.2 Processing Stages

#### Stage 1: Data Ingestion
```python
# File: avm_project/scripts/phase13_data_collector.py

class Phase13DataCollector:
    def __init__(self, output_dir: str = 'data/raw') -> None:
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
    
    def collect_datagokr_real_estate(self, api_key: str, region_code: str, deal_ym: str) -> pd.DataFrame:
        """Fetch real estate transaction data from data.go.kr API"""
        # Pagination loop: pageNo 1..100
        # Rate limiting: sleep(1) between requests
        # Error handling: Retry on 503 (up to 3x)
        # Return: DataFrame with 100K+ rows
        pass
    
    def collect_molit_csv(self, csv_urls: List[str]) -> pd.DataFrame:
        """Download and parse MOLIT CSV files"""
        # Parallel download (3 regions × 3 months)
        # CSV schema validation
        # Encoding: EUC-KR → UTF-8 conversion
        pass
    
    def merge_datasources(self, dfs: List[pd.DataFrame]) -> pd.DataFrame:
        """Merge data.go.kr + MOLIT + Vworld"""
        # Concatenate vertically
        # Deduplication by (거래일, 도로명, 거래금액) - 정확도 95%
        # Standardize column names
        pass
```

#### Stage 2: Data Validation
```python
# Validation rules (avm_project/scripts/phase13_validator.py)

VALIDATION_RULES = {
    '거래가': {
        'type': int,
        'min': 50_000,         # 5천만원
        'max': 5_000_000,      # 50억원
        'null_rate_max': 0.01,
    },
    '평면적': {
        'type': float,
        'min': 10,             # 10 m²
        'max': 1000,           # 1000 m²
        'null_rate_max': 0.03,
    },
    '위도': {
        'type': float,
        'min': 33.0,           # Korean latitude range
        'max': 39.0,
    },
    '경도': {
        'type': float,
        'min': 124.0,          # Korean longitude range
        'max': 132.0,
    },
    '건축년도': {
        'type': int,
        'min': 1950,
        'max': 2026,
    },
    '도로명': {
        'type': str,
        'pattern': r'^[가-힣0-9a-zA-Z\s,]+$',  # Korean + numbers + eng
        'null_rate_max': 0.05,
    },
}

def validate_dataframe(df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
    """Validate and report data quality"""
    # Check each column against rules
    # Return: (is_valid: bool, report: Dict with stats)
    pass

def filter_outliers(df: pd.DataFrame, method: str = 'iqr', threshold: float = 1.5) -> pd.DataFrame:
    """Remove outliers using 3-sigma or IQR"""
    # For numeric cols: remove rows where value > mean + 3*std
    # For categorical: keep top 95% categories
    pass
```

#### Stage 3: Feature Engineering
```python
# File: avm_project/scripts/phase13_feature_engineering.py

class FeatureEngineer:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df
        self.features = pd.DataFrame()
    
    # Base 10 features (from MOLIT/API)
    # X1: 평면적 (Floor area in m²)
    # X2: 건축년도 (Construction year)
    # X3: 층 (Floor number)
    # X4: 거리_지하철 (Distance to subway in km)
    # X5: 거리_학교 (Distance to school in km)
    # X6: 거리_공원 (Distance to park in km)
    # X7: 거리_병원 (Distance to hospital in km)
    # X8: 도로명_인지도 (Road fame score 0-10)
    # X9: 용도_코드 (Usage code: 1=residential, 2=commercial...)
    # X10: 위도/경도_클러스터 (Geographic cluster ID)
    
    def add_temporal_features(self) -> None:
        """Generate time-based features"""
        self.df['거래년도'] = self.df['거래일'].dt.year
        self.df['거래월'] = self.df['거래일'].dt.month
        self.df['거래분기'] = self.df['거래일'].dt.quarter
        self.df['건물나이'] = self.df['거래년도'] - self.df['건축년도']
        # Result: +4 features (14 total)
    
    def add_location_features(self) -> None:
        """Geographic features"""
        # K-means clustering (n_clusters=50) on lat/lon
        self.df['지역_클러스터'] = self.df[['위도', '경도']].apply(...)
        # Distance encoding: min dist to subway/school/park
        self.df['지하철_거리'] = self.df[['위도', '경도']].apply(nearby_subway, ...)
        self.df['학교_거리'] = ...
        self.df['공원_거리'] = ...
        # Result: +6 features (20 total)
    
    def add_market_features(self) -> None:
        """Rolling market indicators"""
        # Group by region & month: calculate avg price trend
        self.df['지역_월평균가'] = self.df.groupby(['지역', '거래월'])['거래가'].transform('mean')
        self.df['지역_월물량'] = self.df.groupby(['지역', '거래월']).size()
        self.df['지역_가격추이'] = self.df['지역_월평균가'].pct_change()
        # Result: +3 features (23 total)
    
    def add_categorical_features(self) -> None:
        """Encode categorical variables"""
        # One-hot: 용도 (residential, commercial, office, etc.)
        self.df = pd.get_dummies(self.df, columns=['용도'], drop_first=True)
        # Target encoding: 법정동 → avg_price (smoothing=1.0)
        self.df['동_평균가'] = self.df.groupby('법정동')['거래가'].transform('mean')
        # Result: +12 features (35 total)
    
    def add_interaction_features(self) -> None:
        """Polynomial & interaction terms"""
        self.df['면적_x_나이'] = self.df['평면적'] * self.df['건물나이']
        self.df['면적_x_위도'] = self.df['평면적'] * self.df['위도']
        self.df['나이_제곱'] = self.df['건물나이'] ** 2
        # Result: +10 features (45 total)
    
    def finalize(self) -> Tuple[pd.DataFrame, List[str]]:
        """Return feature matrix + column names"""
        feature_cols = [c for c in self.df.columns if c not in ['거래가', 'ID']]
        return self.df, feature_cols
```

**Feature Count Summary**:
```
Base 10 (data.go.kr/MOLIT) 
+ 4 temporal 
+ 6 location 
+ 3 market 
+ 12 categorical 
+ 10 interaction 
= 45 features total
```

#### Stage 4: Data Normalization
```python
# Standardization: X_norm = (X - mean) / std
# Applied to continuous features only (면적, 거리, 나이 등)

from sklearn.preprocessing import StandardScaler

def normalize_features(X_train: pd.DataFrame, X_test: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Fit on train, transform both"""
    scaler = StandardScaler()
    X_train_norm = scaler.fit_transform(X_train)  # 50K rows
    X_test_norm = scaler.transform(X_test)       # 10K rows
    return X_train_norm, X_test_norm
```

#### Stage 5: Train/Test Split
```python
from sklearn.model_selection import train_test_split

# Temporal split: 2026-01-01 ~ 2026-03-01 (train), 2026-04-01 (test)
# Avoids data leakage for time-series forecasting
X_train, X_test = train_test_split(
    X, y,
    test_size=0.20,        # 50K train (80%), 10K test (20%)
    random_state=42,
    shuffle=False,         # Preserve temporal order
)
```

### 2.3 Output Data Format

**Processed Data Outputs** (all in `avm_project/data/processed/`):

```
├── kr_raw_merged.csv              # 60K rows (combined API + MOLIT)
│   ├── Size: ~120 MB
│   ├── Columns: 거래일, 거래가, 평면적, 위도, 경도, ... (26 raw)
│   └── Quality: 95% complete, outliers intact
│
├── kr_validated.parquet           # 50K rows (after filtering)
│   ├── Size: ~30 MB
│   ├── Outliers removed: 10K rows
│   ├── Columns: same 26
│   └── Quality: 99% complete, 3-sigma filtered
│
├── kr_features_45.pkl             # 50K rows × 45 features
│   ├── Format: pandas DataFrame (pickled)
│   ├── Size: ~45 MB
│   ├── Columns: X1_평면적, X2_건축년도, ..., X45_나이_제곱
│   └── Type: float64 (normalized)
│
├── kr_target.pkl                  # 50K rows (target: 거래가)
│   ├── Format: pandas Series
│   ├── Type: float64
│   ├── Unit: 원 (KRW)
│   └── Range: 50M ~ 5B
│
├── train_indices.pkl              # 40K indices (80% of 50K)
├── test_indices.pkl               # 10K indices (20% of 50K)
└── data_manifest.json             # Metadata
    ├── total_rows: 50000
    ├── feature_count: 45
    ├── train_size: 40000
    ├── test_size: 10000
    ├── created_date: "2026-07-05T12:34:56Z"
    ├── data_sources: ["data.go.kr", "MOLIT", "Vworld"]
    ├── null_rate: 0.02
    ├── outlier_rate: 0.02
    └── schema_version: "1.0"
```

---

## 3. 모델 학습 명세

### 3.1 Model Specifications

#### 3.1.1 XGBoost (GPU)

**Framework**: XGBoost with gpu_hist booster  
**Device**: NVIDIA RTX 5050 (or Cloud GPU)  

```python
import xgboost as xgb

params_xgboost = {
    'booster': 'gbtree',
    'tree_method': 'gpu_hist',      # GPU acceleration
    'device': 'cuda',               # CUDA backend
    'objective': 'reg:squarederror',# Regression
    'metric': 'rmse',
    
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
    'grow_policy': 'lossguide',     # GPU-optimized splitting
}

# Training
dtrain = xgb.DMatrix(X_train_norm, label=y_train)
dtest = xgb.DMatrix(X_test_norm, label=y_test)

model_xgb = xgb.train(
    params_xgboost,
    dtrain,
    evals=[(dtrain, 'train'), (dtest, 'eval')],
    evals_result=eval_result,
    verbose_eval=10,
)

# Expected: 15 min training time on RTX 5050
```

**Performance Targets**:
- R² > 0.84
- MAPE < 10.5%
- RMSE < 200만원

#### 3.1.2 LightGBM (GPU)

**Framework**: LightGBM with GPU support  

```python
import lightgbm as lgb

params_lightgbm = {
    'objective': 'regression',
    'metric': 'rmse',
    'boosting_type': 'gbdt',
    'device_type': 'gpu',
    'gpu_device_id': 0,
    'gpu_platform_id': 0,
    
    # Architecture
    'max_depth': 10,
    'num_leaves': 31,
    'min_data_in_leaf': 20,
    
    # Learning
    'learning_rate': 0.05,
    'num_leaves': 31,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    
    # Speed
    'bin_construct_sample_cnt': 200000,
}

train_data = lgb.Dataset(X_train_norm, label=y_train)
test_data = train_data.create_valid(X_test_norm, label=y_test)

model_lgb = lgb.train(
    params_lightgbm,
    train_data,
    valid_sets=[test_data],
    num_boost_round=500,
    early_stopping_rounds=50,
)

# Expected: 8 min training time on RTX 5050 (faster than XGBoost)
```

**Performance Targets**:
- R² > 0.85
- MAPE < 10%
- RMSE < 180만원

#### 3.1.3 Gradient Boosting (CPU Fallback)

**Framework**: scikit-learn GradientBoostingRegressor  

```python
from sklearn.ensemble import GradientBoostingRegressor

model_gb = GradientBoostingRegressor(
    n_estimators=500,
    learning_rate=0.05,
    max_depth=8,
    min_samples_split=5,
    min_samples_leaf=2,
    subsample=0.8,
    random_state=42,
    n_iter_no_change=50,  # Early stopping
    validation_fraction=0.1,
    verbose=1,
)

model_gb.fit(X_train_norm, y_train)

# Expected: 30 min training time on CPU (backup for NPU)
# R² ~0.82-0.84
```

### 3.2 Training Pipeline Code Structure

```python
# File: avm_project/scripts/phase13_model_trainer.py

from dataclasses import dataclass
from typing import Tuple, Dict, Any
import numpy as np
import pandas as pd
import xgboost as xgb
import lightgbm as lgb

@dataclass
class TrainingResult:
    model_name: str
    r2_score: float
    mape: float
    rmse: float
    mae: float
    feature_importance: List[Tuple[str, float]]
    training_time: float
    meets_target: bool

class Phase13ModelTrainer:
    def __init__(self, X_train: np.ndarray, X_test: np.ndarray,
                 y_train: np.ndarray, y_test: np.ndarray,
                 feature_names: List[str]) -> None:
        self.X_train = X_train
        self.X_test = X_test
        self.y_train = y_train
        self.y_test = y_test
        self.feature_names = feature_names
        self.results: Dict[str, TrainingResult] = {}
    
    def train_all_models(self) -> Dict[str, TrainingResult]:
        """Train XGBoost, LightGBM, GradientBoosting"""
        self.results['xgboost'] = self.train_xgboost()    # GPU
        self.results['lightgbm'] = self.train_lightgbm()  # GPU
        self.results['gradient_boost'] = self.train_gradient_boost()  # CPU
        return self.results
    
    def select_best_model(self) -> Tuple[str, Any]:
        """Select model with highest R² (or MAPE if tied)"""
        best = max(self.results.items(), key=lambda x: (x[1].r2_score, -x[1].mape))
        return best[0], best[1]
    
    def save_models(self, output_dir: str) -> None:
        """Save all trained models to disk"""
        # XGBoost: model.save_model(f'{output_dir}/xgboost_kr.json')
        # LightGBM: lgb.Booster.save_model(f'{output_dir}/lightgbm_kr.txt')
        # Gradient Boost: joblib.dump(model, f'{output_dir}/gb_kr.pkl')
        pass

def main() -> None:
    # 1. Load data
    X_train, X_test = load_normalized_features()
    y_train, y_test = load_targets()
    
    # 2. Train
    trainer = Phase13ModelTrainer(X_train, X_test, y_train, y_test, FEATURE_NAMES)
    results = trainer.train_all_models()
    
    # 3. Report
    for name, result in results.items():
        print(f"{name}: R²={result.r2_score:.4f}, MAPE={result.mape:.2%}")
    
    # 4. Select & save best
    best_name, best_result = trainer.select_best_model()
    print(f"✅ Best model: {best_name} (R²={best_result.r2_score:.4f})")
    trainer.save_models('avm_project/models/phase13_kr/')
```

---

## 4. 모델 검증 명세

### 4.1 Validation Metrics

```python
from sklearn.metrics import r2_score, mean_absolute_percentage_error, mean_squared_error

def evaluate_model(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate all validation metrics"""
    r2 = r2_score(y_true, y_pred)
    mape = mean_absolute_percentage_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = np.mean(np.abs(y_true - y_pred))
    
    return {
        'r2': r2,
        'mape': mape,
        'rmse': rmse,
        'mae': mae,
    }

# Expected results (best model):
VALIDATION_TARGETS = {
    'r2': 0.84,          # Minimum
    'mape': 0.105,       # Maximum (10.5%)
    'rmse': 200_000_000, # Maximum in KRW
    'mae': 120_000_000,
}
```

### 4.2 Cross-Validation

```python
from sklearn.model_selection import KFold

def cross_validate_model(X: np.ndarray, y: np.ndarray, model, n_splits: int = 5) -> Dict[str, List[float]]:
    """5-fold cross-validation"""
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    cv_results = {'r2': [], 'mape': []}
    
    for train_idx, val_idx in kf.split(X):
        X_train_cv, X_val_cv = X[train_idx], X[val_idx]
        y_train_cv, y_val_cv = y[train_idx], y[val_idx]
        
        model.fit(X_train_cv, y_train_cv)
        y_pred = model.predict(X_val_cv)
        
        metrics = evaluate_model(y_val_cv, y_pred)
        cv_results['r2'].append(metrics['r2'])
        cv_results['mape'].append(metrics['mape'])
    
    # Report mean ± std
    print(f"R² = {np.mean(cv_results['r2']):.4f} ± {np.std(cv_results['r2']):.4f}")
    print(f"MAPE = {np.mean(cv_results['mape']):.2%} ± {np.std(cv_results['mape']):.2%}")
    
    return cv_results
```

### 4.3 Feature Importance Analysis

```python
def get_feature_importance(model, feature_names: List[str], top_n: int = 10) -> pd.DataFrame:
    """Extract and rank top features"""
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
    elif hasattr(model, 'get_score'):  # XGBoost/LightGBM
        score_dict = model.get_score(importance_type='weight')
        importances = [score_dict.get(f, 0) for f in feature_names]
    
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importances,
    }).sort_values('importance', ascending=False)
    
    # Top 10 features
    print("\n🔝 Top 10 Features:")
    for i, row in importance_df.head(top_n).iterrows():
        print(f"  {i+1}. {row['feature']}: {row['importance']:.4f}")
    
    return importance_df
```

---

## 5. 모델 변환 & 배포 명세 (Phase 13.2.5)

### 5.1 ONNX Export

**Best Model** → ONNX format (framework-agnostic)

```python
import skl2onnx
from skl2onnx import convert_sklearn
from onnx import helper

def export_to_onnx(model, feature_names: List[str], output_path: str) -> None:
    """Convert trained model to ONNX"""
    
    # For Gradient Boosting (scikit-learn)
    initial_type = [('float_input', FloatTensorType([None, len(feature_names)]))]
    
    onx = convert_sklearn(model, initial_types=initial_type)
    
    with open(output_path, 'wb') as f:
        f.write(onx.SerializeToString())
    
    print(f"✅ Saved ONNX model: {output_path} ({os.path.getsize(output_path)/1e6:.1f} MB)")
```

**ONNX Model**: `avm_project/models/phase13_kr/model_kr.onnx`  
**Size**: ~100 MB (unoptimized)  
**Inference Runtime**: ONNX Runtime

### 5.2 OpenVINO Conversion (For NPU)

**ONNX** → **OpenVINO IR** (Intermediate Representation)  

```bash
# Using OpenVINO Model Optimizer
python -m openvino.tools.mo \
  --input_model model_kr.onnx \
  --output_dir ./ir_model \
  --data_type FP32
  # Output: ir_model/model_kr.xml (architecture) + model_kr.bin (weights)

# Quantization to INT8 (10x smaller, minimal accuracy loss)
python -m openvino.tools.mo \
  --input_model model_kr.onnx \
  --output_dir ./ir_model_int8 \
  --data_type INT8
  # Output: ~10-20 MB model
```

**OpenVINO IR Output**:
```
avm_project/models/phase13_kr/
├── model_kr.xml          # 1-2 MB (architecture)
├── model_kr.bin          # 10-15 MB (weights, INT8)
└── model_kr.mapping      # Input/output binding
```

### 5.3 NPU Inference

**Hardware**: Onboard NPU (Intel CPU with Neural Processing Unit)  
**Framework**: OpenVINO Runtime  

```python
# File: avm_project/scripts/phase13_npu_inference.py

from openvino.runtime import Core
import numpy as np

class NPUInference:
    def __init__(self, model_path: str = 'avm_project/models/phase13_kr/model_kr.xml') -> None:
        self.ie = Core()
        self.model = self.ie.read_model(model_path)
        self.compiled_model = self.ie.compile_model(self.model, 'AUTO')  # Auto-select device (NPU if available)
        
        # Get input/output shapes
        self.input_name = next(iter(self.compiled_model.inputs)).any_name
        self.output_name = next(iter(self.compiled_model.outputs)).any_name
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Batch inference on NPU"""
        results = self.compiled_model([X])
        return results[self.output_name]
    
    def predict_single(self, x: np.ndarray) -> float:
        """Single prediction (property valuation)"""
        x_batch = np.array([x], dtype=np.float32)
        y_pred = self.predict(x_batch)
        return float(y_pred[0])

# Usage
npu_model = NPUInference()

# Example property
property_features = np.array([
    84.95,       # 평면적 (m²)
    2015,        # 건축년도
    25,          # 층
    0.5,         # 지하철_거리 (km)
    0.2,         # 학교_거리
    0.3,         # 공원_거리
    # ... 39 more features
], dtype=np.float32)

predicted_price = npu_model.predict_single(property_features)
print(f"Predicted price: ₩{predicted_price:,.0f}")

# Batch prediction
batch_features = np.random.randn(100, 45).astype(np.float32)  # 100 properties
batch_prices = npu_model.predict(batch_features)
# Latency: ~1ms per prediction (vs 5-10ms on CPU)
```

**Performance**:
- **Latency**: <1ms per prediction
- **Throughput**: 1,000+ req/sec
- **Power**: <5W (vs 200W GPU)

---

## 6. API 서비스 명세 (Phase 13.5)

### 6.1 REST API Endpoints

**Base URL**: `http://localhost:8000/api/v1`  
**Framework**: FastAPI  
**Auth**: API Key (header: `X-API-Key`)  

#### 6.1.1 Single Property Valuation

**Endpoint**: `POST /valuate`  
**Auth**: Required  

**Request**:
```json
{
  "property": {
    "area_sqm": 84.95,
    "construction_year": 2015,
    "floor": 25,
    "distance_to_subway_km": 0.5,
    "distance_to_school_km": 0.2,
    "usage_code": 1,
    "latitude": 37.4979,
    "longitude": 127.0470
  }
}
```

**Response (200 OK)**:
```json
{
  "request_id": "req_abc123xyz",
  "predicted_price_krw": 350000000,
  "confidence_interval": {
    "lower": 315000000,
    "upper": 385000000
  },
  "model_version": "phase13_kr_v1.0",
  "inference_time_ms": 1.23,
  "timestamp": "2026-07-15T10:30:45Z"
}
```

#### 6.1.2 Batch Valuation

**Endpoint**: `POST /valuate-batch`  
**Auth**: Required  

**Request**:
```json
{
  "properties": [
    { "area_sqm": 84.95, "construction_year": 2015, ... },
    { "area_sqm": 102.3, "construction_year": 2018, ... }
  ]
}
```

**Response (200 OK)**:
```json
{
  "results": [
    { "predicted_price_krw": 350000000, "confidence_interval": {...} },
    { "predicted_price_krw": 420000000, "confidence_interval": {...} }
  ],
  "batch_size": 2,
  "total_inference_time_ms": 5.67
}
```

#### 6.1.3 Model Health & Metrics

**Endpoint**: `GET /health`  
**Auth**: Not required  

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "model_version": "phase13_kr_v1.0",
  "uptime_seconds": 86400,
  "inference_count": 15234,
  "average_latency_ms": 1.23,
  "error_rate": 0.01,
  "last_retrain": "2026-07-15T00:00:00Z"
}
```

### 6.2 API Specification (OpenAPI/Swagger)

```python
# File: avm_project/scripts/phase13_api_service.py

from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import numpy as np
from datetime import datetime
import logging

app = FastAPI(
    title="Loan4U AVM API",
    description="Phase 13 Korea Property Valuation Model",
    version="1.0.0"
)

logger = logging.getLogger(__name__)

class PropertyInput(BaseModel):
    area_sqm: float = Field(..., gt=10, lt=1000, description="Floor area in m²")
    construction_year: int = Field(..., ge=1950, le=2026)
    floor: int = Field(..., ge=1, le=100)
    distance_to_subway_km: float = Field(..., ge=0, le=20)
    distance_to_school_km: float = Field(..., ge=0, le=20)
    usage_code: int = Field(..., ge=1, le=10)
    latitude: float = Field(..., ge=33.0, le=39.0)
    longitude: float = Field(..., ge=124.0, le=132.0)

class ValuationResponse(BaseModel):
    request_id: str
    predicted_price_krw: float
    confidence_interval: dict
    model_version: str
    inference_time_ms: float
    timestamp: str

@app.post("/api/v1/valuate", response_model=ValuationResponse)
async def valuate(
    property_input: PropertyInput,
    x_api_key: str = Header(...)
) -> ValuationResponse:
    """Single property valuation endpoint"""
    
    # Validate API key
    if not validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Convert to features
    features = convert_input_to_features(property_input)
    
    # Inference
    import time
    start = time.time()
    predicted_price = npu_model.predict_single(features)
    inference_time_ms = (time.time() - start) * 1000
    
    # Confidence interval (±10%)
    ci_lower = predicted_price * 0.9
    ci_upper = predicted_price * 1.1
    
    return ValuationResponse(
        request_id=f"req_{datetime.now().timestamp()}",
        predicted_price_krw=int(predicted_price),
        confidence_interval={
            "lower": int(ci_lower),
            "upper": int(ci_upper),
        },
        model_version="phase13_kr_v1.0",
        inference_time_ms=round(inference_time_ms, 2),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

@app.get("/health")
async def health_check() -> dict:
    """Model health endpoint"""
    return {
        "status": "healthy",
        "model_version": "phase13_kr_v1.0",
        "last_retrain": "2026-07-15T00:00:00Z",
    }
```

---

## 7. 자동 재학습 파이프라인 (Monthly Retraining)

### 7.1 Automated Retraining Scheduler

```python
# File: avm_project/scripts/phase13_auto_retrain.py

from apscheduler.schedulers.background import BackgroundScheduler
import logging

log = logging.getLogger(__name__)

class AutoRetrainScheduler:
    def __init__(self, api_config: dict) -> None:
        self.scheduler = BackgroundScheduler()
        self.api_config = api_config
    
    def schedule_monthly_retrain(self) -> None:
        """Schedule retraining for 1st of each month at 2 AM"""
        self.scheduler.add_job(
            self.retrain_models,
            'cron',
            day=1,
            hour=2,
            minute=0,
            id='monthly_retrain',
        )
        self.scheduler.start()
    
    def retrain_models(self) -> None:
        """Fetch latest data, retrain, and deploy if performance improves"""
        log.info("🚀 Starting monthly model retraining...")
        
        # Step 1: Collect latest data
        new_data = Phase13DataCollector().collect_all_sources()
        log.info(f"✅ Collected {len(new_data)} new transactions")
        
        # Step 2: Merge with historical data
        historical_data = pd.read_parquet('data/processed/kr_validated.parquet')
        combined_data = pd.concat([historical_data, new_data])
        
        # Step 3: Feature engineering
        features, targets = engineer_features(combined_data)
        
        # Step 4: Train new models
        new_results = Phase13ModelTrainer(...).train_all_models()
        
        # Step 5: Compare with current production model
        current_r2 = load_current_model_r2()
        new_r2 = new_results['best_r2']
        
        if new_r2 > current_r2 + 0.01:  # >1% improvement
            log.info(f"✅ New model better: {new_r2:.4f} > {current_r2:.4f}")
            deploy_new_model(new_results['best_model'])
            notify_slack(f"Model deployed! R²: {new_r2:.4f}")
        else:
            log.info(f"⏭️ No improvement: {new_r2:.4f} <= {current_r2:.4f}")
            notify_slack(f"Retrain completed. No deployment needed. R²: {new_r2:.4f}")

# Usage
scheduler = AutoRetrainScheduler(api_config)
scheduler.schedule_monthly_retrain()
```

---

## 8. 배포 체크리스트

```
Pre-Deployment:
- [ ] 모든 테스트 통과 (train/val/test splits)
- [ ] R² > 0.84, MAPE < 10.5% 검증
- [ ] ONNX 모델 변환 완료
- [ ] OpenVINO IR (INT8) 컴파일 완료
- [ ] NPU 하드웨어 호환성 확인
- [ ] API 엔드포인트 문서화 (Swagger)
- [ ] 로깅 & 모니터링 설정

Deployment:
- [ ] 모델 파일 production 서버에 배포
- [ ] NPU 런타임 초기화
- [ ] API 서비스 시작 (FastAPI)
- [ ] Health check 통과
- [ ] Load test 통과 (1000+ req/sec)

Post-Deployment:
- [ ] 모니터링 대시보드 활성화
- [ ] 재학습 스케줄러 시작
- [ ] 알림 채널 (Slack/Email) 연결
- [ ] 롤백 계획 (이전 모델) 준비
```

---

**작성자**: Claude Agent (claude-opus-4-8)  
**최종 검토**: TBD  
**다음 단계**: WBS 작성 & 실행
