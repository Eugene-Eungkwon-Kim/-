#!/usr/bin/env python3
"""
Loan4U Phase 13.2 - GPU Model Trainer
Train XGBoost/LightGBM/GradientBoosting on RTX 5050, targeting R²>0.84.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_percentage_error, r2_score
from sklearn.model_selection import train_test_split

from gpu_config import (
    configure_lightgbm_gpu,
    configure_xgboost_gpu,
    select_training_device,
)

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']
TARGET_COL = 'new_price'


@dataclass
class ModelResult:
    """Training result for one model"""
    model_name: str
    country: str
    r2: float
    mape: float
    train_size: int
    test_size: int
    meets_target: bool = field(init=False)

    def __post_init__(self) -> None:
        self.meets_target = self.r2 > 0.84 and self.mape < 0.105


def load_country_data(csv_path: Path) -> Optional[pd.DataFrame]:
    """Load and validate a country CSV."""
    try:
        df = pd.read_csv(csv_path)
        missing = set(FEATURE_COLS + [TARGET_COL]) - set(df.columns)
        if missing:
            log.warning(f"{csv_path.name}: missing columns {missing}")
            return None
        return df.dropna(subset=FEATURE_COLS + [TARGET_COL])
    except Exception as e:
        log.warning(f"Cannot load {csv_path.name}: {e}")
        return None


def split_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Extract feature matrix and target vector."""
    X = df[FEATURE_COLS].to_numpy(dtype=np.float32)
    y = df[TARGET_COL].to_numpy(dtype=np.float32)
    return X, y


def evaluate_model(y_true: np.ndarray, y_pred: np.ndarray) -> Tuple[float, float]:
    """Return (R², MAPE) for predictions."""
    return r2_score(y_true, y_pred), mean_absolute_percentage_error(y_true, y_pred)


def train_xgboost(X_tr, y_tr, X_te, y_te, device_id: Optional[int]) -> Tuple[float, float]:
    """Train XGBoost on GPU (RTX 5050) or CPU fallback."""
    import xgboost as xgb

    params = configure_xgboost_gpu(device_id)
    model = xgb.XGBRegressor(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, **params,
    )
    model.fit(X_tr, y_tr)
    return evaluate_model(y_te, model.predict(X_te))


def train_lightgbm(X_tr, y_tr, X_te, y_te, device_id: Optional[int]) -> Tuple[float, float]:
    """Train LightGBM on GPU (RTX 5050); fall back to CPU if GPU/OpenCL absent."""
    import lightgbm as lgb

    def _fit(params: Dict[str, object]) -> Tuple[float, float]:
        model = lgb.LGBMRegressor(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            subsample=0.8, verbose=-1, **params,
        )
        model.fit(X_tr, y_tr)
        return evaluate_model(y_te, model.predict(X_te))

    try:
        return _fit(configure_lightgbm_gpu(device_id))
    except Exception:
        return _fit(configure_lightgbm_gpu(None))


def train_gradient_boosting(X_tr, y_tr, X_te, y_te) -> Tuple[float, float]:
    """Train Gradient Boosting on CPU (diversity baseline)."""
    model = GradientBoostingRegressor(
        n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.8,
    )
    model.fit(X_tr, y_tr)
    return evaluate_model(y_te, model.predict(X_te))


def train_country(country: str, df: pd.DataFrame, device_id: int) -> List[ModelResult]:
    """Train all 3 models for one country."""
    X, y = split_features(df)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

    results: List[ModelResult] = []
    trainers = {
        'XGBoost': lambda: train_xgboost(X_tr, y_tr, X_te, y_te, device_id),
        'LightGBM': lambda: train_lightgbm(X_tr, y_tr, X_te, y_te, device_id),
        'GradientBoosting': lambda: train_gradient_boosting(X_tr, y_tr, X_te, y_te),
    }

    for name, fn in trainers.items():
        try:
            r2, mape = fn()
            results.append(ModelResult(name, country, r2, mape, len(X_tr), len(X_te)))
            log.info(f"  {country}/{name}: R²={r2:.3f} MAPE={mape:.1%}")
        except Exception as e:
            log.warning(f"  {country}/{name} failed: {e}")

    return results


def train_all_countries(data_dir: str) -> List[ModelResult]:
    """Orchestrate training across all country datasets."""
    device_id, desc = select_training_device()
    log.info(f"Training device: {desc}")

    all_results: List[ModelResult] = []
    for csv_path in sorted(Path(data_dir).glob('*_data.csv')):
        country = csv_path.stem.replace('_data', '')
        df = load_country_data(csv_path)
        if df is None or len(df) < 50:
            continue
        log.info(f"Training {country} ({len(df)} records)...")
        all_results.extend(train_country(country, df, device_id))

    return all_results


def summarize(results: List[ModelResult]) -> Dict[str, object]:
    """Aggregate training results."""
    if not results:
        return {'total': 0, 'passed': 0, 'best_r2': 0.0}
    passed = sum(1 for r in results if r.meets_target)
    return {
        'total': len(results),
        'passed': passed,
        'pass_rate': passed / len(results),
        'best_r2': max(r.r2 for r in results),
        'avg_r2': sum(r.r2 for r in results) / len(results),
    }


def main() -> None:
    """Run Phase 13.2 model training."""
    import argparse

    parser = argparse.ArgumentParser(description='Phase 13.2 GPU Model Trainer')
    parser.add_argument('--data', default='data/raw', help='Data directory')
    args = parser.parse_args()

    results = train_all_countries(args.data)
    summary = summarize(results)

    print(f"\n{'='*50}")
    print("Phase 13.2 Training Complete")
    print(f"{'='*50}")
    print(f"Models trained: {summary['total']}")
    print(f"Met target (R²>0.84, MAPE<10.5%): {summary['passed']}")
    if summary['total'] > 0:
        print(f"Best R²: {summary['best_r2']:.3f}")
        print(f"Avg R²: {summary['avg_r2']:.3f}")


if __name__ == '__main__':
    main()
