"""Phase 13.3 model validator 핵심 함수 단위 테스트"""
import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.linear_model import LinearRegression

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from phase13_model_validator import (
    cross_validate_model,
    extract_feature_importance,
    select_best_model,
)


@pytest.fixture
def toy_regression_data():
    rng = np.random.RandomState(42)
    X = rng.rand(200, 5)
    y = X[:, 0] * 100 + rng.rand(200) * 0.1
    return X, y


class TestSelectBestModel:
    def test_picks_higher_r2_when_mape_equal(self):
        results = {
            'a': {'tuned_r2': 0.90, 'test_mape': 0.10},
            'b': {'tuned_r2': 0.95, 'test_mape': 0.10},
        }
        assert select_best_model(results) == 'b'

    def test_picks_lower_mape_when_r2_equal(self):
        results = {
            'a': {'tuned_r2': 0.90, 'test_mape': 0.12},
            'b': {'tuned_r2': 0.90, 'test_mape': 0.08},
        }
        assert select_best_model(results) == 'b'

    def test_single_model_is_selected(self):
        results = {'only': {'tuned_r2': 0.5, 'test_mape': 0.2}}
        assert select_best_model(results) == 'only'


class TestCrossValidateModel:
    def test_returns_expected_keys(self, toy_regression_data):
        X, y = toy_regression_data
        result = cross_validate_model(LinearRegression(), X, y, n_splits=5)
        assert set(result.keys()) == {'r2_mean', 'r2_std', 'r2_folds'}
        assert len(result['r2_folds']) == 5

    def test_r2_mean_matches_folds_average(self, toy_regression_data):
        X, y = toy_regression_data
        result = cross_validate_model(LinearRegression(), X, y, n_splits=5)
        assert result['r2_mean'] == pytest.approx(np.mean(result['r2_folds']), abs=1e-9)

    def test_good_fit_yields_high_r2(self, toy_regression_data):
        X, y = toy_regression_data
        result = cross_validate_model(LinearRegression(), X, y, n_splits=5)
        assert result['r2_mean'] > 0.9  # y는 X[:, 0]에 거의 선형 종속


class TestExtractFeatureImportance:
    def test_builtin_and_permutation_cover_all_features(self, toy_regression_data):
        from train_kr_model import FEATURE_COLS
        X, y = toy_regression_data
        model = LinearRegression().fit(X, y)
        importance = extract_feature_importance(model, X, y)
        assert set(importance['permutation'].keys()) == set(FEATURE_COLS)

    def test_dominant_feature_has_highest_permutation_importance(self, toy_regression_data):
        X, y = toy_regression_data
        model = LinearRegression().fit(X, y)
        importance = extract_feature_importance(model, X, y)
        top_feature = max(importance['permutation'], key=importance['permutation'].get)
        assert top_feature == 'area_sqm'  # FEATURE_COLS[0], y가 X[:, 0]에 종속
