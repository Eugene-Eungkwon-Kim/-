# AVM 프로젝트 다음 스텝 상세 계획서

**작성일:** 2026-06-12  
**현재 상태:** Phase 2 완료, Phase 3-5 선택 단계  
**결정 필요:** 다음 3가지 옵션 중 우선순위 결정

---

## 📊 프로젝트 현황 요약

### ✅ 완료된 작업 (Phase 1-2)

| 항목 | 상태 | 산출물 |
|------|------|--------|
| 데이터 처리 파이프라인 | ✅ | `data_preprocessing.py` |
| 기본 ML 모델 (4개) | ✅ | `model_development.py` |
| 고급 ML 모델 (3개) | ✅ | XGBoost, LightGBM, Neural Network |
| FastAPI 서버 | ✅ | `api_server.py` (450줄, 6 endpoints) |
| Docker 컨테이너 | ✅ | Dockerfile, docker-compose.yml |
| 배포 가이드 | ✅ | DOCKER_DEPLOYMENT_GUIDE.md (700줄) |
| 샘플 데이터 | ✅ | 500개 샘플, 30컬럼 |
| 모델 성능 | ✅ | 7개 모델 모두 R² > 0.90 |

### 🎯 현재 API 상태

```
서버: FastAPI (Python 3.11)
포트: 8000 (로컬), 클라우드 (배포 시)
모델: 7개 (Linear Regression, Decision Tree, Random Forest, Gradient Boosting, XGBoost, LightGBM, Neural Network)
엔드포인트:
  - GET /health (헬스 체크)
  - GET /models (모델 목록)
  - GET /model/{name} (모델 상세 정보)
  - POST /predict (단일 예측)
  - POST /predict/batch (배치 예측, 최대 100개)
  - GET /api/version (버전 정보)
문서: Swagger UI (/docs), ReDoc (/redoc)
성능: 50-150ms/예측, 약 20 req/sec
```

---

## 🔀 다음 단계 3가지 옵션 분석

## **OPTION 1: 클라우드 배포 (Phase 4 - Task 4.3)**

### 목표
Docker 컨테이너화된 FastAPI 서버를 Google Cloud Run에 배포하여 **프로덕션 환경에서 실행 가능한 상태** 달성

### 추천 이유
- ✅ **가장 빠른 구현** (1-2시간)
- ✅ **비용 효율적** (~$0.40/월, 무료 크레딧 포함)
- ✅ **프로덕션 준비 완료** 신호
- ✅ **자동 스케일링** (0에서 무제한)
- ✅ 향후 CI/CD 파이프라인 기초

### 구현 단계 (단계별 명령어)

#### 단계 1: GCP 프로젝트 설정 (30분)
```bash
# 1.1 GCP 계정 확인 및 프로젝트 생성
# Google Cloud Console: https://console.cloud.google.com/
# - 새 프로젝트 생성: "avm-api-project"
# - 프로젝트 ID: avm-api-prod (또는 자동 할당)

# 1.2 gcloud CLI 설치 및 인증
gcloud auth login
gcloud config set project avm-api-prod
gcloud auth configure-docker

# 1.3 필요한 API 활성화
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

#### 단계 2: 코드 준비 (15분)
```bash
# 2.1 프로젝트 루트 확인
cd /home/user/-

# 2.2 requirements.txt 확인 및 최적화
cat avm_project/requirements.txt

# 2.3 .gcloudignore 생성 (필요 시)
cat > avm_project/.gcloudignore << 'EOF'
.git
.gitignore
__pycache__
*.pyc
.pytest_cache
.venv
venv/
*.log
.DS_Store
notebooks/
docs/
tests/
data/raw/
EOF
```

#### 단계 3: Docker 이미지 빌드 및 푸시 (20분)
```bash
# 3.1 로컬 테스트 (선택)
cd avm_project
docker build -t avm-api:test .
docker run -p 8000:8000 avm-api:test
# 테스트: curl http://localhost:8000/health

# 3.2 Artifact Registry에 푸시
REGION="us-central1"
PROJECT_ID="avm-api-prod"
IMAGE_NAME="avm-api"

# 3.2.1 리포지토리 생성 (첫 배포 시만)
gcloud artifacts repositories create $IMAGE_NAME \
  --repository-format=docker \
  --location=$REGION

# 3.2.2 이미지 빌드 및 푸시
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/$IMAGE_NAME/$IMAGE_NAME:latest .
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$IMAGE_NAME/$IMAGE_NAME:latest
```

#### 단계 4: Cloud Run 배포 (15분)
```bash
# 4.1 서비스 배포
gcloud run deploy avm-api \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/$IMAGE_NAME/$IMAGE_NAME:latest \
  --platform managed \
  --region $REGION \
  --port 8000 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300s \
  --max-instances 100 \
  --set-env-vars "LOG_LEVEL=info,PYTHONUNBUFFERED=1"

