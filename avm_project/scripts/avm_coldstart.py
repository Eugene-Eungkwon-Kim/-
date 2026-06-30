"""WP 16: 콜드스타트 평가 — 직전 거래가 없이 펀더멘털만으로 가치 추정.

대출 담보 물건은 최근 실거래가 없는 경우가 많다. 메인 엔진은 old_price에
크게 의존(순열 중요도 0.93)하므로, 직전가가 없으면 평가가 불가능하다.
이 모듈은 면적·위경도·층·연식만으로 시세를 추정하는 별도 모델을 제공한다.

정직성: 펀더멘털만의 홀드아웃 R²≈0.86 / MAPE≈18%로, 직전가 기반(MAPE≈11%)보다
부정확하다. 직전가가 있으면 메인 엔진을, 없을 때만 이 콜드스타트를 쓴다.
(합성 데이터 기반이므로 절대 지표는 일반화 성능이 아님 — docs/LIMITATIONS.md 참조)

실행(학습):
    python scripts/avm_coldstart.py --data data/raw/KR_data.csv
"""

import argparse
import logging
import pickle
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

FUNDAMENTAL_COLS = ['area_sqm', 'latitude', 'longitude', 'floor', 'construction_year']
TARGET_COL = 'new_price'

# 펀더멘털 정규화 경계 (한국 부동산 범위)
FUND_MIN = np.array([10.0, 33.0, 124.0, 1.0, 1960.0], dtype=np.float32)
FUND_MAX = np.array([500.0, 38.5, 132.0, 60.0, 2024.0], dtype=np.float32)

MODEL_FILENAME = 'coldstart_KR.pkl'


def _normalize(X: np.ndarray) -> np.ndarray:
    return np.clip((X - FUND_MIN) / (FUND_MAX - FUND_MIN), 0.0, 1.0).astype(np.float32)


class ColdStartEstimator:
    """직전가 없이 펀더멘털만으로 시세를 추정."""

    def __init__(self, model_dir: str = 'output/trained_models') -> None:
        self.model_dir = Path(model_dir)
        self.model: Optional[object] = None
        self._load()

    def _load(self) -> None:
        path = self.model_dir / MODEL_FILENAME
        if path.exists():
            with open(path, 'rb') as f:
                self.model = pickle.load(f)
            log.info(f"ColdStart model loaded: {path}")

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    def estimate(
        self,
        area_sqm: float,
        latitude: float,
        longitude: float,
        floor: int = 5,
        construction_year: int = 2005,
    ) -> float:
        """펀더멘털 → 시세 추정(원). 모델 미학습 시 ValueError."""
        if self.model is None:
            raise ValueError("ColdStart model not trained — run avm_coldstart.py first")
        x = _normalize(np.array([[area_sqm, latitude, longitude, floor, construction_year]],
                                dtype=np.float32))
        return float(self.model.predict(x)[0])


def _split(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """시간 기반 80/20 분할."""
    if 'transaction_month' in df.columns:
        df = df.sort_values('transaction_month').reset_index(drop=True)
    cut = int(len(df) * 0.80)
    X = _normalize(df[FUNDAMENTAL_COLS].values.astype(np.float32))
    y = df[TARGET_COL].values.astype(np.float64)
    return X[:cut], X[cut:], y[:cut], y[cut:]


def train(data_path: str, model_dir: str = 'output/trained_models') -> Dict[str, float]:
    """펀더멘털 콜드스타트 모델 학습 및 저장."""
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.metrics import mean_absolute_percentage_error, r2_score

    df = pd.read_csv(data_path).dropna(subset=FUNDAMENTAL_COLS + [TARGET_COL])
    X_train, X_test, y_train, y_test = _split(df)

    model = GradientBoostingRegressor(
        n_estimators=400, max_depth=5, learning_rate=0.05,
        subsample=0.8, random_state=42,
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    metrics = {
        'r2': round(float(r2_score(y_test, y_pred)), 4),
        'mape': round(float(mean_absolute_percentage_error(y_test, y_pred)), 4),
        'n_train': len(X_train),
        'n_test': len(X_test),
    }

    out_dir = Path(model_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / MODEL_FILENAME, 'wb') as f:
        pickle.dump(model, f)

    log.info(f"ColdStart 학습 완료: R²={metrics['r2']:.4f} MAPE={metrics['mape']*100:.1f}% "
             f"(train={metrics['n_train']}, test={metrics['n_test']})")
    log.info(f"  저장: {out_dir / MODEL_FILENAME}")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description='콜드스타트(펀더멘털) 모델 학습')
    parser.add_argument('--data',   default='data/raw/KR_data.csv')
    parser.add_argument('--output', default='output/trained_models')
    args = parser.parse_args()
    train(args.data, args.output)


if __name__ == '__main__':
    main()
