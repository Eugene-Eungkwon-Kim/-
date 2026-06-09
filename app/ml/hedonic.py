from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler

if TYPE_CHECKING:
    from app.db.models import Complex, Transaction, Unit

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "exclusive_area",
    "floor",
    "build_year",
    "parking_cnt",
    "complex_size",
    "month",
]


class HedhonicPriceModel:
    """
    특성가격모형 (Hedonic Price Model)

    종속변수: log(거래가)
    설명변수: 면적, 층, 연식, 주차, 단지규모, 거래월
    """

    def __init__(self):
        self.model = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            random_state=42,
        )
        self.scaler = StandardScaler()
        self.feature_names: List[str] = FEATURE_NAMES
        self._fitted = False

    def extract_features(
        self,
        unit: "Unit",
        complex_obj: "Complex",
        transaction_month: int = 1,
    ) -> np.ndarray:
        """호실 + 단지 정보 → 특성 벡터"""
        return np.array(
            [
                unit.exclusive_area or 0,
                unit.floor or 0,
                complex_obj.build_year or 0,
                unit.parking_cnt or 0,
                complex_obj.total_units or 0,
                transaction_month,
            ],
            dtype=float,
        )

    def fit(self, transactions: List["Transaction"]) -> None:
        """학습 — 최소 100건 권장"""
        X, y = [], []
        for tx in transactions:
            if tx.unit is None or tx.complex is None:
                continue
            month = tx.contract_date.month if tx.contract_date else 1
            features = self.extract_features(tx.unit, tx.complex, month)
            X.append(features)
            y.append(np.log(float(tx.price)))

        if len(X) < 10:
            raise ValueError(f"학습 데이터 부족: {len(X)}건 (최소 10건)")

        X_arr = np.array(X)
        y_arr = np.array(y)
        X_scaled = self.scaler.fit_transform(X_arr)
        self.model.fit(X_scaled, y_arr)
        self._fitted = True
        logger.info("헤도닉 모델 학습 완료: %d건", len(X))

    def predict(self, unit: "Unit", complex_obj: "Complex", month: int = 1) -> float:
        """감정가 추정 (원화 단위)"""
        if not self._fitted:
            raise RuntimeError("모델 미학습 상태")
        features = self.extract_features(unit, complex_obj, month)
        X_scaled = self.scaler.transform(features.reshape(1, -1))
        log_price = self.model.predict(X_scaled)[0]
        return float(np.exp(log_price))

    def feature_importance(self) -> Dict[str, float]:
        if not self._fitted:
            raise RuntimeError("모델 미학습 상태")
        return dict(zip(self.feature_names, self.model.feature_importances_))

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info("헤도닉 모델 저장: %s", path)

    @classmethod
    def load(cls, path: str) -> "HedhonicPriceModel":
        with open(path, "rb") as f:
            return pickle.load(f)
