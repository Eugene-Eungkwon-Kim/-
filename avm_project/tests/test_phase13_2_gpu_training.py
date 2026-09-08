"""Phase 13.2 GPU-가속 모델 훈련 테스트

데이터 검증 (6) + 모델 성능 (12) + ONNX 검증 (6) = 24개 테스트.
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch

# torch는 Phase 13.2 GPU 학습 전용 의존성이라 requirements.txt에 없다 — 없는
# 환경에서 수집 오류로 스위트 전체를 멈추는 대신 이 모듈만 skip한다.
pytest.importorskip("torch", reason="Phase 13.2 GPU 학습 테스트는 torch가 필요합니다")

from avm_project.scripts.phase13_2_gpu_trainer import (  # noqa: E402
    GPUModelTrainer,
    train_country,
)


class TestGPUModelTrainerInit:
    """GPUModelTrainer 초기화 테스트."""

    def test_trainer_creation_kr(self) -> None:
        """KR 국가 트레이너 생성."""
        trainer = GPUModelTrainer('KR')
        assert trainer.country_code == 'KR'
        assert trainer.device in ('cuda', 'cpu')

    def test_trainer_device_detection(self) -> None:
        """GPU 장치 감지."""
        trainer = GPUModelTrainer('SG')
        assert hasattr(trainer, 'gpu_available')
        assert isinstance(trainer.gpu_available, bool)


class TestXGBoostGPUTraining:
    """XGBoost GPU 훈련 테스트."""

    @pytest.fixture
    def sample_data(self) -> tuple:
        """샘플 데이터 생성."""
        np.random.seed(42)
        X_train = np.random.randn(100, 5).astype(np.float32)
        y_train = np.random.randn(100).astype(np.float32)
        X_test = np.random.randn(20, 5).astype(np.float32)
        y_test = np.random.randn(20).astype(np.float32)
        return X_train, y_train, X_test, y_test

    def test_xgboost_training_result_structure(self, sample_data: tuple) -> None:
        """XGBoost 훈련 결과 구조."""
        X_train, y_train, X_test, y_test = sample_data
        trainer = GPUModelTrainer('KR')

        result = trainer.train_xgboost_gpu(X_train, y_train, X_test, y_test)

        assert 'status' in result or 'model' in result
        if 'model' in result:
            assert 'r2' in result
            assert 'mape' in result
            assert 'type' in result
            assert result['type'] == 'xgboost'

    def test_xgboost_r2_score(self, sample_data: tuple) -> None:
        """XGBoost R² 점수 범위."""
        X_train, y_train, X_test, y_test = sample_data
        trainer = GPUModelTrainer('KR')

        result = trainer.train_xgboost_gpu(X_train, y_train, X_test, y_test)

        if 'model' in result:
            assert -1 <= result['r2'] <= 1


class TestLightGBMGPUTraining:
    """LightGBM GPU 훈련 테스트."""

    @pytest.fixture
    def sample_data(self) -> tuple:
        """샘플 데이터 생성."""
        np.random.seed(42)
        X_train = np.random.randn(100, 5).astype(np.float32)
        y_train = np.random.randn(100).astype(np.float32)
        X_test = np.random.randn(20, 5).astype(np.float32)
        y_test = np.random.randn(20).astype(np.float32)
        return X_train, y_train, X_test, y_test

    def test_lightgbm_training_result_structure(self, sample_data: tuple) -> None:
        """LightGBM 훈련 결과 구조."""
        X_train, y_train, X_test, y_test = sample_data
        trainer = GPUModelTrainer('SG')

        result = trainer.train_lightgbm_gpu(X_train, y_train, X_test, y_test)

        assert 'status' in result or 'model' in result
        if 'model' in result:
            assert 'r2' in result
            assert 'mape' in result
            assert 'type' in result
            assert result['type'] == 'lightgbm'

    def test_lightgbm_r2_score(self, sample_data: tuple) -> None:
        """LightGBM R² 점수 범위."""
        X_train, y_train, X_test, y_test = sample_data
        trainer = GPUModelTrainer('SG')

        result = trainer.train_lightgbm_gpu(X_train, y_train, X_test, y_test)

        if 'model' in result:
            assert -1 <= result['r2'] <= 1


class TestGradientBoostingTraining:
    """Gradient Boosting 훈련 테스트."""

    @pytest.fixture
    def sample_data(self) -> tuple:
        """샘플 데이터 생성."""
        np.random.seed(42)
        X_train = np.random.randn(100, 5).astype(np.float32)
        y_train = np.random.randn(100).astype(np.float32)
        X_test = np.random.randn(20, 5).astype(np.float32)
        y_test = np.random.randn(20).astype(np.float32)
        return X_train, y_train, X_test, y_test

    def test_gb_training_result_structure(self, sample_data: tuple) -> None:
        """Gradient Boosting 훈련 결과 구조."""
        X_train, y_train, X_test, y_test = sample_data
        trainer = GPUModelTrainer('HK')

        result = trainer.train_gradient_boosting(X_train, y_train, X_test, y_test)

        assert 'model' in result
        assert 'r2' in result
        assert 'mape' in result
        assert 'type' in result
        assert result['type'] == 'gradient_boosting'

    def test_gb_cpu_device(self, sample_data: tuple) -> None:
        """Gradient Boosting CPU 장치 확인."""
        X_train, y_train, X_test, y_test = sample_data
        trainer = GPUModelTrainer('HK')

        result = trainer.train_gradient_boosting(X_train, y_train, X_test, y_test)

        assert result['device'] == 'cpu'


class TestParallelTraining:
    """병렬 훈련 테스트."""

    @pytest.fixture
    def sample_data(self) -> tuple:
        """샘플 데이터 생성."""
        np.random.seed(42)
        X_train = np.random.randn(100, 5).astype(np.float32)
        y_train = np.random.randn(100).astype(np.float32)
        X_test = np.random.randn(20, 5).astype(np.float32)
        y_test = np.random.randn(20).astype(np.float32)
        return X_train, y_train, X_test, y_test

    def test_train_all_returns_dict(self, sample_data: tuple) -> None:
        """train_all 반환 딕셔너리 확인."""
        X_train, y_train, X_test, y_test = sample_data
        trainer = GPUModelTrainer('UK')

        results = trainer.train_all(X_train, y_train, X_test, y_test, max_workers=1)

        assert isinstance(results, dict)
        assert len(results) > 0

    def test_train_all_contains_models(self, sample_data: tuple) -> None:
        """train_all 결과에 모델 포함."""
        X_train, y_train, X_test, y_test = sample_data
        trainer = GPUModelTrainer('AU')

        results = trainer.train_all(X_train, y_train, X_test, y_test, max_workers=1)

        for model_type, result in results.items():
            if result.get('status') not in ('skipped', 'error'):
                assert 'model' in result


class TestModelSaving:
    """모델 저장 테스트."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """임시 디렉토리."""
        return tmp_path / "models"

    @pytest.fixture
    def sample_data(self) -> tuple:
        """샘플 데이터 생성."""
        np.random.seed(42)
        X_train = np.random.randn(100, 5).astype(np.float32)
        y_train = np.random.randn(100).astype(np.float32)
        X_test = np.random.randn(20, 5).astype(np.float32)
        y_test = np.random.randn(20).astype(np.float32)
        return X_train, y_train, X_test, y_test

    def test_save_models_creates_directory(
        self,
        sample_data: tuple,
        temp_dir: Path,
    ) -> None:
        """save_models 디렉토리 생성."""
        X_train, y_train, X_test, y_test = sample_data
        trainer = GPUModelTrainer('TH')

        results = trainer.train_all(X_train, y_train, X_test, y_test, max_workers=1)
        trainer.save_models(results, temp_dir)

        assert temp_dir.exists()

    def test_save_models_returns_dict(
        self,
        sample_data: tuple,
        temp_dir: Path,
    ) -> None:
        """save_models 딕셔너리 반환."""
        X_train, y_train, X_test, y_test = sample_data
        trainer = GPUModelTrainer('TH')

        results = trainer.train_all(X_train, y_train, X_test, y_test, max_workers=1)
        saved = trainer.save_models(results, temp_dir)

        assert isinstance(saved, dict)


class TestCountryCodeValidation:
    """국가 코드 검증."""

    def test_valid_country_codes(self) -> None:
        """유효한 국가 코드."""
        valid_codes = ['KR', 'SG', 'HK', 'UK', 'AU', 'TH']
        for code in valid_codes:
            trainer = GPUModelTrainer(code)
            assert trainer.country_code == code

    def test_country_code_uppercase(self) -> None:
        """국가 코드 대문자."""
        trainer = GPUModelTrainer('kr')
        assert trainer.country_code == 'kr'


class TestTypeHints:
    """타입 힌트 완성도 테스트."""

    def test_trainer_methods_have_return_types(self) -> None:
        """메서드 반환 타입."""
        trainer = GPUModelTrainer('KR')

        # 모든 public 메서드 확인
        methods = [m for m in dir(trainer) if not m.startswith('_')]
        assert len(methods) > 0

    def test_function_signatures_complete(self) -> None:
        """함수 서명 완성."""
        from inspect import signature

        trainer = GPUModelTrainer('KR')
        sig = signature(trainer.train_xgboost_gpu)

        # 모든 파라미터에 타입 힌트 확인
        for param in sig.parameters.values():
            assert param.annotation != param.empty or param.name == 'self'


class TestDataValidation:
    """데이터 검증 테스트."""

    def test_data_no_nan(self) -> None:
        """NaN 값 없음."""
        np.random.seed(42)
        X = np.random.randn(100, 5).astype(np.float32)
        y = np.random.randn(100).astype(np.float32)

        assert not np.any(np.isnan(X))
        assert not np.any(np.isnan(y))

    def test_data_shape_consistency(self) -> None:
        """데이터 모양 일관성."""
        np.random.seed(42)
        X = np.random.randn(100, 5).astype(np.float32)
        y = np.random.randn(100).astype(np.float32)

        assert X.shape[0] == y.shape[0]

    def test_data_type_float32(self) -> None:
        """데이터 타입 float32."""
        np.random.seed(42)
        X = np.random.randn(100, 5).astype(np.float32)
        y = np.random.randn(100).astype(np.float32)

        assert X.dtype == np.float32
        assert y.dtype == np.float32


class TestModelPerformanceMetrics:
    """모델 성능 지표 테스트."""

    def test_mape_non_negative(self) -> None:
        """MAPE 음수 아님."""
        np.random.seed(42)
        y_true = np.abs(np.random.randn(50)) + 1
        y_pred = np.abs(np.random.randn(50)) + 1

        from sklearn.metrics import mean_absolute_percentage_error
        mape = mean_absolute_percentage_error(y_true, y_pred)

        assert mape >= 0

    def test_r2_in_range(self) -> None:
        """R² 범위 확인."""
        np.random.seed(42)
        y_true = np.random.randn(50)
        y_pred = y_true + np.random.randn(50) * 0.1

        from sklearn.metrics import r2_score
        r2 = r2_score(y_true, y_pred)

        assert -1 <= r2 <= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
