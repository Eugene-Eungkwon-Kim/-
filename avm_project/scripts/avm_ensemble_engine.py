"""WP 2.2: Ensemble Engine - 3-모델 앙상블 예측 (XGBoost 80%, LightGBM 15%, GB 5%)."""

import logging
import pickle
import time
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)

MODEL_WEIGHTS = {
    'xgboost': 0.80,
    'lightgbm': 0.15,
    'gradient_boosting': 0.05,
}

BASE_CONFIDENCE = 0.90
STD_PENALTY_FACTOR = 0.10
MIN_CONFIDENCE = 0.70
CACHE_MAXSIZE = 10000


class AVMEnsembleEngine:
    """3-모델 앙상블 예측 엔진."""

    def __init__(self, model_dir: str) -> None:
        self.model_dir = Path(model_dir)
        self.models: Dict[str, object] = {}
        self._cache: OrderedDict = OrderedDict()
        self.cache_hits = 0
        self.cache_misses = 0
        self.predictions_count = 0
        self.latencies: List[float] = []
        self._load_models()
        log.info(f"Ensemble engine ready: {list(self.models.keys())}")

    def _load_models(self) -> None:
        """IR 모델 우선 로드, 없으면 pickle 폴백."""
        ir_dir = self.model_dir
        if ir_dir.exists():
            self._load_ir_models(ir_dir)

        if not self.models:
            pkl_dir = ir_dir.parent / 'trained_models'
            if pkl_dir.exists():
                self._load_pickled_models(pkl_dir)

        if not self.models:
            log.error(f"No models found in {self.model_dir}")

    def _load_ir_models(self, ir_dir: Path) -> None:
        """OpenVINO IR 모델 로드."""
        try:
            from openvino.runtime import Core
            ie = Core()
            for xml_file in ir_dir.glob('*.xml'):
                try:
                    model = ie.read_model(str(xml_file))
                    compiled = ie.compile_model(model, 'CPU')
                    name = xml_file.stem
                    self.models[name] = compiled
                    log.info(f"Loaded IR model: {name}")
                except Exception as e:
                    log.warning(f"IR load failed {xml_file.name}: {e}")
        except ImportError:
            log.debug("OpenVINO not available, using pickle fallback")

    def _load_pickled_models(self, pkl_dir: Path) -> None:
        """Pickle sklearn 모델 로드."""
        for pkl_file in sorted(pkl_dir.glob('*.pkl')):
            try:
                with open(pkl_file, 'rb') as f:
                    model = pickle.load(f)
                name = pkl_file.stem
                self.models[name] = model
                log.info(f"Loaded pickled model: {name}")
            except Exception as e:
                log.warning(f"Pickle load failed {pkl_file.name}: {e}")

    def _run_single(self, model_name: str, model: object, features: np.ndarray) -> Optional[float]:
        """단일 모델 예측."""
        try:
            if hasattr(model, 'infer'):  # OpenVINO
                result = model(features.reshape(1, -1))
                return float(list(result.values())[0].flat[0])
            return float(model.predict(features.reshape(1, -1))[0])  # sklearn
        except Exception as e:
            log.warning(f"Model {model_name} failed: {e}")
            return None

    def _calculate_confidence(self, predictions: List[float]) -> float:
        """표준편차 기반 신뢰도 계산."""
        if len(predictions) < 2:
            return BASE_CONFIDENCE
        mean = np.mean(predictions)
        std = np.std(predictions)
        cv = (std / mean) if mean > 0 else 0
        return max(MIN_CONFIDENCE, BASE_CONFIDENCE - cv * STD_PENALTY_FACTOR * 100)

    def predict(self, features: np.ndarray) -> Tuple[float, float, float]:
        """앙상블 예측: (price, confidence, latency_ms)."""
        cache_key = tuple(features.tolist())
        if cache_key in self._cache:
            self.cache_hits += 1
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        self.cache_misses += 1
        start = time.perf_counter()

        raw_predictions: Dict[str, float] = {}
        for name, model in self.models.items():
            pred = self._run_single(name, model, features)
            if pred is not None:
                raw_predictions[name] = pred

        if not raw_predictions:
            log.error("All models failed prediction")
            return 0.0, 0.0, 0.0

        # 가중 평균 (알려진 모델명 기준, 나머지는 균등 가중치)
        total_weight = 0.0
        weighted_sum = 0.0
        for name, pred in raw_predictions.items():
            # 모델명 접두사로 가중치 매핑
            weight = next(
                (w for key, w in MODEL_WEIGHTS.items() if key in name.lower()),
                1.0 / len(raw_predictions)
            )
            weighted_sum += pred * weight
            total_weight += weight

        base_price = weighted_sum / total_weight if total_weight > 0 else np.mean(list(raw_predictions.values()))
        confidence = self._calculate_confidence(list(raw_predictions.values()))
        latency_ms = (time.perf_counter() - start) * 1000.0

        result = (base_price, confidence, latency_ms)

        if len(self._cache) >= CACHE_MAXSIZE:
            self._cache.popitem(last=False)
        self._cache[cache_key] = result

        self.predictions_count += 1
        self.latencies.append(latency_ms)
        return result

    @property
    def cache_hit_rate(self) -> float:
        """캐시 히트율."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    def get_model_stats(self) -> Dict:
        """엔진 통계 조회."""
        latencies = self.latencies or [0.0]
        return {
            'models_loaded': len(self.models),
            'model_names': list(self.models.keys()),
            'device': 'NPU/CPU',
            'cache_size': len(self._cache),
            'cache_hit_rate': self.cache_hit_rate,
            'predictions_count': self.predictions_count,
            'avg_latency_ms': float(np.mean(latencies)),
            'p95_latency_ms': float(np.percentile(latencies, 95)),
        }
