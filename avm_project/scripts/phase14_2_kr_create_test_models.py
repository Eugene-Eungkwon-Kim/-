#!/usr/bin/env python3
"""
Phase 14.2.KR - Create Test ONNX Models for Mobile Integration

Creates lightweight ONNX models that mimic Phase 14.1.KR output for:
- Mobile app development
- Model conversion testing (ONNX → CoreML / TFLite)
- Integration testing

실행:
    python scripts/phase14_2_kr_create_test_models.py \
      --output output/models/korea/quantized_lite/
"""

import argparse
import json
import logging
import onnx
import onnxruntime as rt
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import skl2onnx
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

FEATURE_NAMES = [
    'area_sqm', 'year_built', 'floor_level', 'floors_total',
    'bedrooms', 'bathrooms', 'distance_subway_m', 'distance_school_m',
    'distance_hospital_m', 'distance_park_m', 'crime_rate',
    'nightlight_intensity', 'population_density', 'has_elevator',
    'has_parking', 'has_garden', 'house_type_apt',
    'house_type_townhouse', 'house_type_villa', 'transaction_month_log',
    'transaction_year',
]

REGIONS = ['nationwide', 'seoul', 'busan', 'gyeonggi', 'daegu', 'incheon']

class TestModelGenerator:
    """Generate lightweight ONNX models for testing."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_synthetic_data(self, n_samples: int = 500) -> Tuple[np.ndarray, np.ndarray]:
        """Create synthetic real estate data."""
        np.random.seed(42)

        X = np.random.randn(n_samples, len(FEATURE_NAMES)).astype(np.float32)
        X[:, 0] = np.random.uniform(50, 200, n_samples)
        X[:, 1] = np.random.uniform(1980, 2024, n_samples)

        y = (
            X[:, 0] * 5_000_000 +
            (2024 - X[:, 1]) * 50_000 +
            np.random.randn(n_samples) * 100_000_000
        ).astype(np.float32)

        y = np.clip(y, 100_000_000, 2_000_000_000)

        return X.astype(np.float32), y

    def create_model(self, region: str) -> onnx.ModelProto:
        """Create a simple GradientBoosting model converted to ONNX."""
        log.info(f"Creating test model for {region}...")

        X, y = self.create_synthetic_data()

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = GradientBoostingRegressor(
            n_estimators=50,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            verbose=0,
        )
        model.fit(X_scaled, y)

        initial_type = [('float_input', skl2onnx.FloatTensorType([None, len(FEATURE_NAMES)]))]

        try:
            from skl2onnx import convert_sklearn
            onnx_model = convert_sklearn(model, initial_types=initial_type)
            onnx.checker.check_model(onnx_model)
            return onnx_model
        except Exception as e:
            log.warning(f"Failed to convert to ONNX: {e}, creating dummy model")
            return self._create_dummy_onnx_model()

    def _create_dummy_onnx_model(self) -> onnx.ModelProto:
        """Create a simple dummy ONNX model for testing."""
        from onnx import helper, TensorProto

        X = helper.make_tensor_value_info('float_input', TensorProto.FLOAT, [None, 21])
        Y = helper.make_tensor_value_info('predicted_price', TensorProto.FLOAT, [None, 1])

        const_value = helper.make_tensor(
            name='const_value',
            data_type=TensorProto.FLOAT,
            dims=[1],
            vals=[500_000_000.0],
        )

        node_def = helper.make_node(
            'Add',
            inputs=['float_input_reduced', 'const_value'],
            outputs=['predicted_price'],
            name='add_const',
        )

        reduce_node = helper.make_node(
            'ReduceMean',
            inputs=['float_input'],
            outputs=['float_input_reduced'],
            name='reduce_mean',
        )

        graph_def = helper.make_graph(
            [reduce_node, node_def],
            'DummyModel',
            [X],
            [Y],
            [const_value],
        )

        model_def = helper.make_model(graph_def, producer_name='loan4u')
        onnx.checker.check_model(model_def)
        return model_def

    def save_model(self, onnx_model: onnx.ModelProto, region: str) -> Path:
        """Save ONNX model to disk."""
        filename = f"KR_{region}_lite_int8.onnx"
        filepath = self.output_dir / filename
        onnx.save(onnx_model, str(filepath))

        size_mb = filepath.stat().st_size / 1024 / 1024
        log.info(f"  ✅ Saved: {filepath} ({size_mb:.2f}MB)")
        return filepath

    def run(self) -> None:
        """Create all test models."""
        log.info("\n" + "=" * 80)
        log.info("🧪 Phase 14.2.KR - Creating Test ONNX Models")
        log.info("=" * 80)

        models = {}
        for region in REGIONS:
            model = self.create_model(region)
            filepath = self.save_model(model, region)
            models[region] = str(filepath)

        log.info("\n" + "=" * 80)
        log.info(f"✅ Created {len(models)} test models")
        log.info(f"📁 Output directory: {self.output_dir}")
        log.info("=" * 80)

        self.save_manifest(models)

    def save_manifest(self, models: Dict[str, str]) -> None:
        """Save manifest of created models."""
        manifest = {
            'timestamp': str(Path.ctime(Path.cwd())),
            'purpose': 'Testing Phase 14.2.KR mobile integration',
            'models': models,
            'features': FEATURE_NAMES,
            'note': 'These are lightweight test models. Replace with production models after Phase 14.1.KR completion.',
        }

        manifest_path = self.output_dir / 'manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        log.info(f"📋 Manifest saved: {manifest_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Create test ONNX models for Phase 14.2.KR mobile integration'
    )
    parser.add_argument('--output', default='output/models/korea/quantized_lite/')
    args = parser.parse_args()

    generator = TestModelGenerator(Path(args.output))
    generator.run()


if __name__ == '__main__':
    main()
