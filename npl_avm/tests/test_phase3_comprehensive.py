#!/usr/bin/env python3
"""
Phase 3: 종합 테스트 스위트
목표: 85% 커버리지 달성

테스트 범위:
- 단위 테스트 (데이터, 모델)
- 통합 테스트 (파이프라인)
- E2E 테스트 (사용자 시나리오)
- 성능 테스트 (SLA 검증)
"""

import sys
from pathlib import Path
import logging
import pandas as pd
import numpy as np
import joblib
import pytest
import time
from datetime import datetime

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 프로젝트 경로
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestDataQuality:
    """데이터 품질 테스트."""

    @pytest.fixture
    def data(self):
        """전처리된 데이터 로드."""
        path = project_root / 'data' / 'preprocessed_data_normalized.csv'
        return pd.read_csv(path)

    def test_data_shape(self, data):
        """데이터 형태 검증."""
        assert len(data) >= 200, f"데이터 부족: {len(data)} < 200"
        assert len(data.columns) >= 9, f"특성 부족: {len(data.columns)} < 9"

    def test_no_missing_values(self, data):
        """결측치 검증."""
        missing = data.isnull().sum().sum()
        assert missing == 0, f"결측치 발견: {missing}개"

    def test_price_range(self, data):
        """거래가 범위 검증."""
        if 'hammer_price' in data.columns:
            prices = data['hammer_price']
            assert (prices > 0).all(), "음수 거래가 발견"
            assert (prices < 1e11).all(), "비현실적 거래가 발견"

    def test_area_range(self, data):
        """면적 범위 검증."""
        if 'land_area_sqm' in data.columns:
            # 정규화된 데이터이므로 통계적 범위 확인
            areas = data['land_area_sqm']
            assert areas.std() > 0, "면적 데이터 분산 없음"
            assert not np.isnan(areas).any(), "NaN 값 발견"

    def test_numeric_columns(self, data):
        """수치형 컬럼 검증."""
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        assert len(numeric_cols) >= 8, f"수치형 컬럼 부족: {len(numeric_cols)}"

    def test_data_consistency(self, data):
        """데이터 일관성 검증."""
        # 특정 열의 통계 확인
        stats = data.describe()
        assert stats.loc['count'].min() > 0, "모든 행에 데이터 있음 확인 실패"


class TestModelPerformance:
    """모델 성능 테스트."""

    @pytest.fixture
    def model(self):
        """훈련된 모델 로드."""
        path = project_root / 'models' / 'advanced_best.pkl'
        if path.exists():
            return joblib.load(path)
        return None

    @pytest.fixture
    def data(self):
        """테스트 데이터 로드."""
        path = project_root / 'data' / 'preprocessed_data_normalized.csv'
        df = pd.read_csv(path)
        X = df.drop(['id', 'address_sido', 'address_sigungu', 'address_dong',
                     'address_full', 'reference_date', 'approval_date',
                     'property_type', 'hammer_price'],
                    axis=1, errors='ignore')
        y = df['hammer_price']

        from sklearn.model_selection import train_test_split
        _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        return X_test, y_test

    def test_model_exists(self, model):
        """모델 파일 존재 확인."""
        assert model is not None, "모델 파일 없음"

    def test_model_prediction(self, model, data):
        """모델 예측 기능."""
        if model is None:
            pytest.skip("모델 없음")

        X_test, y_test = data
        y_pred = model.predict(X_test)

        assert len(y_pred) == len(y_test), "예측 길이 불일치"
        assert not np.isnan(y_pred).any(), "NaN 예측값 발견"
        assert not np.isinf(y_pred).any(), "무한대 예측값 발견"

    def test_model_r2_score(self, model, data):
        """모델 R² 점수 검증."""
        if model is None:
            pytest.skip("모델 없음")

        from sklearn.metrics import r2_score
        X_test, y_test = data
        y_pred = model.predict(X_test)

        r2 = r2_score(y_test, y_pred)
        assert r2 >= 0.85, f"R² 부족: {r2:.4f} < 0.85"

    def test_model_rmse(self, model, data):
        """모델 RMSE 검증."""
        if model is None:
            pytest.skip("모델 없음")

        from sklearn.metrics import mean_squared_error
        X_test, y_test = data
        y_pred = model.predict(X_test)

        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        assert rmse < 1e9, f"RMSE 높음: {rmse:.0f}"

    def test_prediction_range(self, model, data):
        """예측값 범위 검증."""
        if model is None:
            pytest.skip("모델 없음")

        X_test, y_test = data
        y_pred = model.predict(X_test)

        # 정규화된 입력 및 출력이므로 절대값 검증
        assert len(y_pred[y_pred > 0]) > len(y_pred) * 0.8, "대부분이 음수"
        assert not np.isnan(y_pred).any(), "NaN 예측값"
        assert not np.isinf(y_pred).any(), "무한대 예측값"


