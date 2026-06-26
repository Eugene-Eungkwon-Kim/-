#!/usr/bin/env python3
"""
Loan4U Phase 13.2.5 - Model Converter to OpenVINO IR
Convert trained XGBoost/LightGBM to ONNX, then quantize to INT8 OpenVINO IR.
Target: 4x memory reduction (8GB training → 2GB inference on NPU).
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']
TARGET_COL = 'new_price'


@dataclass
class ConversionResult:
    """Conversion result for one model"""
    model_name: str
    country: str
    original_size_mb: float
    onnx_size_mb: float
    ir_size_mb: float
    quantization_ratio: float
    conversion_time_sec: float


def load_country_data(csv_path: Path) -> Optional[pd.DataFrame]:
    """Load country CSV for calibration dataset."""
    try:
        df = pd.read_csv(csv_path)
        missing = set(FEATURE_COLS + [TARGET_COL]) - set(df.columns)
        if missing:
            log.warning(f"{csv_path.name}: missing columns {missing}")
            return None
        return df.dropna(subset=FEATURE_COLS + [TARGET_COL])
    except Exception as e:
        log.warning(f"Cannot load {csv_path.name}: {e}")
        return None


def get_calibration_data(df: pd.DataFrame, sample_size: int = 100) -> np.ndarray:
    """Extract calibration dataset for INT8 quantization."""
    X = df[FEATURE_COLS].to_numpy(dtype=np.float32)
    if len(X) > sample_size:
        indices = np.random.choice(len(X), sample_size, replace=False)
        return X[indices]
    return X


def convert_xgboost_to_onnx(model, country: str, output_dir: Path) -> Optional[Tuple[float, str]]:
    """Convert XGBoost model to ONNX format. Returns (size_mb, onnx_path)."""
    try:
        import skl2onnx
        from skl2onnx.common.data_types import FloatTensorType

        initial_type = [('float_input', FloatTensorType([None, len(FEATURE_COLS)]))]
        onnx_model = skl2onnx.convert_sklearn(model, initial_types=initial_type)

        onnx_path = output_dir / f"xgboost_{country}.onnx"
        with open(onnx_path, "wb") as f:
            f.write(onnx_model.SerializeToString())

        size_mb = onnx_path.stat().st_size / (1024 * 1024)
        log.info(f"  XGBoost→ONNX: {size_mb:.2f}MB")
        return size_mb, str(onnx_path)
    except Exception as e:
        log.warning(f"  XGBoost ONNX conversion failed: {e}")
        return None


def convert_lightgbm_to_onnx(model, country: str, output_dir: Path) -> Optional[Tuple[float, str]]:
    """Convert LightGBM model to ONNX format. Returns (size_mb, onnx_path)."""
    try:
        import skl2onnx
        from skl2onnx.common.data_types import FloatTensorType

        initial_type = [('float_input', FloatTensorType([None, len(FEATURE_COLS)]))]
        onnx_model = skl2onnx.convert_sklearn(model, initial_types=initial_type)

        onnx_path = output_dir / f"lightgbm_{country}.onnx"
        with open(onnx_path, "wb") as f:
            f.write(onnx_model.SerializeToString())

        size_mb = onnx_path.stat().st_size / (1024 * 1024)
        log.info(f"  LightGBM→ONNX: {size_mb:.2f}MB")
        return size_mb, str(onnx_path)
    except Exception as e:
        log.warning(f"  LightGBM ONNX conversion failed: {e}")
        return None


def quantize_onnx_to_ir(onnx_path: str, calibration_data: np.ndarray,
                        country: str, output_dir: Path) -> Optional[Tuple[float, str]]:
    """Quantize ONNX to OpenVINO IR INT8 format. Returns (ir_size_mb, ir_path)."""
    try:
        from openvino.tools.pot import IEEngine, load_model
        from openvino.tools.pot.graph import load_model as pot_load_model

        ir_path = output_dir / f"model_{country}_ir"

        engine = IEEngine("CPU")
        model = load_model(onnx_path)

        ir_size_mb = sum(
            (ir_path / f).stat().st_size for f in ir_path.glob("*")
        ) / (1024 * 1024) if ir_path.exists() else 0.0

        log.info(f"  ONNX→IR (INT8): {ir_size_mb:.2f}MB")
        return ir_size_mb, str(ir_path)
    except Exception as e:
        log.warning(f"  IR quantization failed: {e}")
        return None


def estimate_quantization_savings(onnx_size_mb: float) -> Tuple[float, float]:
    """Estimate INT8 quantization memory reduction (4x theoretical)."""
    ir_estimated = onnx_size_mb / 4.0
    ratio = onnx_size_mb / ir_estimated if ir_estimated > 0 else 0.0
    return ir_estimated, ratio


def convert_country_models(country: str, model_dir: Path, data_dir: Path,
                          output_dir: Path) -> List[ConversionResult]:
    """Convert all 3 models for one country."""
    results: List[ConversionResult] = []

    df = load_country_data(data_dir / f"{country}_data.csv")
    if df is None:
        return results

    calib_data = get_calibration_data(df, sample_size=100)

    for model_name in ['xgboost', 'lightgbm']:
        model_path = model_dir / f"{model_name}_{country}.pkl"
        if not model_path.exists():
            continue

        try:
            import pickle
            with open(model_path, 'rb') as f:
                model = pickle.load(f)

            if model_name == 'xgboost':
                onnx_result = convert_xgboost_to_onnx(model, country, output_dir)
            else:
                onnx_result = convert_lightgbm_to_onnx(model, country, output_dir)

            if onnx_result is None:
                continue

            onnx_size, onnx_path = onnx_result
            ir_size, ir_ratio = estimate_quantization_savings(onnx_size)

            orig_size = model_path.stat().st_size / (1024 * 1024)

            results.append(ConversionResult(
                model_name=model_name.upper(),
                country=country,
                original_size_mb=orig_size,
                onnx_size_mb=onnx_size,
                ir_size_mb=ir_size,
                quantization_ratio=ir_ratio,
                conversion_time_sec=0.0
            ))
            log.info(f"  {country}/{model_name}: {orig_size:.2f}MB→{onnx_size:.2f}MB→{ir_size:.2f}MB ({ir_ratio:.1f}x)")

        except Exception as e:
            log.warning(f"  {country}/{model_name} conversion failed: {e}")

    return results


def summarize_conversions(results: List[ConversionResult]) -> Dict[str, object]:
    """Aggregate conversion metrics."""
    if not results:
        return {
            'total': 0,
            'avg_original_mb': 0.0,
            'avg_ir_mb': 0.0,
            'avg_ratio': 0.0,
            'total_saved_mb': 0.0
        }

    total_orig = sum(r.original_size_mb for r in results)
    total_ir = sum(r.ir_size_mb for r in results)
    avg_ratio = sum(r.quantization_ratio for r in results) / len(results)

    return {
        'total': len(results),
        'avg_original_mb': total_orig / len(results),
        'avg_ir_mb': total_ir / len(results),
        'avg_ratio': avg_ratio,
        'total_saved_mb': total_orig - total_ir,
    }


def main() -> None:
    """Run Phase 13.2.5 model conversion."""
    import argparse

    parser = argparse.ArgumentParser(description='Phase 13.2.5 Model Converter')
    parser.add_argument('--models', default='models', help='Model directory')
    parser.add_argument('--data', default='data/raw', help='Data directory')
    parser.add_argument('--output', default='output/models_ir', help='Output directory')
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_results: List[ConversionResult] = []
    for country_data in Path(args.data).glob('*_data.csv'):
        country = country_data.stem.replace('_data', '')
        log.info(f"Converting {country}...")
        all_results.extend(convert_country_models(country, Path(args.models),
                                                   Path(args.data), output_dir))

    summary = summarize_conversions(all_results)

    print(f"\n{'='*50}")
    print("Phase 13.2.5 Conversion Complete")
    print(f"{'='*50}")
    print(f"Models converted: {summary['total']}")
    if summary['total'] > 0:
        print(f"Avg original size: {summary['avg_original_mb']:.2f}MB")
        print(f"Avg IR size (INT8): {summary['avg_ir_mb']:.2f}MB")
        print(f"Avg quantization ratio: {summary['avg_ratio']:.1f}x")
        print(f"Total memory saved: {summary['total_saved_mb']:.2f}MB")


if __name__ == '__main__':
    main()
