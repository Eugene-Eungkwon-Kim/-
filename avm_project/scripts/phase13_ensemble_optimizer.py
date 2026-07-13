#!/usr/bin/env python3
"""
Phase 13.2.2 - Ensemble Model Optimization
3개 모델 → 5개 모델 앙상블로 MAPE 0.5~1% 개선.

Stacking/Voting으로 최적 가중치 산정.

실행:
    python scripts/phase13_ensemble_optimizer.py --data data/processed/KR_engineered.csv
"""

import logging
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, VotingRegressor, StackingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import r2_score, mean_absolute_percentage_error
import xgboost as xgb
import lightgbm as lgb

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']
TARGET_COL = 'new_price'


def load_and_prepare(data_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """데이터 로드 및 분할."""
    df = pd.read_csv(data_path)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if TARGET_COL in numeric_cols:
        numeric_cols.remove(TARGET_COL)
    X = np.ascontiguousarray(df[numeric_cols].fillna(df[numeric_cols].mean()).to_numpy(dtype=np.float64))
    y = np.ascontiguousarray(df[TARGET_COL].to_numpy(dtype=np.float64))
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    return np.ascontiguousarray(X_tr), np.ascontiguousarray(X_te), np.ascontiguousarray(y_tr), np.ascontiguousarray(y_te)


def create_base_models() -> Dict[str, object]:
    """5개 기본 모델 생성."""
    return {
        'xgboost': xgb.XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.05,
                                     colsample_bytree=0.8, subsample=0.8, n_jobs=1, random_state=42),
        'lightgbm': lgb.LGBMRegressor(n_estimators=300, max_depth=6, learning_rate=0.05,
                                       colsample_bytree=0.8, subsample=0.8, n_jobs=1, verbose=-1, random_state=42),
        'gradient_boosting': xgb.XGBRegressor(n_estimators=300, max_depth=5, learning_rate=0.05,
                                               tree_method='hist', n_jobs=1, random_state=42),
        'random_forest': RandomForestRegressor(n_estimators=300, max_depth=15, n_jobs=-1,
                                               min_samples_split=5, random_state=42),
        'extra_trees': ExtraTreesRegressor(n_estimators=300, max_depth=15, n_jobs=-1,
                                           min_samples_split=5, random_state=42),
    }


def evaluate_voting(X_tr: np.ndarray, X_te: np.ndarray, y_tr: np.ndarray, y_te: np.ndarray) -> Dict[str, float]:
    """Voting Regressor 평가."""
    log.info("\n▶ Voting Regressor (균등 가중치)")
    models = create_base_models()
    estimators = [(name, model) for name, model in models.items()]

    voting = VotingRegressor(estimators=estimators)
    voting.fit(X_tr, y_tr)

    y_pred = voting.predict(X_te)
    r2 = r2_score(y_te, y_pred)
    mape = mean_absolute_percentage_error(y_te, y_pred)

    log.info(f"  R²={r2:.4f}, MAPE={mape*100:.2f}%")
    return {'model': voting, 'r2': r2, 'mape': mape, 'type': 'voting'}


def evaluate_weighted_voting(X_tr: np.ndarray, X_te: np.ndarray, y_tr: np.ndarray, y_te: np.ndarray) -> Dict[str, float]:
    """Weighted Voting - CV 점수 기반 가중치."""
    log.info("\n▶ Weighted Voting (성능 기반 가중치)")
    models = create_base_models()

    weights = {}
    for name, model in models.items():
        scores = cross_val_score(model, X_tr, y_tr, cv=3, scoring='r2', n_jobs=1)
        weights[name] = scores.mean()
        log.info(f"  {name}: CV R²={scores.mean():.4f}")

    total_weight = sum(weights.values())
    weights = {k: v/total_weight for k, v in weights.items()}

    estimators = [(name, model) for name, model in models.items()]
    weight_values = [weights[name] for name, _ in estimators]

    voting = VotingRegressor(estimators=estimators, weights=weight_values)
    voting.fit(X_tr, y_tr)

    y_pred = voting.predict(X_te)
    r2 = r2_score(y_te, y_pred)
    mape = mean_absolute_percentage_error(y_te, y_pred)

    log.info(f"  결과: R²={r2:.4f}, MAPE={mape*100:.2f}%")
    return {'model': voting, 'r2': r2, 'mape': mape, 'type': 'weighted_voting', 'weights': weights}


def evaluate_stacking(X_tr: np.ndarray, X_te: np.ndarray, y_tr: np.ndarray, y_te: np.ndarray) -> Dict[str, float]:
    """Stacking Regressor - 메타 모델로 최적 조합."""
    log.info("\n▶ Stacking Regressor (메타 학습기)")
    models = create_base_models()
    estimators = [(name, model) for name, model in models.items()]

    stacking = StackingRegressor(
        estimators=estimators,
        final_estimator=Ridge(alpha=1.0),
        cv=3,
        n_jobs=-1
    )
    stacking.fit(X_tr, y_tr)

    y_pred = stacking.predict(X_te)
    r2 = r2_score(y_te, y_pred)
    mape = mean_absolute_percentage_error(y_te, y_pred)

    log.info(f"  R²={r2:.4f}, MAPE={mape*100:.2f}%")
    return {'model': stacking, 'r2': r2, 'mape': mape, 'type': 'stacking'}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description='Phase 13.2.2 앙상블 최적화')
    parser.add_argument('--data', default='data/processed/KR_engineered.csv')
    parser.add_argument('--output-dir', default='output/ensemble_models')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("Phase 13.2.2 앙상블 최적화 시작")
    log.info("=" * 60)

    X_tr, X_te, y_tr, y_te = load_and_prepare(args.data)
    log.info(f"데이터 분할: train={len(X_tr)}, test={len(X_te)}")

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    results = []
    results.append(evaluate_voting(X_tr, X_te, y_tr, y_te))
    results.append(evaluate_weighted_voting(X_tr, X_te, y_tr, y_te))
    results.append(evaluate_stacking(X_tr, X_te, y_tr, y_te))

    best = max(results, key=lambda x: x['r2'])
    log.info(f"\n{'='*60}")
    log.info(f"최적 앙상블: {best['type'].upper()}")
    log.info(f"R²={best['r2']:.4f}, MAPE={best['mape']*100:.2f}%")
    log.info(f"{'='*60}\n")

    with open(Path(args.output_dir) / 'best_ensemble.pkl', 'wb') as f:
        pickle.dump(best['model'], f)

    log.info(f"✅ 최적 앙상블 모델 저장: {Path(args.output_dir) / 'best_ensemble.pkl'}")


if __name__ == '__main__':
    main()
