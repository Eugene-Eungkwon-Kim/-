#!/usr/bin/env python3
"""
모델 재학습 (Track B) - 실제 실행
일관된 데이터셋(real_estate_combined)으로 7개 모델 재학습 및 정직한 성능 측정
2026-06-23
"""

import sys
import json
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import (RandomForestRegressor, GradientBoostingRegressor,
                              VotingRegressor)
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib

warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent
DATA_FILE = PROJECT_DIR / "data" / "processed" / "cleaned_real_estate_combined_20260617.csv"
SCHEMA_FILE = PROJECT_DIR / "models" / "feature_schema.json"
OUTPUT_DIR = PROJECT_DIR / "models" / "retrained_20260623"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 78)
print("🤖 모델 재학습 (Track B) - 실제 실행")
print("=" * 78)
print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 스키마 및 데이터 로드
schema = json.load(open(SCHEMA_FILE))
features, target = schema["features"], schema["target"]
df = pd.read_csv(DATA_FILE)

X = df[features].astype(float)
y = df[target].astype(float)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\n데이터: {DATA_FILE.name}")
print(f"  전체: {len(df)}행 | feature: {len(features)}개 | target: {target}")
print(f"  Train: {len(X_train)}행 | Test: {len(X_test)}행")
print(f"  타겟 범위: {y.min():.0f} ~ {y.max():.0f} (평균 {y.mean():.0f})")


def evaluate(model, name):
    pred = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
    mae = float(mean_absolute_error(y_test, pred))
    r2 = float(r2_score(y_test, pred))
    mape = float(np.mean(np.abs((y_test - pred) / y_test)) * 100)
    return {"model": name, "r2": r2, "rmse": rmse, "mae": mae, "mape": mape}


results = {}
trained = {}

# 1. Linear Regression
print("\n" + "-" * 78)
m = LinearRegression().fit(X_train, y_train)
results["linear_regression"] = evaluate(m, "Linear Regression")
trained["linear_regression"] = m
r = results["linear_regression"]
print(f"1. Linear Regression    | R²={r['r2']:.4f} RMSE={r['rmse']:.1f} MAE={r['mae']:.1f} MAPE={r['mape']:.1f}%")

# 2. Decision Tree
m = DecisionTreeRegressor(max_depth=10, random_state=42).fit(X_train, y_train)
results["decision_tree"] = evaluate(m, "Decision Tree")
trained["decision_tree"] = m
r = results["decision_tree"]
print(f"2. Decision Tree        | R²={r['r2']:.4f} RMSE={r['rmse']:.1f} MAE={r['mae']:.1f} MAPE={r['mape']:.1f}%")

# 3. Random Forest
m = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1).fit(X_train, y_train)
results["random_forest"] = evaluate(m, "Random Forest")
trained["random_forest"] = m
r = results["random_forest"]
print(f"3. Random Forest        | R²={r['r2']:.4f} RMSE={r['rmse']:.1f} MAE={r['mae']:.1f} MAPE={r['mape']:.1f}%")

# 4. Gradient Boosting
m = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, random_state=42).fit(X_train, y_train)
results["gradient_boosting"] = evaluate(m, "Gradient Boosting")
trained["gradient_boosting"] = m
r = results["gradient_boosting"]
print(f"4. Gradient Boosting    | R²={r['r2']:.4f} RMSE={r['rmse']:.1f} MAE={r['mae']:.1f} MAPE={r['mape']:.1f}%")

# 5. XGBoost
try:
    from xgboost import XGBRegressor
    m = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=6,
                     random_state=42, n_jobs=-1, verbosity=0).fit(X_train, y_train)
    results["xgboost"] = evaluate(m, "XGBoost")
    trained["xgboost"] = m
    r = results["xgboost"]
    print(f"5. XGBoost              | R²={r['r2']:.4f} RMSE={r['rmse']:.1f} MAE={r['mae']:.1f} MAPE={r['mape']:.1f}%")
except ImportError:
    print("5. XGBoost              | ⏭️  xgboost 미설치 - 건너뜀")

# 6. LightGBM
try:
    from lightgbm import LGBMRegressor
    m = LGBMRegressor(n_estimators=100, learning_rate=0.1, max_depth=-1,
                      random_state=42, n_jobs=-1, verbose=-1).fit(X_train, y_train)
    results["lightgbm"] = evaluate(m, "LightGBM")
    trained["lightgbm"] = m
    r = results["lightgbm"]
    print(f"6. LightGBM             | R²={r['r2']:.4f} RMSE={r['rmse']:.1f} MAE={r['mae']:.1f} MAPE={r['mape']:.1f}%")
except ImportError:
    print("6. LightGBM             | ⏭️  lightgbm 미설치 - 건너뜀")

# 7. Ensemble (Voting) - 학습된 트리 기반 모델들로 구성
ensemble_members = [(k, trained[k]) for k in
                    ["random_forest", "gradient_boosting", "xgboost", "lightgbm"]
                    if k in trained]
if len(ensemble_members) >= 2:
    ens = VotingRegressor(estimators=ensemble_members, n_jobs=-1).fit(X_train, y_train)
    results["ensemble"] = evaluate(ens, "Ensemble")
    trained["ensemble"] = ens
    r = results["ensemble"]
    print(f"7. Ensemble (Voting)    | R²={r['r2']:.4f} RMSE={r['rmse']:.1f} MAE={r['mae']:.1f} MAPE={r['mape']:.1f}%")

# 모델 저장
print("\n" + "-" * 78)
print("💾 모델 저장:")
for name, model in trained.items():
    path = OUTPUT_DIR / f"{name}_retrained_20260623.joblib"
    joblib.dump(model, path)
    print(f"   ✓ {path.name}")

# 결과 보고서
summary = {
    "timestamp": datetime.now().isoformat(),
    "dataset": str(DATA_FILE.name),
    "rows_total": len(df),
    "rows_train": len(X_train),
    "rows_test": len(X_test),
    "features": features,
    "target": target,
    "results": results,
}
report_path = OUTPUT_DIR / "retraining_results.json"
json.dump(summary, open(report_path, "w"), indent=2, ensure_ascii=False)

# 최종 요약 + 목표(R²>=0.85) 대비
print("\n" + "=" * 78)
print("📊 재학습 결과 요약 (목표 R² >= 0.85)")
print("=" * 78)
passed = 0
for name, r in sorted(results.items(), key=lambda x: -x[1]["r2"]):
    status = "✅ 달성" if r["r2"] >= 0.85 else "❌ 미달"
    if r["r2"] >= 0.85:
        passed += 1
    print(f"  {r['model']:<22} R²={r['r2']:.4f}  {status}")
print("-" * 78)
print(f"  목표 달성: {passed}/{len(results)} 모델")
print(f"\n보고서: {report_path}")
print(f"완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 78)
