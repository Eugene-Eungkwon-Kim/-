#!/usr/bin/env python3
"""
Phase 13.2.5 - Stacking Ensemble Converter (pkl → ONNX)

StackingRegressor는 XGBoost/LightGBM 기반 추정기를 포함하므로
skl2onnx 기본 변환으로는 실패한다. onnxmltools의 XGBoost/LightGBM
컨버터를 skl2onnx 레지스트리에 등록한 뒤 전체 앙상블을 단일
ONNX 그래프로 변환한다.

실행:
    python scripts/phase13_stacking_converter.py \
      --model output/models/kr_production_v1.0_8p62_mape.pkl \
      --data data/processed/KR_engineered.csv \
      --output output/converted_models/kr_production_v1.0.onnx
"""

import argparse
import json
import logging
import pickle
import time
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

TARGET_COL = 'new_price'
LEAK_PATTERNS = ('new_price', 'price_change_ratio', 'price_gain_pct')
MATCH_RTOL = 1e-3  # ONNX는 float32 연산이므로 상대 오차 기준 사용


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
    log.info("✅ XGBoost/LightGBM 컨버터 등록 완료")


def load_features(data_path: str) -> Tuple[np.ndarray, list]:
    """학습과 동일한 전처리로 특성 행렬 재구성 (누수 컬럼 제거)."""
    df = pd.read_csv(data_path)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if not any(p in c for p in LEAK_PATTERNS)]
    X = df[numeric_cols].fillna(df[numeric_cols].mean()).fillna(0.0).to_numpy(dtype=np.float32)
    return np.ascontiguousarray(X), numeric_cols


def convert_to_onnx(model: object, n_features: int, output_path: Path) -> float:
    """StackingRegressor → 단일 ONNX 그래프 변환. 소요 시간(초) 반환."""
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


def validate_conversion(model: object, onnx_path: Path, X: np.ndarray) -> Dict:
    """pkl vs ONNX 예측값 비교 및 지연시간 측정."""
    import onnxruntime as rt

    sample = X[:500]
    y_pkl = model.predict(sample.astype(np.float64))

    sess = rt.InferenceSession(str(onnx_path), providers=['CPUExecutionProvider'])
    input_name = sess.get_inputs()[0].name
    y_onnx = sess.run(None, {input_name: sample})[0].ravel()

    rel_diff = np.abs(y_pkl - y_onnx) / np.abs(y_pkl)
    match_rate = float(np.mean(rel_diff < MATCH_RTOL))

    t0 = time.time()
    for row in sample[:100]:
        sess.run(None, {input_name: row.reshape(1, -1)})
    onnx_latency_ms = (time.time() - t0) / 100 * 1000

    return {
        'match_rate': match_rate,
        'max_rel_diff': float(rel_diff.max()),
        'mean_rel_diff': float(rel_diff.mean()),
        'onnx_single_latency_ms': round(onnx_latency_ms, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Phase 13.2.5 Stacking ONNX 변환')
    parser.add_argument('--model', default='output/models/kr_production_v1.0_8p62_mape.pkl')
    parser.add_argument('--data', default='data/processed/KR_engineered.csv')
    parser.add_argument('--output', default='output/converted_models/kr_production_v1.0.onnx')
    args = parser.parse_args()

    log.info("=" * 70)
    log.info("Phase 13.2.5 Stacking Ensemble ONNX 변환 시작")
    log.info("=" * 70)

    with open(args.model, 'rb') as f:
        model = pickle.load(f)
    pkl_mb = Path(args.model).stat().st_size / 1024 / 1024
    log.info(f"✅ 모델 로드: {args.model} ({pkl_mb:.1f}MB, {type(model).__name__})")

    X, feature_cols = load_features(args.data)
    log.info(f"✅ 특성 행렬: {X.shape[0]} rows × {X.shape[1]} features")

    register_gbm_converters()

    output_path = Path(args.output)
    elapsed = convert_to_onnx(model, X.shape[1], output_path)
    onnx_mb = output_path.stat().st_size / 1024 / 1024
    log.info(f"✅ ONNX 변환 완료: {output_path} ({onnx_mb:.1f}MB, {elapsed:.1f}초)")
    log.info(f"   크기 감소: {pkl_mb:.1f}MB → {onnx_mb:.1f}MB ({(1 - onnx_mb / pkl_mb) * 100:.0f}%)")

    validation = validate_conversion(model, output_path, X)
    log.info(f"\n검증 결과 (500 샘플, 상대오차 < {MATCH_RTOL}):")
    log.info(f"  Match Rate: {validation['match_rate'] * 100:.1f}%")
    log.info(f"  Max Rel Diff: {validation['max_rel_diff']:.2e}")
    log.info(f"  ONNX 단건 지연: {validation['onnx_single_latency_ms']}ms")

    report = {
        'model': str(args.model),
        'onnx': str(output_path),
        'pkl_size_mb': round(pkl_mb, 1),
        'onnx_size_mb': round(onnx_mb, 1),
        'n_features': X.shape[1],
        'feature_columns': feature_cols,
        'conversion_sec': round(elapsed, 1),
        'validation': validation,
        'status': 'PASS' if validation['match_rate'] >= 0.99 else 'FAIL',
    }
    report_path = output_path.parent / 'conversion_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log.info(f"\n✅ 변환 리포트: {report_path}")
    log.info(f"최종 상태: {report['status']}")


if __name__ == '__main__':
    main()
