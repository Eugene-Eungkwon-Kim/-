"""WP 2.6: AVM Core Engine - 5단계 가치평가 파이프라인 통합."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from scripts.avm_feature_engineering import AVMFeatureEngineer
from scripts.avm_ensemble_engine import AVMEnsembleEngine
from scripts.avm_correction_layer import CorrectionLayer
from scripts.avm_validation_engine import ValidationEngine
from scripts.avm_auction_module import AuctionModule

log = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    'model_dir': 'output/models_ir',
    'trained_models_dir': 'output/trained_models',
    'data_dir': 'data/raw',
}


class AVMCoreEngine:
    """통합 AVM 엔진 - 부동산 자동 가치평가."""

    VERSION = 'v1.0-ensemble'

    def __init__(self, config_path: str = 'config/avm_config.json') -> None:
        self.config = self._load_config(config_path)
        self.feature_engineer = AVMFeatureEngineer()
        self.ensemble = AVMEnsembleEngine(self.config['model_dir'])
        self.corrections = CorrectionLayer()
        self.validator = ValidationEngine()
        self.auction = AuctionModule()
        self._start_time = time.time()
        self._perf_log: List[Dict] = []
        self._fit_validator()
        log.info(f"AVMCoreEngine {self.VERSION} ready")

    def _load_config(self, config_path: str) -> Dict:
        """설정 파일 로드 (실패시 기본값 사용)."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            log.warning(f"Config not found at {config_path}, using defaults")
            return DEFAULT_CONFIG.copy()

    def _fit_validator(self) -> None:
        """학습 데이터로 이상탐지 모델 초기화."""
        try:
            data_dir = Path(self.config['data_dir'])
            csv_files = list(data_dir.glob('*_data.csv'))
            if not csv_files:
                return
            dfs = [pd.read_csv(f) for f in csv_files[:3]]
            df = pd.concat(dfs, ignore_index=True)
            cols = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']
            available = [c for c in cols if c in df.columns]
            if len(available) >= 4:
                X = df[available].dropna().values.astype(np.float32)
                if len(X) > 10:
                    self.validator.fit(X[:, :5] if X.shape[1] >= 5 else X)
        except Exception as e:
            log.warning(f"Validator fit skipped: {e}")

    def valuate(
        self,
        area_sqm: float,
        old_price: float,
        latitude: float,
        longitude: float,
        property_type: str,
        district_grade: str = '3',
        public_appraisal_price: Optional[float] = None,
        market_condition: str = 'normal',
        reference_year: int = 2024,
    ) -> Dict[str, Any]:
        """5단계 부동산 가치평가."""
        start = time.perf_counter()

        # Step 1: 특성 엔지니어링
        input_dict = {
            'area_sqm': area_sqm, 'old_price': old_price,
            'latitude': latitude, 'longitude': longitude,
            'property_type': property_type,
        }
        features = self.feature_engineer.transform(input_dict)

        # Step 2: 앙상블 예측
        base_price, confidence, _ = self.ensemble.predict(features)

        # Step 3: 보정값 적용
        corrected_price = self.corrections.apply_corrections(
            base_price, property_type, district_grade, reference_year
        )

        # Step 4: 검증
        validation = self.validator.validate(features, corrected_price, public_appraisal_price)

        # Step 5: 낙찰가 추정
        auction = self.auction.estimate_auction_price(
            corrected_price, property_type, district_grade, market_condition
        )

        # 최종 신뢰도 조정
        if not validation['is_valid']:
            confidence *= 0.70

        latency_ms = (time.perf_counter() - start) * 1000.0
        self._perf_log.append({'latency_ms': latency_ms, 'confidence': confidence})

        log.info(
            f"Valuation: {corrected_price:,.0f} KRW "
            f"(conf={confidence:.1%}, {latency_ms:.1f}ms)"
        )

        return {
            'base_price': float(base_price),
            'corrected_price': float(corrected_price),
            'confidence': float(confidence),
            'validation_status': validation['is_valid'],
            'validation': validation,
            'auction_forecast': auction,
            'latency_ms': float(latency_ms),
            'model_version': self.VERSION,
            'timestamp': datetime.now().isoformat(),
        }

    def batch_valuate(self, properties: List[Dict]) -> List[Dict]:
        """대량 가치평가."""
        return [self.valuate(**p) for p in properties]

    def get_engine_stats(self) -> Dict[str, Any]:
        """엔진 상태 및 성능 통계."""
        uptime_h = (time.time() - self._start_time) / 3600
        latencies = [p['latency_ms'] for p in self._perf_log] or [0.0]
        confidences = [p['confidence'] for p in self._perf_log] or [0.0]

        return {
            'version': self.VERSION,
            'status': 'ready' if self.ensemble.models else 'degraded',
            'uptime_hours': round(uptime_h, 2),
            'predictions_count': self.ensemble.predictions_count,
            'models': self.ensemble.get_model_stats(),
            'performance': {
                'avg_latency_ms': round(float(np.mean(latencies)), 2),
                'p95_latency_ms': round(float(np.percentile(latencies, 95)), 2),
                'avg_confidence': round(float(np.mean(confidences)), 4),
                'cache_hit_rate': round(self.ensemble.cache_hit_rate, 4),
            },
        }
