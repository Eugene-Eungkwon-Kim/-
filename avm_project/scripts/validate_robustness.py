"""WP 7: 강건성 검증 — 합성 데이터 순환성(circularity) 진단.

R²=0.98은 합성 데이터를 자기 공식으로 만들고 다시 학습한 결과이므로
일반화 성능을 보장하지 않는다. 이 스크립트는 그 한계를 정량적으로 드러낸다:

  1. 노이즈 강건성: 입력에 노이즈 주입 시 성능 저하 측정
  2. 베이스라인 대비: 단순 선형회귀 대비 앙상블의 실질 우위
  3. 분포 외(OOD) 입력: 학습 범위를 벗어난 입력에서의 거동

실행:
    python scripts/validate_robustness.py --data data/raw/KR_data.csv
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_percentage_error, r2_score

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.avm_feature_engineering import FEATURE_MAX, FEATURE_MIN  # noqa: E402

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']
TARGET_COL = 'new_price'
NOISE_LEVELS = [0.0, 0.05, 0.10, 0.20, 0.30]


def _normalize(X: np.ndarray) -> np.ndarray:
    return np.clip((X - FEATURE_MIN) / (FEATURE_MAX - FEATURE_MIN), 0.0, 1.0).astype(np.float32)


def load_models(model_dir: Path) -> Dict[str, object]:
    """학습된 pkl 모델 로드."""
    import pickle
    models: Dict[str, object] = {}
    for pkl in sorted(model_dir.glob('*_KR.pkl')):
        with open(pkl, 'rb') as f:
            models[pkl.stem] = pickle.load(f)
    return models


def _ensemble_predict(models: Dict[str, object], X: np.ndarray) -> np.ndarray:
    """학습 가중치(XGB.80/LGB.15/GB.05)로 앙상블 예측."""
    weights = {'xgboost': 0.80, 'lightgbm': 0.15, 'gradient_boosting': 0.05}
    total, acc = 0.0, np.zeros(len(X), dtype=np.float64)
    for name, model in models.items():
        w = next((v for k, v in weights.items() if k in name.lower()), 0.0)
        if w == 0.0:
            continue
        acc += w * model.predict(X)
        total += w
    return acc / total if total > 0 else acc


def test_noise_robustness(
    models: Dict[str, object],
    X: np.ndarray,
    y: np.ndarray,
    rng: np.random.Generator,
) -> List[Dict]:
    """입력 노이즈 수준별 성능 저하 측정."""
    results: List[Dict] = []
    for level in NOISE_LEVELS:
        noise = rng.normal(1.0, level, size=X.shape).astype(np.float32) if level > 0 else 1.0
        X_noisy = _normalize(X * noise)
        y_pred = _ensemble_predict(models, X_noisy)
        results.append({
            'noise_level': level,
            'r2': round(float(r2_score(y, y_pred)), 4),
            'mape': round(float(mean_absolute_percentage_error(y, y_pred)), 4),
        })
        log.info(f"  노이즈 {level*100:>4.0f}%: R²={results[-1]['r2']:.4f} MAPE={results[-1]['mape']*100:.1f}%")
    return results


def test_linear_baseline(X_norm: np.ndarray, y: np.ndarray) -> Dict:
    """단순 선형회귀 베이스라인 — 앙상블이 이걸 얼마나 능가하는가."""
    cut = int(len(X_norm) * 0.8)
    lr = LinearRegression()
    lr.fit(X_norm[:cut], y[:cut])
    y_pred = lr.predict(X_norm[cut:])
    return {
        'r2': round(float(r2_score(y[cut:], y_pred)), 4),
        'mape': round(float(mean_absolute_percentage_error(y[cut:], y_pred)), 4),
    }


def test_ood_inputs(models: Dict[str, object]) -> List[Dict]:
    """분포 외(OOD) 입력에서의 거동 — 학습 경계를 벗어난 값."""
    cases = [
        ('극소형 5㎡',     [5, 100_000_000, 37.5, 127.0, 1]),
        ('초대형 800㎡',   [800, 3_000_000_000, 37.5, 127.0, 1]),
        ('해외 좌표',      [84, 500_000_000, 45.0, 140.0, 1]),
        ('초고가 100억',   [84, 10_000_000_000, 37.5, 127.0, 1]),
        ('0원 입력',       [84, 0, 37.5, 127.0, 1]),
    ]
    out: List[Dict] = []
    for name, feat in cases:
        X = _normalize(np.array([feat], dtype=np.float32))
        pred = float(_ensemble_predict(models, X)[0])
        out.append({'case': name, 'prediction_억': round(pred / 1e8, 2), 'is_finite': bool(np.isfinite(pred))})
        log.info(f"  OOD [{name}]: {pred/1e8:.2f}억 (유한={np.isfinite(pred)})")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description='AVM 강건성 검증')
    parser.add_argument('--data',   default='data/raw/KR_data.csv')
    parser.add_argument('--models', default='output/trained_models')
    parser.add_argument('--output', default='output/robustness_report.json')
    parser.add_argument('--seed',   type=int, default=42)
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("강건성 검증 — 합성 데이터 순환성 진단")
    log.info("=" * 60)

    df = pd.read_csv(args.data).dropna(subset=FEATURE_COLS + [TARGET_COL])
    X = df[FEATURE_COLS].values.astype(np.float32)
    y = df[TARGET_COL].values.astype(np.float64)
    X_norm = _normalize(X)
    models = load_models(Path(args.models))
    rng = np.random.default_rng(args.seed)

    if not models:
        log.error("학습된 모델 없음 - train_kr_model.py 먼저 실행")
        sys.exit(1)

    log.info("\n[1] 노이즈 강건성")
    noise = test_noise_robustness(models, X, y, rng)

    log.info("\n[2] 선형 베이스라인 대비")
    baseline = test_linear_baseline(X_norm, y)
    ens_pred = _ensemble_predict(models, X_norm[int(len(X_norm)*0.8):])
    ens_r2 = float(r2_score(y[int(len(y)*0.8):], ens_pred))
    log.info(f"  선형회귀  R²={baseline['r2']:.4f}")
    log.info(f"  앙상블    R²={ens_r2:.4f}")
    log.info(f"  실질 우위: {(ens_r2 - baseline['r2'])*100:+.2f}p")

    log.info("\n[3] 분포 외(OOD) 입력")
    ood = test_ood_inputs(models)

    clean_r2 = noise[0]['r2']
    degraded_r2 = noise[-1]['r2']
    report = {
        'timestamp': datetime.now().isoformat(),
        'WARNING': '합성 데이터 기반 검증. 실거래 일반화 성능 아님.',
        'noise_robustness': noise,
        'linear_baseline': baseline,
        'ensemble_r2_holdout': round(ens_r2, 4),
        'ensemble_advantage_over_linear': round(ens_r2 - baseline['r2'], 4),
        'ood_behavior': ood,
        'interpretation': {
            'clean_r2': clean_r2,
            'r2_at_30pct_noise': degraded_r2,
            'degradation': round(clean_r2 - degraded_r2, 4),
            'verdict': '노이즈에 R²가 크게 무너지면 패턴이 표면적임을 시사',
        },
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log.info(f"\n✅ 리포트 저장: {args.output}")


if __name__ == '__main__':
    main()
