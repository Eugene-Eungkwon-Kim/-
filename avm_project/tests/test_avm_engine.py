"""AVM Engine 통합 테스트 - 모든 컴포넌트 검증."""

import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.avm_feature_engineering import AVMFeatureEngineer
from scripts.avm_correction_layer import CorrectionLayer
from scripts.avm_auction_module import AuctionModule
from scripts.avm_validation_engine import ValidationEngine


# ── Feature Engineering ────────────────────────────────────────────────────────

class TestFeatureEngineer:
    def setup_method(self):
        self.eng = AVMFeatureEngineer()

    def test_normalize_range(self):
        features = np.array([100, 500000, 35.5, 126.8, 2], dtype=np.float32)
        result = self.eng.normalize(features)
        assert result.dtype == np.float32
        assert np.all(result >= 0.0) and np.all(result <= 1.0)

    def test_normalize_clips_outliers(self):
        features = np.array([9999, 9999999, 99, 99, 9], dtype=np.float32)
        result = self.eng.normalize(features)
        assert np.all(result <= 1.0)

    def test_normalize_wrong_shape(self):
        with pytest.raises(ValueError):
            self.eng.normalize(np.array([1, 2, 3], dtype=np.float32))

    def test_encode_property_type_known(self):
        assert self.eng.encode_property_type('apartment') == 1
        assert self.eng.encode_property_type('APARTMENT') == 1
        assert self.eng.encode_property_type('multi_family') == 2
        assert self.eng.encode_property_type('officetel') == 4

    def test_encode_property_type_unknown(self):
        assert self.eng.encode_property_type('unknown_type') == 1  # 기본값

    def test_encode_district_grade_valid(self):
        for i in range(1, 7):
            assert self.eng.encode_district_grade(str(i)) == i

    def test_encode_district_grade_invalid(self):
        assert self.eng.encode_district_grade('9') == 3  # 기본값

    def test_transform_complete(self):
        result = self.eng.transform({
            'area_sqm': 100, 'old_price': 500000,
            'latitude': 35.5, 'longitude': 126.8,
            'property_type': 'apartment',
        })
        assert result.shape == (5,)
        assert np.all(result >= 0.0) and np.all(result <= 1.0)

    def test_transform_missing_key(self):
        with pytest.raises(ValueError, match="Missing keys"):
            self.eng.transform({'area_sqm': 100})

    def test_create_derived_features(self):
        import pandas as pd
        df = pd.DataFrame({'area_sqm': [100], 'old_price': [500000]})
        result = self.eng.create_derived_features(df)
        assert 'price_per_sqm' in result.columns
        assert result['price_per_sqm'].iloc[0] == 5000.0

    def test_transform_korean_type(self):
        result = self.eng.transform({
            'area_sqm': 80, 'old_price': 300000,
            'latitude': 37.5, 'longitude': 127.0,
            'property_type': '아파트',
        })
        assert result.shape == (5,)


# ── Correction Layer ───────────────────────────────────────────────────────────

class TestCorrectionLayer:
    def setup_method(self):
        self.layer = CorrectionLayer()

    def test_region_correction_apartment_grade1(self):
        factor = self.layer.get_region_correction('apartment', '1')
        assert factor == 1.30

    def test_region_correction_apartment_grade6(self):
        factor = self.layer.get_region_correction('apartment', '6')
        assert factor == 1.20

    def test_region_correction_officetel(self):
        factor = self.layer.get_region_correction('officetel', '4')
        assert factor == 1.15

    def test_region_correction_unknown_type(self):
        factor = self.layer.get_region_correction('unknown', '3')
        assert factor == 1.20  # 기본값

    def test_temporal_adjustment_2024(self):
        assert self.layer.get_temporal_adjustment(2024) == 1.00

    def test_temporal_adjustment_2022(self):
        assert self.layer.get_temporal_adjustment(2022) == 0.88

    def test_apply_corrections_increases_price(self):
        price = self.layer.apply_corrections(1_000_000, 'apartment', '1', 2024)
        assert price == pytest.approx(1_300_000, rel=1e-3)

    def test_breakdown_keys(self):
        result = self.layer.get_correction_breakdown(1_000_000, 'apartment', '3')
        assert all(k in result for k in ['base_price', 'region_factor', 'corrected_price'])


# ── Auction Module ─────────────────────────────────────────────────────────────

class TestAuctionModule:
    def setup_method(self):
        self.auction = AuctionModule()

    def test_estimate_auction_price_normal_market(self):
        result = self.auction.estimate_auction_price(1_000_000, 'apartment', '3')
        assert result['estimated_auction_price'] == pytest.approx(1_260_000, rel=1e-3)

    def test_market_rising_increases_price(self):
        normal = self.auction.estimate_auction_price(1_000_000, 'apartment', '3', 'normal')
        rising = self.auction.estimate_auction_price(1_000_000, 'apartment', '3', 'rising')
        assert rising['estimated_auction_price'] > normal['estimated_auction_price']

    def test_market_declining_decreases_price(self):
        normal = self.auction.estimate_auction_price(1_000_000, 'apartment', '3', 'normal')
        declining = self.auction.estimate_auction_price(1_000_000, 'apartment', '3', 'declining')
        assert declining['estimated_auction_price'] < normal['estimated_auction_price']

    def test_result_keys(self):
        result = self.auction.estimate_auction_price(1_000_000, 'apartment', '3')
        keys = ['base_price', 'region_rate', 'market_factor', 'estimated_auction_price', 'confidence']
        assert all(k in result for k in keys)

    def test_confidence_range(self):
        result = self.auction.estimate_auction_price(1_000_000, 'apartment', '3')
        assert 0.0 <= result['confidence'] <= 1.0


