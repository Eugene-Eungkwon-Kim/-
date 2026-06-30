#!/usr/bin/env python3
"""
Quick script to train and save models for testing conversion pipeline
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
import xgboost as xgb
import lightgbm as lgb

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']

def save_models_for_country(country: str) -> None:
    """Train and save models for a specific country."""
    data_path = Path('data/raw') / f'{country}_data.csv'

    if not data_path.exists():
        print(f"⚠️ {country}_data.csv not found")
        return

    # Load data
    df = pd.read_csv(data_path)
    print(f"Loaded {country}: {len(df)} rows")

    # Prepare features
    X = df[FEATURE_COLS].to_numpy(dtype=np.float32)
    y = df['new_price'].to_numpy(dtype=np.float32)

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

    # Create output directory
    output_dir = Path('output/trained_models')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Train XGBoost
    xgb_model = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.05, random_state=42)
    xgb_model.fit(X_tr, y_tr)
    with open(output_dir / f'xgboost_{country}.pkl', 'wb') as f:
        pickle.dump(xgb_model, f)
    print(f"✅ Saved xgboost_{country}.pkl")

    # Train LightGBM
    lgb_model = lgb.LGBMRegressor(n_estimators=100, max_depth=6, learning_rate=0.05, verbose=-1, random_state=42)
    lgb_model.fit(X_tr, y_tr)
    with open(output_dir / f'lightgbm_{country}.pkl', 'wb') as f:
        pickle.dump(lgb_model, f)
    print(f"✅ Saved lightgbm_{country}.pkl")

    # Train GradientBoosting
    gb_model = GradientBoostingRegressor(n_estimators=100, max_depth=6, learning_rate=0.05, random_state=42)
    gb_model.fit(X_tr, y_tr)
    with open(output_dir / f'gradient_boosting_{country}.pkl', 'wb') as f:
        pickle.dump(gb_model, f)
    print(f"✅ Saved gradient_boosting_{country}.pkl")

if __name__ == '__main__':
    # Train and save for KR
    save_models_for_country('KR')

    # Verify
    output_dir = Path('output/trained_models')
    saved_models = list(output_dir.glob('*_KR.pkl'))
    print(f"\n✅ Total models saved: {len(saved_models)}")
    for model_file in saved_models:
        size_kb = model_file.stat().st_size / 1024
        print(f"  - {model_file.name}: {size_kb:.1f} KB")
