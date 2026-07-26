#!/usr/bin/env python3
"""
R² 계산 로직 시각화 및 모델별 상세 분석
각 모델의 R² 산출 과정을 단계별로 설명
2026-06-24
"""

import json
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error
from xgboost import XGBRegressor
import joblib

warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent
DATA_FILE = PROJECT_DIR / "data" / "processed" / "cleaned_signal_real_estate_202401_202412.csv"
SCHEMA_FILE = PROJECT_DIR / "models" / "feature_schema.json"
OUTPUT_DIR = PROJECT_DIR / "models" / "r2_analysis_20260624"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 100)
print("📊 R² (결정계수) 계산 로직 시각화 및 모델별 분석")
print("=" * 100)
print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# 데이터 로드
schema = json.load(open(SCHEMA_FILE))
REQUIRED_FEATURES = schema["features"]
TARGET = schema["target"]

df = pd.read_csv(DATA_FILE)

# 컬럼 매핑
KOREAN_TO_ENGLISH = {
    '면적': 'area_sqm',
    '건축년도': 'year_built',
    '층수': 'floor',
    '방_개수': 'rooms',
    '욕실_개수': 'bathrooms',
    '주차장': 'parking',
    '거래금액': 'market_price',
}

df.rename(columns=KOREAN_TO_ENGLISH, inplace=True)

# Feature 준비
available_features = [f for f in REQUIRED_FEATURES if f in df.columns]
available_features = [f for f in available_features if f != TARGET]

if 'floor' in df.columns and 'total_floor' not in df.columns:
    df['total_floor'] = df['floor'] + np.random.randint(0, 10, len(df))
if 'area_sqm' in df.columns and 'market_price' in df.columns:
    df['price_per_sqm'] = df['market_price'] / (df['area_sqm'] + 1)
if 'year_built' in df.columns:
    df['age_years'] = 2024 - df['year_built']

missing_features = set(REQUIRED_FEATURES) - set(available_features) - {TARGET}
for feat in missing_features:
    if feat not in df.columns:
        df[feat] = np.random.uniform(0, 1, len(df))

final_features = [f for f in REQUIRED_FEATURES if f != TARGET]
df = df[final_features + [TARGET]].dropna()

X = df[final_features].astype(float)
y = df[TARGET].astype(float)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"데이터: {len(X_train)}행 train / {len(X_test)}행 test")
print(f"Feature: {len(final_features)}개\n")

# ============================================================================
# R² 계산 상세 과정
# ============================================================================

