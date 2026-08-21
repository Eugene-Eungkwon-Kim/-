#!/usr/bin/env python3
"""
모든 데이터베이스 파일을 검색하여 신호 분석 및 모델 학습
2026-06-24
"""

import sys
import json
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import (RandomForestRegressor, GradientBoostingRegressor,
                              VotingRegressor)
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib

warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
SCHEMA_FILE = PROJECT_DIR / "models" / "feature_schema.json"
OUTPUT_DIR = PROJECT_DIR / "models" / "retrained_20260624_signal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 90)
print("🔍 외장하드 전체 데이터베이스 검색 및 신호 분석")
print("=" * 90)
print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# 스키마 로드
schema = json.load(open(SCHEMA_FILE))
REQUIRED_FEATURES = schema["features"]
TARGET = schema["target"]

print(f"필수 Feature: {REQUIRED_FEATURES}")
print(f"Target: {TARGET}\n")

# 모든 데이터 파일 검색
print("-" * 90)
print("📂 데이터 파일 검색")
print("-" * 90)

csv_files = list(DATA_DIR.rglob("*.csv"))
print(f"발견된 CSV 파일: {len(csv_files)}개\n")

for i, f in enumerate(csv_files[:20], 1):
    try:
        df_temp = pd.read_csv(f, nrows=1)
        print(f"{i:2d}. {str(f.relative_to(PROJECT_DIR)):<50s} | {len(df_temp):>6d}행 (샘플)")
    except Exception as e:
        print(f"{i:2d}. {str(f.relative_to(PROJECT_DIR)):<50s} | ❌ 오류: {str(e)[:40]}")

# 신호가 있는 데이터 찾기
print("\n" + "-" * 90)
print("🔎 신호가 있는 데이터 자동 감지")
print("-" * 90)

best_file = None
best_correlation = -1
best_correlation_name = ""
all_correlations = {}

for csv_file in csv_files:
    if 'processed' in str(csv_file) or 'cleaned' in str(csv_file):
        try:
            df = pd.read_csv(csv_file)

            # 필수 컬럼 확인
            has_all_features = all(col in df.columns for col in REQUIRED_FEATURES + [TARGET])

            if has_all_features:
                # 상관계수 계산
                correlations = {}
                for feat in REQUIRED_FEATURES:
                    try:
                        corr = df[feat].corr(df[TARGET])
                        correlations[feat] = float(corr) if not np.isnan(corr) else 0.0
                    except:
                        correlations[feat] = 0.0

                max_corr = max([abs(c) for c in correlations.values()])
                rel_path = str(csv_file.relative_to(PROJECT_DIR))
                all_correlations[rel_path] = {
                    'max_correlation': max_corr,
                    'rows': len(df),
                    'correlations': correlations
                }

                signal_strength = "✅ 강함" if max_corr > 0.3 else "⚠️  중간" if max_corr > 0.1 else "❌ 약함"
                print(f"✓ {csv_file.name:<40s} | 상관: {max_corr:+.4f} {signal_strength} | {len(df):>5d}행")

                if max_corr > best_correlation:
                    best_correlation = max_corr
                    best_file = csv_file
                    best_correlation_name = csv_file.name
        except Exception as e:
            pass

# 최고 신호 데이터셋 사용
if best_file is None:
    print("\n⚠️  신호 있는 파일 없음 - 가장 최근 데이터 사용")
    best_file = sorted(csv_files, key=lambda x: x.stat().st_mtime)[-1]

print(f"\n🏆 선택된 데이터: {best_file.name}")
print(f"   경로: {best_file.relative_to(PROJECT_DIR)}")
print(f"   신호 강도: {best_correlation:+.4f}")

# 데이터 로드 및 정제
print("\n" + "-" * 90)
print("🔧 데이터 정제 및 준비")
print("-" * 90)

df = pd.read_csv(best_file)
print(f"원본 데이터: {len(df)}행 × {len(df.columns)}컬럼")

