"""
Phase 13.3 - KR 모델 검증 & 하이퍼파라미터 튜닝

train_kr_model.py로 학습된 3개 모델(XGBoost/LightGBM/GradientBoosting)을
5-fold 교차검증, 하이퍼파라미터 튜닝, 특성 중요도 분석으로 검증하고
최적 모델을 선정한다.

실행:
    python scripts/phase13_model_validator.py --data data/raw/KR_data.csv
"""

import argparse
import json
import logging
import pickle
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.model_selection import GridSearchCV, KFold, cross_val_score

from train_kr_model import FEATURE_COLS, TARGET_COL, load_and_validate, split_data

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

TARGET_R2 = 0.84
TARGET_MAPE = 0.105

PARAM_GRIDS: Dict[str, Dict[str, List[Any]]] = {
    'xgboost': {'max_depth': [4, 6, 8], 'learning_rate': [0.03, 0.05, 0.1]},
    'lightgbm': {'num_leaves': [20, 31, 50], 'learning_rate': [0.03, 0.05, 0.1]},
    'gradient_boosting': {'max_depth': [3, 5, 7], 'learning_rate': [0.03, 0.05, 0.1]},
}


def cross_validate_model(model: object, X: np.ndarray, y: np.ndarray, n_splits: int = 5) -> Dict[str, float]:
    """5-fold 교차검증으로 R² mean/std 계산.

    n_jobs=1: 학습된 모델(pkl)은 자체 n_jobs=-1을 갖고 있어(train_kr_model.py),
    바깥쪽까지 병렬화하면 중첩 병렬화로 행(hang)이 발생한다.
    """
    kfold = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    scores = cross_val_score(model, X, y, cv=kfold, scoring='r2', n_jobs=1)
    return {'r2_mean': float(scores.mean()), 'r2_std': float(scores.std()), 'r2_folds': [float(s) for s in scores]}


def _base_estimator(model_name: str) -> object:
    """튜닝용 미학습 추정기 생성 (기존 학습 하이퍼파라미터를 기본값으로 사용).

    n_jobs=1로 고정한다: 바깥쪽 GridSearchCV/cross_val_score가 이미 병렬화하므로,
    모델 내부까지 병렬화하면 중첩 병렬화로 인한 스레드 경합/행(hang)이 발생한다.
    """
    common = {'n_estimators': 300, 'subsample': 0.8, 'random_state': 42}
    if model_name == 'xgboost':
        import xgboost as xgb
        return xgb.XGBRegressor(colsample_bytree=0.8, n_jobs=1, **common)
    if model_name == 'lightgbm':
        import lightgbm as lgb
        return lgb.LGBMRegressor(colsample_bytree=0.8, n_jobs=1, verbose=-1, **common)
    return GradientBoostingRegressor(**common)


def tune_hyperparameters(model_name: str, X_train: np.ndarray, y_train: np.ndarray) -> Tuple[object, Dict[str, Any], float]:
    """GridSearchCV로 최적 하이퍼파라미터 탐색."""
    estimator = _base_estimator(model_name)
    grid = GridSearchCV(
        estimator, PARAM_GRIDS[model_name], cv=3, scoring='r2', n_jobs=-1, refit=True,
    )
    grid.fit(X_train, y_train)
    return grid.best_estimator_, grid.best_params_, float(grid.best_score_)


def extract_feature_importance(model: object, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Dict[str, float]]:
    """내장 중요도 + 순열 중요도(permutation importance) 추출."""
    builtin: Dict[str, float] = {}
    if hasattr(model, 'feature_importances_'):
        builtin = {name: float(v) for name, v in zip(FEATURE_COLS, model.feature_importances_)}

    perm = permutation_importance(model, X_test, y_test, n_repeats=10, random_state=42, n_jobs=-1)
    permutation = {name: float(v) for name, v in zip(FEATURE_COLS, perm.importances_mean)}

    return {'builtin': builtin, 'permutation': permutation}


def select_best_model(validation_results: Dict[str, Dict[str, Any]]) -> str:
    """가중치 기반 최적 모델 선정 (R² 60%, MAPE 40%)."""
    scores = {}
    for name, result in validation_results.items():
        r2_score_norm = result['tuned_r2']
        mape_score_norm = max(0.0, 1.0 - result['test_mape'] / TARGET_MAPE)
        scores[name] = 0.6 * r2_score_norm + 0.4 * mape_score_norm
    return max(scores, key=scores.get)


