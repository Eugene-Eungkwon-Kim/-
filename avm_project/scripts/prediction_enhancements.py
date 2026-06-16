"""
PHASE 4 - 예측 고급 기능 모듈

구현 항목:
  4.1.1 모델 캐싱        : LRU 기반 예측 결과 캐시 (반복 요청 응답시간 단축)
  4.2.1 신뢰도 추정      : 앙상블 분산 기반 예측 구간(신뢰구간) 계산
  4.2.2 이상탐지         : IsolationForest로 비정상 입력 탐지

외부 인프라(Redis 등) 없이 순수 Python/scikit-learn으로 동작하며
api_server.py 및 배치 예측에서 재사용 가능하도록 설계되었습니다.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
from sklearn.ensemble import IsolationForest


# ---------------------------------------------------------------------------
# 4.1.1 모델 캐싱
# ---------------------------------------------------------------------------
class PredictionCache:
    """LRU 예측 캐시.

    동일 특성 벡터에 대한 반복 예측을 메모리에 캐싱한다.
    스레드 안전성이 필요한 경우 호출측에서 락을 관리한다.
    """

    def __init__(self, maxsize: int = 10_000):
        if maxsize <= 0:
            raise ValueError("maxsize는 1 이상이어야 합니다")
        self.maxsize = maxsize
        self._store: OrderedDict[str, float] = OrderedDict()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def _key(features: Sequence[float]) -> str:
        return json.dumps([round(float(x), 6) for x in features], sort_keys=True)

    def get(self, features: Sequence[float]):
        key = self._key(features)
        if key in self._store:
            self._store.move_to_end(key)
            self.hits += 1
            return self._store[key]
        self.misses += 1
        return None

    def put(self, features: Sequence[float], value: float) -> None:
        key = self._key(features)
        self._store[key] = float(value)
        self._store.move_to_end(key)
        if len(self._store) > self.maxsize:
            self._store.popitem(last=False)  # 가장 오래된 항목 제거

    def predict(self, model, features: Sequence[float]) -> float:
        """캐시 우선 예측. 미스 시 모델 추론 후 캐싱."""
        cached = self.get(features)
        if cached is not None:
            return cached
        value = float(model.predict([list(features)])[0])
        self.put(features, value)
        return value

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def stats(self) -> dict:
        return {
            "size": len(self._store),
            "maxsize": self.maxsize,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate, 4),
        }

    def clear(self) -> None:
        self._store.clear()
        self.hits = 0
        self.misses = 0


# ---------------------------------------------------------------------------
# 4.2.1 신뢰도 추정
# ---------------------------------------------------------------------------
@dataclass
class PredictionInterval:
    """예측 신뢰구간 결과."""

    prediction: float
    lower: float
    upper: float
    std: float
    confidence: float

    def to_dict(self) -> dict:
        return {
            "prediction": round(self.prediction, 4),
            "lower_bound": round(self.lower, 4),
            "upper_bound": round(self.upper, 4),
            "std": round(self.std, 4),
            "confidence": self.confidence,
        }


class ConfidenceEstimator:
    """앙상블(트리) 분산 기반 신뢰구간 추정.

    트리 앙상블(RandomForest/GradientBoosting 등)의 개별 추정기 예측
    분산으로 불확실성을 정량화한다. 앙상블이 아닌 모델은 잔차 표준편차를
    사용하는 폴백 경로를 제공한다.
    """

    Z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}

    def __init__(self, model, confidence: float = 0.95, residual_std: float | None = None):
        if confidence not in self.Z:
            raise ValueError(f"confidence는 {list(self.Z)} 중 하나여야 합니다")
        self.model = model
        self.confidence = confidence
        self.residual_std = residual_std

    def _per_tree_predictions(self, features: Sequence[float]) -> np.ndarray | None:
        x = np.asarray([list(features)], dtype=float)
        estimators = getattr(self.model, "estimators_", None)
        if estimators is None:
            return None
        # GradientBoosting은 estimators_가 2D 배열
        flat = np.ravel(estimators)
        preds = []
        for est in flat:
            try:
                preds.append(float(est.predict(x)[0]))
            except Exception:  # noqa: BLE001 - 개별 추정기 실패는 무시
                continue
        return np.asarray(preds) if preds else None

    def estimate(self, features: Sequence[float]) -> PredictionInterval:
        point = float(self.model.predict([list(features)])[0])
        z = self.Z[self.confidence]

        per_tree = self._per_tree_predictions(features)
        if per_tree is not None and len(per_tree) > 1:
            std = float(per_tree.std())
        elif self.residual_std is not None:
            std = float(self.residual_std)
        else:
            # 정보가 없으면 점추정의 5%를 보수적 불확실성으로 사용
            std = abs(point) * 0.05

        margin = z * std
        return PredictionInterval(
            prediction=point,
            lower=point - margin,
            upper=point + margin,
            std=std,
            confidence=self.confidence,
        )


# ---------------------------------------------------------------------------
# 4.2.2 이상탐지
# ---------------------------------------------------------------------------
@dataclass
class AnomalyDetector:
    """IsolationForest 기반 입력 이상탐지.

    학습 데이터 분포에서 벗어난 예측 요청을 식별해 신뢰할 수 없는
    예측을 사전에 경고한다.
    """

    contamination: float = 0.05
    random_state: int = 42
    _model: IsolationForest = field(default=None, init=False, repr=False)
    _fitted: bool = field(default=False, init=False, repr=False)

    def fit(self, X) -> "AnomalyDetector":
        self._model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self._model.fit(np.asarray(X, dtype=float))
        self._fitted = True
        return self

    def _check_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError("AnomalyDetector가 학습되지 않았습니다. fit()을 먼저 호출하세요")

    def is_anomaly(self, features: Sequence[float]) -> bool:
        self._check_fitted()
        return bool(self._model.predict([list(features)])[0] == -1)

    def score(self, features: Sequence[float]) -> float:
        """이상 점수. 값이 낮을수록 이상(비정상)일 가능성이 높다."""
        self._check_fitted()
        return float(self._model.decision_function([list(features)])[0])

    def evaluate(self, features: Sequence[float]) -> dict:
        self._check_fitted()
        score = self.score(features)
        return {
            "is_anomaly": score < 0,
            "anomaly_score": round(score, 6),
            "interpretation": "비정상 입력" if score < 0 else "정상 입력",
        }
