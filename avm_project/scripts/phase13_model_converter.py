#!/usr/bin/env python3
"""
Loan4U Phase 13.2.5 - KR Model Converter (pkl → ONNX → OpenVINO IR)

학습된 KR 모델(xgboost_KR, lightgbm_KR)을 NPU 추론용으로 변환한다.
변환 경로는 단계적 폴백을 가진다:
    pkl → ONNX → OpenVINO IR
각 단계 실패 시 직전 형식을 그대로 사용(AVM 엔진이 자동 폴백)하며,
실제로 변환에 성공한 산출물만 conversion_report.json 에 기록한다.

(이전 멀티-컨트리 경로와 가짜 4x 추정 코드는 제거됨 — KR 전용)
"""

import argparse
import json
import logging
import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']


def convert_xgboost_native(model: object, name: str, output_dir: Path) -> Optional[str]:
    """XGBoost 2.x 네이티브 ONNX 저장. 실패 시 onnxmltools 폴백."""
    onnx_path = output_dir / f"{name}.onnx"
    try:
        model.save_model(str(onnx_path))  # type: ignore[union-attr]
        if onnx_path.exists() and onnx_path.stat().st_size > 0:
            log.info(f"  [{name}] XGBoost 네이티브 ONNX: {onnx_path.stat().st_size/1024:.1f}KB")
            return str(onnx_path)
    except Exception as e:
        log.debug(f"  [{name}] 네이티브 ONNX 실패: {e}")

    try:
        import onnx
        import onnxmltools
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
    """LightGBM → ONNX (hummingbird-ml 우선, onnxmltools 폴백)."""
    onnx_path = output_dir / f"{name}.onnx"
    try:
        from hummingbird.ml import convert as hb_convert
        sample = np.zeros((1, len(FEATURE_COLS)), dtype=np.float32)
        hb_model = hb_convert(model, 'onnx', test_input=sample)
        hb_model.save(str(output_dir / name))
        for f in (output_dir / name).glob('*.onnx'):
            f.rename(onnx_path)
            break
        if onnx_path.exists():
            log.info(f"  [{name}] hummingbird ONNX: {onnx_path.stat().st_size/1024:.1f}KB")
            return str(onnx_path)
    except Exception as e:
        log.debug(f"  [{name}] hummingbird 실패: {e}")

    try:
        import onnx
        import onnxmltools
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
    """ONNX → OpenVINO IR (FP32). openvino 2024.x API. 미설치 시 None."""
    xml_path = output_dir / f"{name}.xml"
    try:
        import openvino as ov
        ov_model = ov.convert_model(onnx_path)
        ov.save_model(ov_model, str(xml_path))
        log.info(f"  [{name}] OpenVINO IR: {xml_path.stat().st_size/1024/1024:.2f}MB")
        return str(xml_path)
    except ImportError:
        log.warning(f"  [{name}] openvino 미설치 - IR 변환 건너뜀")
        return None
    except Exception as e:
        log.warning(f"  [{name}] OpenVINO IR 변환 실패: {e}")
        return None


def convert_kr_models(pkl_dir: Path, output_dir: Path) -> Dict[str, Dict]:
    """KR 모델(xgboost_KR, lightgbm_KR) → ONNX + IR 변환."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Dict] = {}

    converters = {
        'xgboost_KR':  convert_xgboost_native,
        'lightgbm_KR': convert_lightgbm_native,
    }

    for model_key, converter_fn in converters.items():
        pkl_path = pkl_dir / f"{model_key}.pkl"
        if not pkl_path.exists():
            log.warning(f"  {pkl_path} 없음 - 건너뜀")
            continue

        log.info(f"\n▶ {model_key}")
        t0 = time.time()
        pkl_mb = pkl_path.stat().st_size / 1024 / 1024

        with open(pkl_path, 'rb') as f:
            model = pickle.load(f)

        onnx_path = converter_fn(model, model_key, output_dir)
        onnx_mb = Path(onnx_path).stat().st_size / 1024 / 1024 if onnx_path else None
        ir_path = convert_to_openvino_ir(onnx_path, model_key, output_dir) if onnx_path else None
        ir_mb = Path(ir_path).stat().st_size / 1024 / 1024 if ir_path else None

        status = 'ir_ready' if ir_path else ('onnx_only' if onnx_path else 'pkl_only')
        report[model_key] = {
            'pkl_size_mb':  round(pkl_mb, 3),
            'onnx_size_mb': round(onnx_mb, 3) if onnx_mb else None,
            'ir_size_mb':   round(ir_mb, 3) if ir_mb else None,
            'status':       status,
            'elapsed_sec':  round(time.time() - t0, 2),
        }
        log.info(f"  상태: {status}")

    report_path = output_dir.parent / 'conversion_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({'timestamp': datetime.now().isoformat(), 'models': report}, f, indent=2)
    log.info(f"\n✅ 변환 리포트: {report_path}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description='Phase 13.2.5 KR Model Converter')
    parser.add_argument('--pkl-dir', default='output/trained_models', help='pkl 모델 디렉토리')
    parser.add_argument('--output',  default='output/models_ir',      help='출력 디렉토리')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("Phase 13.2.5 KR 모델 변환 시작")
    log.info("=" * 60)

    report = convert_kr_models(Path(args.pkl_dir), Path(args.output))
    success = sum(1 for v in report.values() if v['status'] != 'pkl_only')
    log.info(f"\n{success}/{len(report)} 모델 ONNX/IR 변환 완료")


if __name__ == '__main__':
    main()