class TestPipelineIntegration:
    """파이프라인 통합 테스트."""

    def test_data_to_model_pipeline(self):
        """데이터 로드 → 전처리 → 모델 예측."""
        # 데이터 로드
        data_path = project_root / 'data' / 'preprocessed_data_normalized.csv'
        assert data_path.exists(), "전처리 데이터 없음"

        df = pd.read_csv(data_path)
        assert len(df) > 0, "데이터 로드 실패"

        # 모델 로드
        model_path = project_root / 'models' / 'advanced_best.pkl'
        if not model_path.exists():
            pytest.skip("모델 없음")

        model = joblib.load(model_path)

        # 특성 추출
        X = df.drop(['id', 'address_sido', 'address_sigungu', 'address_dong',
                     'address_full', 'reference_date', 'approval_date',
                     'property_type', 'hammer_price'],
                    axis=1, errors='ignore')

        # 예측
        y_pred = model.predict(X)

        # 검증
        assert len(y_pred) == len(df), "예측 길이 불일치"
        assert not np.isnan(y_pred).any(), "NaN 값 발견"

    def test_scaler_pipeline(self):
        """스케일러 로드 및 검증."""
        scaler_path = project_root / 'models' / 'scaler.pkl'
        if not scaler_path.exists():
            pytest.skip("스케일러 없음")

        scaler = joblib.load(scaler_path)

        # 스케일러 객체 검증
        assert scaler is not None, "스케일러 로드 실패"
        assert hasattr(scaler, 'transform'), "transform 메서드 없음"
        assert hasattr(scaler, 'inverse_transform'), "inverse_transform 메서드 없음"

        # 스케일러 메타데이터 확인
        assert hasattr(scaler, 'mean_'), "mean_ 속성 없음"
        assert hasattr(scaler, 'scale_'), "scale_ 속성 없음"
        assert len(scaler.mean_) > 0, "스케일러 특성 개수 확인 실패"


class TestUserScenarios:
    """사용자 시나리오 테스트."""

    def test_appraiser_single_estimate(self):
        """감정사: 단일 물건 추정 (< 2초)."""
        data_path = project_root / 'data' / 'preprocessed_data_normalized.csv'
        if not data_path.exists():
            pytest.skip("데이터 없음")

        model_path = project_root / 'models' / 'advanced_best.pkl'
        if not model_path.exists():
            pytest.skip("모델 없음")

        # 1건 추정 시간 측정
        start = time.time()

        df = pd.read_csv(data_path).iloc[0:1]
        X = df.drop(['id', 'address_sido', 'address_sigungu', 'address_dong',
                     'address_full', 'reference_date', 'approval_date',
                     'property_type', 'hammer_price'],
                    axis=1, errors='ignore')

        model = joblib.load(model_path)
        y_pred = model.predict(X)

        elapsed = time.time() - start

        # 2초 이내
        assert elapsed < 2.0, f"응답시간 초과: {elapsed:.2f}초 > 2.0초"

    def test_fund_manager_batch_estimate(self):
        """펀드매니저: 100건 배치 추정 (< 5분)."""
        data_path = project_root / 'data' / 'preprocessed_data_normalized.csv'
        if not data_path.exists():
            pytest.skip("데이터 없음")

        model_path = project_root / 'models' / 'advanced_best.pkl'
        if not model_path.exists():
            pytest.skip("모델 없음")

        # 100건 추정 시간 측정
        start = time.time()

        df = pd.read_csv(data_path).iloc[0:min(100, len(pd.read_csv(data_path)))]
        X = df.drop(['id', 'address_sido', 'address_sigungu', 'address_dong',
                     'address_full', 'reference_date', 'approval_date',
                     'property_type', 'hammer_price'],
                    axis=1, errors='ignore')

        model = joblib.load(model_path)
        y_pred = model.predict(X)

        elapsed = time.time() - start

        # 5분(300초) 이내
        assert elapsed < 300.0, f"배치 처리 시간 초과: {elapsed:.2f}초 > 300초"

    def test_analyst_data_query(self):
        """분석가: 데이터 쿼리 (< 300ms)."""
        data_path = project_root / 'data' / 'preprocessed_data_normalized.csv'
        if not data_path.exists():
            pytest.skip("데이터 없음")

        # 데이터 로드 및 필터 시간 측정
        start = time.time()

        df = pd.read_csv(data_path)
        # 필터링 예: building_age < 20
        filtered = df[df['building_age'] < 20] if 'building_age' in df.columns else df

        elapsed = time.time() - start

        # 300ms 이내
        assert elapsed < 0.3, f"쿼리 시간 초과: {elapsed*1000:.1f}ms > 300ms"


