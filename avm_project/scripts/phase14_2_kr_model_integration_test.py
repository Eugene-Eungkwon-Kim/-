#!/usr/bin/env python3
"""
Phase 14.2.KR - Model Integration Test Suite

Tests model loading and inference for iOS/Android app architecture.
Uses ONNX Runtime for cross-platform testing.

실행:
    python scripts/phase14_2_kr_model_integration_test.py \
      --model-dir output/models/korea/quantized_lite/
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

REGIONS = ['seoul', 'busan', 'gyeonggi', 'daegu', 'incheon']
FEATURE_COUNT = 22
FEATURE_NAMES = [
    'area_sqm', 'year_built', 'floor_level', 'floors_total',
    'bedrooms', 'bathrooms', 'distance_subway_m', 'distance_school_m',
    'distance_hospital_m', 'distance_park_m', 'crime_rate',
    'nightlight_intensity', 'population_density', 'has_elevator',
    'has_parking', 'has_garden', 'house_type_apt',
    'house_type_townhouse', 'house_type_villa', 'transaction_month_log',
    'transaction_year', 'region_factor',
]


class ModelIntegrationTester:
    """Test ONNX models for mobile app integration."""

    def __init__(self, model_dir: Path) -> None:
        self.model_dir = Path(model_dir)
        self.results = []

    def load_and_test_model(self, region: str) -> Dict:
        """Load and test single model."""
        try:
            import onnxruntime as ort

            onnx_path = self.model_dir / f"KR_{region}_lite.onnx"

            if not onnx_path.exists():
                log.warning(f"{region:12} ⚠️  Model not found: {onnx_path}")
                return {'region': region, 'success': False, 'error': 'File not found'}

            # Load model
            sess = ort.InferenceSession(str(onnx_path), providers=['CPUExecutionProvider'])

            # Get input/output names
            input_names = [inp.name for inp in sess.get_inputs()]
            output_names = [out.name for out in sess.get_outputs()]

            # Create test features
            test_input = np.random.randn(1, FEATURE_COUNT).astype(np.float32)

            # Run inference
            outputs = sess.run(output_names, {input_names[0]: test_input})
            predicted_price = float(outputs[0][0][0])

            # Validate output
            if predicted_price <= 0 or predicted_price > 10_000_000_000:
                return {
                    'region': region,
                    'success': False,
                    'error': f'Invalid prediction: {predicted_price}',
                }

            file_size = onnx_path.stat().st_size / 1024 / 1024

            log.info(f"{region:12} ✅ {file_size:6.2f}MB  →  ₩{predicted_price:,.0f}")

            return {
                'region': region,
                'success': True,
                'file_size_mb': round(file_size, 3),
                'input_names': input_names,
                'output_names': output_names,
                'feature_count': FEATURE_COUNT,
                'test_prediction': int(predicted_price),
                'inference_time_ms': 0,  # Would need proper timing
            }

        except ImportError:
            log.error("ONNX Runtime not installed: pip install onnxruntime")
            return {'region': region, 'success': False, 'error': 'ONNX Runtime not installed'}
        except Exception as e:
            log.error(f"{region:12} ❌ {str(e)}")
            return {'region': region, 'success': False, 'error': str(e)}

    def run_tests(self) -> None:
        """Run all model tests."""
        log.info("\n" + "=" * 80)
        log.info("🧪 Phase 14.2.KR - Model Integration Test Suite")
        log.info("=" * 80)

        log.info(f"\n📁 Model directory: {self.model_dir}")
        log.info(f"\n{'Region':<15} {'Status':<50}")
        log.info("-" * 65)

        for region in REGIONS:
            result = self.load_and_test_model(region)
            self.results.append(result)

        log.info("-" * 65)

        # Summary
        successful = sum(1 for r in self.results if r['success'])
        total = len(self.results)

        log.info(f"\n✅ Successful: {successful}/{total}")

        if successful > 0:
            total_size = sum(
                r['file_size_mb'] for r in self.results if r.get('file_size_mb')
            )
            log.info(f"📊 Total size: {total_size:.2f}MB")

            avg_price = np.mean([
                r['test_prediction'] for r in self.results if r['success']
            ])
            log.info(f"💰 Avg predicted price: ₩{avg_price:,.0f}")

        log.info("=" * 80)

        # Save report
        self.save_report()

    def save_report(self) -> None:
        """Save test report."""
        report = {
            'test_date': str(Path(__file__).stat().st_mtime),
            'phase': '14.2.KR',
            'test_type': 'Model Integration Test',
            'model_directory': str(self.model_dir),
            'feature_count': FEATURE_COUNT,
            'features': FEATURE_NAMES,
            'regions_tested': REGIONS,
            'results': self.results,
            'summary': {
                'total_tests': len(self.results),
                'successful': sum(1 for r in self.results if r['success']),
                'failed': sum(1 for r in self.results if not r['success']),
            },
        }

        report_path = Path('output') / 'phase14_2_kr_model_integration_report.json'
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        log.info(f"📋 Report saved: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Test ONNX models for Phase 14.2.KR mobile integration'
    )
    parser.add_argument(
        '--model-dir',
        default='output/models/korea/quantized_lite/',
        help='Directory containing ONNX models'
    )
    args = parser.parse_args()

    tester = ModelIntegrationTester(Path(args.model_dir))
    tester.run_tests()


if __name__ == '__main__':
    main()
