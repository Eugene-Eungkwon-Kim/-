#!/usr/bin/env python3
"""
6-모델 앙상블 구축 및 성능 평가
(Linear Regression, Decision Tree, Random Forest, Gradient Boosting, XGBoost, LightGBM)
"""

import numpy as np
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

def temporal_split(df, time_col, ratios=(0.7, 0.15, 0.15)):
    """시간순 정렬 후 train/val/test 분할."""
    df = df.sort_values(time_col).reset_index(drop=True)
    n = len(df)
    a = int(n * ratios[0])
    b = int(n * (ratios[0] + ratios[1]))
    return df.iloc[:a], df.iloc[a:b], df.iloc[b:]

def build_ensemble_model(data_path, target_col, time_col):
    """6-모델 앙상블 구축 및 평가"""

    print("=" * 80)
    print("🚀 6-모델 앙상블 구축 및 평가")
    print("=" * 80)

    # 데이터 로드
    df = pd.read_csv(data_path)
    print(f"✅ 데이터 로드: {len(df):,}행\n")

    # 시간순 분할
    train, val, test = temporal_split(df, time_col)

    def prepare_data(part):
        X = part.select_dtypes(include=[np.number]).drop(columns=[target_col] if target_col in part.columns else [])
        X = X.fillna(train.select_dtypes(include=[np.number]).median())
        y = part[target_col]
        return X, y

    X_train, y_train = prepare_data(train)
    X_val, y_val = prepare_data(val)
    X_test, y_test = prepare_data(test)

    print(f"데이터 분할:")
    print(f"  Train: {len(X_train):,}  Val: {len(X_val):,}  Test: {len(X_test):,}")
    print(f"  특성: {X_train.shape[1]}개\n")

    # 모델 정의
    models = {
        '1. Linear Regression': LinearRegression(),
        '2. Decision Tree': DecisionTreeRegressor(max_depth=10, random_state=42),
        '3. Random Forest': RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42),
        '4. Gradient Boosting': GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, random_state=42),
    }

    if HAS_XGBOOST:
        models['5. XGBoost'] = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42, verbosity=0)

    if HAS_LIGHTGBM:
        models['6. LightGBM'] = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.1, random_state=42, verbose=-1)

    # 모델 학습 및 평가
    results = {}
    predictions = {}

    print("=" * 80)
    print("📊 모델 성능 비교")
    print("=" * 80)

    for name, model in models.items():
        try:
            # 학습
            model.fit(X_train, y_train)

            # 예측
            y_pred_test = model.predict(X_test)

            # 평가
            r2 = r2_score(y_test, y_pred_test)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
            mae = mean_absolute_error(y_test, y_pred_test)

            results[name] = {
                'r2': float(r2),
                'rmse': float(rmse),
                'mae': float(mae),
                'status': '✅'
            }
            predictions[name] = y_pred_test

            print(f"{name}")
            print(f"  R² = {r2:.4f}  RMSE = {rmse:.1f}  MAE = {mae:.1f}")
            print()
        except Exception as e:
            print(f"{name} — ❌ 오류: {e}\n")
            results[name] = {'status': '❌', 'error': str(e)}

    # 앙상블 예측 (평균)
    print("=" * 80)
    print("🎯 앙상블 예측 (가중 평균)")
    print("=" * 80)

    valid_predictions = {k: v for k, v in predictions.items() if isinstance(v, np.ndarray)}
    if valid_predictions:
        ensemble_pred = np.mean(list(valid_predictions.values()), axis=0)
        ensemble_r2 = r2_score(y_test, ensemble_pred)
        ensemble_rmse = np.sqrt(mean_squared_error(y_test, ensemble_pred))
        ensemble_mae = mean_absolute_error(y_test, ensemble_pred)

        results['ENSEMBLE (Average)'] = {
            'r2': float(ensemble_r2),
            'rmse': float(ensemble_rmse),
            'mae': float(ensemble_mae),
            'status': '✅',
            'n_models': len(valid_predictions)
        }

        print(f"ENSEMBLE (Average of {len(valid_predictions)} models)")
        print(f"  R² = {ensemble_r2:.4f}  RMSE = {ensemble_rmse:.1f}  MAE = {ensemble_mae:.1f}")
        print()

    # 결과 저장
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f'ensemble_evaluation_{datetime.now():%Y%m%d_%H%M%S}.json'
    output_file.write_text(json.dumps({
        'timestamp': datetime.now().isoformat(),
        'data': str(data_path),
        'target': target_col,
        'time_column': time_col,
        'train_size': len(X_train),
        'val_size': len(X_val),
        'test_size': len(X_test),
        'n_features': X_train.shape[1],
        'results': results
    }, indent=2, ensure_ascii=False))

    print("=" * 80)
    print(f"📁 결과 저장: {output_file}")
    print("=" * 80)

    # 최고 성능 모델
    best_model = max([(k, v['r2']) for k, v in results.items() if 'r2' in v], key=lambda x: x[1])
    print(f"\n🏆 최고 성능: {best_model[0]} (R² = {best_model[1]:.4f})")

if __name__ == "__main__":
    build_ensemble_model(
        data_path='avm_project/data/raw/signal_real_estate_202401_202412.csv',
        target_col='거래금액',
        time_col='거래일'
    )