# 4.2 배포 확인
gcloud run services describe avm-api --region $REGION
```

### 예상 산출물

| 항목 | 내용 | 검증 방법 |
|------|------|---------|
| **배포 URL** | `https://avm-api-xxxxx.run.app` | `gcloud run services describe avm-api` |
| **API 엔드포인트** | 6개 모두 활성화 | `curl https://avm-api-xxxxx.run.app/health` |
| **자동 스케일링** | 0 → 100 인스턴스 | Cloud Run 콘솔에서 메트릭 확인 |
| **로깅** | Cloud Logging 통합 | `gcloud run logs read avm-api` |
| **모니터링** | 요청 수, 응답 시간, 오류율 | Cloud Console 대시보드 |

### 성공 기준

```bash
# 테스트 1: 헬스 체크
curl -X GET "https://avm-api-xxxxx.run.app/health"
# 예상 응답: {"status":"healthy","timestamp":"...","models_available":7}

# 테스트 2: 모델 목록 조회
curl -X GET "https://avm-api-xxxxx.run.app/models"
# 예상: 7개 모델 반환

# 테스트 3: 예측 요청
curl -X POST "https://avm-api-xxxxx.run.app/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "property_data": {
      "area_sqm": 100.5,
      "year_built": 2010,
      "rooms": 3,
      "bathrooms": 2,
      "parking": 1,
      "floor": 5,
      "total_floor": 20,
      "condition": 7,
      "original_price": 500000000,
      "appraised_price": 480000000,
      "outstanding_debt": 300000000,
      "market_price": 490000000,
      "transaction_count_1y": 5,
      "ltv": 0.62,
      "loan_term_months": 240,
      "days_on_market": 30,
      "appraisal_rounds": 2,
      "age_years": 14,
      "price_per_sqm": 4876000,
      "debt_to_price_ratio": 0.61,
      "price_variance": 0.02
    },
    "model_name": "lightgbm"
  }'
# 예상 응답: 예측 가격 + 신뢰도 점수

# 테스트 4: 배치 예측 (2개 부동산)
curl -X POST "https://avm-api-xxxxx.run.app/predict/batch" \
  -H "Content-Type: application/json" \
  -d '[{...}, {...}]'
# 예상 응답: count=2, predictions=[...]

# 테스트 5: Swagger UI 접근
# https://avm-api-xxxxx.run.app/docs
# 모든 엔드포인트 상호작용 가능 확인
```

### 예상 소요 시간

| 단계 | 소요 시간 | 누적 시간 |
|------|----------|----------|
| GCP 설정 | 30분 | 30분 |
| 코드 준비 | 15분 | 45분 |
| 이미지 빌드/푸시 | 20분 | 1시간 5분 |
| Cloud Run 배포 | 15분 | 1시간 20분 |
| 테스트 및 검증 | 20분 | 1시간 40분 |
| **총 예상 시간** | | **1시간 40분** |

### 비용 추정

```
Google Cloud Run 비용 (월):
- 요청: 2M 무료 + $0.40/M 추가
- 컴퓨팅 시간: 180,000 GB-초 무료 + $0.00001667/GB-초
- 예상: $0.40/월 (무료 크레딧 포함)

초기 설정: $0 (Google Cloud 무료 크레딧 사용)
```

### 다음 단계와의 연결

```
OPTION 1 완료 후 진행 경로:
├─ OPTION 2 (모델 최적화): 배포된 API의 성능 개선
│  └─ 하이퍼파라미터 튜닝 → 새 모델 업로드 → 배포 재시작
├─ OPTION 3 (실제 데이터): API 인증 후 데이터 수집
│  └─ 실제 데이터로 재학습 → 모델 업데이트
└─ Phase 5 (최종화):
   └─ CI/CD 파이프라인 구축 (GitHub Actions)
      └─ 자동 배포 설정
```

---

## **OPTION 2: 모델 최적화 (Phase 3)**

### 목표
7개 ML 모델의 **성능 극대화**를 위해 하이퍼파라미터를 체계적으로 최적화하고, SHAP를 통한 Feature Importance 분석으로 **모델 해석 가능성 및 신뢰도 향상**

### 추천 이유
- ✅ **R² 점수 개선** (현재 0.9053-1.0000 → 목표 0.95-0.98+)
- ✅ **모델 신뢰도 증대** (SHAP 분석으로 예측 근거 가시화)
- ✅ **프로덕션 품질 향상** (과적합 감지 및 개선)
- ✅ **비즈니스 인사이트** (중요 요소 파악)

### 구현 단계

#### 단계 1: 하이퍼파라미터 최적화 (3-4시간)

