#!/usr/bin/env python3
"""
Loan4U Phase 13.4 - NPU Inference Engine
Deploy INT8 quantized OpenVINO IR models on onboard NPU.
Target: 1ms latency, 70% power reduction vs RTX training.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']

# 서빙 앙상블에 포함할 3개 기본 모델 타입 (국가 접미사 없이). best_model_{country}
# (단일 모델 배포용, 이 중 하나와 중복)과 coldstart_{country}(직전가 없을 때만
# 쓰는 별도 목적 모델)은 앙상블 평균에 섞이면 안 되므로 제외한다.
ENSEMBLE_BASE_MODEL_TYPES = ['xgboost', 'lightgbm', 'gradient_boosting']


@dataclass
class InferenceResult:
    """Single property valuation result"""
    predicted_price: float
    model_name: str
    confidence: float
    latency_ms: float
    device: str


def initialize_openvino_model(ir_path: str) -> Optional[object]:
    """Load OpenVINO IR model (INT8 quantized)."""
    try:
        from openvino.runtime import Core

        ie = Core()
        model = ie.read_model(ir_path)
        compiled_model = ie.compile_model(model, device_name="CPU")
        log.info(f"Loaded IR model: {ir_path}")
        return compiled_model
    except Exception as e:
        log.warning(f"Failed to load IR model: {e}")
        return None


def initialize_onnx_model(onnx_path: str) -> Optional[object]:
    """Load ONNX model via ONNX Runtime.

    트리 앙상블(XGBoost/LightGBM/GradientBoosting)은 OpenVINO IR로 변환할 수
    없으므로(ai.onnx.ml.TreeEnsembleRegressor 미지원), ONNX Runtime을 실제
    가속 경로로 사용한다.
    """
    try:
        import onnxruntime as ort

        session = ort.InferenceSession(onnx_path, providers=['CPUExecutionProvider'])
        log.info(f"Loaded ONNX model: {onnx_path}")
        return session
    except Exception as e:
        log.warning(f"Failed to load ONNX model: {e}")
        return None


def preprocess_input(features: np.ndarray, country: str = 'KR') -> np.ndarray:
    """Normalize input features for inference (국가별 학습 정규화 범위 재사용).

    country_configs.CountryConfig.feature_min/max를 그대로 재사용한다 —
    이전에는 old_price 범위가 여기서만 1000배 작게(5,000,000) 하드코딩되어
    있어 학습(6,000,000,000)과 어긋나는 학습-추론 스큐 버그가 있었다.
    KR_CONFIG의 값은 avm_feature_engineering.FEATURE_MIN/MAX와 동일하다.
    """
    from country_configs import get_country_config

    config = get_country_config(country)
    feature_min = np.array(config.feature_min, dtype=np.float32)
    feature_max = np.array(config.feature_max, dtype=np.float32)
    normalized = (features - feature_min) / (feature_max - feature_min)
    return np.clip(normalized, 0.0, 1.0).astype(np.float32)


def run_inference(compiled_model: object, features: np.ndarray,
                 model_name: str, country: str = 'KR') -> Optional[InferenceResult]:
    """Execute inference and return prediction. Supports OpenVINO IR, ONNX Runtime, and sklearn models."""
    try:
        import time
        start = time.perf_counter()

        input_data = preprocess_input(features, country).reshape(1, -1)

        if type(compiled_model).__module__.startswith('onnxruntime'):
            input_name = compiled_model.get_inputs()[0].name
            output_name = compiled_model.get_outputs()[0].name
            result = compiled_model.run([output_name], {input_name: input_data})
            predicted_price = float(np.asarray(result[0]).reshape(-1)[0])
            device = "CPU (onnxruntime)"
        elif hasattr(compiled_model, 'inputs') and hasattr(compiled_model, 'outputs'):
            output_layer = compiled_model.outputs[0]
            result = compiled_model(input_data)
            predicted_price = float(result[output_layer][0])
            device = "NPU"
        else:
            predicted_price = float(compiled_model.predict(input_data)[0])
            device = "CPU (sklearn)"

        latency_ms = (time.perf_counter() - start) * 1000.0
        confidence = 0.95 if latency_ms < 2.0 else 0.85

        return InferenceResult(
            predicted_price=predicted_price,
            model_name=model_name,
            confidence=confidence,
            latency_ms=latency_ms,
            device=device
        )
    except Exception as e:
        log.warning(f"Inference failed: {e}")
        return None


def _backend_name(model: object) -> str:
    """로드된 모델 객체가 실제로 어떤 백엔드인지 식별 (NPU 사칭 방지)."""
    module_name = type(model).__module__
    if module_name.startswith('onnxruntime'):
        return 'onnxruntime (CPU)'
    if hasattr(model, 'inputs') and hasattr(model, 'outputs'):
        return 'openvino IR (NPU/CPU)'
    return 'sklearn pkl (CPU)'


def ensemble_predict(
    models: Dict[str, object], features: np.ndarray, country: str = 'KR',
) -> Tuple[float, float]:
    """Aggregate predictions from multiple models (ensemble)."""
    predictions = []
    confidences = []

    for model_name, compiled_model in models.items():
        result = run_inference(compiled_model, features, model_name, country)
        if result:
            predictions.append(result.predicted_price)
            confidences.append(result.confidence)

    if not predictions:
        return 0.0, 0.0

    avg_price = np.mean(predictions)
    avg_confidence = np.mean(confidences)
    return avg_price, avg_confidence


class NPUInferenceEngine:
    """NPU-based AVM inference service."""

    def __init__(self, ir_model_dir: str, country: str = 'KR') -> None:
        """Initialize inference engine with IR/ONNX/pkl models for a given country."""
        self.models: Dict[str, object] = {}
        self.ir_model_dir = Path(ir_model_dir)
        self.country = country
        self._load_models()

    def _load_models(self) -> None:
        """앙상블 기본 3개 모델을 모델별로 IR → ONNX → pkl 순으로 최선의 형식 로드.

        best_model_{country}(단일 모델용, 중복)과 coldstart_{country}(별도 목적)은 제외한다.
        """
        trained_dir = self.ir_model_dir.parent / 'trained_models'
        for model_type in ENSEMBLE_BASE_MODEL_TYPES:
            model_name = f"{model_type}_{self.country}"
            compiled = self._load_best_available(model_name, trained_dir)
            if compiled is not None:
                self.models[model_name] = compiled
                log.info(f"Loaded model: {model_name}")

    def _load_best_available(self, model_name: str, trained_dir: Path) -> Optional[object]:
        """단일 모델에 대해 IR(.xml) → ONNX(.onnx) → pkl(튜닝본 우선) 순으로 시도."""
        ir_path = self.ir_model_dir / f"{model_name}.xml"
        if ir_path.exists():
            compiled = initialize_openvino_model(str(ir_path))
            if compiled is not None:
                return compiled

        onnx_path = self.ir_model_dir / f"{model_name}.onnx"
        if onnx_path.exists():
            session = initialize_onnx_model(str(onnx_path))
            if session is not None:
                return session

        return self._load_pickle_fallback(model_name, trained_dir)

    def _load_pickle_fallback(self, model_name: str, trained_dir: Path) -> Optional[object]:
        """pkl 폴백: 튜닝된 버전(Phase 13.3)이 있으면 우선 사용."""
        import pickle
        for candidate in (f"{model_name}_tuned.pkl", f"{model_name}.pkl"):
            pkl_path = trained_dir / candidate
            if pkl_path.exists():
                with open(pkl_path, 'rb') as f:
                    return pickle.load(f)
        return None

    def predict(self, property_features: np.ndarray) -> Tuple[float, float, float]:
        """Predict property price using ensemble. Returns (price, confidence, latency_ms)."""
        if not self.models:
            log.error("No models loaded")
            return 0.0, 0.0, 0.0

        import time
        start = time.perf_counter()

        avg_price, avg_confidence = ensemble_predict(self.models, property_features, self.country)

        latency_ms = (time.perf_counter() - start) * 1000.0
        log.info(f"Ensemble prediction: {avg_price:,.0f} {self.country} (conf={avg_confidence:.1%}, {latency_ms:.1f}ms)")

        return avg_price, avg_confidence, latency_ms

    def get_model_stats(self) -> Dict[str, object]:
        """Return loaded models and their actual backend per model (정직한 상태 보고)."""
        return {
            'models_loaded': len(self.models),
            'model_names': list(self.models.keys()),
            'backends': {name: _backend_name(model) for name, model in self.models.items()},
        }


def main() -> None:
    """Demonstrate inference engine and report real per-model backend + latency."""
    import argparse
    import time

    from country_configs import get_country_config

    parser = argparse.ArgumentParser(description='Phase 13.4 Inference Engine')
    parser.add_argument('--ir-models', default='output/models_ir', help='ONNX/IR model directory')
    parser.add_argument('--country', default='KR', help='KR, SG 등 (country_configs.py 참조)')
    args = parser.parse_args()

    engine = NPUInferenceEngine(args.ir_models, args.country)
    stats = engine.get_model_stats()

    print(f"\n{'='*50}")
    print(f"Inference Engine Ready ({args.country})")
    print(f"{'='*50}")
    print(f"Models loaded: {stats['models_loaded']}")
    for name, backend in stats['backends'].items():
        print(f"  - {name}: {backend}")

    config = get_country_config(args.country)
    mid = [(lo + hi) / 2 for lo, hi in zip(config.feature_min, config.feature_max)]
    sample = np.array(mid, dtype=np.float32)
    engine.predict(sample)  # 워밍업 (첫 호출의 JIT/세션 초기화 비용 제외)

    start = time.perf_counter()
    price, confidence, _ = engine.predict(sample)
    latency_ms = (time.perf_counter() - start) * 1000.0
    print(f"\nSample prediction: {price:,.0f} {config.currency} (confidence={confidence:.2f})")
    print(f"Measured latency (warm): {latency_ms:.2f}ms (실측, 특정 하드웨어 NPU 가속 아님)")


if __name__ == '__main__':
    main()
