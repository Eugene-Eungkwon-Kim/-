#!/usr/bin/env python3
"""
Phase 14.2.KR - Simple ONNX Model Generator

Creates minimal valid ONNX models for iOS/Android conversion testing.
Models simulate price prediction (input: 21 features, output: price)

실행:
    python scripts/phase14_2_kr_simple_onnx_generator.py \
      --output output/models/korea/quantized_lite/
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List
import struct

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

REGIONS = ['nationwide', 'seoul', 'busan', 'gyeonggi', 'daegu', 'incheon']
FEATURE_COUNT = 21

def create_simple_onnx_binary(region: str, output_path: Path) -> None:
    """Create a minimal ONNX model using ONNX protobuf format."""
    try:
        import onnx
        from onnx import helper, TensorProto, numpy_helper
        import numpy as np

        # Input: 21 float features
        X = helper.make_tensor_value_info('features', TensorProto.FLOAT, [None, FEATURE_COUNT])
        # Output: 1 float (predicted price)
        Y = helper.make_tensor_value_info('price', TensorProto.FLOAT, [None, 1])

        # Create a simple computation graph:
        # 1. Sum all features
        # 2. Multiply by weight
        # 3. Add bias (500M won base price)

        # Weights for summing features
        sum_weights = helper.make_tensor(
            name='sum_weights',
            data_type=TensorProto.FLOAT,
            dims=[FEATURE_COUNT, 1],
            vals=np.ones(FEATURE_COUNT, dtype=np.float32).tolist(),
        )

        # Multiply weight
        multiply_weight = helper.make_tensor(
            name='multiply_weight',
            data_type=TensorProto.FLOAT,
            dims=[1],
            vals=[5_000_000.0],  # Price per unit area
        )

        # Base price (bias)
        base_price = helper.make_tensor(
            name='base_price',
            data_type=TensorProto.FLOAT,
            dims=[1],
            vals=[500_000_000.0],  # 500M won baseline
        )

        # Nodes
        matmul_node = helper.make_node(
            'MatMul',
            inputs=['features', 'sum_weights'],
            outputs=['summed_features'],
            name='matmul_sum',
        )

        mul_node = helper.make_node(
            'Mul',
            inputs=['summed_features', 'multiply_weight'],
            outputs=['weighted'],
            name='multiply',
        )

        add_node = helper.make_node(
            'Add',
            inputs=['weighted', 'base_price'],
            outputs=['price'],
            name='add_bias',
        )

        # Graph
        graph = helper.make_graph(
            [matmul_node, mul_node, add_node],
            'loan4u_price_predictor',
            [X],
            [Y],
            [sum_weights, multiply_weight, base_price],
        )

        # Model
        model = helper.make_model(graph, producer_name='loan4u', opset_imports=[
            helper.make_opsetid('', 12)
        ])

        # Validate
        onnx.checker.check_model(model)

        # Save
        onnx.save(model, str(output_path))
        size_mb = output_path.stat().st_size / 1024 / 1024
        log.info(f"  ✅ {region:12} → {size_mb:6.3f}MB")

    except ImportError:
        log.error("ONNX library not installed. Run: pip install onnx")
        raise


class ONNXModelGenerator:
    """Generate test ONNX models."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_all_models(self) -> Dict[str, Path]:
        """Create ONNX models for all regions."""
        models = {}
        log.info("\n" + "=" * 80)
        log.info("🧪 Phase 14.2.KR - Generating Test ONNX Models")
        log.info("=" * 80)
        log.info("\n📊 Creating models for regions:")
        log.info(f"{'Region':<15} {'Size':<10}")
        log.info("-" * 25)

        for region in REGIONS:
            filepath = self.output_dir / f"KR_{region}_lite_int8.onnx"
            create_simple_onnx_binary(region, filepath)
            models[region] = filepath

        log.info("-" * 25)
        total_size = sum(p.stat().st_size for p in models.values()) / 1024 / 1024
        log.info(f"✅ Total size: {total_size:.2f}MB\n")

        return models

    def save_manifest(self, models: Dict[str, Path]) -> None:
        """Save model manifest."""
        manifest = {
            'type': 'test_models',
            'version': '1.0.0',
            'purpose': 'Phase 14.2.KR mobile app integration testing',
            'feature_count': FEATURE_COUNT,
            'regions': REGIONS,
            'models': {region: str(path) for region, path in models.items()},
            'total_size_mb': sum(p.stat().st_size for p in models.values()) / 1024 / 1024,
            'note': 'Replace with production models from Phase 14.1.KR after completion',
        }

        manifest_path = self.output_dir / 'manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        log.info(f"📋 Manifest saved: {manifest_path}")

    def run(self) -> None:
        """Generate all models and manifest."""
        models = self.create_all_models()
        self.save_manifest(models)

        log.info("=" * 80)
        log.info("✅ Test ONNX models ready for conversion to iOS/Android formats")
        log.info("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Generate test ONNX models for Phase 14.2.KR'
    )
    parser.add_argument(
        '--output',
        default='output/models/korea/quantized_lite/',
        help='Output directory for ONNX models'
    )
    args = parser.parse_args()

    generator = ONNXModelGenerator(Path(args.output))
    generator.run()


if __name__ == '__main__':
    main()
