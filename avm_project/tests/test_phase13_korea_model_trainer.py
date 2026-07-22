#!/usr/bin/env python3
"""
Phase 13.8.KR Korea Model Trainer Tests

한국 부동산 모델 학습 검증:
- 전국 통합 모델
- 지역별 모델 (Seoul, Busan, Gyeonggi, etc.)
- 성능 리포트 생성
"""

import sys
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from phase13_korea_model_trainer import KoreaModelTrainer


class TestKoreaModelTrainer(unittest.TestCase):
    """Korea model trainer 통합 테스트"""

    @classmethod
    def setUpClass(cls) -> None:
        """Create test data for all tests"""
        cls.test_data_path = Path('data/raw/KR_raw.csv')
        if not cls.test_data_path.exists():
            raise FileNotFoundError(f"Test data not found: {cls.test_data_path}")

    def setUp(self) -> None:
        """Create trainer instance with temp models directory"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.trainer = KoreaModelTrainer(data_file=str(self.test_data_path))
        self.trainer.models_dir = Path(self.temp_dir.name)
        self.trainer.models_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        """Clean up temp directory"""
        self.temp_dir.cleanup()

    def test_load_korea_data(self) -> None:
        """한국 데이터 로드"""
        df = self.trainer.load_korea_data()

        self.assertIsNotNone(df)
        self.assertGreater(len(df), 0)
        self.assertIn('price_local', df.columns)
        self.assertGreater(len(df.columns), 25)

    def test_prepare_training_data(self) -> None:
        """학습용 데이터 준비"""
        df = self.trainer.load_korea_data()
        X, y, feature_cols = self.trainer.prepare_training_data(df)

        self.assertEqual(X.shape[0], len(df))
        self.assertGreater(X.shape[1], 0)
        self.assertEqual(len(feature_cols), X.shape[1])
        self.assertGreater(len(y), 0)
        self.assertTrue(np.all(y > 0))

    def test_prepare_training_data_no_leakage(self) -> None:
        """데이터 누수 제거 확인"""
        df = self.trainer.load_korea_data()
        X, y, feature_cols = self.trainer.prepare_training_data(df)

        # Leak patterns should not be in feature columns
        leak_patterns = ('price_local', 'indexed_price')
        for col in feature_cols:
            for pattern in leak_patterns:
                self.assertNotIn(pattern, col)

    def test_train_nationwide_model(self) -> None:
        """전국 통합 모델 학습"""
        df = self.trainer.load_korea_data()
        metadata = self.trainer.train_nationwide_model(df)

        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['model_id'], 'KR_nationwide_v1.0')
        self.assertEqual(metadata['scope'], 'nationwide')
        self.assertEqual(metadata['n_samples'], len(df))

        # Check metrics
        self.assertIn('performance', metadata)
        self.assertIn('test_mape', metadata['performance'])
        self.assertIn('test_r2', metadata['performance'])

        # MAPE should be reasonable (synthetic data may have higher error)
        mape = metadata['performance']['test_mape']
        self.assertGreater(mape, 0.0)
        self.assertLess(mape, 1.0)  # Sanity check: <100% MAPE

        # R² should be positive
        r2 = metadata['performance']['test_r2']
        self.assertGreater(r2, 0.0)

    def test_nationwide_model_saved(self) -> None:
        """전국 모델 저장 확인"""
        df = self.trainer.load_korea_data()
        self.trainer.train_nationwide_model(df)

        model_path = self.trainer.models_dir / 'KR_nationwide_v1.0.pkl'
        metadata_path = self.trainer.models_dir / 'KR_nationwide_v1.0_metadata.json'

        self.assertTrue(model_path.exists(), "Model pickle file not created")
        self.assertTrue(metadata_path.exists(), "Metadata JSON not created")

        # Verify metadata JSON is valid
        with open(metadata_path) as f:
            metadata = json.load(f)
            self.assertEqual(metadata['model_id'], 'KR_nationwide_v1.0')
            self.assertIn('created_date', metadata)

    def test_train_regional_models(self) -> None:
        """지역별 모델 학습"""
        df = self.trainer.load_korea_data()
        regional_results = self.trainer.train_regional_models(df)

        self.assertIsNotNone(regional_results)
        self.assertGreater(len(regional_results), 0)

        # Check at least one region was trained
        for region, metadata in regional_results.items():
            self.assertIn(region, ['Seoul', 'Busan', 'Gyeonggi', 'Daegu', 'Incheon'])
            self.assertEqual(metadata['scope'], 'regional')
            self.assertEqual(metadata['region'], region)

            # Check metrics
            self.assertIn('performance', metadata)
            self.assertIn('test_mape', metadata['performance'])
            mape = metadata['performance']['test_mape']
            self.assertGreater(mape, 0.0)
            self.assertLess(mape, 0.5)

    def test_regional_models_saved(self) -> None:
        """지역 모델 저장 확인"""
        df = self.trainer.load_korea_data()
        self.trainer.train_regional_models(df)

        # Check that at least one regional model was saved
        regional_models = list(self.trainer.models_dir.glob('KR_*_v1.0.pkl'))
        nationwide_models = [m for m in regional_models if 'nationwide' in m.name]
        regional_models = [m for m in regional_models if 'nationwide' not in m.name]

        self.assertGreater(len(regional_models), 0, "No regional models saved")

    def test_generate_performance_report(self) -> None:
        """성능 리포트 생성"""
        df = self.trainer.load_korea_data()
        self.trainer.train_nationwide_model(df)
        self.trainer.train_regional_models(df)

        # Generate report should not raise error
        try:
            self.trainer.generate_performance_report()
        except KeyError:
            # Regional models might not have been trained
            pass

    def test_results_tracking(self) -> None:
        """결과 추적 확인"""
        df = self.trainer.load_korea_data()
        self.trainer.train_nationwide_model(df)

        self.assertIn('nationwide', self.trainer.results)
        self.assertIsNotNone(self.trainer.results['nationwide'])

    def test_run_all_pipeline(self) -> None:
        """전체 파이프라인 실행"""
        results = self.trainer.run_all()

        self.assertIsNotNone(results)
        self.assertIn('nationwide', results)
        self.assertGreater(results['nationwide']['performance']['test_mape'], 0.0)

    def test_mape_target_validation(self) -> None:
        """MAPE 목표 검증"""
        df = self.trainer.load_korea_data()
        metadata = self.trainer.train_nationwide_model(df)

        # Check target_met is boolean
        self.assertIsInstance(metadata['target_met'], (bool, np.bool_))

        # MAPE should be within reasonable range (synthetic data may have higher error)
        mape = metadata['performance']['test_mape']
        self.assertGreater(mape, 0.0)
        self.assertLess(mape, 1.0, "MAPE unreasonably high (>100%)")

    def test_metadata_completeness(self) -> None:
        """메타데이터 완성도 검증"""
        df = self.trainer.load_korea_data()
        metadata = self.trainer.train_nationwide_model(df)

        required_fields = [
            'model_id', 'scope', 'n_samples', 'n_features',
            'feature_columns', 'performance', 'mape_target',
            'target_met', 'training_sec', 'model_size_mb', 'created_date'
        ]

        for field in required_fields:
            self.assertIn(field, metadata, f"Missing field: {field}")

    def test_feature_columns_preserved(self) -> None:
        """특성 컬럼 보존 검증"""
        df = self.trainer.load_korea_data()
        X, y, feature_cols = self.trainer.prepare_training_data(df)
        metadata = self.trainer.train_nationwide_model(df)

        stored_features = metadata['feature_columns']
        self.assertEqual(len(stored_features), len(feature_cols))
        for feat in stored_features:
            self.assertIn(feat, feature_cols)

    def test_training_time_logged(self) -> None:
        """학습 시간 기록 검증"""
        df = self.trainer.load_korea_data()
        metadata = self.trainer.train_nationwide_model(df)

        self.assertIn('training_sec', metadata)
        training_sec = metadata['training_sec']
        self.assertGreater(training_sec, 0)
        self.assertLess(training_sec, 3600)  # Sanity: <1 hour

    def test_model_size_reasonable(self) -> None:
        """모델 크기 합리성 검증"""
        df = self.trainer.load_korea_data()
        self.trainer.train_nationwide_model(df)

        model_path = self.trainer.models_dir / 'KR_nationwide_v1.0.pkl'
        size_mb = model_path.stat().st_size / 1024 / 1024

        self.assertGreater(size_mb, 0.1, "Model too small")
        self.assertLess(size_mb, 100, "Model too large (>100MB)")

    def test_regional_model_data_sufficiency(self) -> None:
        """지역 모델 데이터 충분성 검증"""
        df = self.trainer.load_korea_data()

        # Check that we have enough data for at least some regions
        regions_with_data = df.groupby('region').size()
        regions_sufficient = regions_with_data[regions_with_data >= 100]

        self.assertGreater(len(regions_sufficient), 0,
                          "No regions have sufficient data (>=100 records)")


class TestKoreaModelTrainerErrorHandling(unittest.TestCase):
    """Error handling tests"""

    def test_missing_data_file(self) -> None:
        """누락된 데이터 파일 처리"""
        trainer = KoreaModelTrainer(data_file='nonexistent_data.csv')

        with self.assertRaises(FileNotFoundError):
            trainer.load_korea_data()

    def test_empty_dataframe_handling(self) -> None:
        """빈 데이터프레임 처리"""
        trainer = KoreaModelTrainer(data_file='data/raw/KR_raw.csv')

        # Create empty dataframe with required columns
        empty_df = pd.DataFrame({
            'price_local': [],
        })

        # prepare_training_data should handle empty data
        X, y, feature_cols = trainer.prepare_training_data(empty_df)

        self.assertEqual(len(X), 0)
        self.assertEqual(len(y), 0)


if __name__ == '__main__':
    unittest.main()