##### 1.1 Random Forest 최적화
```python
# 파일: scripts/hyperparameter_tuning.py (신규 생성)

from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestRegressor
import pandas as pd
import numpy as np
import json
import logging

class HyperparameterTuner:
    """하이퍼파라미터 최적화 클래스"""
    
    def __init__(self, X_train, y_train, X_val, y_val):
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.results = {}
        
    def tune_random_forest(self):
        """Random Forest 하이퍼파라미터 튜닝"""
        param_grid = {
            'n_estimators': [50, 100, 200, 300],
            'max_depth': [10, 15, 20, 25, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['sqrt', 'log2'],
            'bootstrap': [True, False]
        }
        
        model = RandomForestRegressor(random_state=42, n_jobs=-1)
        grid_search = GridSearchCV(
            model,
            param_grid,
            cv=5,
            scoring='r2',
            n_jobs=-1,
            verbose=2
        )
        
        grid_search.fit(self.X_train, self.y_train)
        
        best_model = grid_search.best_estimator_
        val_r2 = best_model.score(self.X_val, self.y_val)
        
        return {
            'model': best_model,
            'best_params': grid_search.best_params_,
            'best_train_r2': grid_search.best_score_,
            'val_r2': val_r2,
            'cv_results': grid_search.cv_results_
        }
    
    def tune_gradient_boosting(self):
        """Gradient Boosting 하이퍼파라미터 튜닝"""
        from sklearn.ensemble import GradientBoostingRegressor
        
        param_grid = {
            'n_estimators': [100, 200, 300],
            'learning_rate': [0.001, 0.01, 0.05, 0.1],
            'max_depth': [3, 4, 5, 6],
            'subsample': [0.7, 0.8, 0.9, 1.0],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
        
        model = GradientBoostingRegressor(random_state=42)
        grid_search = GridSearchCV(
            model,
            param_grid,
            cv=5,
            scoring='r2',
            n_jobs=-1,
            verbose=2
        )
        
        grid_search.fit(self.X_train, self.y_train)
        
        best_model = grid_search.best_estimator_
        val_r2 = best_model.score(self.X_val, self.y_val)
        
        return {
            'model': best_model,
            'best_params': grid_search.best_params_,
            'best_train_r2': grid_search.best_score_,
            'val_r2': val_r2
        }
    
    def tune_xgboost(self):
        """XGBoost 하이퍼파라미터 튜닝"""
        import xgboost as xgb
        
        param_grid = {
            'n_estimators': [100, 200, 300],
            'learning_rate': [0.001, 0.01, 0.05, 0.1],
            'max_depth': [3, 4, 5, 6, 7],
            'subsample': [0.7, 0.8, 0.9, 1.0],
            'colsample_bytree': [0.7, 0.8, 0.9, 1.0],
            'min_child_weight': [1, 2, 3]
        }
        
        model = xgb.XGBRegressor(random_state=42, n_jobs=-1)
        grid_search = GridSearchCV(
            model,
            param_grid,
            cv=5,
            scoring='r2',
            n_jobs=-1,
            verbose=2
        )
        
        grid_search.fit(self.X_train, self.y_train)
        
        best_model = grid_search.best_estimator_
        val_r2 = best_model.score(self.X_val, self.y_val)
        
        return {
            'model': best_model,
            'best_params': grid_search.best_params_,
            'best_train_r2': grid_search.best_score_,
            'val_r2': val_r2
        }
    
    def tune_lightgbm(self):
        """LightGBM 하이퍼파라미터 튜닝"""
        import lightgbm as lgb
        
        param_grid = {
            'n_estimators': [100, 200, 300],
            'learning_rate': [0.001, 0.01, 0.05, 0.1],
            'num_leaves': [20, 31, 50, 100],
            'max_depth': [3, 4, 5, 6, 7],
            'subsample': [0.7, 0.8, 0.9, 1.0],
            'colsample_bytree': [0.7, 0.8, 0.9, 1.0],
            'min_child_samples': [10, 20, 30]
        }
        
        model = lgb.LGBMRegressor(random_state=42, n_jobs=-1)
        grid_search = GridSearchCV(
            model,
            param_grid,
            cv=5,
            scoring='r2',
            n_jobs=-1,
            verbose=2
        )
        
        grid_search.fit(self.X_train, self.y_train)
        
        best_model = grid_search.best_estimator_
        val_r2 = best_model.score(self.X_val, self.y_val)
        
        return {
            'model': best_model,
            'best_params': grid_search.best_params_,
            'best_train_r2': grid_search.best_score_,
            'val_r2': val_r2
        }
```

