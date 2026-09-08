"""Phase 13.4 NPU 추론 엔진 & 모델 컨버터 단위 테스트"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from phase13_npu_inference import (
    ENSEMBLE_BASE_MODEL_TYPES,
    _backend_name,
    preprocess_input,
)
from phase13_model_converter import _select_converter, ENSEMBLE_MODEL_TYPES


class TestPreprocessInput:
    def test_matches_training_normalization_range(self):
        """old_price 정규화 범위가 avm_feature_engineering의 학습 범위와 일치해야 한다.

        회귀 테스트: 과거에 이 함수가 old_price max를 5,000,000으로 하드코딩해
        실제 학습 범위(6,000,000,000)와 1000배 어긋나는 학습-추론 스큐 버그가 있었다.
        """
        from avm_feature_engineering import FEATURE_MAX, FEATURE_MIN

        features = FEATURE_MAX.copy()
        normalized = preprocess_input(features, country='KR')
        assert normalized == pytest.approx(np.ones(5), abs=1e-5)

        features = FEATURE_MIN.copy()
        normalized = preprocess_input(features, country='KR')
        assert normalized == pytest.approx(np.zeros(5), abs=1e-5)

    def test_realistic_old_price_does_not_saturate(self):
        """800M원(현실적 old_price)은 정규화 후 1.0으로 잘리면(saturate) 안 된다."""
        features = np.array([84.0, 800_000_000.0, 37.5, 127.0, 1.0], dtype=np.float32)
        normalized = preprocess_input(features, country='KR')
        assert 0.0 < normalized[1] < 1.0

    def test_output_clipped_to_unit_range(self):
        features = np.array([-100.0, -1.0, 100.0, 200.0, 10.0], dtype=np.float32)
        normalized = preprocess_input(features, country='KR')
        assert np.all(normalized >= 0.0) and np.all(normalized <= 1.0)

    def test_sg_uses_different_normalization_range(self):
        """SG는 KR과 다른(훨씬 작은 SGD 스케일) 정규화 범위를 사용해야 한다."""
        features = np.array([80.0, 1_500_000.0, 1.30, 103.85, 1.0], dtype=np.float32)
        normalized_sg = preprocess_input(features, country='SG')
        normalized_kr = preprocess_input(features, country='KR')
        assert not np.allclose(normalized_sg, normalized_kr)


class TestBackendName:
    def test_sklearn_model_reports_pkl_backend(self):
        from sklearn.linear_model import LinearRegression
        model = LinearRegression().fit([[1], [2]], [1, 2])
        assert _backend_name(model) == 'sklearn pkl (CPU)'


class TestEnsembleBaseModels:
    def test_excludes_best_model_and_coldstart(self):
        """best_model(단일모델용, 중복)과 coldstart(별도 목적)는 앙상블에서 제외 (국가 무관)."""
        assert 'best_model' not in ENSEMBLE_BASE_MODEL_TYPES
        assert 'coldstart' not in ENSEMBLE_BASE_MODEL_TYPES
        assert set(ENSEMBLE_BASE_MODEL_TYPES) == {'xgboost', 'lightgbm', 'gradient_boosting'}


class TestSelectConverter:
    def test_sklearn_model_uses_generic_converter(self):
        from phase13_model_converter import convert_sklearn_native
        from sklearn.ensemble import GradientBoostingRegressor
        model = GradientBoostingRegressor()
        assert _select_converter(model) is convert_sklearn_native

    def test_ensemble_model_types_includes_best_model(self):
        """best_model(Phase 13.3 선정 모델)은 변환 대상에 포함되어야 한다 (국가 무관)."""
        assert 'best_model' in ENSEMBLE_MODEL_TYPES