def _evaluate_single_model(
    model_name: str,
    pkl_path: Path,
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    models_dir: Path,
    country: str,
) -> Optional[Dict[str, Any]]:
    """개별 모델 검증: CV → 튜닝 → 테스트 → 저장."""
    from sklearn.metrics import mean_absolute_percentage_error, r2_score

    if not pkl_path.exists():
        log.warning(f"  {pkl_path} 없음 - 건너뜀")
        return None

    log.info(f"\n▶ {model_name}")
    with open(pkl_path, 'rb') as f:
        trained_model = pickle.load(f)

    cv_result = cross_validate_model(trained_model, X_train, y_train)
    log.info(f"  5-fold CV: R²={cv_result['r2_mean']:.4f} ± {cv_result['r2_std']:.4f}")

    tuned_model, best_params, tuned_r2 = tune_hyperparameters(model_name, X_train, y_train)
    log.info(f"  튜닝 결과: R²={tuned_r2:.4f} params={best_params}")

    y_pred = tuned_model.predict(X_test)
    test_r2 = float(r2_score(y_test, y_pred))
    test_mape = float(mean_absolute_percentage_error(y_test, y_pred))
    log.info(f"  홀드아웃: R²={test_r2:.4f} MAPE={test_mape*100:.2f}%")

    importance = extract_feature_importance(tuned_model, X_test, y_test)
    save_tuned_model(tuned_model, model_name, models_dir, country)

    return {
        'cv': cv_result,
        'best_params': best_params,
        'tuned_r2': tuned_r2,
        'test_r2': test_r2,
        'test_mape': test_mape,
        'meets_target': test_r2 >= TARGET_R2 and test_mape <= TARGET_MAPE,
        'feature_importance': importance,
    }


def validate_all_models(
    data_path: str, models_dir: Path, country: str = 'KR',
) -> Dict[str, Dict[str, Any]]:
    """전체 검증 파이프라인 오케스트레이션."""
    df = load_and_validate(data_path)
    X_train, X_test, y_train, y_test, _, _ = split_data(df, country)

    results: Dict[str, Dict[str, Any]] = {}
    for model_name in PARAM_GRIDS:
        pkl_path = models_dir / f"{model_name}_{country}.pkl"
        result = _evaluate_single_model(model_name, pkl_path, X_train, X_test, y_train, y_test, models_dir, country)
        if result:
            results[model_name] = result

    return results


def save_tuned_model(model: object, name: str, output_dir: Path, country: str = 'KR') -> None:
    """튜닝된 모델 저장."""
    path = output_dir / f"{name}_{country}_tuned.pkl"
    with open(path, 'wb') as f:
        pickle.dump(model, f)
    log.info(f"  튜닝 모델 저장: {path}")


def save_validation_report(results: Dict[str, Dict[str, Any]], best_model: str, output_path: Path) -> None:
    """검증 리포트 JSON 저장."""
    report = {
        'targets': {'r2': TARGET_R2, 'mape': TARGET_MAPE},
        'best_model': best_model,
        'models': results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log.info(f"\n✅ 검증 리포트 저장: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description='Phase 13.3 국가별 모델 검증')
    parser.add_argument('--data', default='data/raw/KR_data.csv')
    parser.add_argument('--models-dir', default='output/trained_models')
    parser.add_argument('--report', default=None, help='기본값: output/{country}_validation_report.json')
    parser.add_argument('--country', default='KR', help='KR, SG 등 (country_configs.py 참조)')
    args = parser.parse_args()
    report_path = Path(args.report) if args.report else Path(f'output/{args.country.lower()}_validation_report.json')

    log.info("=" * 60)
    log.info(f"Phase 13.3 {args.country} 모델 검증 시작")
    log.info("=" * 60)

    t_start = time.time()
    results = validate_all_models(args.data, Path(args.models_dir), args.country)
    best_model = select_best_model(results)
    elapsed = time.time() - t_start

    log.info("\n" + "=" * 60)
    log.info(f"최적 모델: {best_model}")
    log.info(f"총 소요시간: {elapsed:.1f}초")
    log.info("=" * 60)

    save_validation_report(results, best_model, report_path)

    best_path = Path(args.models_dir) / f"{best_model}_{args.country}_tuned.pkl"
    best_model_path = Path(args.models_dir) / f'best_model_{args.country}.pkl'
    shutil.copy(best_path, best_model_path)
    log.info(f"✅ 최적 모델 저장: {best_model_path}")


if __name__ == '__main__':
    main()