##### 1.2 실행 스크립트
```bash
# scripts/run_hyperparameter_tuning.py

python3 << 'EOF'
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import pickle
import json
from pathlib import Path
from scripts.hyperparameter_tuning import HyperparameterTuner

# 데이터 로드
data = pd.read_csv('output/processed_sample_data.csv')

# 특성과 타겟 분리 (숫자 컬럼만 사용)
numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
if '최종_판매가격' in numeric_cols:
    numeric_cols.remove('최종_판매가격')

X = data[numeric_cols]
y = data['최종_판매가격']

# 데이터 분할 (훈련 80%, 검증 20%)
X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 정규화
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)

# 튜닝 실행
tuner = HyperparameterTuner(X_train_scaled, y_train, X_val_scaled, y_val)

tuning_results = {}

print("\n=== Random Forest 튜닝 중 ===")
tuning_results['random_forest'] = tuner.tune_random_forest()
print(f"Random Forest - Train R²: {tuning_results['random_forest']['best_train_r2']:.4f}, Val R²: {tuning_results['random_forest']['val_r2']:.4f}")

print("\n=== Gradient Boosting 튜닝 중 ===")
tuning_results['gradient_boosting'] = tuner.tune_gradient_boosting()
print(f"GB - Train R²: {tuning_results['gradient_boosting']['best_train_r2']:.4f}, Val R²: {tuning_results['gradient_boosting']['val_r2']:.4f}")

print("\n=== XGBoost 튜닝 중 ===")
tuning_results['xgboost'] = tuner.tune_xgboost()
print(f"XGBoost - Train R²: {tuning_results['xgboost']['best_train_r2']:.4f}, Val R²: {tuning_results['xgboost']['val_r2']:.4f}")

print("\n=== LightGBM 튜닝 중 ===")
tuning_results['lightgbm'] = tuner.tune_lightgbm()
print(f"LightGBM - Train R²: {tuning_results['lightgbm']['best_train_r2']:.4f}, Val R²: {tuning_results['lightgbm']['val_r2']:.4f}")

# 결과 저장
for model_name, result in tuning_results.items():
    best_model = result.pop('model')
    # 모델 저장
    with open(f'models/{model_name}_tuned.pkl', 'wb') as f:
        pickle.dump(best_model, f)
    # 파라미터 저장
    with open(f'output/{model_name}_tuned_params.json', 'w') as f:
        json.dump(result, f, indent=2, default=str)

print("\n✅ 튜닝 완료! 모든 결과는 output/ 디렉토리에 저장됨")
EOF
```

#### 단계 2: Feature Importance 분석 (2-3시간)

```python
# 파일: scripts/feature_importance_analysis.py (신규)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import shap
from pathlib import Path

class FeatureImportanceAnalyzer:
    """Feature Importance 및 SHAP 분석"""
    
    def __init__(self, X_data, y_data, feature_names):
        self.X_data = X_data
        self.y_data = y_data
        self.feature_names = feature_names
        self.results = {}
        
    def analyze_tree_models(self, model, model_name):
        """트리 기반 모델 분석"""
        importances = model.feature_importances_
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
        
        self.results[f'{model_name}_feature_importance'] = importance_df
        return importance_df
    
    def analyze_shap(self, model, X_test, model_name, model_type='tree'):
        """SHAP 값 계산 및 시각화"""
        if model_type == 'tree':
            explainer = shap.TreeExplainer(model)
        elif model_type == 'kernel':
            explainer = shap.KernelExplainer(model.predict, X_test)
        
        shap_values = explainer.shap_values(X_test)
        
        # SHAP 요약 플롯 생성
        plt.figure(figsize=(10, 8))
        shap.summary_plot(shap_values, X_test, feature_names=self.feature_names, show=False)
        plt.title(f'{model_name} - SHAP Summary Plot')
        plt.tight_layout()
        plt.savefig(f'output/{model_name}_shap_summary.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # SHAP 값 저장
        shap_importance = pd.DataFrame({
            'feature': self.feature_names,
            'shap_importance': np.abs(shap_values).mean(axis=0)
        }).sort_values('shap_importance', ascending=False)
        
        self.results[f'{model_name}_shap_importance'] = shap_importance
        return shap_importance
    
    def plot_feature_importance(self, model_name, importance_df, top_n=15):
        """Feature Importance 시각화"""
        top_features = importance_df.head(top_n)
        
        plt.figure(figsize=(12, 8))
        sns.barplot(data=top_features, x='importance', y='feature', palette='viridis')
        plt.title(f'{model_name} - Top {top_n} Feature Importance')
        plt.xlabel('Importance Score')
        plt.ylabel('Feature')
        plt.tight_layout()
        plt.savefig(f'output/{model_name}_feature_importance.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_report(self):
        """분석 리포트 생성"""
        report = []
        report.append("# Feature Importance 분석 리포트\n")
        report.append(f"생성일: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for key, df in self.results.items():
            report.append(f"## {key}\n\n")
            report.append(df.head(15).to_markdown())
            report.append("\n\n")
        
        with open('docs/FEATURE_IMPORTANCE_ANALYSIS.md', 'w') as f:
            f.writelines(report)
```

#### 단계 3: 모델 비교 및 재학습 (1시간)

