#!/usr/bin/env python3
"""Phase 14.1.KR - Quantizer 단위 테스트 (순수 로직 검증)."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from phase14_1_kr_model_quantizer import (  # noqa: E402
    REGION_BY_MODEL,
    _mape,
    build_features,
    slice_region,
)


class TestBuildFeatures(unittest.TestCase):
    def setUp(self) -> None:
        self.df = pd.DataFrame({
            'region': ['Seoul', 'Busan'],
            'area_m2': [84.0, 60.0],
            'price_local': [5.0e8, 3.0e8],
            'indexed_price': [1.1, 1.0],
            'address': ['a', 'b'],
        })

    def test_removes_leak_and_nonnumeric_columns(self) -> None:
        X, y, cols = build_features(self.df)
        self.assertNotIn('price_local', cols)
        self.assertNotIn('indexed_price', cols)
        self.assertNotIn('address', cols)
        self.assertIn('area_m2', cols)

    def test_target_matches_price_local(self) -> None:
        _, y, _ = build_features(self.df)
        np.testing.assert_array_equal(y, np.array([5.0e8, 3.0e8]))

    def test_feature_matrix_is_float32(self) -> None:
        X, _, _ = build_features(self.df)
        self.assertEqual(X.dtype, np.float32)


class TestSliceRegion(unittest.TestCase):
    def setUp(self) -> None:
        self.df = pd.DataFrame({
            'region': ['Seoul', 'Seoul', 'Busan'],
            'price_local': [1, 2, 3],
        })

    def test_none_returns_full_frame(self) -> None:
        self.assertEqual(len(slice_region(self.df, None)), 3)

    def test_region_filters_rows(self) -> None:
        self.assertEqual(len(slice_region(self.df, 'Seoul')), 2)
        self.assertEqual(len(slice_region(self.df, 'Busan')), 1)


class TestMape(unittest.TestCase):
    def test_zero_error(self) -> None:
        y = np.array([100.0, 200.0])
        self.assertAlmostEqual(_mape(y, y), 0.0)

    def test_ten_percent_error(self) -> None:
        y_true = np.array([100.0, 200.0])
        y_pred = np.array([110.0, 220.0])
        self.assertAlmostEqual(_mape(y_true, y_pred), 0.10)


class TestRegionMapping(unittest.TestCase):
    def test_nationwide_has_no_region(self) -> None:
        self.assertIsNone(REGION_BY_MODEL['KR_nationwide_v1.0'])

    def test_all_regional_models_mapped(self) -> None:
        for model_id in ['KR_seoul_v1.0', 'KR_busan_v1.0', 'KR_gyeonggi_v1.0',
                         'KR_daegu_v1.0', 'KR_incheon_v1.0']:
            self.assertIsNotNone(REGION_BY_MODEL[model_id])


if __name__ == '__main__':
    unittest.main()