# ── Validation Engine ──────────────────────────────────────────────────────────

class TestValidationEngine:
    def setup_method(self):
        self.validator = ValidationEngine()
        # 이상탐지 모델 학습 (간단한 더미 데이터)
        X = np.random.rand(200, 5).astype(np.float32)
        self.validator.fit(X)

    def test_check_anomaly_normal(self):
        features = np.array([0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float32)
        result = self.validator.check_anomaly(features)
        assert 'is_anomaly' in result
        assert isinstance(result['is_anomaly'], bool)

    def test_check_anomaly_not_fitted(self):
        v = ValidationEngine()
        result = v.check_anomaly(np.zeros(5, dtype=np.float32))
        assert result['status'] == 'not_fitted'

    def test_confidence_interval_width(self):
        ci = self.validator.estimate_confidence_interval(1_000_000)
        assert ci['upper_bound'] > ci['lower_bound']
        assert ci['lower_bound'] < 1_000_000 < ci['upper_bound']

    def test_confidence_interval_custom_std(self):
        ci = self.validator.estimate_confidence_interval(1_000_000, std=50000)
        assert ci['std'] == 50000

    def test_appraisal_acceptable(self):
        result = self.validator.check_appraisal_range(1_000_000, 1_050_000)
        assert result['status'] == 'acceptable'

    def test_appraisal_warning(self):
        result = self.validator.check_appraisal_range(1_000_000, 1_150_000)
        assert result['status'] == 'warning'

    def test_appraisal_critical(self):
        result = self.validator.check_appraisal_range(1_000_000, 1_500_000)
        assert result['status'] == 'critical'

    def test_validate_returns_all_keys(self):
        features = np.array([0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float32)
        result = self.validator.validate(features, 1_000_000)
        assert all(k in result for k in ['is_valid', 'risk_level', 'anomaly', 'confidence_interval'])

    def test_validate_with_appraisal(self):
        features = np.array([0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float32)
        result = self.validator.validate(features, 1_000_000, public_appraisal_price=1_200_000)
        assert result['appraisal_check'] is not None


# ── Core Engine (통합) ──────────────────────────────────────────────────────────

class TestCoreEngine:
    @pytest.fixture(scope='class')
    def engine(self):
        from scripts.avm_core_engine import AVMCoreEngine
        return AVMCoreEngine()

    def test_valuate_returns_price(self, engine):
        result = engine.valuate(
            area_sqm=100, old_price=500_000,
            latitude=35.5, longitude=126.8,
            property_type='apartment',
        )
        assert result['corrected_price'] > 0

    def test_valuate_confidence_range(self, engine):
        result = engine.valuate(
            area_sqm=100, old_price=500_000,
            latitude=35.5, longitude=126.8,
            property_type='apartment',
        )
        assert 0.0 <= result['confidence'] <= 1.0

    def test_valuate_all_keys(self, engine):
        result = engine.valuate(
            area_sqm=100, old_price=500_000,
            latitude=35.5, longitude=126.8,
            property_type='apartment',
        )
        keys = ['base_price', 'corrected_price', 'confidence',
                'validation_status', 'validation', 'auction_forecast',
                'latency_ms', 'model_version', 'timestamp']
        assert all(k in result for k in keys)

    def test_valuate_auction_forecast(self, engine):
        result = engine.valuate(
            area_sqm=100, old_price=500_000,
            latitude=35.5, longitude=126.8,
            property_type='apartment',
        )
        assert result['auction_forecast']['estimated_auction_price'] > 0

    def test_batch_valuate(self, engine):
        props = [
            {'area_sqm': 80, 'old_price': 400_000, 'latitude': 35.0,
             'longitude': 127.0, 'property_type': 'apartment'},
            {'area_sqm': 120, 'old_price': 600_000, 'latitude': 37.5,
             'longitude': 126.9, 'property_type': 'officetel'},
        ]
        results = engine.batch_valuate(props)
        assert len(results) == 2
        assert all(r['corrected_price'] > 0 for r in results)

    def test_engine_stats_keys(self, engine):
        stats = engine.get_engine_stats()
        assert all(k in stats for k in ['version', 'status', 'models', 'performance'])

    def test_cache_hit_after_repeat(self, engine):
        args = dict(area_sqm=100, old_price=500_000, latitude=35.5,
                    longitude=126.8, property_type='apartment')
        engine.valuate(**args)
        hits_before = engine.ensemble.cache_hits
        engine.valuate(**args)
        assert engine.ensemble.cache_hits > hits_before

    def test_latency_reasonable(self, engine):
        import time
        start = time.perf_counter()
        engine.valuate(
            area_sqm=100, old_price=500_000,
            latitude=35.5, longitude=126.8,
            property_type='apartment',
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500  # 500ms 이내 (CPU 폴백 포함)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
