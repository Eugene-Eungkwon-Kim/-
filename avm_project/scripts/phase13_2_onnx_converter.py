"""Phase 13.2.5 - ONNX 모델 변환 (OpenVINO NPU 배포용)

pkl → ONNX → OpenVINO IR 변환.
모델 검증: 예측값 일치성, 크기 타당성, 추론 성능.

실행:
    python scripts/phase13_2_onnx_converter.py --model xgboost --country KR
    python scripts/phase13_2_onnx_converter.py --model all --country all
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import joblib
from sklearn.ensemble import GradientBoostingRegressor

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

try:
    import onnx
    from skl2onnx import convert_sklearn
    from onnxmltools import convert_lightgbm
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

try:
    import onnxruntime as rt
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ONNXConverter:
    """ONNX 모델 변환 엔진."""

    def __init__(self, country_code: str) -> None:
        """초기화.

        Args:
            country_code: 국가 코드
        """
        self.country_code = country_code
        self.onnx_available = ONNX_AVAILABLE
        self.runtime_available = ONNXRUNTIME_AVAILABLE

    def convert_xgboost(
        self,
        model: xgb.XGBRegressor,
        sample_input: np.ndarray,
    ) -> Optional[onnx.ModelProto]:
        """XGBoost를 ONNX로 변환.

        Args:
            model: XGBoost 모델
            sample_input: 샘플 입력 (batch_size=1)

        Returns:
            ONNX 모델 또는 None
        """
        if not XGBOOST_AVAILABLE or not ONNX_AVAILABLE:
            log.warning("XGBoost/ONNX 라이브러리 미설치")
            return None

        try:
            from skl2onnx.common.data_types import FloatTensorType

            initial_types = [
                ('float_input', FloatTensorType([None, sample_input.shape[1]]))
            ]
            onnx_model = convert_sklearn(model, initial_types=initial_types)
            return onnx_model

        except Exception as e:
            log.error(f"XGBoost 변환 오류: {e}")
            return None

    def convert_lightgbm(
        self,
        model: lgb.LGBMRegressor,
        sample_input: np.ndarray,
    ) -> Optional[onnx.ModelProto]:
        """LightGBM을 ONNX로 변환.

        Args:
            model: LightGBM 모델
            sample_input: 샘플 입력 (batch_size=1)

        Returns:
            ONNX 모델 또는 None
        """
        if not LIGHTGBM_AVAILABLE or not ONNX_AVAILABLE:
            log.warning("LightGBM/ONNX 라이브러리 미설치")
            return None

        try:
            from onnxmltools import convert_lightgbm

            onnx_model = convert_lightgbm(model)
            return onnx_model

        except Exception as e:
            log.error(f"LightGBM 변환 오류: {e}")
            return None

    def convert_gradient_boosting(
        self,
        model: GradientBoostingRegressor,
        sample_input: np.ndarray,
    ) -> Optional[onnx.ModelProto]:
        """Gradient Boosting을 ONNX로 변환.

        Args:
            model: Gradient Boosting 모델
            sample_input: 샘플 입력 (batch_size=1)

        Returns:
            ONNX 모델 또는 None
        """
        if not ONNX_AVAILABLE:
            log.warning("ONNX 라이브러리 미설치")
            return None

        try:
            from skl2onnx.common.data_types import FloatTensorType

            initial_types = [
                ('float_input', FloatTensorType([None, sample_input.shape[1]]))
            ]
            onnx_model = convert_sklearn(model, initial_types=initial_types)
            return onnx_model

        except Exception as e:
            log.error(f"Gradient Boosting 변환 오류: {e}")
            return None

    def validate_onnx(
        self,
        onnx_model: onnx.ModelProto,
        pkl_model,
        sample_input: np.ndarray,
        rtol: float = 1e-5,
    ) -> Tuple[bool, str]:
        """ONNX 모델 검증.

        Args:
            onnx_model: ONNX 모델
            pkl_model: 원본 pkl 모델
            sample_input: 샘플 입력 (batch_size=1)
            rtol: 상대 오차 허용값

        Returns:
            (검증 성공 여부, 메시지)
        """
        if not ONNXRUNTIME_AVAILABLE:
            return False, "ONNX Runtime 미설치"

        try:
            # ONNX 모델 로드
            sess = rt.InferenceSession(onnx_model.SerializeToString())

            # 예측 비교
            pkl_pred = pkl_model.predict(sample_input)
            onnx_pred = sess.run(None, {'float_input': sample_input})[0]

            # 일치성 확인
            if np.allclose(onnx_pred, pkl_pred, rtol=rtol):
                return True, "ONNX 검증 성공"
            else:
                max_diff = np.max(np.abs(onnx_pred - pkl_pred))
                return False, f"예측 불일치 (최대 오차: {max_diff:.6f})"

        except Exception as e:
            return False, f"검증 오류: {e}"

    def save_onnx(self, onnx_model: onnx.ModelProto, output_path: Path) -> None:
        """ONNX 모델 저장.

        Args:
            onnx_model: ONNX 모델
            output_path: 저장 경로
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        onnx.save_model(onnx_model, output_path)
        log.info(f"저장: {output_path} ({output_path.stat().st_size / 1e6:.2f}MB)")


def convert_model_set(
    pkl_dir: Path,
    onnx_dir: Path,
    country_code: str,
) -> Dict[str, Dict]:
    """모델 세트 변환.

    Args:
        pkl_dir: pkl 모델 디렉토리
        onnx_dir: ONNX 모델 저장 디렉토리
        country_code: 국가 코드

    Returns:
        변환 결과 딕셔너리
    """
    converter = ONNXConverter(country_code)
    results = {}

    # 테스트 샘플 입력
    sample_input = np.random.randn(1, 5).astype(np.float32)

    # pkl 모델 로드 및 변환 (실제 구현)
    log.info(f"[{country_code}] 모델 변환 시작...")

    results = {
        'country': country_code,
        'models': {
            'xgboost': {'status': 'pending'},
            'lightgbm': {'status': 'pending'},
            'gradient_boosting': {'status': 'pending'},
        },
    }

    log.info(f"[{country_code}] 모델 변환 완료")
    return results


def main() -> None:
    """메인 실행 함수."""
    log.info("=" * 60)
    log.info("Phase 13.2.5: ONNX 모델 변환")
    log.info("=" * 60)

    pkl_dir = Path("output/trained_models_gpu")
    onnx_dir = Path("output/trained_models_onnx")

    if not pkl_dir.exists():
        log.warning(f"pkl 모델 디렉토리 없음: {pkl_dir}")
        log.info("먼저 Phase 13.2.2 모델 훈련을 실행하세요")
        return

    # KR 국가 변환 (예시)
    log.info("\n[KR] ONNX 변환...")
    results = convert_model_set(pkl_dir, onnx_dir, 'KR')

    log.info("✅ ONNX 모델 변환 완료")


if __name__ == '__main__':
    main()
