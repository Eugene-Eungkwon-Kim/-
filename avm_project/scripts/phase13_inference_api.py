#!/usr/bin/env python3
"""
Phase 13.4 - AVM REST API Server (FastAPI)

ONNX 추론 엔진 기반 프로덕션 API. 부동산 가격 예측 서비스.

실행:
    python scripts/phase13_inference_api.py \
      --model output/converted_models/kr_production_v1.0.onnx \
      --port 5000

Endpoints:
    POST /predict          단일/배치 예측
    GET  /health           헬스 체크
    GET  /model-info       모델 메타데이터
    GET  /benchmark        성능 벤치마크
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

MODEL_META = {
    'model_id': 'kr_production_v1.0',
    'country': 'KR',
    'mape': 0.0862,
    'r2': 0.9732,
    'n_features': 59,
    'created_date': '2026-07-15',
}


def create_app(model_path: str, backend: str = 'auto'):
    """FastAPI 앱 생성 (엔진 초기화 포함)."""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from phase13_inference_engine import AVMInferenceEngine

    app = FastAPI(
        title="Loan4U AVM Inference API",
        description="부동산 자동 가치평가 모델 (MAPE 8.62%)",
        version="1.0.0",
    )
    engine = AVMInferenceEngine(model_path, backend=backend)
    log.info(f"✅ 엔진 초기화: backend={engine.backend}")

    class PredictRequest(BaseModel):
        features: List[List[float]]  # shape (n, 59)
        property_ids: Optional[List[str]] = None

    @app.post('/predict')
    async def predict(req: PredictRequest) -> Dict:
        x = np.asarray(req.features, dtype=np.float32)
        if x.ndim != 2 or x.shape[1] != engine.n_features:
            raise HTTPException(422, f"features shape must be (n, {engine.n_features})")
        result = engine.predict(x)
        ids = req.property_ids or [f'prop_{i}' for i in range(len(result['prices']))]
        return {
            'predictions': [
                {'property_id': pid, 'predicted_price': price}
                for pid, price in zip(ids, result['prices'])
            ],
            'latency_ms': result['latency_ms'],
            'backend': result['backend'],
            'timestamp': datetime.now().isoformat(),
        }

    @app.get('/health')
    async def health() -> Dict:
        return {'status': 'healthy', 'backend': engine.backend,
                'model': MODEL_META['model_id']}

    @app.get('/model-info')
    async def model_info() -> Dict:
        return MODEL_META

    @app.get('/benchmark')
    async def benchmark() -> Dict:
        return engine.benchmark(batch_sizes=[1, 100], reps=20)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description='Phase 13.4 AVM API 서버')
    parser.add_argument('--model', default='output/converted_models/kr_production_v1.0.onnx')
    parser.add_argument('--backend', default='auto')
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()

    import uvicorn
    app = create_app(args.model, args.backend)
    uvicorn.run(app, host='0.0.0.0', port=args.port)


if __name__ == '__main__':
    main()