# 필수 컬럼만 선택
if not all(col in df.columns for col in REQUIRED_FEATURES + [TARGET]):
    print("⚠️  일부 컬럼 부족 - 스키마 재검토 필요")
    print(f"데이터 컬럼: {list(df.columns)}")
    print(f"필수: {REQUIRED_FEATURES + [TARGET]}")
else:
    df = df[REQUIRED_FEATURES + [TARGET]].copy()

# 결측치 처리
missing = df.isnull().sum().sum()
if missing > 0:
    print(f"결측치 {missing}개 제거")
    df = df.dropna()

print(f"정제 후: {len(df)}행 × {len(df.columns)}컬럼")
print(f"타겟 범위: {df[TARGET].min():.0f} ~ {df[TARGET].max():.0f}")

# 신호 재확인
print("\n신호 분석 (정제 후):")
max_corr_final = 0
for feat in REQUIRED_FEATURES:
    corr = df[feat].corr(df[TARGET])
    if abs(corr) > max_corr_final:
        max_corr_final = abs(corr)

print(f"최대 상관계수: {max_corr_final:+.4f}")

if max_corr_final < 0.1:
    print("⚠️  경고: 신호가 여전히 약함 - 데이터 품질 재검토 필요")
elif max_corr_final < 0.3:
    print("⚠️  주의: 신호가 약함 - 모델 성능 제한 예상")
else:
    print("✅ 신호 양호 - 정상 모델 성능 예상")

# Train/Test 분할
X = df[REQUIRED_FEATURES].astype(float)
y = df[TARGET].astype(float)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\nTrain/Test 분할: {len(X_train)}행 / {len(X_test)}행")

# 모델 학습
print("\n" + "-" * 90)
print("🤖 7개 모델 학습 및 평가")
print("-" * 90)

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
m = LinearRegression().fit(X_train, y_train)
results["linear_regression"] = evaluate(m, "Linear Regression")
trained["linear_regression"] = m
r = results["linear_regression"]
status = "✅" if r['r2'] >= 0.85 else "⚠️ " if r['r2'] >= 0.70 else "❌"
print(f"1. Linear Regression    | R²={r['r2']:+.4f} RMSE={r['rmse']:>8.1f} MAE={r['mae']:>8.1f} {status}")

# 2. Decision Tree
m = DecisionTreeRegressor(max_depth=10, random_state=42).fit(X_train, y_train)
results["decision_tree"] = evaluate(m, "Decision Tree")
trained["decision_tree"] = m
r = results["decision_tree"]
status = "✅" if r['r2'] >= 0.85 else "⚠️ " if r['r2'] >= 0.70 else "❌"
print(f"2. Decision Tree        | R²={r['r2']:+.4f} RMSE={r['rmse']:>8.1f} MAE={r['mae']:>8.1f} {status}")

# 3. Random Forest
m = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1).fit(X_train, y_train)
results["random_forest"] = evaluate(m, "Random Forest")
trained["random_forest"] = m
r = results["random_forest"]
status = "✅" if r['r2'] >= 0.85 else "⚠️ " if r['r2'] >= 0.70 else "❌"
print(f"3. Random Forest        | R²={r['r2']:+.4f} RMSE={r['rmse']:>8.1f} MAE={r['mae']:>8.1f} {status}")

# 4. Gradient Boosting
m = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, random_state=42).fit(X_train, y_train)
results["gradient_boosting"] = evaluate(m, "Gradient Boosting")
trained["gradient_boosting"] = m
r = results["gradient_boosting"]
status = "✅" if r['r2'] >= 0.85 else "⚠️ " if r['r2'] >= 0.70 else "❌"
print(f"4. Gradient Boosting    | R²={r['r2']:+.4f} RMSE={r['rmse']:>8.1f} MAE={r['mae']:>8.1f} {status}")