```bash
# 모든 튜닝된 모델 로드 및 평가
python3 << 'EOF'
import pandas as pd
import numpy as np
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import pickle
import json

data = pd.read_csv('output/processed_sample_data.csv')
numeric_cols = [col for col in data.select_dtypes(include=[np.number]).columns if col != '최종_판매가격']
X = data[numeric_cols]
y = data['최종_판매가격']

# 테스트 데이터 (마지막 100개)
X_test = X.iloc[-100:]
y_test = y.iloc[-100:]

comparison_results = []

for model_file in ['random_forest_tuned', 'gradient_boosting_tuned', 'xgboost_tuned', 'lightgbm_tuned']:
    try:
        with open(f'models/{model_file}.pkl', 'rb') as f:
            model = pickle.load(f)
        
        y_pred = model.predict(X_test)
        r2 = r2_score(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        
        comparison_results.append({
            'model': model_file.replace('_tuned', ''),
            'r2_score': r2,
            'rmse': rmse,
            'mae': mae
        })
        
        print(f"{model_file}: R²={r2:.4f}, RMSE={rmse:,.0f}, MAE={mae:,.0f}")
    except Exception as e:
        print(f"❌ {model_file}: {e}")

# 결과 저장
with open('output/model_comparison_tuned.json', 'w') as f:
    json.dump(comparison_results, f, indent=2)

print("\n✅ 모델 비교 완료! output/model_comparison_tuned.json에 저장됨")
EOF
```

### 예상 산출물

| 항목 | 파일명 | 설명 |
|------|--------|------|
| **튜닝된 모델** | `models/*_tuned.pkl` | 4개 모델 (RF, GB, XGB, LGBM) |
| **최적 파라미터** | `output/*_tuned_params.json` | 각 모델 최적 하이퍼파라미터 |
| **Feature Importance** | `output/*_feature_importance.png` | 상위 15개 특성 시각화 |
| **SHAP 분석** | `output/*_shap_summary.png` | SHAP Summary Plot |
| **모델 비교** | `output/model_comparison_tuned.json` | 성능 비교 (R², RMSE, MAE) |
| **분석 리포트** | `docs/FEATURE_IMPORTANCE_ANALYSIS.md` | 종합 분석 문서 |

### 예상 성능 개선

```
현재 vs 최적화 후 (예상):

Random Forest:
  현재: R² 0.9717 → 예상: 0.9750+
  개선도: +0.33%

Gradient Boosting:
  현재: R² 0.9683 → 예상: 0.9720+
  개선도: +0.37%

XGBoost:
  현재: R² 0.9701 → 예상: 0.9750+
  개선도: +0.49%

LightGBM:
  현재: R² 0.9719 → 예상: 0.9780+
  개선도: +0.61%

전체 개선: 약 3-5% 성능 향상 예상
```

### 예상 소요 시간

| 단계 | 소요 시간 | 누적 시간 |
|------|----------|----------|
| 파일 생성 및 환경 설정 | 20분 | 20분 |
| Random Forest 튜닝 | 40분 | 1시간 |
| Gradient Boosting 튜닝 | 40분 | 1시간 40분 |
| XGBoost 튜닝 | 40분 | 2시간 20분 |
| LightGBM 튜닝 | 40분 | 3시간 |
| Feature Importance 분석 | 40분 | 3시간 40분 |
| SHAP 분석 | 40분 | 4시간 20분 |
| 리포트 작성 및 검증 | 20분 | **4시간 40분** |

### 다음 단계와의 연결

```
OPTION 2 완료 후 진행 경로:
├─ 튜닝된 모델 업로드
│  └─ models/*.pkl 업데이트 → API 재시작
├─ OPTION 1과 연계:
│  └─ 배포된 Cloud Run API 모델 업데이트
└─ Phase 5 (최종화):
   └─ 실제 데이터 수집 후 모델 재학습
```

---

## **OPTION 3: Data.go.kr API 인증 및 실제 데이터 수집 (Phase 2 - Task 2.1/2.2)**

### 목표
Data.go.kr API 인증 상태를 확인 및 해결한 후, **2024년 전체 한국 부동산 실거래 데이터 수집** (약 50,000-150,000건) 후 **실제 데이터로 모델 재학습**

### 추천 이유
- ✅ **실제 운영 데이터 확보** (샘플 데이터 → 프로덕션 데이터)
- ✅ **모델 신뢰도 극대화** (실데이터 학습 모델)
- ✅ **최종 프로덕션 준비** (Phase 3-5 완성)
- ⚠️ **시간 소요** (API 승인 대기 포함 2-7일)

### 구현 단계

#### 단계 1: API 인증 상태 확인 (1-2시간)

```bash
# 1.1 Data.go.kr 포털 접속
# URL: https://www.data.go.kr/
# 단계:
#   1. 로그인 (이메일: eugene1108@gmail.com)
#   2. 우측 상단 "마이페이지" 클릭
#   3. 좌측 메뉴 "개인 정보" → "신청 목록" 또는 "API 관리"
#   4. "부동산 실거래 정보 조회 서비스" API 확인
#   5. 상태 확인:
#      - ✅ 승인됨 (Active): 기존 API 키 사용 가능
#      - ⏳ 심사중: 승인 대기 (2-3일)
#      - ❌ 거절됨: 재신청 필요
#      - ⛔ 만료됨: 연장 신청

# 1.2 현재 API 키 확인
# 마이페이지 → "API 관리" → "부동산 실거래 정보"
# API 키 복사 및 저장

# 1.3 API 테스트 (기존 키로)
curl -G "http://apis.data.go.kr/1613000/RealEstateTransactionService/getRealEstateTransactionList" \
  --data-urlencode "LAWD_CD=27110" \
  --data-urlencode "DEAL_YMD=202401" \
  --data-urlencode "serviceKey=YOUR_API_KEY"

# 응답 확인:
# - 200 OK: API 정상 작동 ✅
# - 403 Forbidden: API 키 미승인 또는 만료 ❌
# - 400 Bad Request: 파라미터 오류
```

