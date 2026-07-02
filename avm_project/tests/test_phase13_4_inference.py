"""Phase 13.4 NPU 추론 엔진 & 모델 컨버터 단위 테스트"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from phase13_npu_inference import (
    ENSEMBLE_BASE_MODELS,
    _backend_name,
    preprocess_input,
)
from phase13_model_converter import _select_converter, ENSEMBLE_MODEL_KEYS


class TestPreprocessInput:
    def test_matches_training_normalization_range(self):
        """old_price 정규화 범위가 avm_feature_engineering의 학습 범위와 일치해야 한다.

        회귀 테스트: 과거에 이 함수가 old_price max를 5,000,000으로 하드코딩해
        실제 학습 범위(6,000,000,000)와 1000배 어긋나는 학습-추론 스큐 버그가 있었다.
        """
        from avm_feature_engineering import FEATURE_MAX, FEATURE_MIN

        features = FEATURE_MAX.copy()
        normalized = preprocess_input(features)
        assert normalized == pytest.approx(np.ones(5), abs=1e-5)

        features = FEATURE_MIN.copy()
        normalized = preprocess_input(features)
        assert normalized == pytest.approx(np.zeros(5), abs=1e-5)

    def test_realistic_old_price_does_not_saturate(self):
        """800M원(현실적 old_price)은 정규화 후 1.0으로 잘리면(saturate) 안 된다."""
        features = np.array([84.0, 800_000_000.0, 37.5, 127.0, 1.0], dtype=np.float32)
        normalized = preprocess_input(features)
        assert 0.0 < normalized[1] < 1.0

    def test_output_clipped_to_unit_range(self):
        features = np.array([-100.0, -1.0, 100.0, 200.0, 10.0], dtype=np.float32)
        normalized = preprocess_input(features)
        assert np.all(normalized >= 0.0) and np.all(normalized <= 1.0)


class TestBackendName:
    def test_sklearn_model_reports_pkl_backend(self):
        from sklearn.linear_model import LinearRegression
        model = LinearRegression().fit([[1], [2]], [1, 2])
        assert _backend_name(model) == 'sklearn pkl (CPU)'


class TestEnsembleBaseModels:
    def test_excludes_best_model_and_coldstart(self):
        """best_model_KR(단일모델용, 중복)과 coldstart_KR(별도 목적)은 앙상블에서 제외."""
        assert 'best_model_KR' not in ENSEMBLE_BASE_MODELS
        assert 'coldstart_KR' not in ENSEMBLE_BASE_MODELS
        assert set(ENSEMBLE_BASE_MODELS) == {'xgboost_KR', 'lightgbm_KR', 'gradient_boosting_KR'}


class TestSelectConverter:
    def test_sklearn_model_uses_generic_converter(self):
        from phase13_model_converter import convert_sklearn_native
        from sklearn.ensemble import GradientBoostingRegressor
        model = GradientBoostingRegressor()
        assert _select_converter(model) is convert_sklearn_native

    def test_ensemble_model_keys_includes_best_model(self):
        """best_model_KR(Phase 13.3 선정 모델)은 변환 대상에 포함되어야 한다."""
        assert 'best_model_KR' in ENSEMBLE_MODEL_KEYS
