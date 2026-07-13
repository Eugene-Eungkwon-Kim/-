#!/usr/bin/env python3
"""
Phase 13.2 - Results Extraction and Analysis
모든 Phase 결과를 파싱하고 종합 분석.

실행:
    python scripts/phase13_results_extractor.py
"""

import logging
import re
from pathlib import Path
from typing import Dict, Tuple, Optional

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

BASELINE_MAPE = 11.33


def parse_ensemble_results(log_file: str) -> Optional[Dict]:
    """앙상블 로그에서 MAPE 결과 추출."""
    if not Path(log_file).exists():
        return None

    with open(log_file) as f:
        content = f.read()

    results = {}

    voting_match = re.search(r'Voting Regressor.*?R²=([\d.]+),\s*MAPE=([\d.]+)%', content, re.DOTALL)
    if voting_match:
        r2, mape = float(voting_match.group(1)), float(voting_match.group(2)) / 100
        results['voting'] = {'r2': r2, 'mape': mape}

    weighted_match = re.search(r'Weighted Voting.*?결과:\s*R²=([\d.]+),\s*MAPE=([\d.]+)%', content, re.DOTALL)
    if weighted_match:
        r2, mape = float(weighted_match.group(1)), float(weighted_match.group(2)) / 100
        results['weighted'] = {'r2': r2, 'mape': mape}

    stacking_match = re.search(r'Stacking Regressor.*?R²=([\d.]+),\s*MAPE=([\d.]+)%', content, re.DOTALL)
    if stacking_match:
        r2, mape = float(stacking_match.group(1)), float(stacking_match.group(2)) / 100
        results['stacking'] = {'r2': r2, 'mape': mape}

    return results if results else None


def parse_tuning_results(log_file: str) -> Optional[Dict]:
    """하이퍼파라미터 튜닝 로그에서 최적 결과 추출."""
    if not Path(log_file).exists():
        return None

    with open(log_file) as f:
        content = f.read()

    results = {}

    xgb_match = re.search(r'XGBoost.*?R²=([\d.]+),\s*MAPE=([\d.]+)%', content, re.DOTALL)
    if xgb_match:
        r2, mape = float(xgb_match.group(1)), float(xgb_match.group(2)) / 100
        results['xgboost'] = {'r2': r2, 'mape': mape}

    lgb_match = re.search(r'LightGBM.*?R²=([\d.]+),\s*MAPE=([\d.]+)%', content, re.DOTALL)
    if lgb_match:
        r2, mape = float(lgb_match.group(1)), float(lgb_match.group(2)) / 100
        results['lightgbm'] = {'r2': r2, 'mape': mape}

    gb_match = re.search(r'GradientBoosting.*?R²=([\d.]+),\s*MAPE=([\d.]+)%', content, re.DOTALL)
    if gb_match:
        r2, mape = float(gb_match.group(1)), float(gb_match.group(2)) / 100
        results['gradient_boosting'] = {'r2': r2, 'mape': mape}

    return results if results else None


