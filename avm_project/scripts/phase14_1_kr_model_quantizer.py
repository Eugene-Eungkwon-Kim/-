#!/usr/bin/env python3
"""
Phase 14.1.KR - Korea Model INT8 Quantizer (pkl → ONNX → INT8)

한국 부동산 모델(StackingRegressor)을 ONNX로 내보낸 뒤 ONNX Runtime
동적 양자화로 INT8 변환한다. OpenVINO IR 경로는 NPU 전용이므로 별도
단계로 분리하고, 여기서는 설치 환경에서 실제 실행·검증 가능한 ONNX
Runtime 경로로 크기 축소와 정확도 보존을 달성한다.

실행:
    python scripts/phase14_1_kr_model_quantizer.py \
      --models-dir output/models/korea \
      --data data/raw/KR_raw.csv \
      --output-dir output/models/korea/quantized
"""

import argparse
import json
import logging
import pickle
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

TARGET_COL = 'price_local'
LEAK_PATTERNS = ('price_local', 'indexed_price')
MATCH_RTOL = 1e-3
INT8_MAPE_TOLERANCE = 0.02  # 양자화로 인한 허용 MAPE 증가폭 (<2%)

REGION_BY_MODEL = {
    'KR_nationwide_v1.0': None,
    'KR_seoul_v1.0': 'Seoul',
    'KR_busan_v1.0': 'Busan',
    'KR_gyeonggi_v1.0': 'Gyeonggi',
    'KR_daegu_v1.0': 'Daegu',
    'KR_incheon_v1.0': 'Incheon',
}


def register_gbm_converters() -> None:
    """XGBoost/LightGBM용 onnxmltools 컨버터를 skl2onnx에 등록."""
    from skl2onnx import update_registered_converter
    from skl2onnx.common.shape_calculator import calculate_linear_regressor_output_shapes
    from onnxmltools.convert.xgboost.operator_converters.XGBoost import convert_xgboost
    from onnxmltools.convert.lightgbm.operator_converters.LightGbm import convert_lightgbm
    import xgboost as xgb
    import lightgbm as lgb

    update_registered_converter(
        xgb.XGBRegressor, 'XGBoostXGBRegressor',
        calculate_linear_regressor_output_shapes, convert_xgboost,
    )
    update_registered_converter(
        lgb.LGBMRegressor, 'LightGbmLGBMRegressor',
        calculate_linear_regressor_output_shapes, convert_lightgbm,
        options={'split': None},
    )


def build_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """학습과 동일한 전처리로 특성 행렬·타깃 재구성."""
    y = df[TARGET_COL].to_numpy(dtype=np.float64)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [c for c in numeric_cols if not any(p in c for p in LEAK_PATTERNS)]
    X = df[feature_cols].fillna(0.0).to_numpy(dtype=np.float32)
    return np.ascontiguousarray(X), y, feature_cols


def slice_region(df: pd.DataFrame, region: Optional[str]) -> pd.DataFrame:
    """지역 모델은 해당 지역 행만 사용 (학습 시와 동일)."""
    if region is None:
        return df
    return df[df['region'] == region]


def export_onnx(model: object, n_features: int, output_path: Path) -> float:
    """StackingRegressor → 단일 ONNX 그래프. 소요 시간(초) 반환."""
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType

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
    """ONNX Runtime 동적 양자화로 INT8 변환. 소요 시간(초) 반환."""
    from onnxruntime.quantization import quantize_dynamic, QuantType

    t0 = time.time()
    quantize_dynamic(
        model_input=str(onnx_path),
        model_output=str(int8_path),
        weight_type=QuantType.QInt8,
    )
    return time.time() - t0


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs((y_true - y_pred) / y_true)))


def _predict_onnx(onnx_path: Path, X: np.ndarray) -> np.ndarray:
    import onnxruntime as rt

    sess = rt.InferenceSession(str(onnx_path), providers=['CPUExecutionProvider'])
    input_name = sess.get_inputs()[0].name
    return sess.run(None, {input_name: X})[0].ravel()