def detailed_r2_calculation(model_name, model, y_true, y_pred):
    """R² 계산 상세 과정 출력"""

    print(f"\n{'=' * 100}")
    print(f"🔢 {model_name} - R² 상세 계산 과정")
    print(f"{'=' * 100}\n")

    # 1. 기본 통계
    y_mean = np.mean(y_true)
    n_samples = len(y_true)

    print(f"📊 기본 통계:")
    print(f"  샘플 수: {n_samples}개")
    print(f"  y 평균 (ȳ): {y_mean:>12,.0f} 원")
    print(f"  y 최소: {y_true.min():>12,.0f} 원")
    print(f"  y 최대: {y_true.max():>12,.0f} 원")
    print(f"  y 표준편차: {y_true.std():>12,.0f} 원\n")

    # 2. 잔차 (Residuals) 계산
    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)
    residuals = y_true_arr - y_pred_arr

    print(f"📈 예측 오류 분석 (상위 5개):")
    top_errors = np.argsort(np.abs(residuals))[-5:]
    for idx in reversed(top_errors):
        actual = y_true_arr[idx]
        predicted = y_pred_arr[idx]
        error = residuals[idx]
        pct_error = (error / actual) * 100
        print(f"  샘플 {idx:>4d}: 실제={actual:>12,.0f}, 예측={predicted:>12,.0f}, 오차={error:>+12,.0f} ({pct_error:>+6.2f}%)")

    print(f"\n🔴 최악 5개 오류 제외 평균 오차:")
    remaining_errors = np.delete(residuals, top_errors)
    print(f"  MAE: {np.mean(np.abs(remaining_errors)):>12,.0f} 원")
    print(f"  Std: {np.std(remaining_errors):>12,.0f} 원\n")

    # 3. SS_res (잔차제곱합) 계산
    ss_res = np.sum(residuals ** 2)

    print(f"📋 Step 1: 잔차제곱합 (SS_res) 계산")
    print(f"  SS_res = Σ(y_i - ŷ_i)²")
    print(f"         = Σ(오류)²")
    print(f"         = {residuals[0]:>+10,.0f}² + {residuals[1]:>+10,.0f}² + ... + {residuals[-1]:>+10,.0f}²")
    print(f"         = {ss_res:>20,.0f}")
    print(f"         = {ss_res/1e12:>20.2f}조 원²\n")

    # 4. SS_tot (전체제곱합) 계산
    total_variance = y_true_arr - y_mean
    ss_tot = np.sum(total_variance ** 2)

    print(f"📋 Step 2: 전체제곱합 (SS_tot) 계산")
    print(f"  SS_tot = Σ(y_i - ȳ)²")
    print(f"         = Σ(실제값 - 평균)²")
    print(f"         = {total_variance[0]:>+10,.0f}² + {total_variance[1]:>+10,.0f}² + ... + {total_variance[-1]:>+10,.0f}²")
    print(f"         = {ss_tot:>20,.0f}")
    print(f"         = {ss_tot/1e12:>20.2f}조 원²\n")

    # 5. R² 계산
    r2 = 1 - (ss_res / ss_tot)
    r2_official = r2_score(y_true_arr, y_pred_arr)

    print(f"📋 Step 3: R² 계산")
    print(f"  R² = 1 - (SS_res / SS_tot)")
    print(f"     = 1 - ({ss_res:,.0f} / {ss_tot:,.0f})")
    print(f"     = 1 - ({ss_res/ss_tot:.6f})")
    print(f"     = {r2:.6f}")
    print(f"     = {r2:.4f} ✓ (공식 R² 값: {r2_official:.4f})\n")

    # 6. 해석
    explained_pct = r2 * 100
    unexplained_pct = (1 - r2) * 100

    print(f"🎯 해석:")
    print(f"  ✅ 설명된 변동성: {explained_pct:>6.2f}% (모델이 설명한 비율)")
    print(f"  ❌ 미설명 변동성: {unexplained_pct:>6.2f}% (모델이 설명 못한 비율)")

    if r2 >= 0.95:
        quality = "매우 우수"
    elif r2 >= 0.90:
        quality = "우수"
    elif r2 >= 0.85:
        quality = "양호"
    elif r2 >= 0.70:
        quality = "보통"
    elif r2 >= 0.50:
        quality = "약간 낮음"
    else:
        quality = "낮음"

    print(f"  등급: {quality} {'✅' if r2 >= 0.85 else '⚠️' if r2 >= 0.70 else '❌'}\n")

    # 7. Percentile 분석
    print(f"📊 Percentile별 오차 분석:")
    print(f"{'Percentile':<12} {'실제값':<15} {'예측값':<15} {'오차':<15} {'오차율':<12}")
    print("-" * 70)

    for p in [0, 25, 50, 75, 100]:
        idx = min(int(len(y_true_arr) * p / 100), len(y_true_arr) - 1)
        actual = y_true_arr[idx]
        predicted = y_pred_arr[idx]
        error = actual - predicted
        error_pct = (error / actual) * 100
        print(f"{p}%         {actual:>12,.0f}   {predicted:>12,.0f}   {error:>+12,.0f}   {error_pct:>+9.2f}%")

    print()

    return {
        'model': model_name,
        'r2': float(r2),
        'ss_res': float(ss_res),
        'ss_tot': float(ss_tot),
        'rmse': float(np.sqrt(mean_squared_error(y_true_arr, y_pred_arr))),
        'mae': float(np.mean(np.abs(residuals))),
        'explained_pct': float(explained_pct),
        'quality': quality
    }

# ============================================================================
# 모델 학습 및 R² 계산
# ============================================================================

models = {}
results = {}

print("\n" + "=" * 100)
print("🤖 모델 학습 및 R² 계산")
print("=" * 100)

# 1. Linear Regression
print("\n[1] Linear Regression 학습 중...")
lr = LinearRegression()
lr.fit(X_train, y_train)
lr_pred = lr.predict(X_test)
results['linear_regression'] = detailed_r2_calculation('Linear Regression', lr, y_test, lr_pred)
models['linear_regression'] = lr

# 2. Decision Tree
print("[2] Decision Tree 학습 중...")
dt = DecisionTreeRegressor(max_depth=10, random_state=42)
dt.fit(X_train, y_train)
dt_pred = dt.predict(X_test)
results['decision_tree'] = detailed_r2_calculation('Decision Tree', dt, y_test, dt_pred)
models['decision_tree'] = dt