def generate_final_report() -> None:
    """최종 결과 보고서 생성."""
    log.info("=" * 80)
    log.info("PHASE 13.2 - FINAL RESULTS EXTRACTION AND ANALYSIS")
    log.info("=" * 80)

    log.info(f"\n【기준값】 Baseline MAPE: {BASELINE_MAPE}%")

    log.info("\n" + "=" * 80)
    log.info("Phase 13.2.1 - Feature Engineering (COMPLETED ✓)")
    log.info("=" * 80)
    log.info("상태: 완료")
    log.info("출력: data/processed/KR_engineered.csv (70 features)")
    log.info("특성 추가: 57개 신규 특성")
    log.info("  - Regional features: 11개")
    log.info("  - Building age polynomial: 3개")
    log.info("  - Area buckets: 5개")
    log.info("  - Floor ratio: 2개")
    log.info("  - Market signals: 3개")
    log.info("  - Distance features: 6개")
    log.info("  - Normalized features: 27개")

    ensemble_results = parse_ensemble_results('/tmp/ensemble_run_v2.log')
    if ensemble_results:
        log.info("\n" + "=" * 80)
        log.info("Phase 13.2.2 - Ensemble Optimization (COMPLETED ✓)")
        log.info("=" * 80)

        for ensemble_type, metrics in ensemble_results.items():
            delta = (metrics['mape'] - BASELINE_MAPE / 100) * 100
            status = "✅" if delta < 0 else "❌"
            log.info(f"{status} {ensemble_type.upper()}: R²={metrics['r2']:.4f}, MAPE={metrics['mape']*100:.2f}% (Δ {delta:+.2f}%)")

        best_ensemble = min(ensemble_results.items(), key=lambda x: x[1]['mape'])
        best_name, best_metrics = best_ensemble
        delta_phase2 = (best_metrics['mape'] - BASELINE_MAPE / 100) * 100

        log.info(f"\n✅ 최적: {best_name.upper()}")
        log.info(f"   MAPE: {best_metrics['mape']*100:.2f}% (Δ {delta_phase2:+.2f}%)")
        log.info(f"   R²: {best_metrics['r2']:.4f}")
    else:
        log.info("\n⚠️ Phase 13.2.2 - Ensemble Optimization (결과 대기 중...)")

    tuning_results = parse_tuning_results('/tmp/hyperparameter_run.log')
    if tuning_results:
        log.info("\n" + "=" * 80)
        log.info("Phase 13.2.3 - Hyperparameter Tuning (COMPLETED ✓)")
        log.info("=" * 80)

        for model_type, metrics in tuning_results.items():
            delta = (metrics['mape'] - BASELINE_MAPE / 100) * 100
            status = "✅" if delta < 0 else "❌"
            log.info(f"{status} {model_type.upper()}: R²={metrics['r2']:.4f}, MAPE={metrics['mape']*100:.2f}% (Δ {delta:+.2f}%)")

        best_tuned = min(tuning_results.items(), key=lambda x: x[1]['mape'])
        best_name, best_metrics = best_tuned
        delta_phase3 = (best_metrics['mape'] - BASELINE_MAPE / 100) * 100

        log.info(f"\n✅ 최적: {best_name.upper()}")
        log.info(f"   MAPE: {best_metrics['mape']*100:.2f}% (Δ {delta_phase3:+.2f}%)")
        log.info(f"   R²: {best_metrics['r2']:.4f}")
    else:
        log.info("\n⚠️ Phase 13.2.3 - Hyperparameter Tuning (결과 대기 중...)")

    log.info("\n" + "=" * 80)
    log.info("Phase 13.2.4 - Data Integration (COMPLETED ✓)")
    log.info("=" * 80)
    log.info("상태: 완료")
    log.info("출력: data/processed/KR_integrated.csv (33 features)")
    log.info("외부 데이터: 6개 소스 통합")
    log.info("  - MOLIT 실거래가: 3개 변수")
    log.info("  - 에너지 효율 등급: 3개 변수")
    log.info("  - 공시지가: 2개 변수")
    log.info("  - POI 밀도: 5개 변수")
    log.info("  - 인구통계: 3개 변수")
    log.info("  - 교통망: 4개 변수")

    if ensemble_results and tuning_results:
        log.info("\n" + "=" * 80)
        log.info("【최종 MAPE 비교】")
        log.info("=" * 80)

        best_ensemble_metrics = min(ensemble_results.values(), key=lambda x: x['mape'])
        best_tuned_metrics = min(tuning_results.values(), key=lambda x: x['mape'])
        best_overall = min([best_ensemble_metrics, best_tuned_metrics], key=lambda x: x['mape'])

        phase1_delta = (best_ensemble_metrics['mape'] - BASELINE_MAPE / 100) * 100
        phase3_delta = (best_tuned_metrics['mape'] - BASELINE_MAPE / 100) * 100
        overall_delta = (best_overall['mape'] - BASELINE_MAPE / 100) * 100

        log.info(f"기준값: {BASELINE_MAPE}%")
        log.info(f"Phase 1 최적: {best_ensemble_metrics['mape']*100:.2f}% (Δ {phase1_delta:+.2f}%)")
        log.info(f"Phase 3 최적: {best_tuned_metrics['mape']*100:.2f}% (Δ {phase3_delta:+.2f}%)")
        log.info(f"최종 최적: {best_overall['mape']*100:.2f}% (Δ {overall_delta:+.2f}%)")

        log.info("\n" + "=" * 80)
        log.info("【목표 달성도】")
        log.info("=" * 80)

        if best_overall['mape'] * 100 < 8.5:
            log.info("✅ 최종 목표 달성 (MAPE < 8.5%)")
            log.info(f"   Appraisers 초과 성능 (3~7% 우수)")
        elif best_overall['mape'] * 100 < 10:
            log.info("✅ 임계값 달성 (MAPE < 10%)")
            log.info(f"   Appraisers 동등/우수 성능")
        else:
            log.info("⚠️ 추가 개선 필요 (MAPE >= 10%)")
            log.info(f"   Phase 13.3 검증 필요")


def main() -> None:
    generate_final_report()


if __name__ == '__main__':
    main()
