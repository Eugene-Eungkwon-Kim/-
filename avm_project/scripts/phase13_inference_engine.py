#!/usr/bin/env python3
"""
Phase 13.4 - AVM Inference Engine (ONNX Runtime)

변환된 ONNX 모델의 통합 추론 엔진. 사용 가능한 최적 백엔드를
자동 감지한다: NPU(OpenVINO) → GPU(CUDA) → CPU 순서로 폴백.

실행 (벤치마크):
    python scripts/phase13_inference_engine.py \
      --model output/converted_models/kr_production_v1.0.onnx
"""

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

BACKEND_PROVIDERS = {
    'npu': 'OpenVINOExecutionProvider',
    'gpu': 'CUDAExecutionProvider',
    'cpu': 'CPUExecutionProvider',
}


class AVMInferenceEngine:
    """ONNX 기반 AVM 추론 엔진 (NPU→GPU→CPU 자동 폴백)."""

    def __init__(self, model_path: str, backend: str = 'auto') -> None:
        import onnxruntime as rt
        self.model_path = model_path
        self.backend = self._select_backend(backend, rt.get_available_providers())
        self.session = rt.InferenceSession(
            model_path, providers=[BACKEND_PROVIDERS[self.backend]]
        )
        self.input_name = self.session.get_inputs()[0].name
        self.n_features = self.session.get_inputs()[0].shape[1]
        self._warmup()

    def _select_backend(self, requested: str, available: List[str]) -> str:
        """요청 백엔드 확인, 'auto'면 NPU→GPU→CPU 우선순위로 선택."""
        if requested != 'auto':
            if BACKEND_PROVIDERS[requested] not in available:
                log.warning(f"⚠️ {requested} 백엔드 미지원 - CPU로 폴백")
                return 'cpu'
            return requested
        for name in ('npu', 'gpu', 'cpu'):
            if BACKEND_PROVIDERS[name] in available:
                return name
        return 'cpu'

    def _warmup(self, n_runs: int = 5) -> None:
        """첫 추론 지연 제거를 위한 워밍업."""
        dummy = np.zeros((1, self.n_features), dtype=np.float32)
        for _ in range(n_runs):
            self.session.run(None, {self.input_name: dummy})

    def predict(self, features: np.ndarray) -> Dict:
        """단건/배치 예측. features shape: (n_features,) 또는 (n, n_features)."""
        x = np.asarray(features, dtype=np.float32)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        t0 = time.perf_counter()
        prices = self.session.run(None, {self.input_name: x})[0].ravel()
        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            'prices': prices.tolist(),
            'latency_ms': round(latency_ms, 3),
            'backend': self.backend,
        }

    def benchmark(self, batch_sizes: Optional[List[int]] = None, reps: int = 50) -> Dict:
        """배치 크기별 p50/p95 지연시간 및 처리량 측정."""
        results = {}
        for n in batch_sizes or [1, 10, 100, 1000]:
            x = np.random.randn(n, self.n_features).astype(np.float32)
            latencies = []
            for _ in range(reps):
                t0 = time.perf_counter()
                self.session.run(None, {self.input_name: x})
                latencies.append((time.perf_counter() - t0) * 1000)
            lat = np.array(latencies)
            results[str(n)] = {
                'p50_ms': round(float(np.percentile(lat, 50)), 3),
                'p95_ms': round(float(np.percentile(lat, 95)), 3),
                'throughput_props_sec': round(n / np.percentile(lat, 50) * 1000),
            }
        return {'backend': self.backend, 'batch_results': results}


def main() -> None:
    parser = argparse.ArgumentParser(description='Phase 13.4 추론 엔진 벤치마크')
    parser.add_argument('--model', default='output/converted_models/kr_production_v1.0.onnx')
    parser.add_argument('--backend', default='auto', choices=['auto', 'npu', 'gpu', 'cpu'])
    parser.add_argument('--output', default='output/benchmark_results.json')
    args = parser.parse_args()

    log.info("=" * 70)
    log.info("Phase 13.4 AVM 추론 엔진 벤치마크")
    log.info("=" * 70)

    engine = AVMInferenceEngine(args.model, backend=args.backend)
    log.info(f"✅ 엔진 초기화: backend={engine.backend}, features={engine.n_features}")

    report = engine.benchmark()
    log.info(f"\n{'Batch':>6} | {'p50 (ms)':>9} | {'p95 (ms)':>9} | {'처리량 (props/s)':>16}")
    log.info("-" * 52)
    for n, r in report['batch_results'].items():
        log.info(f"{n:>6} | {r['p50_ms']:>9} | {r['p95_ms']:>9} | {r['throughput_props_sec']:>16,}")

    single_p50 = report['batch_results']['1']['p50_ms']
    report['sla'] = {
        'target_single_latency_ms': 5.0,
        'actual_single_latency_ms': single_p50,
        'status': 'PASS' if single_p50 < 5.0 else 'FAIL',
    }
    log.info(f"\nSLA (단건 < 5ms): {report['sla']['status']} ({single_p50}ms)")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log.info(f"✅ 벤치마크 리포트: {output_path}")


if __name__ == '__main__':
    main()
