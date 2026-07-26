#!/usr/bin/env python3
"""
Step 3: 실거래 데이터로 모델 전체 재학습 및 성능 평가
자동화된 파이프라인
"""

import numpy as np
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import joblib
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
    """시간순 분할 (미래 누수 방지)"""
    df = df.sort_values(time_col).reset_index(drop=True)
    n = len(df)
    a = int(n * ratios[0])
    b = int(n * (ratios[0] + ratios[1]))
    return df.iloc[:a], df.iloc[a:b], df.iloc[b:]

def retrain_models(data_path, target_col, time_col):
    """
    실거래 데이터로 6-모델 앙상블 재학습
    """

    print("=" * 100)
    print("🚀 Step 3: 실거래 데이터로 모델 재학습")
    print("=" * 100)

    # 데이터 로드
    print(f"\n📂 데이터 로드: {data_path}")
    df = pd.read_csv(data_path)
    print(f"   행: {len(df):,}  컬럼: {len(df.columns)}")

    # 시간순 분할
    print(f"\n📊 시간순 분할 (70/15/15)")
    train, val, test = temporal_split(df, time_col)
    print(f"   Train: {len(train):,}  Val: {len(val):,}  Test: {len(test):,}")

    # 특성-타겟 준비
    def prepare_data(part):
        X = part.select_dtypes(include=[np.number]).drop(
            columns=[target_col] if target_col in part.columns else [],
            errors='ignore'
        )
        X = X.fillna(train.select_dtypes(include=[np.number]).median())
        y = part[target_col]
        return X, y

    X_train, y_train = prepare_data(train)
    X_val, y_val = prepare_data(val)
    X_test, y_test = prepare_data(test)

    print(f"\n✅ 특성: {X_train.shape[1]}개")
    print(f"   특성명: {list(X_train.columns)}")

    # 모델 정의
    models = {
        '1. Linear Regression': LinearRegression(),
        '2. Decision Tree': DecisionTreeRegressor(max_depth=10, random_state=42),
        '3. Random Forest': RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1),
        '4. Gradient Boosting': GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, random_state=42),
    }

    if HAS_XGBOOST:
        models['5. XGBoost'] = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42, verbosity=0)

    if HAS_LIGHTGBM:
        models['6. LightGBM'] = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.1, random_state=42, verbose=-1)

    # 모델 학습 및 평가
    print("\n" + "=" * 100)
    print("🎯 모델 성능 평가 (테스트셋 기준)")
    print("=" * 100)

    results = {}
    predictions = {}
    model_paths = {}

    for name, model in models.items():
        try:
            print(f"\n📍 {name}")

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
            }
            predictions[name] = y_pred_test

            print(f"   ✅ R² = {r2:.4f}  RMSE = {rmse:,.0f}  MAE = {mae:,.0f}")

            # 모델 저장
            model_dir = Path('avm_project/models')
            model_dir.mkdir(parents=True, exist_ok=True)

            model_file = model_dir / f"{name.split('. ')[1]}_model_real_2024.joblib"
            joblib.dump(model, model_file)
            model_paths[name] = str(model_file)
            print(f"   💾 저장: {model_file}")

        except Exception as e:
            print(f"   ❌ 오류: {e}")
            results[name] = {'status': 'error', 'error': str(e)}

    # 앙상블 (평균)
    print(f"\n" + "=" * 100)
    print("🎯 앙상블 예측 (평균)")
    print("=" * 100)

    valid_predictions = {k: v for k, v in predictions.items() if isinstance(v, np.ndarray)}
    if valid_predictions:
        ensemble_pred = np.mean(list(valid_predictions.values()), axis=0)
        ensemble_r2 = r2_score(y_test, ensemble_pred)
        ensemble_rmse = np.sqrt(mean_squared_error(y_test, ensemble_pred))
        ensemble_mae = mean_absolute_error(y_test, ensemble_pred)

        print(f"\n🎯 ENSEMBLE (평균 of {len(valid_predictions)} 모델)")
        print(f"   ✅ R² = {ensemble_r2:.4f}  RMSE = {ensemble_rmse:,.0f}  MAE = {ensemble_mae:,.0f}")

        results['ENSEMBLE'] = {
            'r2': float(ensemble_r2),
            'rmse': float(ensemble_rmse),
            'mae': float(ensemble_mae),
            'n_models': len(valid_predictions)
        }

        # 앙상블 모델 저장
        ensemble_dir = Path('avm_project/models')
        ensemble_file = ensemble_dir / 'production_model_real_2024.joblib'

        # 메타 모델로 저장
        ensemble_meta = {
            'type': 'ensemble_average',
            'models': model_paths,
            'timestamp': datetime.now().isoformat(),
            'r2': float(ensemble_r2)
        }
        joblib.dump(ensemble_meta, ensemble_file)
        print(f"   💾 프로덕션 모델 저장: {ensemble_file}")

    # 최종 보고서
    print(f"\n" + "=" * 100)
    print("📋 최종 성능 요약")
    print("=" * 100)

    summary_df = pd.DataFrame([
        (name, data.get('r2', 'N/A'), data.get('rmse', 'N/A'))
        for name, data in results.items()
    ], columns=['모델', 'R²', 'RMSE'])

    print("\n" + summary_df.to_string(index=False))

    # 최고 성능 모델
    best_model = max([(k, v.get('r2', 0)) for k, v in results.items() if 'r2' in v], key=lambda x: x[1])
    print(f"\n🏆 최고 성능: {best_model[0]} (R² = {best_model[1]:.4f})")

    # 배포 준비 확인
    if ensemble_r2 >= 0.80:
        print(f"\n✅ 배포 준비: R² ≥ 0.80 달성")
        print(f"   다음 단계: python scripts/phase_c_step4_deploy.py")
    elif ensemble_r2 >= 0.75:
        print(f"\n⚠️ 조건부 배포 가능: R² ≥ 0.75")
        print(f"   권장: 추가 특성 검토 후 재학습")
    else:
        print(f"\n❌ 배포 보류: R² < 0.75")
        print(f"   필요: 데이터 품질 재검토 또는 추가 특성")

    # 결과 저장
    output_file = Path('output') / f'retrain_results_{datetime.now():%Y%m%d_%H%M%S}.json'
    output_file.parent.mkdir(exist_ok=True)

    output_file.write_text(json.dumps({
        'timestamp': datetime.now().isoformat(),
        'data': str(data_path),
        'target': target_col,
        'n_train': len(X_train),
        'n_features': X_train.shape[1],
        'results': results,
    }, indent=2, ensure_ascii=False))

    print(f"\n📁 결과 저장: {output_file}")

    return ensemble_r2 >= 0.80

if __name__ == "__main__":
    success = retrain_models(
        data_path='avm_project/data/raw/real_estate_2024.csv',
        target_col='거래금액',
        time_col='거래일'
    )
    exit(0 if success else 1)
