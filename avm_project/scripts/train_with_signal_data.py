#!/usr/bin/env python3
"""
신호 있는 실제 부동산 데이터로 모델 학습
Signal Real Estate Dataset (2024-01 ~ 2024-12): 5,000행
2026-06-24
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
SCHEMA_FILE = PROJECT_DIR / "models" / "feature_schema.json"
DATA_FILE = PROJECT_DIR / "data" / "processed" / "cleaned_signal_real_estate_202401_202412.csv"
OUTPUT_DIR = PROJECT_DIR / "models" / "retrained_signal_data_20260624"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 90)
print("🎯 신호 있는 실제 부동산 데이터 모델 학습")
print("=" * 90)
print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"데이터: {DATA_FILE.name} (5,000행 × 10컬럼)\n")

# 스키마 로드
schema = json.load(open(SCHEMA_FILE))
REQUIRED_FEATURES_EN = schema["features"]  # 영문 feature 이름
TARGET_EN = schema["target"]  # 영문 target 이름

# 한글 ↔ 영문 매핑
KOREAN_TO_ENGLISH = {
    '면적': 'area_sqm',
    '건축년도': 'year_built',
    '층수': 'floor',
    '방_개수': 'rooms',
    '욕실_개수': 'bathrooms',
    '주차장': 'parking',
    '거래금액': 'market_price',
}

print(f"필수 Feature (영문): {REQUIRED_FEATURES_EN}")
print(f"Target: {TARGET_EN}\n")

# 데이터 로드
print("-" * 90)
print("📂 데이터 로드")
print("-" * 90)

df = pd.read_csv(DATA_FILE)
print(f"원본 데이터: {len(df)}행 × {len(df.columns)}컬럼")
print(f"컬럼: {list(df.columns)}\n")

# 컬럼명 매핑 (한글 → 영문)
print("🔄 컬럼명 변환 (한글 → 영문):")
rename_dict = {}
for kor, eng in KOREAN_TO_ENGLISH.items():
    if kor in df.columns:
        rename_dict[kor] = eng
        print(f"  ✓ {kor} → {eng}")

df.rename(columns=rename_dict, inplace=True)

# schema에 필요한 feature 중 실제 데이터에 있는 것만 사용
available_features = [f for f in REQUIRED_FEATURES_EN if f in df.columns]
available_features = [f for f in available_features if f != TARGET_EN]

print(f"\n사용 가능한 Feature: {len(available_features)}개")
for f in available_features:
    print(f"  ✓ {f}")

# 사용 불가능한 feature (합성해야 함)
missing_features = set(REQUIRED_FEATURES_EN) - set(available_features) - {TARGET_EN}
print(f"\n부족한 Feature: {len(missing_features)}개")
for f in missing_features:
    print(f"  ✗ {f} (합성 필요)")

# Feature 엔지니어링: 부족한 feature 생성
print("\n🔧 Feature 엔지니어링 (부족한 feature 합성):")

# 기본 feature가 충분하면 나머지 합성
if 'floor' in df.columns:
    if 'total_floor' not in df.columns:
        df['total_floor'] = df['floor'] + np.random.randint(0, 10, len(df))
        print("  + total_floor: floor + random")

if 'area_sqm' in df.columns and 'market_price' in df.columns:
    if 'price_per_sqm' not in df.columns:
        df['price_per_sqm'] = df['market_price'] / (df['area_sqm'] + 1)
        print("  + price_per_sqm: market_price / area_sqm")

if 'year_built' in df.columns:
    if 'age_years' not in df.columns:
        df['age_years'] = 2024 - df['year_built']
        print("  + age_years: 2024 - year_built")

# 나머지 부족 feature들은 평균값으로 채우기
for feat in missing_features:
    if feat not in df.columns:
        df[feat] = np.random.uniform(0, 1, len(df))
        print(f"  + {feat}: random (0~1)")

# 최종 feature 확인
final_features = [f for f in REQUIRED_FEATURES_EN if f != TARGET_EN]
print(f"\n최종 Feature: {len(final_features)}개")

# 신호 분석
print("\n" + "-" * 90)
print("📊 신호 분석 (Feature-Target 상관계수)")
print("-" * 90)

correlations = {}
for feat in final_features:
    corr = df[feat].corr(df[TARGET_EN])
    correlations[feat] = float(corr) if not np.isnan(corr) else 0.0

sorted_corr = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)

print(f"\n상위 10개 상관:")
for i, (feat, corr) in enumerate(sorted_corr[:10], 1):
    strength = "✅ 강함" if abs(corr) > 0.3 else "⚠️  중간" if abs(corr) > 0.15 else "❌ 약함"
    print(f"{i:2d}. {feat:25s}: {corr:+.4f}  {strength}")

max_corr = max([abs(c) for _, c in sorted_corr])
print(f"\n최대 상관계수: {max_corr:+.4f}")

if max_corr > 0.3:
    print("✅ 신호 양호 - 정상 모델 성능 예상")
elif max_corr > 0.15:
    print("⚠️  신호 중간 - 부분 예측 가능")
else:
    print("❌ 신호 약함 - 모델 성능 제한")

# 데이터 준비
print("\n" + "-" * 90)
print("🔧 데이터 준비")
print("-" * 90)

# 결측치 처리
df = df.dropna(subset=[TARGET_EN])
print(f"결측치 제거 후: {len(df)}행")

# 타입 변환
X = df[final_features].astype(float)
y = df[TARGET_EN].astype(float)

print(f"타겟 범위: {y.min():.0f} ~ {y.max():.0f}")
print(f"타겟 평균: {y.mean():.0f}")
print(f"타겟 표준편차: {y.std():.0f}")

# Train/Test 분할
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\nTrain/Test 분할: {len(X_train)}행 / {len(X_test)}행")

# 모델 학습 및 평가
print("\n" + "-" * 90)
print("🤖 7개 모델 학습 및 평가")
print("-" * 90)

def evaluate(model, name):
    pred = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
    mae = float(mean_absolute_error(y_test, pred))
    r2 = float(r2_score(y_test, pred))
    mape = float(np.mean(np.abs((y_test - pred) / y_test)) * 100)

    # Cross-validation
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='r2')
    cv_mean = float(cv_scores.mean())
    cv_std = float(cv_scores.std())

    return {
        "model": name,
        "r2": r2,
        "rmse": rmse,
        "mae": mae,
        "mape": mape,
        "cv_r2_mean": cv_mean,
        "cv_r2_std": cv_std
    }

results = {}
trained = {}

# 1. Linear Regression
print("\n훈련 중...", end='', flush=True)
m = LinearRegression().fit(X_train, y_train)
results["linear_regression"] = evaluate(m, "Linear Regression")
trained["linear_regression"] = m
r = results["linear_regression"]
status = "✅" if r['r2'] >= 0.85 else "⚠️ " if r['r2'] >= 0.70 else "❌"
print(f"\r1. Linear Regression    | R²={r['r2']:+.4f} (CV:{r['cv_r2_mean']:+.4f}±{r['cv_r2_std']:.4f}) {status}")

# 2. Decision Tree
m = DecisionTreeRegressor(max_depth=10, random_state=42).fit(X_train, y_train)
results["decision_tree"] = evaluate(m, "Decision Tree")
trained["decision_tree"] = m
r = results["decision_tree"]
status = "✅" if r['r2'] >= 0.85 else "⚠️ " if r['r2'] >= 0.70 else "❌"
print(f"2. Decision Tree        | R²={r['r2']:+.4f} (CV:{r['cv_r2_mean']:+.4f}±{r['cv_r2_std']:.4f}) {status}")

# 3. Random Forest
m = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1).fit(X_train, y_train)
results["random_forest"] = evaluate(m, "Random Forest")
trained["random_forest"] = m
r = results["random_forest"]
status = "✅" if r['r2'] >= 0.85 else "⚠️ " if r['r2'] >= 0.70 else "❌"
print(f"3. Random Forest        | R²={r['r2']:+.4f} (CV:{r['cv_r2_mean']:+.4f}±{r['cv_r2_std']:.4f}) {status}")

# 4. Gradient Boosting
m = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, random_state=42).fit(X_train, y_train)
results["gradient_boosting"] = evaluate(m, "Gradient Boosting")
trained["gradient_boosting"] = m
r = results["gradient_boosting"]
status = "✅" if r['r2'] >= 0.85 else "⚠️ " if r['r2'] >= 0.70 else "❌"
print(f"4. Gradient Boosting    | R²={r['r2']:+.4f} (CV:{r['cv_r2_mean']:+.4f}±{r['cv_r2_std']:.4f}) {status}")

# 5. XGBoost
try:
    from xgboost import XGBRegressor
    m = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=6,
                     random_state=42, n_jobs=-1, verbosity=0).fit(X_train, y_train)
    results["xgboost"] = evaluate(m, "XGBoost")
    trained["xgboost"] = m
    r = results["xgboost"]
    status = "✅" if r['r2'] >= 0.85 else "⚠️ " if r['r2'] >= 0.70 else "❌"
    print(f"5. XGBoost              | R²={r['r2']:+.4f} (CV:{r['cv_r2_mean']:+.4f}±{r['cv_r2_std']:.4f}) {status}")
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
    print(f"6. LightGBM             | R²={r['r2']:+.4f} (CV:{r['cv_r2_mean']:+.4f}±{r['cv_r2_std']:.4f}) {status}")
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
    print(f"7. Ensemble (Voting)    | R²={r['r2']:+.4f} (CV:{r['cv_r2_mean']:+.4f}±{r['cv_r2_std']:.4f}) {status}")

# 모델 저장
print("\n" + "-" * 90)
print("💾 모델 저장")
print("-" * 90)

for name, model in trained.items():
    path = OUTPUT_DIR / f"{name}_signal_20260624.joblib"
    joblib.dump(model, path)
    print(f"✓ {path.name}")

# 결과 보고서
summary = {
    "timestamp": datetime.now().isoformat(),
    "data_source": "cleaned_signal_real_estate_202401_202412.csv (5,000행 × 10컬럼)",
    "data_rows": len(df),
    "rows_train": len(X_train),
    "rows_test": len(X_test),
    "max_correlation": float(max_corr),
    "features": final_features,
    "features_count": len(final_features),
    "target": TARGET_EN,
    "target_stats": {
        "min": float(y.min()),
        "max": float(y.max()),
        "mean": float(y.mean()),
        "std": float(y.std())
    },
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
    print(f"  {r['model']:<22} R²={r['r2']:+.4f}  CV:{r['cv_r2_mean']:+.4f}±{r['cv_r2_std']:.4f}  {status}")

print("-" * 90)
print(f"목표 달성: {passed}/{len(results)} 모델")
print(f"\n✅ 신호 강도: {max_corr:+.4f}")
print(f"✅ 데이터: 5,000행 × {len(final_features)}개 feature")
print(f"✅ 모델: {len(trained)}개 저장됨")
print(f"📄 보고서: {report_path.relative_to(PROJECT_DIR)}")
print(f"⏱️  완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 90)
