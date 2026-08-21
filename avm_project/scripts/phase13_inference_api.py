#!/usr/bin/env python3
"""
Phase 13.5 - AVM REST API Server (FastAPI, Multi-Country)

ONNX 추론 엔진 기반 프로덕션 API. 9개국 부동산 가격 예측 서비스.

실행:
    python scripts/phase13_inference_api.py --port 5000

Endpoints:
    POST /predict?country=BR           단일/배치 예측 (국가 선택)
    GET  /health                        헬스 체크 (전체)
    GET  /health?country=SG             국가별 헬스 체크
    GET  /models                        등록된 모델 목록
    GET  /model/{country}/info          국가별 메타데이터
    GET  /benchmark?country=UK          국가별 성능 벤치마크
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


def create_app(backend: str = 'auto'):
    """다국가 FastAPI 앱 생성."""
    from fastapi import FastAPI, HTTPException, Query
    from pydantic import BaseModel

    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from phase13_model_registry import ModelRegistry

    registry = ModelRegistry()
    app = FastAPI(
        title="Loan4U AVM Global API",
        description="9-country property valuation service",
        version="2.0.0",
    )
    log.info(f"✅ 레지스트리 초기화: {registry.list_countries()}")

    class PredictRequest(BaseModel):
        features: List[List[float]]
        property_ids: Optional[List[str]] = None

    def _validate_country(country: str) -> None:
        """국가 코드 검증."""
        if country not in registry.list_countries():
            raise HTTPException(
                400, f"Invalid country: {country}. Supported: {registry.list_countries()}"
            )

    @app.post('/predict')
    async def predict(req: PredictRequest, country: str = Query('KR')) -> Dict:
        _validate_country(country)
        engine = registry.load_model(country)

        x = np.asarray(req.features, dtype=np.float32)
        if not registry.validate_features(country, x):
            expected = registry.get_feature_count(country)
            raise HTTPException(
                422, f"Invalid shape for {country}: expected (n, {expected}), got {x.shape}"
            )

        result = engine.predict(x)
        ids = req.property_ids or [f'{country}_{i}' for i in range(len(result['prices']))]
        return {
            'country': country,
            'predictions': [
                {'property_id': pid, 'predicted_price': price}
                for pid, price in zip(ids, result['prices'])
            ],
            'latency_ms': result['latency_ms'],
            'backend': result['backend'],
            'timestamp': datetime.now().isoformat(),
        }

    @app.get('/health')
    async def health(country: Optional[str] = Query(None)) -> Dict:
        if country:
            _validate_country(country)
            engine = registry.load_model(country)
            return {
                'status': 'healthy',
                'country': country,
                'backend': engine.backend,
                'model': registry.get_info(country).get('model_id'),
            }
        summary = registry.get_model_summary()
        return {
            'status': 'healthy',
            'countries_available': summary['countries'],
            'timestamp': summary['timestamp'],
        }

    @app.get('/models')
    async def list_models() -> Dict:
        return registry.get_model_summary()

    @app.get('/model/{country}/info')
    async def model_info(country: str) -> Dict:
        _validate_country(country)
        return registry.get_info(country) or {'error': f'{country} not found'}

    @app.get('/benchmark')
    async def benchmark(country: str = Query('KR')) -> Dict:
        _validate_country(country)
        engine = registry.load_model(country)
        return {
            'country': country,
            'backend': engine.backend,
            **engine.benchmark(batch_sizes=[1, 100], reps=20),
        }

    return app, registry


def main() -> None:
    parser = argparse.ArgumentParser(description='Phase 13.5 Multi-Country AVM API')
    parser.add_argument('--backend', default='auto')
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()

    import uvicorn
    app, registry = create_app(args.backend)
    log.info(f"🚀 Starting API on http://0.0.0.0:{args.port}")
    log.info(f"   Available countries: {registry.list_countries()}")
    uvicorn.run(app, host='0.0.0.0', port=args.port)


if __name__ == '__main__':
    main()