# 5. XGBoost
try:
    from xgboost import XGBRegressor
    m = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=6,
                     random_state=42, n_jobs=-1, verbosity=0).fit(X_train, y_train)
    results["xgboost"] = evaluate(m, "XGBoost")
    trained["xgboost"] = m
    r = results["xgboost"]
    status = "✅" if r['r2'] >= 0.85 else "⚠️ " if r['r2'] >= 0.70 else "❌"
    print(f"5. XGBoost              | R²={r['r2']:+.4f} RMSE={r['rmse']:>8.1f} MAE={r['mae']:>8.1f} {status}")
except ImportError:
    print(f"5. XGBoost              | ⏭️  미설치")

# 6. LightGBM
try:
    from lightgbm import LGBMRegressor
    m = LGBMRegressor(n_estimators=100, learning_rate=0.1, max_depth=-1,
                      random_state=42, n_jobs=-1, verbose=-1).fit(X_train, y_train)
    results["lightgbm"] = evaluate(m, "LightGBM")
    trained["lightgbm"] = m
    r = results["lightgbm"]
    status = "✅" if r['r2'] >= 0.85 else "⚠️ " if r['r2'] >= 0.70 else "❌"
    print(f"6. LightGBM             | R²={r['r2']:+.4f} RMSE={r['rmse']:>8.1f} MAE={r['mae']:>8.1f} {status}")
except ImportError:
    print(f"6. LightGBM             | ⏭️  미설치")

# 7. Ensemble
ensemble_members = [(k, trained[k]) for k in
                    ["random_forest", "gradient_boosting", "xgboost", "lightgbm"]
                    if k in trained]
if len(ensemble_members) >= 2:
    ens = VotingRegressor(estimators=ensemble_members, n_jobs=-1).fit(X_train, y_train)
    results["ensemble"] = evaluate(ens, "Ensemble")
    trained["ensemble"] = ens
    r = results["ensemble"]
    status = "✅" if r['r2'] >= 0.85 else "⚠️ " if r['r2'] >= 0.70 else "❌"
    print(f"7. Ensemble (Voting)    | R²={r['r2']:+.4f} RMSE={r['rmse']:>8.1f} MAE={r['mae']:>8.1f} {status}")

# 모델 저장
print("\n" + "-" * 90)
print("💾 모델 저장")
print("-" * 90)

for name, model in trained.items():
    path = OUTPUT_DIR / f"{name}_20260624.joblib"
    joblib.dump(model, path)
    print(f"✓ {path.name}")

# 결과 보고서
summary = {
    "timestamp": datetime.now().isoformat(),
    "data_source": str(best_file.relative_to(PROJECT_DIR)),
    "data_rows": len(df),
    "rows_train": len(X_train),
    "rows_test": len(X_test),
    "max_correlation": float(max_corr_final),
    "features": REQUIRED_FEATURES,
    "target": TARGET,
    "results": results,
}

report_path = OUTPUT_DIR / "training_results.json"
json.dump(summary, open(report_path, "w"), indent=2, ensure_ascii=False)

# 최종 요약
print("\n" + "=" * 90)
print("📊 최종 결과 (목표 R² ≥ 0.85)")
print("=" * 90)

passed = 0
for name, r in sorted(results.items(), key=lambda x: -x[1]["r2"]):
    status = "✅ 달성" if r["r2"] >= 0.85 else "⚠️  부분달성" if r["r2"] >= 0.70 else "❌ 미달"
    if r["r2"] >= 0.85:
        passed += 1
    print(f"  {r['model']:<22} R²={r['r2']:+.4f}  {status}")

print("-" * 90)
print(f"목표 달성: {passed}/{len(results)} 모델")
print(f"\n데이터 소스: {best_file.relative_to(PROJECT_DIR)}")
print(f"신호 강도: {max_corr_final:+.4f}")
print(f"보고서: {report_path}")
print(f"완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 90)