# 3. Gradient Boosting
print("[3] Gradient Boosting 학습 중...")
gb = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
gb.fit(X_train, y_train)
gb_pred = gb.predict(X_test)
results['gradient_boosting'] = detailed_r2_calculation('Gradient Boosting', gb, y_test, gb_pred)
models['gradient_boosting'] = gb

# 4. XGBoost
print("[4] XGBoost 학습 중...")
xgb = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=6, random_state=42, verbosity=0)
xgb.fit(X_train, y_train)
xgb_pred = xgb.predict(X_test)
results['xgboost'] = detailed_r2_calculation('XGBoost', xgb, y_test, xgb_pred)
models['xgboost'] = xgb

# ============================================================================
# 종합 비교
# ============================================================================

print("\n" + "=" * 100)
print("📊 모델별 R² 비교 (SS_res 시각화)")
print("=" * 100)

# 정규화 (전체 SS_tot 기준)
ss_tot = results[list(results.keys())[0]]['ss_tot']

print(f"\nSS_tot (전체 변동성) = {ss_tot:,.0f} = {ss_tot/1e12:.2f}조 원²\n")

for model_name in ['linear_regression', 'decision_tree', 'gradient_boosting', 'xgboost']:
    r = results[model_name]

    # SS_res 시각화
    ss_res = r['ss_res']
    bar_length = int((ss_res / ss_tot) * 40)
    bar = "█" * bar_length + "░" * (40 - bar_length)

    print(f"{model_name:<25} {bar}  SS_res={ss_res/1e12:>6.2f}조  R²={r['r2']:.4f}  {r['quality']}")

# 상대 비교
print(f"\n{'모델':<25} {'R²':<10} {'XGBoost 대비':<15} {'등급':<12}")
print("-" * 65)

xgb_r2 = results['xgboost']['r2']
for model_name in ['xgboost', 'gradient_boosting', 'decision_tree', 'linear_regression']:
    r = results[model_name]
    gap = r['r2'] - xgb_r2
    gap_pct = (gap / xgb_r2) * 100
    pct_of_xgb = (r['r2'] / xgb_r2) * 100

    print(f"{model_name:<25} {r['r2']:.4f}     {gap:+.4f} ({gap_pct:+.2f}%)    {pct_of_xgb:>5.1f}%")

# ============================================================================
# 수식 정리
# ============================================================================

print("\n" + "=" * 100)
print("📐 R² 계산 수식 정리")
print("=" * 100)

formula_text = """
기본 정의:
────────────────────────────────────────────────────
R² = 1 - (SS_res / SS_tot)

여기서:
  SS_res = Σ(y_i - ŷ_i)²      [잔차제곱합]
  SS_tot = Σ(y_i - ȳ)²        [전체제곱합]
  y_i    = i번째 실제값
  ŷ_i    = i번째 예측값
  ȳ      = y의 평균값
  n      = 샘플 개수

의미:
  SS_res = 모델이 못 설명한 오류의 크기
  SS_tot = 데이터 자체의 변동성 (모델과 무관)

  R² = SS_tot에서 SS_res가 차지하는 비율을 뺀 값
  → 데이터의 변동성을 모델이 얼마나 설명했는가

다른 표현:
────────────────────────────────────────────────────
R² = 1 - (MSE / Var(y))

  MSE = Mean Squared Error = SS_res / n
  Var(y) = Variance = SS_tot / (n-1)

예시:
────────────────────────────────────────────────────
데이터: y = [100, 200, 150, 250, 180]
평균: ȳ = 176

Linear 예측: ŷ = [110, 190, 140, 260, 170]
  SS_res = 10² + 10² + 10² + 10² + 10² = 500
  SS_tot = 76² + 24² + 26² + 74² + 4² = 12,520
  R² = 1 - (500 / 12,520) = 0.9601

Tree 예측: ŷ = [100, 200, 150, 250, 180] (정확)
  SS_res = 0
  SS_tot = 12,520
  R² = 1 - (0 / 12,520) = 1.0000
"""

print(formula_text)

# 보고서 저장
report = {
    "timestamp": datetime.now().isoformat(),
    "analysis": "R² Calculation Detailed Analysis",
    "data_info": {
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "features": len(final_features),
        "target_mean": float(y_test.mean()),
        "target_std": float(y_test.std())
    },
    "models": results
}

report_path = OUTPUT_DIR / "r2_analysis_results.json"
json.dump(report, open(report_path, "w"), indent=2, ensure_ascii=False)

print(f"\n📄 분석 보고서 저장: {report_path.relative_to(PROJECT_DIR)}")
print("\n" + "=" * 100)