#### 단계 2: API 키 업데이트 및 설정 (30분)

```bash
# 2.1 환경 변수 설정
export DATAGOVKR_API_KEY="your-approved-api-key"

# 또는 설정 파일 업데이트
python3 << 'EOF'
import json

config = {
    "api": {
        "data_gov_kr": {
            "base_url": "http://apis.data.go.kr/1613000",
            "api_key": "your-approved-api-key",
            "timeout": 30
        }
    }
}

with open('config/avm_config.json', 'r') as f:
    existing_config = json.load(f)

existing_config.update(config)

with open('config/avm_config.json', 'w') as f:
    json.dump(existing_config, f, indent=2)

print("✅ API 키 업데이트 완료")
EOF

# 2.2 설정 확인
python3 -c "import json; config=json.load(open('config/avm_config.json')); print('API Key Status:', '✅' if config.get('api',{}).get('data_gov_kr',{}).get('api_key') else '❌')"
```

#### 단계 3: 월별 데이터 수집 (5-7일, 자동화)

```bash
# 3.1 전체 연도 데이터 수집 (2024-01 ~ 2024-12)
python3 scripts/avm_orchestrator.py \
  --mode data_collection \
  --start-date 202401 \
  --end-date 202412 \
  --api-key "$DATAGOVKR_API_KEY"

# 또는 개별 스크립트 실행
python3 << 'EOF'
from scripts.data_collection_handler import KoreanRealEstateDataCollector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

collector = KoreanRealEstateDataCollector(api_key='your-api-key')

# 2024년 전체 데이터 수집
months = [f'202{4}{m:02d}' for m in range(1, 13)]

for month in months:
    logger.info(f"수집 중: {month}")
    try:
        df = collector.collect_real_estate_transaction_data(month)
        df.to_csv(f'data/raw/real_estate_{month}.csv', index=False)
        logger.info(f"✅ {month}: {len(df)}건 저장")
    except Exception as e:
        logger.error(f"❌ {month}: {e}")

print("\n✅ 전체 데이터 수집 완료!")
EOF

# 3.2 수집 상태 모니터링
watch -n 10 'ls -lh data/raw/real_estate_*.csv | wc -l && du -sh data/raw/'
```

#### 단계 4: 수집 데이터 통합 및 전처리 (2-3시간)

```bash
# 4.1 월별 파일 통합
python3 << 'EOF'
import pandas as pd
import numpy as np
from pathlib import Path

# 모든 월별 파일 로드
data_files = sorted(Path('data/raw/').glob('real_estate_202401.csv'))
dfs = []

for file in data_files:
    try:
        df = pd.read_csv(file)
        dfs.append(df)
        print(f"✅ {file.name}: {len(df)} 행")
    except Exception as e:
        print(f"❌ {file.name}: {e}")

# 통합
full_data = pd.concat(dfs, ignore_index=True)
print(f"\n총 데이터: {len(full_data)} 행 × {len(full_data.columns)} 컬럼")

# 통합 데이터 저장
full_data.to_csv('data/raw/real_estate_2024_full.csv', index=False)
print("✅ 통합 데이터 저장: data/raw/real_estate_2024_full.csv")

# 기본 통계
print("\n기본 통계:")
print(f"컬럼: {full_data.columns.tolist()}")
print(f"결측값: {full_data.isnull().sum().sum()}")
print(f"가격 범위: {full_data['거래금액'].min():,} ~ {full_data['거래금액'].max():,}₩")
EOF

# 4.2 전처리 파이프라인 실행
python3 << 'EOF'
from scripts.data_preprocessing import DataPreprocessor

preprocessor = DataPreprocessor()

# 데이터 로드
data = preprocessor.load_data('data/raw/real_estate_2024_full.csv')
print(f"원본 데이터: {len(data)} 행")

# 전처리
data = preprocessor.handle_missing_values(data)
data = preprocessor.detect_outliers(data)
data = preprocessor.normalize_data(data)
data = preprocessor.feature_engineering(data)

# 저장
preprocessor.save_processed_data(data, 'output/processed_real_estate_2024.csv')
print(f"처리 완료 데이터: {len(data)} 행 × {len(data.columns)} 컬럼")
EOF
```

#### 단계 5: 실제 데이터로 모델 재학습 (2-3시간)

