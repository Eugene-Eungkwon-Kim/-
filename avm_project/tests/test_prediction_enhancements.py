"""PHASE 4 고급 기능 모듈 테스트 (캐싱 / 신뢰도 / 이상탐지)."""

import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from prediction_enhancements import (  # noqa: E402
    AnomalyDetector,
    ConfidenceEstimator,
    PredictionCache,
)


@pytest.fixture
def trained_rf():
    rng = np.random.default_rng(42)
    X = rng.uniform(0, 1, size=(200, 4))
    y = X @ np.array([3.0, -2.0, 1.5, 0.5]) + rng.normal(0, 0.01, 200)
    model = RandomForestRegressor(n_estimators=30, random_state=42)
    model.fit(X, y)
    return model, X, y


@pytest.fixture
def trained_linear():
    rng = np.random.default_rng(0)
    X = rng.uniform(0, 1, size=(100, 3))
    y = X @ np.array([1.0, 2.0, 3.0])
    model = LinearRegression().fit(X, y)
    return model, X


# --- PredictionCache ---
class TestPredictionCache:
    def test_miss_then_hit(self, trained_linear):
        model, X = trained_linear
        cache = PredictionCache(maxsize=10)
        feat = X[0].tolist()
        v1 = cache.predict(model, feat)
        v2 = cache.predict(model, feat)
        assert v1 == v2
        assert cache.hits == 1
        assert cache.misses == 1
        assert cache.hit_rate == 0.5

    def test_lru_eviction(self, trained_linear):
        model, X = trained_linear
        cache = PredictionCache(maxsize=2)
        for i in range(3):
            cache.predict(model, X[i].tolist())
        assert cache.stats()["size"] == 2

    def test_invalid_maxsize(self):
        with pytest.raises(ValueError):
            PredictionCache(maxsize=0)

    def test_clear_resets(self, trained_linear):
        model, X = trained_linear
        cache = PredictionCache()
        cache.predict(model, X[0].tolist())
        cache.clear()
        assert cache.stats()["size"] == 0
        assert cache.hits == 0


# --- ConfidenceEstimator ---
class TestConfidenceEstimator:
    def test_interval_contains_point(self, trained_rf):
        model, X, _ = trained_rf
        est = ConfidenceEstimator(model, confidence=0.95)
        result = est.estimate(X[0].tolist())
        assert result.lower <= result.prediction <= result.upper
        assert result.std >= 0
        assert result.confidence == 0.95

    def test_higher_confidence_wider_interval(self, trained_rf):
        model, X, _ = trained_rf
        feat = X[5].tolist()
        narrow = ConfidenceEstimator(model, 0.90).estimate(feat)
        wide = ConfidenceEstimator(model, 0.99).estimate(feat)
        assert (wide.upper - wide.lower) >= (narrow.upper - narrow.lower)

    def test_linear_fallback_residual(self, trained_linear):
        model, X = trained_linear
        est = ConfidenceEstimator(model, 0.95, residual_std=2.0)
        result = est.estimate(X[0].tolist())
        assert result.std == 2.0

    def test_invalid_confidence(self, trained_rf):
        model, _, _ = trained_rf
        with pytest.raises(ValueError):
            ConfidenceEstimator(model, confidence=0.80)

    def test_to_dict(self, trained_rf):
        model, X, _ = trained_rf
        result = ConfidenceEstimator(model).estimate(X[0].tolist())
        d = result.to_dict()
        assert {"prediction", "lower_bound", "upper_bound", "std", "confidence"} <= d.keys()


# --- AnomalyDetector ---
class TestAnomalyDetector:
    def test_requires_fit(self):
        det = AnomalyDetector()
        with pytest.raises(RuntimeError):
            det.is_anomaly([0.5, 0.5, 0.5, 0.5])

    def test_normal_vs_outlier(self, trained_rf):
        _, X, _ = trained_rf
        det = AnomalyDetector(contamination=0.05).fit(X)
        normal_point = X.mean(axis=0).tolist()
        outlier = (X.mean(axis=0) + 100).tolist()
        assert det.is_anomaly(outlier) is True
        # 분포 중심점은 정상으로 판정되어야 함
        assert det.is_anomaly(normal_point) is False

    def test_evaluate_structure(self, trained_rf):
        _, X, _ = trained_rf
        det = AnomalyDetector().fit(X)
        result = det.evaluate(X[0].tolist())
        assert "is_anomaly" in result
        assert "anomaly_score" in result
        assert "interpretation" in result

    def test_score_is_float(self, trained_rf):
        _, X, _ = trained_rf
        det = AnomalyDetector().fit(X)
        assert isinstance(det.score(X[0].tolist()), float)
