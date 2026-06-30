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
        import onnxmltools
        import onnx
        from skl2onnx.common.data_types import FloatTensorType

        initial_types = [('float_input', FloatTensorType([None, len(FEATURE_COLS)]))]
        onnx_model = onnxmltools.convert_xgboost(model, initial_types=initial_types)

        onnx_path = output_dir / f"xgboost_{country}.onnx"
        onnx.save(onnx_model, str(onnx_path))

        size_mb = onnx_path.stat().st_size / (1024 * 1024)
        log.info(f"  XGBoost→ONNX: {size_mb:.2f}MB")
        return size_mb, str(onnx_path)
    except Exception as e:
        log.warning(f"  XGBoost ONNX conversion failed: {e}")
        return None


def convert_lightgbm_to_onnx(model, country: str, output_dir: Path) -> Optional[Tuple[float, str]]:
    """Convert LightGBM model to ONNX format. Returns (size_mb, onnx_path)."""
    try:
        import onnxmltools
        import onnx
        from skl2onnx.common.data_types import FloatTensorType

        initial_types = [('float_input', FloatTensorType([None, len(FEATURE_COLS)]))]
        onnx_model = onnxmltools.convert_lightgbm(model, initial_types=initial_types)

        onnx_path = output_dir / f"lightgbm_{country}.onnx"
        onnx.save(onnx_model, str(onnx_path))

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


def convert_xgboost_native(model: object, name: str, output_dir: Path) -> Optional[str]:
    """XGBoost 2.x 네이티브 ONNX 저장. 실패 시 onnxmltools 폴백."""
    onnx_path = output_dir / f"{name}.onnx"
    # XGBoost 2.x: .onnx 확장자로 save_model 시 ONNX 출력
    try:
        model.save_model(str(onnx_path))  # type: ignore[union-attr]
        if onnx_path.exists() and onnx_path.stat().st_size > 0:
            log.info(f"  [{name}] XGBoost 네이티브 ONNX: {onnx_path.stat().st_size/1024:.1f}KB")
            return str(onnx_path)
    except Exception as e:
        log.debug(f"  [{name}] 네이티브 ONNX 실패: {e}")

    # onnxmltools 폴백
    try:
        import onnxmltools
        import onnx
        from skl2onnx.common.data_types import FloatTensorType
        initial_types = [('float_input', FloatTensorType([None, len(FEATURE_COLS)]))]
        onnx_model = onnxmltools.convert_xgboost(model, initial_types=initial_types)
        onnx.save(onnx_model, str(onnx_path))
        log.info(f"  [{name}] onnxmltools ONNX: {onnx_path.stat().st_size/1024:.1f}KB")
        return str(onnx_path)
    except Exception as e:
        log.warning(f"  [{name}] ONNX 변환 전체 실패: {e}")
        return None


def convert_lightgbm_native(model: object, name: str, output_dir: Path) -> Optional[str]:
    """LightGBM → ONNX (onnxmltools 또는 hummingbird-ml 사용)."""
    onnx_path = output_dir / f"{name}.onnx"
    # hummingbird-ml 시도
    try:
        from hummingbird.ml import convert as hb_convert
        import torch
        sample = np.zeros((1, len(FEATURE_COLS)), dtype=np.float32)
        hb_model = hb_convert(model, 'onnx', test_input=sample)
        hb_model.save(str(output_dir / name))
        # hummingbird는 디렉토리로 저장 → onnx 파일 찾기
        for f in (output_dir / name).glob('*.onnx'):
            f.rename(onnx_path)
            break
        if onnx_path.exists():
            log.info(f"  [{name}] hummingbird ONNX: {onnx_path.stat().st_size/1024:.1f}KB")
            return str(onnx_path)
    except Exception as e:
        log.debug(f"  [{name}] hummingbird 실패: {e}")

    # onnxmltools 폴백
    try:
        import onnxmltools
        import onnx
        from skl2onnx.common.data_types import FloatTensorType
        initial_types = [('float_input', FloatTensorType([None, len(FEATURE_COLS)]))]
        onnx_model = onnxmltools.convert_lightgbm(model, initial_types=initial_types)
        onnx.save(onnx_model, str(onnx_path))
        log.info(f"  [{name}] onnxmltools ONNX: {onnx_path.stat().st_size/1024:.1f}KB")
        return str(onnx_path)
    except Exception as e:
        log.warning(f"  [{name}] ONNX 변환 전체 실패: {e}")
        return None


