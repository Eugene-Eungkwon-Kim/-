"""
Phase 13.5 - 특성 드리프트 감지

두 데이터셋(기준 vs 현재) 간 특성 분포 변화를 Kolmogorov-Smirnov 검정으로
감지한다. 재학습 파이프라인이 매주 새 데이터를 수집할 때, 이전 기준
분포와 크게 달라진 특성이 있으면 경고해 모델 성능 저하를 조기에 포착한다.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List

import pandas as pd
from scipy.stats import ks_2samp

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

SIGNIFICANCE_LEVEL = 0.05


@dataclass
class DriftResult:
    """단일 특성의 드리프트 검정 결과."""
    feature: str
    p_value: float
    is_drifted: bool
    severity: str  # 'none' | 'medium' | 'high'


def _severity_for(p_value: float) -> str:
    """p-value 기준 심각도 분류."""
    if p_value >= SIGNIFICANCE_LEVEL:
        return 'none'
    return 'high' if p_value < 0.01 else 'medium'


def detect_drift(
    reference: pd.DataFrame, current: pd.DataFrame, features: List[str],
) -> Dict[str, DriftResult]:
    """특성별 KS 검정으로 분포 드리프트 감지."""
    results: Dict[str, DriftResult] = {}
    for feature in features:
        if feature not in reference.columns or feature not in current.columns:
            continue
        stat, p_value = ks_2samp(reference[feature].dropna(), current[feature].dropna())
        severity = _severity_for(p_value)
        results[feature] = DriftResult(
            feature=feature, p_value=float(p_value),
            is_drifted=severity != 'none', severity=severity,
        )
    return results


def summarize_drift(results: Dict[str, DriftResult]) -> Dict[str, object]:
    """드리프트 결과 요약 (알림용)."""
    drifted = [r for r in results.values() if r.is_drifted]
    return {
        'total_features': len(results),
        'drifted_features': [r.feature for r in drifted],
        'drifted_count': len(drifted),
        'has_high_severity': any(r.severity == 'high' for r in drifted),
    }