def _latency_ms(onnx_path: Path, X: np.ndarray, n: int = 100) -> float:
    import onnxruntime as rt

    sess = rt.InferenceSession(str(onnx_path), providers=['CPUExecutionProvider'])
    input_name = sess.get_inputs()[0].name
    sample = X[:n]
    t0 = time.time()
    for row in sample:
        sess.run(None, {input_name: row.reshape(1, -1)})
    return (time.time() - t0) / len(sample) * 1000


def validate(
    model: object,
    onnx_path: Path,
    int8_path: Path,
    X: np.ndarray,
    y: np.ndarray,
) -> Dict:
    """pkl / ONNX-fp32 / ONNX-int8 정확도·지연 비교."""
    sample = X[:500]
    y_sample = y[:500]

    y_pkl = model.predict(sample.astype(np.float64))
    y_fp32 = _predict_onnx(onnx_path, sample)
    y_int8 = _predict_onnx(int8_path, sample)

    mape_pkl = _mape(y_sample, y_pkl)
    mape_int8 = _mape(y_sample, y_int8)

    rel_diff = np.abs(y_pkl - y_int8) / np.abs(y_pkl)

    return {
        'mape_pkl': round(mape_pkl, 4),
        'mape_onnx_fp32': round(_mape(y_sample, y_fp32), 4),
        'mape_int8': round(mape_int8, 4),
        'mape_delta': round(mape_int8 - mape_pkl, 4),
        'int8_vs_pkl_max_rel_diff': round(float(rel_diff.max()), 4),
        'int8_vs_pkl_mean_rel_diff': round(float(rel_diff.mean()), 4),
        'latency_fp32_ms': round(_latency_ms(onnx_path, sample), 2),
        'latency_int8_ms': round(_latency_ms(int8_path, sample), 2),
    }


def quantize_model(
    model_id: str,
    models_dir: Path,
    output_dir: Path,
    df: pd.DataFrame,
) -> Optional[Dict]:
    """단일 모델 양자화 파이프라인 실행."""
    pkl_path = models_dir / f'{model_id}.pkl'
    if not pkl_path.exists():
        log.warning(f"⚠️  Skip {model_id}: pkl not found")
        return None

    with open(pkl_path, 'rb') as f:
        model = pickle.load(f)
    pkl_mb = pkl_path.stat().st_size / 1024 / 1024

    df_scope = slice_region(df, REGION_BY_MODEL[model_id])
    X, y, _ = build_features(df_scope)

    onnx_path = output_dir / f'{model_id}.onnx'
    int8_path = output_dir / f'{model_id}_int8.onnx'

    export_sec = export_onnx(model, X.shape[1], onnx_path)
    onnx_mb = onnx_path.stat().st_size / 1024 / 1024
    quant_sec = quantize_int8(onnx_path, int8_path)
    int8_mb = int8_path.stat().st_size / 1024 / 1024

    metrics = validate(model, onnx_path, int8_path, X, y)
    accuracy_ok = metrics['mape_delta'] <= INT8_MAPE_TOLERANCE

    # 트리 앙상블은 TreeEnsembleRegressor 연산자에 노드가 저장되어
    # quantize_dynamic이 손대지 않는다. INT8 이득이 사실상 없으면 표기.
    int8_ratio = onnx_mb / int8_mb if int8_mb else 1.0
    int8_effective = int8_ratio >= 1.05

    result = {
        'model_id': model_id,
        'region': REGION_BY_MODEL[model_id] or 'nationwide',
        'n_features': X.shape[1],
        'sizes_mb': {
            'pkl': round(pkl_mb, 2),
            'onnx_fp32': round(onnx_mb, 2),
            'onnx_int8': round(int8_mb, 2),
        },
        'onnx_conversion_ratio': round(pkl_mb / onnx_mb, 2),
        'int8_quant_ratio': round(int8_ratio, 3),
        'int8_effective': int8_effective,
        'total_size_reduction_pct': round((1 - int8_mb / pkl_mb) * 100, 1),
        'timing_sec': {'export': round(export_sec, 1), 'quantize': round(quant_sec, 1)},
        'validation': metrics,
        'status': 'PASS' if accuracy_ok else 'REVIEW',
    }

    quant_note = '' if int8_effective else ' (INT8 no-op: tree ensemble)'
    log.info(
        f"✅ {model_id}: pkl {pkl_mb:.1f}MB → onnx {onnx_mb:.1f}MB "
        f"({result['onnx_conversion_ratio']}x), int8 ×{int8_ratio:.2f}{quant_note}, "
        f"MAPE Δ {metrics['mape_delta']:+.4f} [{result['status']}]"
    )
    return result


