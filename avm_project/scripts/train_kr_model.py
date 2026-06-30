"""
KR 데이터 전용 모델 학습 스크립트
KR_data.csv → XGBoost/LightGBM/GradientBoosting 학습 → output/trained_models/

실행:
    python train_kr_model.py --data data/raw/KR_data.csv
"""

import argparse
import logging
import pickle
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_percentage_error
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


def split_data(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """학습/검증 분할 (70/30)."""
    X = df[FEATURE_COLS].values.astype(np.float32)
    y = df[TARGET_COL].values.astype(np.float64)
    return train_test_split(X, y, test_size=0.30, random_state=42)


def evaluate(y_true: np.ndarray, y_pred: np.ndarray, model_name: str) -> Dict:
    """R², MAPE 평가."""
    r2 = r2_score(y_true, y_pred)
    mape = mean_absolute_percentage_error(y_true, y_pred)
    meets = r2 >= TARGET_R2 and mape <= TARGET_MAPE

    status = "✅ PASS" if meets else "❌ FAIL"
    log.info(f"  {model_name}: R²={r2:.4f} MAPE={mape*100:.2f}% {status}")

    return {'r2': r2, 'mape': mape, 'meets_target': meets}


def train_xgboost(X_train: np.ndarray, y_train: np.ndarray) -> object:
    """XGBoost 학습."""
    try:
        import xgboost as xgb
        params = {
            'n_estimators': 500, 'max_depth': 6, 'learning_rate': 0.05,
            'subsample': 0.8, 'colsample_bytree': 0.8,
            'random_state': 42, 'n_jobs': -1,
        }
        # GPU 가용 시 사용
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


def save_model(model: object, name: str, output_dir: Path) -> None:
    """모델 저장."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}_KR.pkl"
    with open(path, 'wb') as f:
        pickle.dump(model, f)
    size_mb = path.stat().st_size / 1024 / 1024
    log.info(f"  저장: {path} ({size_mb:.2f} MB)")


def main():
    parser = argparse.ArgumentParser(description='KR AVM 모델 학습')
    parser.add_argument('--data', default='data/raw/KR_data.csv', help='KR 데이터 CSV 경로')
    parser.add_argument('--output', default='output/trained_models', help='모델 저장 경로')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("KR AVM 모델 학습 시작")
    log.info("=" * 60)

    df = load_and_validate(args.data)
    X_train, X_test, y_train, y_test = split_data(df)
    log.info(f"학습: {len(X_train):,}건 | 검증: {len(X_test):,}건")

    output_dir = Path(args.output)
    results = {}

    trainers = {
        'xgboost': train_xgboost,
        'lightgbm': train_lightgbm,
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
        save_model(model, name, output_dir)
        results[name] = result

    # 결과 요약
    log.info("\n" + "=" * 60)
    log.info("학습 결과 요약")
    log.info("=" * 60)
    passed = sum(1 for r in results.values() if r['meets_target'])
    for name, r in results.items():
        status = "✅ PASS" if r['meets_target'] else "❌ FAIL"
        log.info(f"{status} {name}: R²={r['r2']:.4f} MAPE={r['mape']*100:.2f}%")
    log.info(f"\n{passed}/{len(results)} 모델 목표 달성 (R² > {TARGET_R2}, MAPE < {TARGET_MAPE*100}%)")

    if passed == len(results):
        log.info("\n✅ 모든 모델 목표 달성 - 엔진 배포 준비 완료")
    else:
        log.warning("\n⚠️ 일부 모델 목표 미달 - 데이터 추가 수집 또는 하이퍼파라미터 조정 필요")


if __name__ == '__main__':
    main()
