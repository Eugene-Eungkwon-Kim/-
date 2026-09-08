#!/usr/bin/env python3
"""
Phase 13.2 - Complete KPI Improvement Pipeline
모든 개선 방법을 순서대로 실행하여 MAPE 11.33% → 5~8% 달성 목표.

실행:
    python scripts/phase13_kpi_improvement_all.py
"""

import logging
import subprocess
import sys
import time
from pathlib import Path

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


def run_phase(name: str, script: str, args: str = '') -> bool:
    """개별 Phase 실행."""
    log.info(f"\n{'='*70}")
    log.info(f"{'='*70}")
    log.info(f"  Phase: {name}")
    log.info(f"  Script: {script}")
    log.info(f"{'='*70}")

    t0 = time.time()
    cmd = f"python {script} {args}"

    try:
        result = subprocess.run(cmd, shell=True, cwd='/home/user/-', check=True)
        elapsed = time.time() - t0
        log.info(f"✅ {name} 완료 ({elapsed:.1f}초)")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"❌ {name} 실패: {e}")
        return False


def main() -> None:
    log.info("=" * 70)
    log.info("PHASE 13.2 전체 KPI 개선 파이프라인 시작")
    log.info("목표: MAPE 11.33% → <10% 달성 (1주일 내)")
    log.info("=" * 70)

    phases = [
        ("1. 특성 공학 (Feature Engineering)", "avm_project/scripts/phase13_feature_engineering.py",
         "--data data/raw/KR_data.csv --output data/processed/KR_engineered.csv"),

        ("2. 모델 앙상블 강화 (Ensemble Optimization)", "avm_project/scripts/phase13_ensemble_optimizer.py",
         "--data data/processed/KR_engineered.csv --output-dir output/ensemble_models"),

        ("3. 하이퍼파라미터 튜닝 (Hyperparameter Optimization)", "avm_project/scripts/phase13_hyperparameter_tuning.py",
         "--data data/processed/KR_engineered.csv --output-dir output/tuned_models"),

        ("4. 외부 데이터 통합 (Data Integration)", "avm_project/scripts/phase13_data_integration.py",
         "--data data/raw/KR_data.csv --output data/processed/KR_integrated.csv"),
    ]

    results = []
    t_start = time.time()

    for name, script, args in phases:
        success = run_phase(name, script, args)
        results.append((name, success))
        if not success:
            log.warning(f"⚠️ {name} 실패 - 다음 단계로 계속...")

    elapsed_total = time.time() - t_start

    log.info(f"\n{'='*70}")
    log.info("전체 파이프라인 완료 요약")
    log.info(f"{'='*70}")

    passed = sum(1 for _, success in results if success)
    for name, success in results:
        status = "✅ 완료" if success else "❌ 실패"
        log.info(f"  {status}: {name}")

    log.info(f"\n총 소요 시간: {elapsed_total/60:.1f}분")
    log.info(f"완료율: {passed}/{len(results)}")

    if passed == len(results):
        log.info("\n🎉 모든 Phase 완료!")
        log.info("다음 단계: 통합 모델 재학습 및 KPI 검증")
        return 0
    else:
        log.error(f"\n⚠️ {len(results)-passed}개 Phase 실패")
        return 1


if __name__ == '__main__':
    sys.exit(main())