```bash
# 5.1 새 데이터로 모델 학습
python3 << 'EOF'
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from scripts.model_development import AVMModelDeveloper
import json

# 처리된 데이터 로드
data = pd.read_csv('output/processed_real_estate_2024.csv')

# 숫자 컬럼만 사용
numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
if '최종_판매가격' in numeric_cols:
    numeric_cols.remove('최종_판매가격')

X = data[numeric_cols]
y = data['최종_판매가격']

# 데이터 분할
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 정규화
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# 모델 학습
developer = AVMModelDeveloper()
developer.X_train = X_train
developer.y_train = y_train
developer.X_test = X_test
developer.y_test = y_test

models = {}
models['linear_regression'] = developer.train_linear_regression()
models['decision_tree'] = developer.train_decision_tree()
models['random_forest'] = developer.train_random_forest()
models['gradient_boosting'] = developer.train_gradient_boosting()
models['xgboost'] = developer.train_xgboost()
models['lightgbm'] = developer.train_lightgbm()
models['neural_network'] = developer.train_neural_network()

# 성능 평가
results = []
for name, model in models.items():
    r2 = model.score(X_test, y_test) if hasattr(model, 'score') else developer.evaluate_model(model, X_test, y_test)
    results.append({'model': name, 'r2_score': r2})
    print(f"{name}: R² = {r2:.4f}")

# 결과 저장
with open('output/model_results_real_data.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n✅ 모든 모델 학습 완료! 결과는 output/model_results_real_data.json에 저장됨")
EOF
```

### 예상 산출물

| 항목 | 내용 | 용량 | 저장 위치 |
|------|------|------|---------|
| **월별 원본 파일** | 12개 CSV 파일 (1월-12월) | 500MB~1GB | `data/raw/real_estate_202401.csv` ~ |
| **통합 데이터** | 2024년 전체 거래 데이터 | 500MB~1GB | `data/raw/real_estate_2024_full.csv` |
| **처리된 데이터** | 전처리 완료 데이터 | 600MB~1.2GB | `output/processed_real_estate_2024.csv` |
| **재학습 모델** | 7개 모델 (실데이터 기반) | 500MB~1GB | `models/[model_name]_realdata.pkl` |
| **성능 리포트** | 모델 평가 결과 | 50KB | `output/model_results_real_data.json` |
| **데이터 분석 리포트** | EDA 및 품질 리포트 | 100KB | `docs/REAL_DATA_ANALYSIS.md` |

### 예상 데이터 규모

```
부동산 실거래 정보 (2024년):
- 월별 거래건수: 1,000 ~ 5,000건
- 예상 총 거래건수: 24,000 ~ 60,000건
- 데이터 컬럼: 약 15-20개
- 파일 크기: 월별 50-150MB, 연간 500MB-1.5GB

예: 2024년 01월 (2월초 기준)
- 거래건수: 약 3,500건
- 컬럼: 15개 (지역, 가격, 면적, 층수 등)
- 파일크기: 약 45MB
```

### 예상 소요 시간

| 단계 | 소요 시간 | 누적 시간 |
|------|----------|----------|
| API 상태 확인 | 1-2시간 | 1-2시간 |
| API 키 업데이트 | 30분 | 1.5-2.5시간 |
| 월별 데이터 수집 | 5-7일 (자동) | 5-7일 + 2.5시간 |
| 데이터 통합 | 1시간 | 5-7일 + 3.5시간 |
| 전처리 | 2시간 | 5-7일 + 5.5시간 |
| 모델 재학습 | 2시간 | 5-7일 + 7.5시간 |
| **총 예상 시간** | | **5-7일 (API 승인 포함)** |

### 다음 단계와의 연결

```
OPTION 3 완료 후 진행 경로:
├─ Phase 3: 모델 검증 및 평가
│  └─ Feature Importance 분석 (OPTION 2와 중복 가능)
│  └─ SHAP 분석
├─ OPTION 1 연계: 새 모델로 API 배포
│  └─ 모델 업데이트 → Cloud Run 재배포
├─ OPTION 2 연계: 하이퍼파라미터 재최적화
│  └─ 실데이터 기반 GridSearchCV 실행
└─ Phase 5 (최종화):
   └─ 자동화 Cron job 설정 (주간 데이터 수집 및 재학습)
```

---

## 📊 3가지 옵션 비교표

| 항목 | OPTION 1 (배포) | OPTION 2 (최적화) | OPTION 3 (실데이터) |
|------|---|---|---|
| **난이도** | ⭐ (쉬움) | ⭐⭐ (중간) | ⭐⭐⭐ (어려움) |
| **소요 시간** | 1-2시간 | 4-5시간 | 5-7일 |
| **비용** | $0.4/월 | $0 | $0 |
| **효과** | 프로덕션 준비 | 성능 개선 | 실운영 기반 |
| **우선순위** | 🥇 **1순위** | 🥈 **2순위** | 🥉 **3순위** |
| **다음 단계** | OPTION 2/3 병행 | OPTION 1/3 병행 | OPTION 1/2 완성 후 |
| **병행 가능** | ✅ | ✅ | ✅ (순차적) |

