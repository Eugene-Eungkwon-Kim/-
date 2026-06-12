#!/usr/bin/env python3
"""
Phase 6-4-B: 극적 하이퍼파라미터 재튜닝
목표: ±3% 정확도 최적화를 위한 극적 조정
"""

import sys
from pathlib import Path
import logging
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    logger.info("\n" + "="*60)
    logger.info("Phase 6-4-B: 극적 하이퍼파라미터 재튜닝")
    logger.info("="*60)

    # 데이터 로드
    df_original = pd.read_csv(project_root / 'data' / 'preprocessed_data.csv')
    df_advanced = pd.read_csv(project_root / 'data' / 'preprocessed_data_advanced_features.csv')

    with open(project_root / 'models' / 'advanced_features_list.txt', 'r') as f:
        feature_list = [line.strip() for line in f.readlines()]

    X_features = df_advanced[feature_list].fillna(0)
    y_original = df_original['hammer_price']

    logger.info(f"\n데이터: {len(X_features)} rows × {len(X_features.columns)} features")

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_features, y_original, test_size=0.2, random_state=42
    )

    logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

    logger.info(f"\n[1/2] GridSearchCV로 하이퍼파라미터 탐색...")

    # 극적 하이퍼파라미터 조합
    param_grid = {
        'learning_rate': [0.01, 0.03, 0.05, 0.1],
        'max_depth': [3, 4, 5, 6],
        'reg_lambda': [0.5, 1.0, 2.0, 5.0],
        'subsample': [0.5, 0.7, 0.9],
        'colsample_bytree': [0.6, 0.8, 0.95],
    }

    base_model = xgb.XGBRegressor(
        n_estimators=200,
        min_child_weight=1,
        random_state=42,
        n_jobs=-1,
        verbose=0
    )

    logger.info(f"검색 공간: {4 * 4 * 4 * 3 * 3} 조합")

    grid_search = GridSearchCV(
        base_model,
        param_grid,
        cv=5,
        scoring='r2',
        n_jobs=-1,
        verbose=0
    )

    grid_search.fit(X_train, y_train)

    best_model = grid_search.best_estimator_
    best_params = grid_search.best_params_

    logger.info(f"\n최적 하이퍼파라미터:")
    for key, value in best_params.items():
        logger.info(f"   {key}: {value}")

    logger.info(f"\n[2/2] 최적 모델 평가...")

    y_pred_train = best_model.predict(X_train)
    y_pred_test = best_model.predict(X_test)

    r2_train = r2_score(y_train, y_pred_train)
    r2_test = r2_score(y_test, y_pred_test)
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
    mae_test = mean_absolute_error(y_test, y_pred_test)
    mape_test = np.mean(np.abs((y_test - y_pred_test) / y_test)) * 100

    # ±3% 달성률
    within_3pct = (np.abs((y_test - y_pred_test) / y_test) <= 0.03).sum()
    pct_within_3 = 100 * within_3pct / len(y_test)

    logger.info(f"\n성능 메트릭:")
    logger.info(f"   Train R²:      {r2_train:.4f}")
    logger.info(f"   Test R²:       {r2_test:.4f}")
    logger.info(f"   RMSE:          Won {rmse_test:,.0f}")
    logger.info(f"   MAE:           Won {mae_test:,.0f}")
    logger.info(f"   MAPE:          {mape_test:.2f}%")
    logger.info(f"\n   ±3% 범위 내:   {within_3pct}/{len(y_test)} ({pct_within_3:.1f}%)")

    logger.info(f"\n개선도 (vs Phase 2 19.56%):")
    improvement = 19.56 - mape_test
    logger.info(f"   {improvement:+.2f}%")

    # 특성별 중요도 상위 10개
    logger.info(f"\n상위 10개 중요 특성:")
    feature_importance = pd.DataFrame({
        'feature': X_train.columns,
        'importance': best_model.feature_importances_
    }).sort_values('importance', ascending=False)

    for idx, row in feature_importance.head(10).iterrows():
        logger.info(f"   {row['feature']}: {row['importance']:.4f}")

    # 모델 저장
    logger.info(f"\n모델 저장...")

    models_dir = project_root / 'models'
    model_path = models_dir / 'advanced_v3_tuned.pkl'
    joblib.dump(best_model, model_path)
    logger.info(f"   ✓ {model_path}")

    # 특성 목록 저장
    features_path = models_dir / 'advanced_v3_features.txt'
    with open(features_path, 'w') as f:
        for feat in X_train.columns:
            f.write(f"{feat}\n")
    logger.info(f"   ✓ {features_path}")

    # 메타데이터 저장
    import json
    from datetime import datetime

    metadata = {
        'model_name': 'XGBoost Extreme Tuning',
        'r2_train': float(r2_train),
        'r2_test': float(r2_test),
        'rmse': float(rmse_test),
        'mae': float(mae_test),
        'mape': float(mape_test),
        'within_3pct': float(pct_within_3),
        'improvement_vs_phase2': float(improvement),
        'total_features': len(X_train.columns),
        'hyperparameters': {k: float(v) if isinstance(v, (int, np.integer)) else v
                           for k, v in best_params.items()},
        'created_at': datetime.now().isoformat(),
        'version': 'v3_extreme_tuning',
    }

    metadata_path = models_dir / 'advanced_v3_metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"   ✓ {metadata_path}")

    logger.info(f"\n" + "="*60)
    logger.info(f"✅ Phase 6-4-B 완료!")
    logger.info(f"="*60)

    return {
        'r2_test': r2_test,
        'mape': mape_test,
        'within_3pct': pct_within_3,
    }


if __name__ == "__main__":
    result = main()
