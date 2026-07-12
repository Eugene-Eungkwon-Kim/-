#!/usr/bin/env python3
"""
Phase 13.2 - MAPE Improvement Measurement
기준 모델 대비 개선도 측정 (11.33% → 목표 <10%).

실행:
    python scripts/phase13_mape_measurement.py
"""

import logging
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, VotingRegressor, StackingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import r2_score, mean_absolute_percentage_error
import xgboost as xgb
import lightgbm as lgb

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

TARGET_COL = 'new_price'
BASELINE_MAPE = 0.1133
CRITICAL_MAPE = 0.10
TARGET_MAPE = 0.085


def load_data(data_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """데이터 로드 및 분할."""
    df = pd.read_csv(data_path)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if TARGET_COL in numeric_cols:
        numeric_cols.remove(TARGET_COL)
    X = df[numeric_cols].fillna(df[numeric_cols].mean()).to_numpy(dtype=np.float32)
    y = df[TARGET_COL].to_numpy(dtype=np.float32)
    return train_test_split(X, y, test_size=0.2, random_state=42)


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


def measure_baseline_ensemble(X_tr: np.ndarray, X_te: np.ndarray, y_tr: np.ndarray, y_te: np.ndarray) -> Dict:
    """기준 앙상블 모델 (균등 가중치 Voting)."""
    log.info("\n▶ 기준 앙상블 (Baseline Voting)")
    models = create_base_models()
    estimators = [(name, model) for name, model in models.items()]

    voting = VotingRegressor(estimators=estimators)
    voting.fit(X_tr, y_tr)
    y_pred = voting.predict(X_te)

    r2 = r2_score(y_te, y_pred)
    mape = mean_absolute_percentage_error(y_te, y_pred)

    log.info(f"  R²={r2:.4f}, MAPE={mape*100:.2f}%")
    return {'r2': r2, 'mape': mape, 'model': voting}


def measure_weighted_ensemble(X_tr: np.ndarray, X_te: np.ndarray, y_tr: np.ndarray, y_te: np.ndarray) -> Dict:
    """성능 기반 가중치 Voting."""
    log.info("\n▶ 가중치 앙상블 (Performance-Weighted Voting)")
    models = create_base_models()

    weights = {}
    for name, model in models.items():
        scores = cross_val_score(model, X_tr, y_tr, cv=3, scoring='r2', n_jobs=1)
        weights[name] = scores.mean()

    total_weight = sum(weights.values())
    weights = {k: v/total_weight for k, v in weights.items()}

    estimators = [(name, model) for name, model in models.items()]
    weight_values = [weights[name] for name, _ in estimators]

    voting = VotingRegressor(estimators=estimators, weights=weight_values)
    voting.fit(X_tr, y_tr)
    y_pred = voting.predict(X_te)

    r2 = r2_score(y_te, y_pred)
    mape = mean_absolute_percentage_error(y_te, y_pred)

    log.info(f"  R²={r2:.4f}, MAPE={mape*100:.2f}%")
    return {'r2': r2, 'mape': mape, 'model': voting, 'weights': weights}


def measure_stacking_ensemble(X_tr: np.ndarray, X_te: np.ndarray, y_tr: np.ndarray, y_te: np.ndarray) -> Dict:
    """Stacking 메타 학습기."""
    log.info("\n▶ 스태킹 앙상블 (Stacking Meta-Learner)")
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
    return {'r2': r2, 'mape': mape, 'model': stacking}


def measure_improvements(engineered_path: str, integrated_path: Optional[str] = None) -> None:
    """MAPE 개선도 측정."""
    log.info("=" * 70)
    log.info("PHASE 13.2 MAPE 개선도 측정")
    log.info("=" * 70)

    log.info(f"\n【기준값】 Baseline MAPE: {BASELINE_MAPE*100:.2f}%")
    log.info(f"【목표값】 Target MAPE (임계): {CRITICAL_MAPE*100:.2f}%")
    log.info(f"【목표값】 Target MAPE (최종): {TARGET_MAPE*100:.2f}%")

    log.info("\n=" * 70)
    log.info("Step 1: 특성 공학 후 개선도 측정 (Phase 1)")
    log.info("=" * 70)

    X_tr_eng, X_te_eng, y_tr_eng, y_te_eng = load_data(engineered_path)
    log.info(f"데이터 로드: {len(X_tr_eng)} train, {len(X_te_eng)} test")
    log.info(f"특성 수: {X_tr_eng.shape[1]} features")

    ensemble_results = []
    ensemble_results.append(('Baseline', measure_baseline_ensemble(X_tr_eng, X_te_eng, y_tr_eng, y_te_eng)))
    ensemble_results.append(('Weighted', measure_weighted_ensemble(X_tr_eng, X_te_eng, y_tr_eng, y_te_eng)))
    ensemble_results.append(('Stacking', measure_stacking_ensemble(X_tr_eng, X_te_eng, y_tr_eng, y_te_eng)))

    best_eng = min(ensemble_results, key=lambda x: x[1]['mape'])
    delta_phase1 = (best_eng[1]['mape'] - BASELINE_MAPE) * 100

    log.info(f"\n【Phase 1 최적】 {best_eng[0]} ensemble")
    log.info(f"  MAPE: {best_eng[1]['mape']*100:.2f}% (Δ {delta_phase1:+.2f}%)")
    log.info(f"  R²: {best_eng[1]['r2']:.4f}")

    if integrated_path and Path(integrated_path).exists():
        log.info("\n" + "=" * 70)
        log.info("Step 2: 외부 데이터 통합 후 개선도 측정 (Phase 1 + 4)")
        log.info("=" * 70)

        X_tr_int, X_te_int, y_tr_int, y_te_int = load_data(integrated_path)
        log.info(f"데이터 로드: {len(X_tr_int)} train, {len(X_te_int)} test")
        log.info(f"특성 수: {X_tr_int.shape[1]} features")

        int_results = []
        int_results.append(('Baseline', measure_baseline_ensemble(X_tr_int, X_te_int, y_tr_int, y_te_int)))
        int_results.append(('Weighted', measure_weighted_ensemble(X_tr_int, X_te_int, y_tr_int, y_te_int)))
        int_results.append(('Stacking', measure_stacking_ensemble(X_tr_int, X_te_int, y_tr_int, y_te_int)))

        best_int = min(int_results, key=lambda x: x[1]['mape'])
        delta_total = (best_int[1]['mape'] - BASELINE_MAPE) * 100
        delta_phase4 = (best_int[1]['mape'] - best_eng[1]['mape']) * 100

        log.info(f"\n【Phase 1+4 최적】 {best_int[0]} ensemble")
        log.info(f"  MAPE: {best_int[1]['mape']*100:.2f}% (Δ {delta_total:+.2f}%)")
        log.info(f"  R²: {best_int[1]['r2']:.4f}")
        log.info(f"  Phase 4 추가 개선: Δ {delta_phase4:+.2f}%")

    log.info("\n" + "=" * 70)
    log.info("결과 요약")
    log.info("=" * 70)
    log.info(f"기준값 (Baseline): {BASELINE_MAPE*100:.2f}%")
    log.info(f"Phase 1 최적: {best_eng[1]['mape']*100:.2f}% (Δ {delta_phase1:+.2f}%)")

    if integrated_path and Path(integrated_path).exists():
        log.info(f"Phase 1+4 최적: {best_int[1]['mape']*100:.2f}% (Δ {delta_total:+.2f}%)")
        status = "✅ 목표 달성" if best_int[1]['mape'] < TARGET_MAPE else ("⚠️ 임계값 달성" if best_int[1]['mape'] < CRITICAL_MAPE else "❌ 추가 개선 필요")
        log.info(f"상태: {status}")
    else:
        status = "✅ 목표 달성" if best_eng[1]['mape'] < TARGET_MAPE else ("⚠️ 임계값 달성" if best_eng[1]['mape'] < CRITICAL_MAPE else "❌ 추가 개선 필요")
        log.info(f"상태: {status}")


def main() -> None:
    engineered_data = 'data/processed/KR_engineered.csv'
    integrated_data = 'data/processed/KR_integrated.csv'

    if not Path(engineered_data).exists():
        log.error(f"❌ Missing: {engineered_data}")
        return

    measure_improvements(engineered_data, integrated_data)


if __name__ == '__main__':
    main()
