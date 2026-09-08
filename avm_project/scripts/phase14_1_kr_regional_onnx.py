#!/usr/bin/env python3
"""
Phase 14.1.KR - Regional Models ONNX Conversion & Quantization

지역별 단일 LightGBM 모델을 ONNX로 변환하고 INT8 양자화.

실행:
    python scripts/phase14_1_kr_regional_onnx.py \
      --models-dir output/models/korea/regional_lite \
      --output-dir output/models/korea/quantized_lite
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

try:
    import lightgbm as lgb
except ImportError:
    lgb = None  # export_onnx의 타입힌트만 참조 — 실제 변환 시점엔 register_gbm_converters()가 다시 임포트한다.

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

REGIONS = ['Seoul', 'Busan', 'Gyeonggi', 'Daegu', 'Incheon']


def register_gbm_converters() -> None:
    """LightGBM 컨버터 등록."""
    from skl2onnx import update_registered_converter
    from skl2onnx.common.shape_calculator import calculate_linear_regressor_output_shapes
    from onnxmltools.convert.lightgbm.operator_converters.LightGbm import convert_lightgbm
    import lightgbm as lgb

    update_registered_converter(
        lgb.LGBMRegressor, 'LightGbmLGBMRegressor',
        calculate_linear_regressor_output_shapes, convert_lightgbm,
        options={'split': None},
    )


def export_onnx(model: lgb.LGBMRegressor, n_features: int, output_path: Path) -> float:
    """LightGBM → ONNX 변환."""
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    import time

    t0 = time.time()
    onnx_model = convert_sklearn(
        model,
        initial_types=[('float_input', FloatTensorType([None, n_features]))],
        target_opset={'': 15, 'ai.onnx.ml': 3},
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(onnx_model.SerializeToString())
    return time.time() - t0


def quantize_int8(onnx_path: Path, int8_path: Path) -> float:
    """ONNX INT8 양자화."""
    from onnxruntime.quantization import quantize_dynamic, QuantType
    import time

    t0 = time.time()
    quantize_dynamic(
        model_input=str(onnx_path),
        model_output=str(int8_path),
        weight_type=QuantType.QInt8,
    )
    return time.time() - t0


def convert_region_model(
    region: str,
    model_dir: Path,
    output_dir: Path,
) -> Optional[Dict]:
    """단일 지역 모델 변환."""
    import pickle

    # 학습된 모델 로드
    model_path = model_dir / f'{region}_lite.pkl'
    if not model_path.exists():
        log.warning(f"⚠️  {region}: Model not found")
        return None

    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    pkl_mb = model_path.stat().st_size / 1024 / 1024

    # ONNX 변환
    n_features = 22  # KR 데이터셋의 특성 수
    onnx_path = output_dir / f'KR_{region.lower()}_lite.onnx'
    export_sec = export_onnx(model, n_features, onnx_path)
    onnx_mb = onnx_path.stat().st_size / 1024 / 1024

    # INT8 양자화
    int8_path = output_dir / f'KR_{region.lower()}_lite_int8.onnx'
    quant_sec = quantize_int8(onnx_path, int8_path)
    int8_mb = int8_path.stat().st_size / 1024 / 1024

    log.info(
        f"  {region:12} {pkl_mb:6.3f}MB → {onnx_mb:6.3f}MB → "
        f"{int8_mb:6.3f}MB | export {export_sec:.1f}s quant {quant_sec:.1f}s"
    )

    return {
        'region': region,
        'sizes_mb': {
            'pkl': round(pkl_mb, 3),
            'onnx': round(onnx_mb, 3),
            'int8': round(int8_mb, 3),
        },
        'pkl_to_onnx_ratio': round(pkl_mb / onnx_mb, 1),
        'pkl_to_int8_ratio': round(pkl_mb / int8_mb, 1),
        'timing_sec': {'export': round(export_sec, 2), 'quantize': round(quant_sec, 2)},
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description='Phase 14.1.KR Regional ONNX Conversion')
    parser.add_argument('--models-dir', default='output/models/korea/regional_lite')
    parser.add_argument('--output-dir', default='output/models/korea/quantized_lite')
    args = parser.parse_args()

    model_dir = Path(args.models_dir)
    output_dir = Path(args.output_dir)

    log.info("\n" + "=" * 80)
    log.info("🇰🇷 Phase 14.1.KR Regional Model ONNX Conversion & Quantization")
    log.info("=" * 80)

    register_gbm_converters()

    log.info("\n📊 Converting 5 regional models to ONNX + INT8:")
    log.info("-" * 80)

    results = [
        convert_region_model(region, model_dir, output_dir)
        for region in REGIONS
    ]

    valid = [r for r in results if r]

    # 요약
    log.info("\n" + "=" * 80)
    log.info("Regional Model Conversion Summary")
    log.info("=" * 80)

    total_pkl = sum(r['sizes_mb']['pkl'] for r in valid)
    total_int8 = sum(r['sizes_mb']['int8'] for r in valid)

    for r in valid:
        log.info(
            f"  {r['region']:12} {r['sizes_mb']['pkl']:7.3f}MB → "
            f"{r['sizes_mb']['int8']:7.3f}MB ({r['pkl_to_int8_ratio']:6.0f}x)"
        )

    log.info("-" * 80)
    log.info(f"  Total (5 regions): {total_pkl:.3f}MB → {total_int8:.3f}MB "
             f"({total_pkl / total_int8 if total_int8 else 0:.0f}x)")

    # 전국 모델 포함
    nationwide_int8 = 42.7  # Current stacking ONNX quantized
    total_with_nationwide = nationwide_int8 + total_int8

    log.info(f"\n🎯 Full deployment (nationwide + 5 regional, INT8):")
    log.info(f"  Nationwide: {nationwide_int8:.1f}MB")
    log.info(f"  Regional: {total_int8:.3f}MB")
    log.info(f"  Total: {total_with_nationwide:.1f}MB")
    log.info(f"  vs current (212.0MB): {212.0 / total_with_nationwide:.2f}x reduction")

    # 리포트
    report = {
        'timestamp': datetime.now().isoformat(),
        'objective': 'Convert lightweight regional models to ONNX + INT8',
        'regional_models': valid,
        'summary': {
            'total_pkl_mb': round(total_pkl, 3),
            'total_int8_mb': round(total_int8, 3),
            'pkl_to_int8_ratio': round(total_pkl / total_int8, 1) if total_int8 else 0,
        },
        'full_deployment': {
            'nationwide_onnx_int8_mb': nationwide_int8,
            'regional_int8_mb': round(total_int8, 3),
            'total_mb': round(total_with_nationwide, 1),
            'vs_current_212mb': round(212.0 / total_with_nationwide, 2),
        },
    }

    report_path = output_dir / 'regional_onnx_report.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    log.info(f"\n✅ Report saved: {report_path}")
    log.info("=" * 80)


if __name__ == '__main__':
    main()
