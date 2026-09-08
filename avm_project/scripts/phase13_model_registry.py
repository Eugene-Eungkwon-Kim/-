#!/usr/bin/env python3
"""
Phase 13.5 - Model Registry & Country Routing
다국가 모델 메타데이터 관리 및 런타임 라우팅 + 학습 파이프라인 등록 이력.

구조:
  ModelRegistry.load_model('SG')     → AVMInferenceEngine (캐시됨)
  ModelRegistry.get_info('BR')       → {model_id, MAPE, R², features, ...}
  ModelRegistry.list_countries()     → [KR, BR, SG, HK, UK, DE, AU, CA, TH]
  ModelRegistry.register_model(...)  → 새로 학습된 모델을 이력에 등록
  ModelRegistry.list_models('KR')    → 국가별 등록 이력 (최신순)
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

SUPPORTED_COUNTRIES = {'KR', 'BR', 'SG', 'HK', 'UK', 'DE', 'AU', 'CA', 'TH'}


@dataclass
class ModelMetadata:
    """단일 학습 실행의 등록 메타데이터 (phase13_automation_engine.py가 생성)."""

    version: str
    country: str
    algorithm: str
    r2_score: float
    mape: float
    training_date: str
    model_size_mb: float
    ir_size_mb: float
    status: str


class ModelRegistry:
    """9개국 모델 카탈로그·캐싱 + 학습 파이프라인 등록 이력 저장소."""

    def __init__(self, model_dir: str = 'output/converted_models',
                 metadata_dir: str = 'output/models',
                 registry_dir: str = 'output/registry') -> None:
        self.model_dir = Path(model_dir)
        self.metadata_dir = Path(metadata_dir)
        self.registry_dir = Path(registry_dir)
        self._model_cache: Dict[str, object] = {}
        self._metadata_cache: Dict[str, Dict] = {}
        self._load_all_metadata()

    def _load_all_metadata(self) -> None:
        """모든 국가의 메타데이터 JSON 로드."""
        for cc in SUPPORTED_COUNTRIES:
            meta_file = self.metadata_dir / f'{cc.lower()}_production_v1.0_metadata.json'
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        self._metadata_cache[cc] = json.load(f)
                except Exception as e:
                    log.warning(f"Failed to load {cc} metadata: {e}")

    def get_info(self, country: str) -> Optional[Dict]:
        """국가의 모델 메타데이터 반환."""
        if country not in self._metadata_cache:
            return None
        return self._metadata_cache[country].copy()

    def load_model(self, country: str):
        """국가별 ONNX 모델 로드 (캐시)."""
        if country not in SUPPORTED_COUNTRIES:
            raise ValueError(f"Unsupported country: {country}")

        if country in self._model_cache:
            return self._model_cache[country]

        model_file = self.model_dir / f'{country.lower()}_production_v1.0.onnx'
        if not model_file.exists():
            raise FileNotFoundError(f"Model not found: {model_file}")

        try:
            from phase13_inference_engine import AVMInferenceEngine
            engine = AVMInferenceEngine(str(model_file), backend='auto')
            self._model_cache[country] = engine
            log.info(f"✅ Loaded {country} model (backend={engine.backend})")
            return engine
        except Exception as e:
            log.error(f"Failed to load {country} model: {e}")
            raise

    def list_countries(self) -> List[str]:
        """사용 가능한 모든 국가 반환."""
        available = [cc for cc in SUPPORTED_COUNTRIES if cc in self._metadata_cache]
        return sorted(available)

    def get_feature_count(self, country: str) -> Optional[int]:
        """국가별 특성 개수."""
        meta = self.get_info(country)
        return meta.get('n_features') if meta else None

    def validate_features(self, country: str, features: np.ndarray) -> bool:
        """요청 특성 형상 검증."""
        expected_n_features = self.get_feature_count(country)
        if expected_n_features is None:
            return False
        return features.ndim == 2 and features.shape[1] == expected_n_features

    def get_model_summary(self) -> Dict:
        """모든 모델 정보 요약 반환."""
        summary = {
            'countries': self.list_countries(),
            'models': {},
            'timestamp': __import__('datetime').datetime.now().isoformat(),
        }
        for cc in summary['countries']:
            meta = self.get_info(cc)
            if meta:
                summary['models'][cc] = {
                    'model_id': meta.get('model_id'),
                    'performance': meta.get('performance', {}),
                    'n_features': meta.get('n_features'),
                    'created_date': meta.get('created_date'),
                }
        return summary

    def _registry_file(self, country: str) -> Path:
        return self.registry_dir / f'{country}.json'

    def register_model(self, metadata: ModelMetadata, pkl_path: str, onnx_path: str) -> str:
        """새로 학습된 모델을 등록 이력에 추가하고 model_id를 반환한다.

        국가별 파일(예: registry/KR.json)에 최신 등록이 맨 앞에 오도록
        누적한다 — 과거 실행 이력을 지우지 않고 감사(audit) 가능하게 둔다.
        """
        model_id = f"{metadata.country}_{metadata.algorithm}_{metadata.version}"
        entry = {
            **asdict(metadata),
            'model_id': model_id,
            'pkl_path': pkl_path,
            'onnx_path': onnx_path,
        }

        self.registry_dir.mkdir(parents=True, exist_ok=True)
        entries = self.list_models(metadata.country)
        entries.insert(0, entry)
        with open(self._registry_file(metadata.country), 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

        return model_id

    def list_models(self, country: str) -> List[Dict]:
        """국가별 등록 이력을 최신 등록순으로 반환한다 (없으면 빈 리스트)."""
        reg_file = self._registry_file(country)
        if not reg_file.exists():
            return []
        with open(reg_file, 'r', encoding='utf-8') as f:
            return json.load(f)


if __name__ == '__main__':
    # phase14_deploy.yml이 stdout을 model_registry_status.json으로 그대로
    # 리다이렉트한다 — 사람이 읽는 텍스트가 아니라 유효한 JSON을 찍어야 한다.
    registry = ModelRegistry()
    print(json.dumps(registry.get_model_summary(), ensure_ascii=False, indent=2))
