#!/usr/bin/env python3
"""
Phase 14.2.KR - Model Integration Test (contract-driven)

Verifies every KR model loads and produces a realistic price for a realistic
property, using the shared 22-feature contract (phase14_2_kr_inference).

실행:
    python scripts/phase14_2_kr_model_integration_test.py
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List

import numpy as np

from phase14_2_kr_inference import build_feature_vector, load_contract

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

MODELS = {
    'nationwide': 'Seoul',
    'seoul': 'Seoul',
    'busan': 'Busan',
    'gyeonggi': 'Gyeonggi',
    'daegu': 'Daegu',
    'incheon': 'Incheon',
}

# Realistic sample: 84 m^2 apartment built in 2015
SAMPLE = {'area_m2': 84.0, 'year_built': 2015}
PRICE_MIN, PRICE_MAX = 10_000_000, 100_000_000_000


class ModelIntegrationTester:
    def __init__(self, model_dir: Path) -> None:
        self.model_dir = Path(model_dir)
        self.results: List[Dict] = []

    def test_one(self, model_key: str, region: str) -> Dict:
        import onnxruntime as ort

        onnx_path = self.model_dir / f"KR_{model_key}_lite.onnx"
        if not onnx_path.exists():
            log.warning(f"{model_key:11} ⚠️  not found: {onnx_path.name}")
            return {'model': model_key, 'success': False, 'error': 'file not found'}

        sess = ort.InferenceSession(str(onnx_path), providers=['CPUExecutionProvider'])
        in_name = sess.get_inputs()[0].name
        in_dim = sess.get_inputs()[0].shape[1]

        vec = build_feature_vector(region, SAMPLE['area_m2'], SAMPLE['year_built'])
        if vec.shape[1] != in_dim:
            return {'model': model_key, 'success': False,
                    'error': f'feature dim {vec.shape[1]} != model {in_dim}'}

        price = float(sess.run(None, {in_name: vec})[0].ravel()[0])
        ok = PRICE_MIN <= price <= PRICE_MAX
        size_mb = onnx_path.stat().st_size / 1024 / 1024
        log.info(f"{model_key:11} {'✅' if ok else '❌'} {size_mb:5.2f}MB  →  ₩{price:,.0f}")
        return {'model': model_key, 'region': region, 'success': ok,
                'file_size_mb': round(size_mb, 3), 'input_name': in_name,
                'input_dim': in_dim, 'prediction': int(price)}

    def run(self) -> bool:
        log.info("=" * 72)
        log.info("🧪 Phase 14.2.KR - Contract-driven Model Integration Test")
        log.info("=" * 72)
        log.info(f"Contract features: {len(load_contract())} | sample: {SAMPLE}")
        log.info("-" * 72)

        for model_key, region in MODELS.items():
            self.results.append(self.test_one(model_key, region))

        log.info("-" * 72)
        ok = sum(1 for r in self.results if r['success'])
        log.info(f"✅ Passed: {ok}/{len(self.results)}")
        self._save_report()
        return ok == len(self.results)

    def _save_report(self) -> None:
        report = {
            'phase': '14.2.KR',
            'feature_count': len(load_contract()),
            'feature_order': load_contract(),
            'sample_input': SAMPLE,
            'results': self.results,
            'passed': sum(1 for r in self.results if r['success']),
            'total': len(self.results),
        }
        out = Path('output') / 'phase14_2_kr_model_integration_report.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        log.info(f"📋 Report: {out}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-dir', default='output/models/korea/quantized_lite/')
    args = parser.parse_args()
    ok = ModelIntegrationTester(Path(args.model_dir)).run()
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
