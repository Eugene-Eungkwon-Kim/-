"""
KR 데이터 전용 모델 학습 스크립트
KR_data.csv → XGBoost/LightGBM/GradientBoosting 학습 → output/trained_models/

실행:
    python train_kr_model.py --data data/raw/KR_data.csv
"""

import argparse
import json
import logging
import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_percentage_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']
TARGET_COL = 'new_price'
MIN_ROWS = 100   # 최소 학습 데이터 수
TARGET_R2 = 0.84
TARGET_MAPE = 0.105


def load_and_validate(csv_path: str) -> pd.DataFrame:
    """데이터 로드 및 기본 검증."""
    df = pd.read_csv(csv_path)

    missing = set(FEATURE_COLS + [TARGET_COL]) - set(df.columns)
    if missing:
        raise ValueError(f"필수 컬럼 없음: {missing}")

    df = df.dropna(subset=FEATURE_COLS + [TARGET_COL])
    df = df[df[TARGET_COL] > 0]
    df = df[df['area_sqm'] > 0]

    if len(df) < MIN_ROWS:
        raise ValueError(f"데이터 부족: {len(df)}행 (최소 {MIN_ROWS}행 필요)")

    log.info(f"데이터 로드: {len(df):,}행")
    log.info(f"  거래가 범위: {df[TARGET_COL].min():,.0f} ~ {df[TARGET_COL].max():,.0f}원")
    log.info(f"  면적 범위: {df['area_sqm'].min():.1f} ~ {df['area_sqm'].max():.1f}㎡")

    return df


def _normalize_features(X: np.ndarray, country: str = 'KR') -> np.ndarray:
    """국가별 Min-Max 정규화 적용 (학습-추론 일관성 보장).

    country_configs.KR_CONFIG.feature_min/max는 avm_feature_engineering의
    FEATURE_MIN/MAX와 동일한 값이므로, 기본값(KR)은 리팩토링 전과 동일하게 동작한다.
    """
    from country_configs import get_country_config
    config = get_country_config(country)
    feature_min = np.array(config.feature_min, dtype=np.float32)
    feature_max = np.array(config.feature_max, dtype=np.float32)
    normalized = (X - feature_min) / (feature_max - feature_min)
    return np.clip(normalized, 0.0, 1.0).astype(np.float32)


def split_data(
    df: pd.DataFrame, country: str = 'KR',
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, pd.DataFrame, pd.DataFrame]:
    """시간 기반 분할 (80% train / 20% test) + 정규화."""
    if 'transaction_month' in df.columns:
        df_sorted = df.sort_values('transaction_month').reset_index(drop=True)
        cutoff = int(len(df_sorted) * 0.80)
        train_df, test_df = df_sorted.iloc[:cutoff], df_sorted.iloc[cutoff:]
    else:
        train_df, test_df = train_test_split(df, test_size=0.20, random_state=42)
    X_train = _normalize_features(train_df[FEATURE_COLS].values.astype(np.float32), country)
    X_test  = _normalize_features(test_df[FEATURE_COLS].values.astype(np.float32), country)
    y_train = train_df[TARGET_COL].values.astype(np.float64)
    y_test  = test_df[TARGET_COL].values.astype(np.float64)
    return X_train, X_test, y_train, y_test, train_df, test_df


def evaluate(y_true: np.ndarray, y_pred: np.ndarray, model_name: str) -> Dict:
    """R², MAPE 평가."""
    r2 = r2_score(y_true, y_pred)
    mape = mean_absolute_percentage_error(y_true, y_pred)
    meets = r2 >= TARGET_R2 and mape <= TARGET_MAPE

    status = "✅ PASS" if meets else "❌ FAIL"
    log.info(f"  {model_name}: R²={r2:.4f} MAPE={mape*100:.2f}% {status}")

    return {'r2': r2, 'mape': mape, 'meets_target': meets}


def train_xgboost(X_train: np.ndarray, y_train: np.ndarray) -> object:
    """XGBoost 학습 (GPU 우선, CPU 폴백)."""
    try:
        import xgboost as xgb
        params = {
            'n_estimators': 500, 'max_depth': 6, 'learning_rate': 0.05,
            'subsample': 0.8, 'colsample_bytree': 0.8,
            'min_child_weight': 5, 'reg_alpha': 0.1, 'reg_lambda': 1.0,
            'random_state': 42, 'n_jobs': -1,
        }
        try:
            model = xgb.XGBRegressor(device='cuda', **params)
            model.fit(X_train, y_train, verbose=False)
        except Exception:
            model = xgb.XGBRegressor(**params)
            model.fit(X_train, y_train, verbose=False)
        return model
    except ImportError:
        log.warning("XGBoost 미설치 - 건너뜀")
        return None