class TestSLACompliance:
    """SLA 준수 테스트."""

    def test_api_response_time(self):
        """API 응답시간 SLA (p95 < 500ms)."""
        model_path = project_root / 'models' / 'advanced_best.pkl'
        if not model_path.exists():
            pytest.skip("모델 없음")

        data_path = project_root / 'data' / 'preprocessed_data_normalized.csv'
        if not data_path.exists():
            pytest.skip("데이터 없음")

        model = joblib.load(model_path)
        df = pd.read_csv(data_path)
        X = df.drop(['id', 'address_sido', 'address_sigungu', 'address_dong',
                     'address_full', 'reference_date', 'approval_date',
                     'property_type', 'hammer_price'],
                    axis=1, errors='ignore')

        # 10회 반복 측정
        times = []
        for _ in range(10):
            start = time.time()
            y_pred = model.predict(X.iloc[0:1])
            times.append(time.time() - start)

        times_sorted = sorted(times)
        p95 = times_sorted[int(len(times_sorted) * 0.95)]

        # p95 < 500ms
        assert p95 < 0.5, f"SLA 위반: p95 {p95*1000:.1f}ms > 500ms"

    def test_model_accuracy_sla(self):
        """모델 정확도 SLA (R² >= 0.85)."""
        model_path = project_root / 'models' / 'advanced_best.pkl'
        if not model_path.exists():
            pytest.skip("모델 없음")

        data_path = project_root / 'data' / 'preprocessed_data_normalized.csv'
        if not data_path.exists():
            pytest.skip("데이터 없음")

        from sklearn.metrics import r2_score
        from sklearn.model_selection import train_test_split

        df = pd.read_csv(data_path)
        X = df.drop(['id', 'address_sido', 'address_sigungu', 'address_dong',
                     'address_full', 'reference_date', 'approval_date',
                     'property_type', 'hammer_price'],
                    axis=1, errors='ignore')
        y = df['hammer_price']

        _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = joblib.load(model_path)
        y_pred = model.predict(X_test)

        r2 = r2_score(y_test, y_pred)

        # R² >= 0.85
        assert r2 >= 0.85, f"정확도 SLA 미충족: R² {r2:.4f} < 0.85"


def run_all_tests():
    """모든 테스트 실행."""
    logger.info("=" * 60)
    logger.info("🧪 Phase 3 종합 테스트 스위트 시작")
    logger.info("=" * 60)

    # pytest 실행
    pytest_args = [
        str(Path(__file__)),
        "-v",
        "--tb=short",
        "--color=yes",
    ]

    exit_code = pytest.main(pytest_args)

    logger.info("\n" + "=" * 60)
    if exit_code == 0:
        logger.info("✅ 모든 테스트 통과!")
    else:
        logger.info("❌ 일부 테스트 실패")
    logger.info("=" * 60)

    return exit_code


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