---

## 🎯 권장 실행 순서

### 시나리오 1: 빠른 프로덕션 출시 (추천) ⭐

```
Week 1:
  Day 1-2: OPTION 1 (배포) → 1-2시간 소요
           └─ Cloud Run API 라이브
  Day 3-5: OPTION 2 (최적화) → 4-5시간 소요 (병행 가능)
           └─ 하이퍼파라미터 튜닝 완료 → API 업데이트

Week 2:
  Day 1-7: OPTION 3 (실데이터) → 5-7일 (API 승인 대기 포함)
           └─ 2024년 전체 데이터 수집 → 모델 재학습 → 재배포

최종 상태:
✅ 프로덕션 API 운영 중 (Cloud Run)
✅ 최적화된 7개 모델 배포
✅ 실제 데이터 기반 학습
✅ Phase 3-5 준비 완료
```

### 시나리오 2: 최고 품질 모델 개발

```
Week 1:
  Day 1-7: OPTION 3 (실데이터) → 5-7일 (우선 실행)
           └─ 2024년 전체 데이터 수집 및 처리

Week 2:
  Day 1-3: OPTION 2 (최적화) → 4-5시간
           └─ 실데이터 기반 하이퍼파라미터 최적화
  Day 4-5: OPTION 1 (배포) → 1-2시간
           └─ 최고 성능 모델로 배포

최종 상태:
✅ 최고 성능 모델 (실데이터 + 최적화)
✅ 프로덕션 API 운영 (Cloud Run)
✅ 최소 R² 0.95 달성
```

---

## ✅ 실행 체크리스트

### OPTION 1 (배포) 체크리스트
- [ ] GCP 프로젝트 생성 및 활성화
- [ ] gcloud CLI 설치 및 인증
- [ ] Docker 이미지 빌드 테스트
- [ ] Artifact Registry 저장소 생성
- [ ] 이미지 푸시
- [ ] Cloud Run 배포
- [ ] 5개 엔드포인트 모두 테스트
- [ ] 배포 URL 문서화

### OPTION 2 (최적화) 체크리스트
- [ ] hyperparameter_tuning.py 파일 생성
- [ ] Random Forest 파라미터 그리드 설정
- [ ] Gradient Boosting 파라미터 그리드 설정
- [ ] XGBoost 파라미터 그리드 설정
- [ ] LightGBM 파라미터 그리드 설정
- [ ] GridSearchCV 실행 (5-Fold CV)
- [ ] 튜닝 결과 저장
- [ ] Feature Importance 분석
- [ ] SHAP 값 계산 및 시각화
- [ ] 모델 성능 비교 리포트 생성
- [ ] 튜닝된 모델 업데이트

### OPTION 3 (실데이터) 체크리스트
- [ ] Data.go.kr 포털 접속 및 API 상태 확인
- [ ] API 키 승인 상태 확인
  - [ ] 승인됨 → 기존 키 사용
  - [ ] 대기중 → 승인 대기 (2-3일)
  - [ ] 거절됨 → 재신청
- [ ] 환경 변수 또는 config 파일에 API 키 설정
- [ ] API 연결 테스트
- [ ] 월별 데이터 수집 스크립트 실행
- [ ] 모든 월별 파일 다운로드 확인 (12개)
- [ ] 데이터 통합 (real_estate_2024_full.csv)
- [ ] 전처리 실행
- [ ] 7개 모델 재학습
- [ ] 새 모델 성능 평가
- [ ] 모델 파일 업데이트
- [ ] API/배포 시스템 재시작

---

## 🚀 최종 권장사항

### 즉시 실행 (오늘)
```
→ OPTION 1: 클라우드 배포 (1-2시간)
  이유: 프로덕션 준비 상태 증명, 빠른 완성
```

### 동시 진행 (병행)
```
→ OPTION 2: 모델 최적화 (4-5시간)
  이유: 배포 후 성능 개선, 배포된 API 모델 업데이트 가능
```

### 계획 수립 (병행)
```
→ OPTION 3: 실데이터 수집 준비
  1. Data.go.kr API 상태 즉시 확인
  2. API 승인 상태에 따라 일정 조정
  3. 승인 대기 중에 OPTION 1, 2 완성
  4. 승인 후 실행 (5-7일)
```

---

**최종 결론:**
- **가장 실용적 경로**: OPTION 1 → OPTION 2 → OPTION 3 (순차적)
- **예상 총 소요 시간**: 5-7일 (API 승인 포함)
- **최종 산출물**: 프로덕션 API + 최고 성능 모델 + 실제 데이터 기반 학습
- **다음 단계**: Phase 5 (CI/CD 파이프라인, 자동화, 최종 배포)

---

**작성자:** Claude AI  
**마지막 업데이트:** 2026-06-12  
**상태:** 준비 완료 ✅
