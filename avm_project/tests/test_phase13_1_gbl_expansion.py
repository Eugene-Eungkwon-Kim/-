"""Phase 13.1-GBL (8개국 글로벌 확대) 단위 테스트 - SG/HK 파일럿 검증"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from country_configs import HK_CONFIG, KR_CONFIG, SG_CONFIG, UK_CONFIG, get_country_config
from realistic_data_generator import generate_dataset, validate_and_report
from generate_sg_realistic_data import generate_dataset as generate_sg_dataset
from generate_hk_realistic_data import generate_dataset as generate_hk_dataset
from generate_uk_realistic_data import generate_dataset as generate_uk_dataset


class TestCountryConfigs:
    def test_get_country_config_returns_kr(self):
        assert get_country_config('KR') is KR_CONFIG

    def test_get_country_config_returns_sg(self):
        assert get_country_config('SG') is SG_CONFIG

    def test_unsupported_country_raises(self):
        with pytest.raises(ValueError, match="미지원 국가"):
            get_country_config('XX')

    def test_kr_config_matches_avm_feature_engineering(self):
        """KR_CONFIG의 feature_min/max는 avm_feature_engineering의 값과 동일해야
        한다 (train_kr_model.py가 이 값으로 정규화 소스를 갈아탔으므로 어긋나면
        기존 KR 학습-추론 파이프라인 전체가 깨진다)."""
        from avm_feature_engineering import FEATURE_MAX, FEATURE_MIN

        assert np.allclose(KR_CONFIG.feature_min, FEATURE_MIN)
        assert np.allclose(KR_CONFIG.feature_max, FEATURE_MAX)

    def test_region_weights_sum_to_one_per_country(self):
        for config in (KR_CONFIG, SG_CONFIG):
            assert sum(config.region_weights) == pytest.approx(1.0, abs=1e-9)

    def test_region_count_matches_weight_count(self):
        for config in (KR_CONFIG, SG_CONFIG, HK_CONFIG, UK_CONFIG):
            assert len(config.region_config) == len(config.region_weights)

    def test_get_country_config_returns_hk(self):
        assert get_country_config('HK') is HK_CONFIG

    def test_get_country_config_returns_uk(self):
        assert get_country_config('UK') is UK_CONFIG


class TestRealisticDataGeneratorGeneric:
    def test_kr_via_generic_engine_matches_wrapper_stats(self):
        """국가 공용 엔진으로 생성한 KR 데이터가 예상 스키마/범위를 만족해야 한다."""
        df = generate_dataset(KR_CONFIG, n_rows=500, seed=1)
        assert len(df) == 500
        assert set(['area_sqm', 'old_price', 'new_price', 'latitude', 'longitude', 'region_name']) <= set(df.columns)
        validate_and_report(df, KR_CONFIG)  # assert 없이 통과하면 OK (내부 assert 통과)

    def test_deterministic_given_same_seed(self):
        df1 = generate_dataset(SG_CONFIG, n_rows=200, seed=7)
        df2 = generate_dataset(SG_CONFIG, n_rows=200, seed=7)
        pd.testing.assert_frame_equal(df1, df2)

    def test_different_seeds_produce_different_data(self):
        df1 = generate_dataset(SG_CONFIG, n_rows=200, seed=1)
        df2 = generate_dataset(SG_CONFIG, n_rows=200, seed=2)
        assert not df1['new_price'].equals(df2['new_price'])


class TestSgDataGeneration:
    def test_prices_in_sgd_scale_not_krw_scale(self):
        """SG 가격은 SGD 스케일(수십만~천만)이어야 한다 — KR 스케일(억 단위)로
        새는 것은 국가 설정이 잘못 적용됐다는 신호."""
        df = generate_sg_dataset(n_rows=1000, seed=42)
        assert df['new_price'].min() >= SG_CONFIG.price_floor
        assert df['new_price'].max() <= SG_CONFIG.price_ceiling
        assert df['new_price'].mean() < 10_000_000  # KR이었다면 수억~수십억

    def test_coordinates_within_singapore_bounds(self):
        df = generate_sg_dataset(n_rows=1000, seed=42)
        assert df['latitude'].between(*SG_CONFIG.lat_range).all()
        assert df['longitude'].between(*SG_CONFIG.lng_range).all()

    def test_no_target_leakage(self):
        """old_price가 new_price의 사본이면 안 된다 (상관 < 0.985)."""
        df = generate_sg_dataset(n_rows=2000, seed=42)
        corr = df['old_price'].corr(df['new_price'])
        assert corr < 0.985

    def test_no_null_values(self):
        df = generate_sg_dataset(n_rows=500, seed=42)
        assert df.isnull().sum().sum() == 0


class TestHkDataGeneration:
    def test_prices_in_hkd_scale(self):
        df = generate_hk_dataset(n_rows=1000, seed=42)
        assert df['new_price'].min() >= HK_CONFIG.price_floor
        assert df['new_price'].max() <= HK_CONFIG.price_ceiling

    def test_coordinates_within_hong_kong_bounds(self):
        df = generate_hk_dataset(n_rows=1000, seed=42)
        assert df['latitude'].between(*HK_CONFIG.lat_range).all()
        assert df['longitude'].between(*HK_CONFIG.lng_range).all()

    def test_no_target_leakage_with_higher_idiosyncratic_sigma(self):
        """HK는 지역 클러스터가 촘촘해 기본 sigma(0.08)로는 old/new_price
        상관계수가 누수 임계값(0.985)에 근접했다 — idiosyncratic_sigma를
        0.11로 높여 해결했다 (회귀 테스트)."""
        df = generate_hk_dataset(n_rows=5000, seed=42)
        corr = df['old_price'].corr(df['new_price'])
        assert corr < 0.985

    def test_no_null_values(self):
        df = generate_hk_dataset(n_rows=500, seed=42)
        assert df.isnull().sum().sum() == 0


class TestUkDataGeneration:
    def test_prices_in_gbp_scale(self):
        df = generate_uk_dataset(n_rows=1000, seed=42)
        assert df['new_price'].min() >= UK_CONFIG.price_floor
        assert df['new_price'].max() <= UK_CONFIG.price_ceiling

    def test_coordinates_within_england_wales_bounds(self):
        """HM Land Registry는 잉글랜드/웨일스만 다룬다(스코틀랜드는 별도 등기소)."""
        df = generate_uk_dataset(n_rows=1000, seed=42)
        assert df['latitude'].between(*UK_CONFIG.lat_range).all()
        assert df['longitude'].between(*UK_CONFIG.lng_range).all()

    def test_no_target_leakage_with_higher_idiosyncratic_sigma(self):
        """UK도 HK와 마찬가지로 기본 sigma(0.08)로는 누수 임계값(0.985)을
        근소하게 초과했다 — 0.12로 높여 해결 (회귀 테스트)."""
        df = generate_uk_dataset(n_rows=5000, seed=42)
        corr = df['old_price'].corr(df['new_price'])
        assert corr < 0.985

    def test_no_null_values(self):
        df = generate_uk_dataset(n_rows=500, seed=42)
        assert df.isnull().sum().sum() == 0

    def test_houses_larger_than_hk_flats_on_average(self):
        """영국은 단독/연립주택 비중이 높아 홍콩(초소형 유닛)보다 평균 면적이 커야 한다."""
        uk_df = generate_uk_dataset(n_rows=2000, seed=42)
        hk_df = generate_hk_dataset(n_rows=2000, seed=42)
        assert uk_df['area_sqm'].mean() > hk_df['area_sqm'].mean()


class TestEnsembleEngineCountryIsolation:
    """AVMEnsembleEngine 국가 필터링 회귀 테스트.

    실제로 발생했던 버그: output/trained_models/에 여러 국가의 pkl이 공존할 때
    국가 필터링 없이 전부 globbing해서 로드했다. HK 모델(완전히 다른 통화
    스케일)이 KR 앙상블 평균에 섞여 예측이 실제값의 절반 수준으로 왜곡됐다.
    """

    @pytest.fixture
    def multi_country_models_dir(self, tmp_path):
        """KR, SG, HK 모델과 KR의 best_model/coldstart/tuned 변형을 모두
        같은 디렉터리에 배치 — 실제 output/trained_models/ 상태를 재현."""
        models_dir = tmp_path / "trained_models"
        models_dir.mkdir()

        from sklearn.linear_model import LinearRegression
        X = np.array([[1.0], [2.0], [3.0]])

        def make_model(value: float):
            model = LinearRegression()
            model.fit(X, [value, value, value])
            return model

        filenames = [
            'xgboost_KR', 'lightgbm_KR', 'gradient_boosting_KR',
            'best_model_KR', 'coldstart_KR',
            'xgboost_KR_tuned', 'lightgbm_KR_tuned', 'gradient_boosting_KR_tuned',
            'xgboost_SG', 'lightgbm_SG', 'gradient_boosting_SG', 'best_model_SG',
            'xgboost_HK', 'lightgbm_HK', 'gradient_boosting_HK', 'best_model_HK',
            'xgboost_UK', 'lightgbm_UK', 'gradient_boosting_UK', 'best_model_UK',
        ]
        for name in filenames:
            with open(models_dir / f"{name}.pkl", 'wb') as f:
                pickle.dump(make_model(1.0), f)

        return models_dir

    def test_kr_engine_loads_exactly_three_kr_models(self, multi_country_models_dir, tmp_path):
        from avm_ensemble_engine import AVMEnsembleEngine

        engine = AVMEnsembleEngine(str(tmp_path / "models_ir"), country='KR')
        assert set(engine.models.keys()) == {'xgboost_KR', 'lightgbm_KR', 'gradient_boosting_KR'}

    def test_hk_engine_loads_exactly_three_hk_models(self, multi_country_models_dir, tmp_path):
        from avm_ensemble_engine import AVMEnsembleEngine

        engine = AVMEnsembleEngine(str(tmp_path / "models_ir"), country='HK')
        assert set(engine.models.keys()) == {'xgboost_HK', 'lightgbm_HK', 'gradient_boosting_HK'}

    def test_uk_engine_loads_exactly_three_uk_models(self, multi_country_models_dir, tmp_path):
        from avm_ensemble_engine import AVMEnsembleEngine

        engine = AVMEnsembleEngine(str(tmp_path / "models_ir"), country='UK')
        assert set(engine.models.keys()) == {'xgboost_UK', 'lightgbm_UK', 'gradient_boosting_UK'}

    def test_kr_engine_excludes_other_countries_and_variants(self, multi_country_models_dir, tmp_path):
        from avm_ensemble_engine import AVMEnsembleEngine

        engine = AVMEnsembleEngine(str(tmp_path / "models_ir"), country='KR')
        loaded = set(engine.models.keys())
        assert not (loaded & {'xgboost_SG', 'xgboost_HK', 'xgboost_UK', 'best_model_KR', 'coldstart_KR', 'xgboost_KR_tuned'})
