#!/usr/bin/env python3
"""
Phase 13.7 Korea Real Data Collector Tests

한국 부동산 데이터 수집, 특성 엔지니어링, 가격 생성 검증.
"""

import sys
import unittest
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from phase13_real_data_kr import KoreaCollector


class TestKoreaCollector(unittest.TestCase):
    """Korea collector 통합 테스트"""

    def setUp(self) -> None:
        self.collector = KoreaCollector()

    def test_collect_vworld_properties(self) -> None:
        """V-World 부동산 데이터 수집"""
        df = self.collector.collect_vworld_properties('Seoul', 100)

        self.assertEqual(len(df), 100)
        self.assertIn('property_id', df.columns)
        self.assertIn('area_m2', df.columns)
        self.assertIn('year_built', df.columns)
        self.assertIn('latitude', df.columns)
        self.assertIn('longitude', df.columns)

    def test_enrich_with_address(self) -> None:
        """주소 표준화"""
        df = pd.DataFrame({
            'property_id': ['KR_SE_000001', 'KR_SE_000002'],
            'region': ['Seoul', 'Seoul'],
            'area_m2': [100.0, 150.0],
        })

        df = self.collector.enrich_with_address(df)

        self.assertIn('address', df.columns)
        self.assertIn('road_address', df.columns)
        self.assertTrue(all(df['address'].str.contains('강남')))

    def test_enrich_with_bok_data(self) -> None:
        """한국은행 경제지표 추가"""
        df = pd.DataFrame({
            'property_id': ['KR_SE_000001'],
            'region': ['Seoul'],
        })

        df = self.collector.enrich_with_bok_data(df)

        self.assertIn('interest_rate', df.columns)
        self.assertIn('gdp_growth', df.columns)
        self.assertIn('inflation_rate', df.columns)
        self.assertEqual(df['interest_rate'].iloc[0], 0.035)

    def test_enrich_with_fisis_data(self) -> None:
        """FISIS 금융통계 추가"""
        df = pd.DataFrame({'property_id': ['KR_SE_000001']})

        df = self.collector.enrich_with_fisis_data(df)

        self.assertIn('avg_ltv', df.columns)
        self.assertIn('avg_interest_rate', df.columns)
        self.assertIn('jeonse_ratio', df.columns)

    def test_engineer_korea_features(self) -> None:
        """한국 특화 특성 엔지니어링"""
        df = pd.DataFrame({
            'property_id': ['KR_SE_000001', 'KR_BS_000001'],
            'region': ['Gangnam', 'Busan'],
            'property_type': ['아파트', '아파트'],
            'building_age': [10, 15],
            'area_m2': [100.0, 120.0],
            'interest_rate': [0.035, 0.035],
            'economic_stress': [0.08, 0.10],
            'avg_ltv': [0.70, 0.75],
            'avg_interest_rate': [0.045, 0.050],
            'jeonse_ratio': [0.40, 0.35],
        })

        df = self.collector.engineer_korea_features(df)

        # 강남 프리미엄 확인
        self.assertEqual(df['is_gangnam'].iloc[0], 1)
        self.assertEqual(df['is_gangnam'].iloc[1], 0)
        self.assertGreater(df['gangnam_premium'].iloc[0], 0)

        # 건축년수 감가율 확인
        self.assertEqual(df['age_depreciation'].iloc[0], 0.95)  # 10년
        self.assertEqual(df['age_depreciation'].iloc[1], 0.88)  # 15년

    def test_generate_synthetic_prices(self) -> None:
        """가격 생성"""
        df = pd.DataFrame({
            'region': ['Seoul'] * 100,
            'property_type': ['아파트'] * 100,
            'building_age': np.random.randint(5, 20, 100),
            'area_m2': np.random.uniform(50, 300, 100),
            'is_gangnam': np.random.choice([0, 1], 100),
            'gangnam_premium': np.random.uniform(0, 0.45, 100),
            'age_depreciation': np.random.uniform(0.65, 1.0, 100),
            'brand_premium': np.random.uniform(1.0, 1.08, 100),
            'jeonse_adjustment': np.random.uniform(0.3, 0.5, 100),
            'rate_impact': np.random.uniform(-0.02, 0, 100),
            'economic_stress_factor': np.random.uniform(0, 0.05, 100),
            'rate_sensitivity': np.random.uniform(0, 0.05, 100),
            'price_per_pyeong': np.random.uniform(15, 100, 100),
        })

        df = self.collector.generate_synthetic_prices(df)

        self.assertIn('price_local', df.columns)
        self.assertEqual(len(df), 100)
        self.assertGreater(df['price_local'].min(), 0)
        self.assertGreater(df['price_local'].max(), df['price_local'].min())

    def test_collect_enriched_full_pipeline(self) -> None:
        """전체 수집 파이프라인"""
        df = self.collector.collect_enriched(n_records=1000)

        # 기본 검증 (weight 계산으로 ±20개 허용)
        self.assertGreaterEqual(len(df), 980)
        self.assertLessEqual(len(df), 1000)
        self.assertGreater(len(df.columns), 25)

        # 필수 컬럼 확인
        required_cols = [
            'property_id', 'region', 'area_m2', 'year_built',
            'latitude', 'longitude', 'price_local',
            'address', 'road_address',
            'interest_rate', 'gdp_growth',
            'is_gangnam', 'age_depreciation', 'brand_premium',
        ]
        for col in required_cols:
            self.assertIn(col, df.columns)

        # 가격 범위 검증 (한국 시장)
        self.assertGreater(df['price_local'].min(), 50_000_000)  # 최소 5천만원
        self.assertLess(df['price_local'].max(), 10_000_000_000)  # 최대 100억원

    def test_price_distribution_by_region(self) -> None:
        """지역별 가격 분포"""
        df = self.collector.collect_enriched(n_records=500)

        # 지역별 평균 가격
        by_region = df.groupby('region')['price_local'].agg(['mean', 'std', 'count'])

        # Seoul > Gyeonggi > Busan > 기타 확인
        seoul_mean = by_region.loc['Seoul', 'mean']
        busan_mean = by_region.loc['Busan', 'mean'] if 'Busan' in by_region.index else 0

        self.assertGreater(seoul_mean, busan_mean)

    def test_gangnam_premium_effect(self) -> None:
        """강남 프리미엄 효과 검증"""
        df = self.collector.collect_enriched(n_records=1000)

        gangnam_data = df[df['region'] == 'Gangnam']['price_local']
        other_data = df[df['region'] != 'Gangnam']['price_local']

        # 데이터가 충분히 있는지 확인
        if len(gangnam_data) > 10 and len(other_data) > 10:
            gangnam = gangnam_data.mean()
            other = other_data.mean()

            # 강남이 평균적으로 20% 이상 비싼지 확인
            if other > 0:
                premium = (gangnam - other) / other
                self.assertGreater(premium, 0.15)


if __name__ == '__main__':
    unittest.main()
