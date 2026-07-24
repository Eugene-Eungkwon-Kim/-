#!/usr/bin/env python3
"""
Phase 14.2.KR - Convert ONNX Models to iOS Core ML Format

Converts ONNX models to .mlmodel format for iOS integration.

실행:
    python scripts/phase14_2_kr_convert_models_ios.py \
      --input-dir output/models/korea/quantized_lite/ \
      --output-dir ios_app/Loan4U_iOS/Models/
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List
import sys

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

REGIONS = ['nationwide', 'seoul', 'busan', 'gyeonggi', 'daegu', 'incheon']


class ONNX2CoreMLConverter:
    """Convert ONNX models to Core ML format."""

    def __init__(self, input_dir: Path, output_dir: Path) -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def convert_model(self, onnx_path: Path, output_path: Path) -> bool:
        """Convert single ONNX model to Core ML."""
        try:
            import onnx
            import coremltools as ct

            log.info(f"  Converting: {onnx_path.name}...")

            # Load ONNX model
            onnx_model = onnx.load(str(onnx_path))
            onnx.checker.check_model(onnx_model)

            # Convert to Core ML
            ml_model = ct.convert(
                onnx_model,
                convert_to="mlprogram",
                compute_units=ct.ComputeUnit.ALL,
            )

            # Save
            ml_model.save(str(output_path))
            size_mb = output_path.stat().st_size / 1024 / 1024
            log.info(f"    ✅ {size_mb:.3f}MB")
            return True

        except ImportError as e:
            log.error(f"Required library not installed: {e}")
            log.error("Install with: pip install coremltools onnx")
            return False
        except Exception as e:
            log.error(f"    ❌ Failed: {e}")
            return False

    def convert_all(self) -> Dict[str, Path]:
        """Convert all ONNX models to Core ML."""
        log.info("\n" + "=" * 80)
        log.info("🍎 Phase 14.2.KR - ONNX to Core ML Conversion (iOS)")
        log.info("=" * 80)

        results = {}
        log.info(f"\n📁 Input:  {self.input_dir}")
        log.info(f"📁 Output: {self.output_dir}")
        log.info(f"\n{'Region':<15} {'Status':<20}")
        log.info("-" * 35)

        for region in REGIONS:
            onnx_path = self.input_dir / f"KR_{region}_lite.onnx"
            mlmodel_path = self.output_dir / f"KR_{region}_lite_int8.mlmodel"

            if not onnx_path.exists():
                log.warning(f"{region:<15} ⚠️  ONNX file not found")
                continue

            if self.convert_model(onnx_path, mlmodel_path):
                results[region] = mlmodel_path
            else:
                results[region] = None

        log.info("-" * 35)

        # Summary
        successful = sum(1 for v in results.values() if v is not None)
        total_size = sum(
            p.stat().st_size / 1024 / 1024
            for p in results.values()
            if p is not None
        )

        log.info(f"\n✅ Converted: {successful}/{len(REGIONS)} models")
        log.info(f"📊 Total size: {total_size:.2f}MB")
        log.info("=" * 80)

        return results

    def save_report(self, results: Dict[str, Path]) -> None:
        """Save conversion report."""
        report = {
            'timestamp': str(Path(__file__).stat().st_mtime),
            'conversion_type': 'ONNX → Core ML',
            'platform': 'iOS',
            'input_directory': str(self.input_dir),
            'output_directory': str(self.output_dir),
            'models': {
                region: {
                    'path': str(path) if path else None,
                    'size_mb': path.stat().st_size / 1024 / 1024 if path else 0,
                    'status': 'success' if path else 'failed',
                }
                for region, path in results.items()
            },
            'total_size_mb': sum(
                p.stat().st_size / 1024 / 1024 for p in results.values() if p
            ),
        }

        report_path = self.output_dir / 'conversion_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        log.info(f"📋 Report saved: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Convert ONNX models to iOS Core ML format'
    )
    parser.add_argument(
        '--input-dir',
        default='output/models/korea/quantized_lite/',
        help='Input directory with ONNX models'
    )
    parser.add_argument(
        '--output-dir',
        default='ios_app/Loan4U_iOS/Models/',
        help='Output directory for Core ML models'
    )
    args = parser.parse_args()

    converter = ONNX2CoreMLConverter(Path(args.input_dir), Path(args.output_dir))
    results = converter.convert_all()
    converter.save_report(results)


if __name__ == '__main__':
    main()
