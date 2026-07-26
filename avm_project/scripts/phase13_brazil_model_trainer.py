#!/usr/bin/env python3
"""
Phase 13.X.BR - Brazil Model Training (Stacking Ensemble)
KR 프로덕션 아키텍처 재사용: 5개 기본 모델 + Ridge 메타 학습기.

목표: MAPE < 10% (BR 시장 임계값)

실행:
    python scripts/phase13_brazil_model_trainer.py \
      --data data/processed/BR_engineered.csv \
      --output output/models/br_production_v1.0.pkl
"""

import argparse
import json
import logging
import pickle
import time
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesRegressor, GradientBoostingRegressor,
    RandomForestRegressor, StackingRegressor,
)
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_percentage_error, r2_score
from sklearn.model_selection import train_test_split

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

TARGET_COL = 'price_brl'
LEAK_PATTERNS = ('price_brl', 'indexed_price')
MAPE_TARGET = 0.10


def load_dataset(data_path: str) -> Tuple[np.ndarray, np.ndarray, list]:
    """누수 컬럼 제거 후 특성/타겟 분리."""
    df = pd.read_csv(data_path)
    y = df[TARGET_COL].to_numpy(dtype=np.float64)

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [c for c in numeric_cols if not any(p in c for p in LEAK_PATTERNS)]
    X = df[feature_cols].fillna(df[feature_cols].mean()).fillna(0.0).to_numpy(dtype=np.float64)

    return X, y, feature_cols


def build_stacking_model() -> StackingRegressor:
    """KR 프로덕션과 동일 구조의 Stacking Ensemble."""
    import lightgbm as lgb
    import xgboost as xgb

    base_models = [
        ('xgb', xgb.XGBRegressor(n_estimators=300, max_depth=8, learning_rate=0.05,
                                 subsample=0.8, n_jobs=-1, random_state=42)),
        ('lgbm', lgb.LGBMRegressor(n_estimators=300, max_depth=8, learning_rate=0.05,
                                   subsample=0.8, n_jobs=-1, random_state=42, verbose=-1)),
        ('gb', GradientBoostingRegressor(n_estimators=200, max_depth=6,
                                         learning_rate=0.05, random_state=42)),
        ('rf', RandomForestRegressor(n_estimators=200, max_depth=12,
                                     n_jobs=-1, random_state=42)),
        ('et', ExtraTreesRegressor(n_estimators=200, max_depth=12,
                                   n_jobs=-1, random_state=42)),
    ]
    return StackingRegressor(estimators=base_models, final_estimator=Ridge(alpha=1.0),
                             cv=5, n_jobs=-1)


def evaluate(model: StackingRegressor, X_train: np.ndarray, y_train: np.ndarray,
             X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
    """학습/테스트 성능 평가."""
    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)
    return {
        'train_mape': float(mean_absolute_percentage_error(y_train, train_pred)),
        'test_mape': float(mean_absolute_percentage_error(y_test, test_pred)),
        'train_r2': float(r2_score(y_train, train_pred)),
        'test_r2': float(r2_score(y_test, test_pred)),
    }


def save_artifacts(model: StackingRegressor, metrics: Dict, feature_cols: list,
                   output_path: Path, elapsed: float, n_samples: int) -> None:
    """모델 pkl + 메타데이터 JSON 저장."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        pickle.dump(model, f)

    metadata = {
        'model_id': 'br_production_v1.0',
        'country': 'BR',
        'architecture': 'StackingRegressor (5 base + Ridge meta)',
        'performance': metrics,
        'mape_target': MAPE_TARGET,
        'target_met': metrics['test_mape'] < MAPE_TARGET,
        'n_features': len(feature_cols),
        'n_samples': n_samples,
        'feature_columns': feature_cols,
        'training_sec': round(elapsed, 1),
        'model_size_mb': round(output_path.stat().st_size / 1024 / 1024, 1),
        'created_date': '2026-07-18',
    }
    meta_path = output_path.parent / 'br_production_v1.0_metadata.json'
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    log.info(f"✅ 메타데이터: {meta_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description='Phase 13.X.BR 모델 학습')
    parser.add_argument('--data', default='data/processed/BR_engineered.csv')
    parser.add_argument('--output', default='output/models/br_production_v1.0.pkl')
    args = parser.parse_args()

    log.info("=" * 70)
    log.info("Phase 13.X.BR Stacking Ensemble 학습 시작")
    log.info("=" * 70)

    X, y, feature_cols = load_dataset(args.data)
    log.info(f"✅ 데이터: {X.shape[0]:,} rows × {X.shape[1]} features")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = build_stacking_model()
    t0 = time.time()
    model.fit(X_train, y_train)
    elapsed = time.time() - t0
    log.info(f"✅ 학습 완료: {elapsed:.1f}초")

    metrics = evaluate(model, X_train, y_train, X_test, y_test)
    log.info(f"\n성능 (목표 MAPE < {MAPE_TARGET:.0%}):")
    log.info(f"  Test MAPE: {metrics['test_mape']:.2%}  {'✅ PASS' if metrics['test_mape'] < MAPE_TARGET else '❌ FAIL'}")
    log.info(f"  Test R²:   {metrics['test_r2']:.4f}")
    log.info(f"  Overfit gap: {metrics['test_mape'] - metrics['train_mape']:.4f}")

    save_artifacts(model, metrics, feature_cols, Path(args.output), elapsed, X.shape[0])
    log.info(f"✅ 모델 저장: {args.output}")

    exit(0 if metrics['test_mape'] < MAPE_TARGET else 1)


if __name__ == '__main__':
    main()