def write_report(results: List[Dict], output_dir: Path) -> Path:
    """양자화 종합 리포트(JSON) 생성."""
    valid = [r for r in results if r]
    total_pkl = sum(r['sizes_mb']['pkl'] for r in valid)
    total_int8 = sum(r['sizes_mb']['onnx_int8'] for r in valid)
    summary = {
        'total_models': len(valid),
        'passed': sum(1 for r in valid if r['status'] == 'PASS'),
        'avg_onnx_conversion_ratio': round(
            sum(r['onnx_conversion_ratio'] for r in valid) / len(valid), 2
        ) if valid else 0,
        'int8_effective_count': sum(1 for r in valid if r['int8_effective']),
        'total_pkl_mb': round(total_pkl, 1),
        'total_int8_mb': round(total_int8, 1),
        'total_reduction_ratio': round(total_pkl / total_int8, 2) if total_int8 else 0,
        'note': ('INT8 dynamic quantization is a no-op on tree-ensemble models; '
                 'size reduction comes from pkl→ONNX serialization. To reach 4x, '
                 'reduce ensemble complexity (n_estimators/depth) or use a single GBM.'),
    }
    report = {'summary': summary, 'models': valid}
    report_path = output_dir / 'quantization_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report_path


def print_summary(results: List[Dict]) -> None:
    """콘솔 요약 출력."""
    valid = [r for r in results if r]
    total_pkl = sum(r['sizes_mb']['pkl'] for r in valid)
    total_int8 = sum(r['sizes_mb']['onnx_int8'] for r in valid)

    int8_ok = sum(1 for r in valid if r['int8_effective'])

    log.info("\n" + "=" * 70)
    log.info("Phase 14.1.KR INT8 Quantization Summary")
    log.info("=" * 70)
    log.info(f"  Models processed: {len(valid)}")
    log.info(f"  Total size: {total_pkl:.1f}MB → {total_int8:.1f}MB "
             f"({total_pkl / total_int8:.1f}x, from pkl→ONNX serialization)"
             if total_int8 else "")
    log.info(f"  INT8 quant effective on: {int8_ok}/{len(valid)} models "
             f"(tree ensembles unaffected by dynamic quant)")
    log.info(f"  Accuracy preserved (MAPE Δ ≤ {INT8_MAPE_TOLERANCE}): "
             f"{sum(1 for r in valid if r['status'] == 'PASS')}/{len(valid)}")
    log.info("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description='Phase 14.1.KR INT8 Quantizer')
    parser.add_argument('--models-dir', default='output/models/korea')
    parser.add_argument('--data', default='data/raw/KR_raw.csv')
    parser.add_argument('--output-dir', default='output/models/korea/quantized')
    args = parser.parse_args()

    models_dir = Path(args.models_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    log.info("🇰🇷 Phase 14.1.KR INT8 Quantization 시작")
    df = pd.read_csv(args.data)
    log.info(f"✅ 검증 데이터 로드: {len(df):,} rows")

    register_gbm_converters()

    results = [
        quantize_model(model_id, models_dir, output_dir, df)
        for model_id in REGION_BY_MODEL
    ]

    report_path = write_report(results, output_dir)
    print_summary(results)
    log.info(f"✅ 리포트 저장: {report_path}")


if __name__ == '__main__':
    main()