def train_lightgbm(X_train: np.ndarray, y_train: np.ndarray) -> object:
    """LightGBM 학습."""
    try:
        import lightgbm as lgb
        params = {
            'n_estimators': 500, 'max_depth': 6, 'learning_rate': 0.05,
            'subsample': 0.8, 'colsample_bytree': 0.8,
            'random_state': 42, 'n_jobs': -1, 'verbose': -1,
        }
        model = lgb.LGBMRegressor(**params)
        model.fit(X_train, y_train)
        return model
    except ImportError:
        log.warning("LightGBM 미설치 - 건너뜀")
        return None


def train_gradient_boosting(X_train: np.ndarray, y_train: np.ndarray) -> object:
    """Gradient Boosting 학습 (sklearn, 항상 가용)."""
    model = GradientBoostingRegressor(
        n_estimators=300, max_depth=5, learning_rate=0.05,
        subsample=0.8, random_state=42,
    )
    model.fit(X_train, y_train)
    return model


def evaluate_by_region(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    test_df: pd.DataFrame,
) -> Dict[str, Dict]:
    """지역별 R², MAPE 계산."""
    if 'region_name' not in test_df.columns:
        return {}
    results: Dict[str, Dict] = {}
    for region in test_df['region_name'].unique():
        mask = (test_df['region_name'] == region).values
        if mask.sum() < 5:
            continue
        results[region] = {
            'r2':   round(float(r2_score(y_true[mask], y_pred[mask])), 4),
            'mape': round(float(mean_absolute_percentage_error(y_true[mask], y_pred[mask])), 4),
            'n':    int(mask.sum()),
        }
    return results


def save_model(model: object, name: str, output_dir: Path, country: str = 'KR') -> None:
    """모델 저장."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}_{country}.pkl"
    with open(path, 'wb') as f:
        pickle.dump(model, f)
    size_mb = path.stat().st_size / 1024 / 1024
    log.info(f"  저장: {path} ({size_mb:.2f} MB)")


def save_training_report(
    results: Dict[str, Dict],
    output_dir: Path,
    elapsed_sec: float,
    country: str = 'KR',
) -> None:
    """output/{country.lower()}_training_report.json 저장."""
    report = {
        'timestamp':    datetime.now().isoformat(),
        'elapsed_sec':  round(elapsed_sec, 1),
        'feature_cols': FEATURE_COLS,
        'targets':      {'r2': TARGET_R2, 'mape': TARGET_MAPE},
        'models':       results,
    }
    path = output_dir / f'{country.lower()}_training_report.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log.info(f"  리포트 저장: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description='국가별 AVM 모델 학습')
    parser.add_argument('--data',    default='data/raw/KR_data.csv')
    parser.add_argument('--output',  default='output/trained_models')
    parser.add_argument('--country', default='KR', help='KR, SG 등 (country_configs.py 참조)')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info(f"{args.country} AVM 모델 학습 시작")
    log.info("=" * 60)

    t_start = time.time()
    df = load_and_validate(args.data)
    X_train, X_test, y_train, y_test, train_df, test_df = split_data(df, args.country)
    log.info(f"학습: {len(X_train):,}건 | 검증: {len(X_test):,}건")

    output_dir = Path(args.output)
    results: Dict[str, Dict] = {}

    trainers = {
        'xgboost':           train_xgboost,
        'lightgbm':          train_lightgbm,
        'gradient_boosting': train_gradient_boosting,
    }

    log.info("\n[학습 시작]")
    for name, trainer in trainers.items():
        log.info(f"\n▶ {name}")
        model = trainer(X_train, y_train)
        if model is None:
            continue
        y_pred = model.predict(X_test)
        result = evaluate(y_test, y_pred, name)
        result['region_breakdown'] = evaluate_by_region(y_test, y_pred, test_df.reset_index(drop=True))
        save_model(model, name, output_dir, args.country)
        results[name] = result

    elapsed = time.time() - t_start
    log.info("\n" + "=" * 60)
    log.info("학습 결과 요약")
    log.info("=" * 60)
    passed = sum(1 for r in results.values() if r['meets_target'])
    for name, r in results.items():
        status = "✅ PASS" if r['meets_target'] else "❌ FAIL"
        log.info(f"{status} {name}: R²={r['r2']:.4f} MAPE={r['mape']*100:.2f}%")
        for region, rb in r.get('region_breakdown', {}).items():
            log.info(f"      {region}: R²={rb['r2']:.3f} MAPE={rb['mape']*100:.1f}% (n={rb['n']})")
    log.info(f"\n{passed}/{len(results)} 모델 목표 달성 (R²>{TARGET_R2}, MAPE<{TARGET_MAPE*100:.1f}%)")
    log.info(f"총 소요시간: {elapsed:.1f}초")

    save_training_report(results, output_dir, elapsed, args.country)

    if passed == len(results):
        log.info("\n✅ 모든 모델 목표 달성 - 엔진 배포 준비 완료")
    else:
        log.warning("\n⚠️ 일부 모델 목표 미달 - 데이터 추가 수집 또는 하이퍼파라미터 조정 필요")


if __name__ == '__main__':
    main()
