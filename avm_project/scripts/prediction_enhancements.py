"""예측 향상 기능: 캐싱, 신뢰도, 이상탐지"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from collections import OrderedDict
import numpy as np
from sklearn.ensemble import IsolationForest


@dataclass
class ConfidenceInterval:
    """신뢰도 구간 결과"""
    prediction: float
    lower: float
    upper: float
    std: float
    confidence: float

    def to_dict(self) -> Dict[str, float]:
        """결과를 딕셔너리로 변환"""
        return {
            'prediction': self.prediction,
            'lower_bound': self.lower,
            'upper_bound': self.upper,
            'std': self.std,
            'confidence': self.confidence,
        }


class PredictionCache:
    """LRU 캐시를 사용한 예측 캐싱"""
    def __init__(self, maxsize: int = 10000) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.hits = 0
        self.misses = 0

    def predict(self, model: Any, features: List[float]) -> float:
        """캐시에서 먼저 확인하고, 없으면 모델로 예측"""
        key = tuple(features)
        if key in self.cache:
            self.hits += 1
            return self.cache[key]

        self.misses += 1
        prediction = float(model.predict([features])[0])

        if len(self.cache) >= self.maxsize:
            self.cache.popitem(last=False)

        self.cache[key] = prediction
        return prediction

    def clear(self) -> None:
        """캐시 초기화"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def stats(self) -> Dict[str, int]:
        """캐시 통계"""
        return {'size': len(self.cache), 'maxsize': self.maxsize}

    @property
    def hit_rate(self) -> float:
        """캐시 히트율"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class ConfidenceEstimator:
    """신뢰도 구간 추정"""
    def __init__(self, model: Any, confidence: float = 0.95,
                 residual_std: Optional[float] = None) -> None:
        if confidence < 0.9 or confidence >= 1.0:
            raise ValueError("confidence must be between 0.9 and 1.0")
        self.model = model
        self.confidence = confidence
        self.residual_std = residual_std
        self.z_score = 1.96 if confidence == 0.95 else 2.576

    def estimate(self, features: List[float]) -> ConfidenceInterval:
        """신뢰도 구간 추정"""
        prediction = float(self.model.predict([features])[0])

        if self.residual_std is not None:
            std = self.residual_std
        else:
            std = abs(prediction) * 0.05

        margin = self.z_score * std
        return ConfidenceInterval(
            prediction=prediction,
            lower=prediction - margin,
            upper=prediction + margin,
            std=std,
            confidence=self.confidence
        )


class AnomalyDetector:
    """이상 탐지"""
    def __init__(self, contamination: float = 0.05) -> None:
        self.contamination = contamination
        self.detector = IsolationForest(
            contamination=contamination,
            random_state=42
        )
        self.fitted = False

    def fit(self, X: np.ndarray) -> 'AnomalyDetector':
        """이상 탐지 모델 학습"""
        self.detector.fit(X)
        self.fitted = True
        return self

    def is_anomaly(self, features: List[float]) -> bool:
        """이상 여부 판정"""
        if not self.fitted:
            raise RuntimeError("AnomalyDetector must be fitted first")
        prediction = self.detector.predict([features])[0]
        return bool(prediction == -1)

    def score(self, features: List[float]) -> float:
        """이상 점수 (낮을수록 이상)"""
        if not self.fitted:
            raise RuntimeError("AnomalyDetector must be fitted first")
        return float(self.detector.score_samples([features])[0])

    def evaluate(self, features: List[float]) -> Dict[str, Any]:
        """이상 탐지 결과"""
        is_anom = self.is_anomaly(features)
        score = self.score(features)
        return {
            'is_anomaly': is_anom,
            'anomaly_score': score,
            'interpretation': 'anomaly' if is_anom else 'normal'
        }
