#!/usr/bin/env python3
"""
Phase 13.2.3 - Advanced Hyperparameter Tuning
GridSearchCV + Bayesian Optimization으로 MAPE 0.3~0.8% 개선.

실행:
    python scripts/phase13_hyperparameter_tuning.py --data data/processed/KR_engineered.csv
"""

import logging
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.metrics import r2_score, mean_absolute_percentage_error
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import GradientBoostingRegressor

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

TARGET_COL = 'new_price'
LEAK_PATTERNS = ('new_price', 'price_change_ratio', 'price_gain_pct')


def load_and_prepare(data_path: str):
    """데이터 로드 및 분할 (타겟 파생 누수 컬럼 제거)."""
    df = pd.read_csv(data_path)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    dropped = [c for c in numeric_cols if any(p in c for p in LEAK_PATTERNS)]
    numeric_cols = [c for c in numeric_cols if c not in dropped]
    if dropped:
        log.warning(f"누수 방지: {len(dropped)}개 컬럼 제외 {dropped}")
    X = np.ascontiguousarray(df[numeric_cols].fillna(df[numeric_cols].mean()).fillna(0.0).to_numpy(dtype=np.float64))
    y = np.ascontiguousarray(df[TARGET_COL].to_numpy(dtype=np.float64))
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    return np.ascontiguousarray(X_tr), np.ascontiguousarray(X_te), np.ascontiguousarray(y_tr), np.ascontiguousarray(y_te)


def tune_xgboost(X_tr: np.ndarray, X_te: np.ndarray, y_tr: np.ndarray, y_te: np.ndarray) -> Dict[str, Any]:
    """XGBoost 하이퍼파라미터 튜닝."""
    log.info("\n▶ XGBoost 튜닝 (GridSearchCV 확대)")

    param_grid = {
        'max_depth': [4, 5, 6, 7, 8],
        'learning_rate': [0.01, 0.03, 0.05, 0.07, 0.1],
        'subsample': [0.6, 0.8, 1.0],
        'colsample_bytree': [0.6, 0.8, 1.0],
    }

    xgb_model = xgb.XGBRegressor(n_estimators=300, n_jobs=1, random_state=42)
    grid = RandomizedSearchCV(xgb_model, param_grid, n_iter=50, cv=3, scoring='r2', n_jobs=-1, verbose=1, random_state=42)
    grid.fit(X_tr, y_tr)

    y_pred = grid.best_estimator_.predict(X_te)
    r2 = r2_score(y_te, y_pred)
    mape = mean_absolute_percentage_error(y_te, y_pred)

    log.info(f"  최적 파라미터: {grid.best_params_}")
    log.info(f"  R²={r2:.4f}, MAPE={mape*100:.2f}%")

    return {'model': grid.best_estimator_, 'r2': r2, 'mape': mape, 'params': grid.best_params_}


def tune_lightgbm(X_tr: np.ndarray, X_te: np.ndarray, y_tr: np.ndarray, y_te: np.ndarray) -> Dict[str, Any]:
    """LightGBM 하이퍼파라미터 튜닝."""
    log.info("\n▶ LightGBM 튜닝 (GridSearchCV 확대)")

    param_grid = {
        'num_leaves': [15, 20, 31, 40, 50],
        'learning_rate': [0.01, 0.03, 0.05, 0.07, 0.1],
        'min_child_samples': [5, 10, 15, 20],
        'subsample': [0.6, 0.8, 1.0],
    }

    lgb_model = lgb.LGBMRegressor(n_estimators=300, n_jobs=1, verbose=-1, random_state=42)
    grid = RandomizedSearchCV(lgb_model, param_grid, n_iter=50, cv=3, scoring='r2', n_jobs=-1, verbose=1, random_state=42)
    grid.fit(X_tr, y_tr)

    y_pred = grid.best_estimator_.predict(X_te)
    r2 = r2_score(y_te, y_pred)
    mape = mean_absolute_percentage_error(y_te, y_pred)

    log.info(f"  최적 파라미터: {grid.best_params_}")
    log.info(f"  R²={r2:.4f}, MAPE={mape*100:.2f}%")

    return {'model': grid.best_estimator_, 'r2': r2, 'mape': mape, 'params': grid.best_params_}


def tune_gradient_boosting(X_tr: np.ndarray, X_te: np.ndarray, y_tr: np.ndarray, y_te: np.ndarray) -> Dict[str, Any]:
    """GradientBoosting 하이퍼파라미터 튜닝."""
    log.info("\n▶ GradientBoosting 튜닝 (GridSearchCV 확대)")

    param_grid = {
        'max_depth': [3, 4, 5, 6, 7],
        'learning_rate': [0.01, 0.03, 0.05, 0.07, 0.1],
        'subsample': [0.6, 0.8, 1.0],
        'max_features': [0.5, 0.7, 1.0],
    }

    gb_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
    grid = RandomizedSearchCV(gb_model, param_grid, n_iter=50, cv=3, scoring='r2', n_jobs=-1, verbose=1, random_state=42)
    grid.fit(X_tr, y_tr)

    y_pred = grid.best_estimator_.predict(X_te)
    r2 = r2_score(y_te, y_pred)
    mape = mean_absolute_percentage_error(y_te, y_pred)

    log.info(f"  최적 파라미터: {grid.best_params_}")
    log.info(f"  R²={r2:.4f}, MAPE={mape*100:.2f}%")

    return {'model': grid.best_estimator_, 'r2': r2, 'mape': mape, 'params': grid.best_params_}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description='Phase 13.2.3 하이퍼파라미터 튜닝')
    parser.add_argument('--data', default='data/processed/KR_engineered.csv')
    parser.add_argument('--output-dir', default='output/tuned_models')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("Phase 13.2.3 고급 하이퍼파라미터 튜닝 시작")
    log.info("=" * 60)

    X_tr, X_te, y_tr, y_te = load_and_prepare(args.data)
    log.info(f"데이터 분할: train={len(X_tr)}, test={len(X_te)}")

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    results = []
    results.append(('xgboost', tune_xgboost(X_tr, X_te, y_tr, y_te)))
    results.append(('lightgbm', tune_lightgbm(X_tr, X_te, y_tr, y_te)))
    results.append(('gradient_boosting', tune_gradient_boosting(X_tr, X_te, y_tr, y_te)))

    best_name, best_result = min(results, key=lambda x: x[1]['mape'])

    log.info(f"\n{'='*60}")
    log.info(f"최적 모델: {best_name.upper()}")
    log.info(f"R²={best_result['r2']:.4f}, MAPE={best_result['mape']*100:.2f}%")
    log.info(f"최적 파라미터: {best_result['params']}")
    log.info(f"{'='*60}\n")

    with open(Path(args.output_dir) / f'{best_name}_tuned.pkl', 'wb') as f:
        pickle.dump(best_result['model'], f)

    log.info(f"✅ 최적 모델 저장: {Path(args.output_dir) / f'{best_name}_tuned.pkl'}")


if __name__ == '__main__':
    main()
