"""WP 8: 피처 중요도 분석 — 모델이 무엇을 보고 예측하는가.

각 모델의 feature_importances_를 추출하고, 가능하면 순열 중요도
(permutation importance)로 교차검증한다. 순열 중요도는 모델 내장
중요도보다 신뢰도가 높다(상관 피처 편향이 적음).

실행:
    python scripts/analyze_feature_importance.py --data data/raw/KR_data.csv
"""

import argparse
import json
import logging
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import r2_score

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.avm_feature_engineering import FEATURE_MAX, FEATURE_MIN  # noqa: E402

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']
TARGET_COL = 'new_price'


def _normalize(X: np.ndarray) -> np.ndarray:
    return np.clip((X - FEATURE_MIN) / (FEATURE_MAX - FEATURE_MIN), 0.0, 1.0).astype(np.float32)


def native_importance(model: object) -> Dict[str, float]:
    """모델 내장 feature_importances_ 추출 (정규화하여 합=1)."""
    if not hasattr(model, 'feature_importances_'):
        return {}
    imp = np.asarray(model.feature_importances_, dtype=np.float64)
    total = imp.sum()
    imp = imp / total if total > 0 else imp
    return {col: round(float(v), 4) for col, v in zip(FEATURE_COLS, imp)}


def permutation_based(model: object, X: np.ndarray, y: np.ndarray,
                      rng_seed: int = 42) -> Dict[str, float]:
    """순열 중요도 — 피처를 섞었을 때 R² 하락폭."""
    result = permutation_importance(
        model, X, y, n_repeats=5, random_state=rng_seed, scoring='r2',
    )
    imp = np.clip(result.importances_mean, 0.0, None)
    total = imp.sum()
    imp = imp / total if total > 0 else imp
    return {col: round(float(v), 4) for col, v in zip(FEATURE_COLS, imp)}


def main() -> None:
    parser = argparse.ArgumentParser(description='피처 중요도 분석')
    parser.add_argument('--data',   default='data/raw/KR_data.csv')
    parser.add_argument('--models', default='output/trained_models')
    parser.add_argument('--output', default='output/feature_importance_report.json')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("피처 중요도 분석")
    log.info("=" * 60)

    df = pd.read_csv(args.data).dropna(subset=FEATURE_COLS + [TARGET_COL])
    X = _normalize(df[FEATURE_COLS].values.astype(np.float32))
    y = df[TARGET_COL].values.astype(np.float64)

    model_dir = Path(args.models)
    report: Dict[str, Dict] = {}

    for pkl in sorted(model_dir.glob('*_KR.pkl')):
        name = pkl.stem
        with open(pkl, 'rb') as f:
            model = pickle.load(f)
        log.info(f"\n▶ {name}")

        native = native_importance(model)
        perm = permutation_based(model, X, y)
        report[name] = {'native': native, 'permutation': perm}

        for col in FEATURE_COLS:
            log.info(f"  {col:>14}: native={native.get(col,0):.3f}  perm={perm.get(col,0):.3f}")

    # 모델 간 평균 순열 중요도로 종합 순위
    agg: Dict[str, List[float]] = {c: [] for c in FEATURE_COLS}
    for r in report.values():
        for c in FEATURE_COLS:
            agg[c].append(r['permutation'].get(c, 0.0))
    consensus = {c: round(float(np.mean(v)), 4) for c, v in agg.items()}
    ranked = sorted(consensus.items(), key=lambda kv: kv[1], reverse=True)

    log.info("\n[종합 순위 - 순열 중요도 평균]")
    for rank, (col, val) in enumerate(ranked, 1):
        log.info(f"  {rank}. {col}: {val:.3f}")

    out = {
        'timestamp': datetime.now().isoformat(),
        'note': '합성 데이터 기반. old_price가 압도적이면 데이터가 단순함을 시사.',
        'per_model': report,
        'consensus_permutation': consensus,
        'ranking': [c for c, _ in ranked],
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    log.info(f"\n✅ 리포트 저장: {args.output}")


if __name__ == '__main__':
    main()