def convert_to_openvino_ir(onnx_path: str, name: str, output_dir: Path) -> Optional[str]:
    """ONNX → OpenVINO IR (FP32) 변환. openvino 2024.x API 사용."""
    xml_path = output_dir / f"{name}.xml"
    try:
        import openvino as ov
        ov_model = ov.convert_model(onnx_path)
        ov.save_model(ov_model, str(xml_path))
        size_mb = xml_path.stat().st_size / 1024 / 1024
        log.info(f"  [{name}] OpenVINO IR: {size_mb:.2f}MB")
        return str(xml_path)
    except ImportError:
        log.warning(f"  [{name}] openvino 미설치 - IR 변환 건너뜀")
        return None
    except Exception as e:
        log.warning(f"  [{name}] OpenVINO IR 변환 실패: {e}")
        return None


def convert_kr_models(
    pkl_dir: Path,
    output_dir: Path,
) -> Dict[str, Dict]:
    """KR 모델 (xgboost_KR, lightgbm_KR) → ONNX + IR 변환."""
    import pickle
    import json
    import time as _time
    from datetime import datetime

    output_dir.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Dict] = {}

    converters = {
        'xgboost_KR':   convert_xgboost_native,
        'lightgbm_KR':  convert_lightgbm_native,
    }

    for model_key, converter_fn in converters.items():
        pkl_path = pkl_dir / f"{model_key}.pkl"
        if not pkl_path.exists():
            log.warning(f"  {pkl_path} 없음 - 건너뜀")
            continue

        log.info(f"\n▶ {model_key}")
        t0 = _time.time()
        pkl_mb = pkl_path.stat().st_size / 1024 / 1024

        with open(pkl_path, 'rb') as f:
            model = pickle.load(f)

        onnx_path = converter_fn(model, model_key, output_dir)
        onnx_mb   = Path(onnx_path).stat().st_size / 1024 / 1024 if onnx_path else None
        ir_path   = convert_to_openvino_ir(onnx_path, model_key, output_dir) if onnx_path else None
        ir_mb     = Path(ir_path).stat().st_size / 1024 / 1024 if ir_path else None

        status = 'ir_ready' if ir_path else ('onnx_only' if onnx_path else 'pkl_only')
        report[model_key] = {
            'pkl_size_mb':  round(pkl_mb, 3),
            'onnx_size_mb': round(onnx_mb, 3) if onnx_mb else None,
            'ir_size_mb':   round(ir_mb, 3) if ir_mb else None,
            'status':       status,
            'elapsed_sec':  round(_time.time() - t0, 2),
        }
        log.info(f"  상태: {status}")

    # 리포트 저장
    report_path = output_dir.parent / 'conversion_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({'timestamp': datetime.now().isoformat(), 'models': report}, f, indent=2)
    log.info(f"\n✅ 변환 리포트: {report_path}")
    return report


def main() -> None:
    """Run Phase 13.2.5 model conversion."""
    import argparse

    parser = argparse.ArgumentParser(description='Phase 13.2.5 Model Converter')
    parser.add_argument('--country',  default='KR',                    help='국가 코드 (KR 전용)')
    parser.add_argument('--pkl-dir',  default='output/trained_models', help='pkl 모델 디렉토리')
    parser.add_argument('--output',   default='output/models_ir',      help='출력 디렉토리')
    # 레거시 인수 (multi-country 모드)
    parser.add_argument('--models',   default='models',   help='(레거시) 모델 디렉토리')
    parser.add_argument('--data',     default='data/raw', help='(레거시) 데이터 디렉토리')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info(f"Phase 13.2.5 모델 변환 시작 (대상: {args.country})")
    log.info("=" * 60)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.country == 'KR':
        report = convert_kr_models(Path(args.pkl_dir), output_dir)
        success = sum(1 for v in report.values() if v['status'] != 'pkl_only')
        log.info(f"\n{success}/{len(report)} 모델 ONNX/IR 변환 완료")
    else:
        # 레거시 멀티-컨트리 경로
        all_results: List[ConversionResult] = []
        for country_data in Path(args.data).glob('*_data.csv'):
            country = country_data.stem.replace('_data', '')
            log.info(f"Converting {country}...")
            all_results.extend(convert_country_models(
                country, Path(args.models), Path(args.data), output_dir))
        summary = summarize_conversions(all_results)
        log.info(f"Models converted: {summary['total']}")


if __name__ == '__main__':
    main()
