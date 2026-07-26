#!/usr/bin/env python3
"""
Phase 14.KR - Threshold Checker
모델 성능 임계값 검증 및 배포 승인 결정

실행:
    python scripts/phase14_kr_threshold_checker.py --models-dir output/models/korea --mape-target 0.11 --strict-mode false
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


def load_model_metadata(models_dir: Path) -> Dict[str, Dict]:
    """메타데이터 로드"""
    metadata = {}

    for metadata_file in models_dir.glob('*_metadata.json'):
        with open(metadata_file) as f:
            data = json.load(f)
            model_id = data['model_id']
            metadata[model_id] = {
                'mape': data['performance']['test_mape'],
                'r2': data['performance']['test_r2'],
                'n_samples': data['n_samples'],
                'scope': data['scope'],
                'region': data.get('region', 'nationwide'),
            }

    return metadata


def check_thresholds(
    metadata: Dict[str, Dict],
    mape_target: float = 0.11,
    r2_minimum: float = 0.50,
    strict_mode: bool = False
) -> Tuple[Dict, bool]:
    """임계값 검증"""
    results = {
        'timestamp': datetime.now().isoformat(),
        'passed': [],
        'warned': [],
        'failed': [],
        'summary': {},
    }

    for model_id, metrics in metadata.items():
        mape = metrics['mape']
        r2 = metrics['r2']

        passed = mape <= mape_target and r2 >= r2_minimum
        mape_warning = mape <= (mape_target * 1.3)  # 30% threshold buffer
        r2_warning = r2 >= (r2_minimum * 0.9)  # 10% threshold buffer

        if passed:
            results['passed'].append({
                'model_id': model_id,
                'mape': mape,
                'r2': r2,
                'status': '✅ PASS',
            })
        elif strict_mode and (mape > mape_target or r2 < r2_minimum):
            results['failed'].append({
                'model_id': model_id,
                'mape': mape,
                'r2': r2,
                'status': '❌ FAIL',
                'issues': [
                    f"MAPE {mape*100:.2f}% > target {mape_target*100:.0f}%" if mape > mape_target else None,
                    f"R² {r2:.4f} < minimum {r2_minimum:.2f}" if r2 < r2_minimum else None,
                ]
            })
        else:
            results['warned'].append({
                'model_id': model_id,
                'mape': mape,
                'r2': r2,
                'status': '⚠️ REVIEW',
                'notes': [
                    f"MAPE {mape*100:.2f}% approaching target {mape_target*100:.0f}%" if mape_warning else None,
                    f"R² {r2:.4f} above minimum {r2_minimum:.2f}" if r2_warning else None,
                ]
            })

    # Calculate summary
    results['summary'] = {
        'total_models': len(metadata),
        'passed': len(results['passed']),
        'warned': len(results['warned']),
        'failed': len(results['failed']),
        'pass_rate': len(results['passed']) / len(metadata) if metadata else 0,
        'avg_mape': sum(m['mape'] for m in metadata.values()) / len(metadata) if metadata else 0,
        'avg_r2': sum(m['r2'] for m in metadata.values()) / len(metadata) if metadata else 0,
        'mape_target': mape_target,
        'r2_minimum': r2_minimum,
        'deployment_approved': len(results['failed']) == 0,
    }

    all_passed = len(results['failed']) == 0
    return results, all_passed


def generate_threshold_report(results: Dict, output_path: Path) -> bool:
    """임계값 리포트 생성"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    return True


def print_threshold_report(results: Dict) -> None:
    """콘솔 임계값 리포트 출력"""
    summary = results['summary']

    log.info("\n" + "=" * 70)
    log.info("Threshold Check Report")
    log.info("=" * 70)

    log.info(f"\n📊 Summary:")
    log.info(f"  Total Models: {summary['total_models']}")
    log.info(f"  Passed: {summary['passed']} ✅")
    log.info(f"  Warned: {summary['warned']} ⚠️")
    log.info(f"  Failed: {summary['failed']} ❌")
    log.info(f"  Pass Rate: {summary['pass_rate']*100:.1f}%")

    log.info(f"\n📈 Performance Metrics:")
    log.info(f"  Avg MAPE: {summary['avg_mape']*100:.2f}% (target: {summary['mape_target']*100:.0f}%)")
    log.info(f"  Avg R²: {summary['avg_r2']:.4f} (minimum: {summary['r2_minimum']:.2f})")

    if results['passed']:
        log.info(f"\n✅ PASSED ({len(results['passed'])} models):")
        for item in results['passed']:
            log.info(f"  {item['model_id']}: MAPE {item['mape']*100:.2f}%, R² {item['r2']:.4f}")

    if results['warned']:
        log.info(f"\n⚠️ WARNED ({len(results['warned'])} models):")
        for item in results['warned']:
            log.info(f"  {item['model_id']}: MAPE {item['mape']*100:.2f}%, R² {item['r2']:.4f}")
            if item.get('notes'):
                for note in item['notes']:
                    if note:
                        log.info(f"    - {note}")

    if results['failed']:
        log.info(f"\n❌ FAILED ({len(results['failed'])} models):")
        for item in results['failed']:
            log.info(f"  {item['model_id']}: MAPE {item['mape']*100:.2f}%, R² {item['r2']:.4f}")
            if item.get('issues'):
                for issue in item['issues']:
                    if issue:
                        log.info(f"    - {issue}")

    deployment_status = '✅ APPROVED' if summary['deployment_approved'] else '❌ BLOCKED'
    log.info(f"\n🎯 Deployment Status: {deployment_status}")

    log.info("\n" + "=" * 70)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description='Phase 14.KR Threshold Checker')
    parser.add_argument('--models-dir', required=True, help='Directory with trained models')
    parser.add_argument('--mape-target', type=float, default=0.11, help='Target MAPE (default: 0.11)')
    parser.add_argument('--r2-minimum', type=float, default=0.50, help='Minimum R² (default: 0.50)')
    parser.add_argument('--strict-mode', type=lambda x: x.lower() == 'true', default=False, help='Strict mode (fail if below threshold)')
    parser.add_argument('--output', default='reports/korea/threshold_check.json')
    args = parser.parse_args()

    models_dir = Path(args.models_dir)
    if not models_dir.exists():
        log.error(f"Models directory not found: {models_dir}")
        return

    log.info("🎯 Checking model performance thresholds...")
    metadata = load_model_metadata(models_dir)

    results, all_passed = check_thresholds(
        metadata,
        mape_target=args.mape_target,
        r2_minimum=args.r2_minimum,
        strict_mode=args.strict_mode
    )

    print_threshold_report(results)

    output_path = Path(args.output)
    success = generate_threshold_report(results, output_path)

    if success:
        log.info(f"✅ Report saved: {output_path}")

    # Exit with appropriate code
    if all_passed:
        log.info("\n✅ All models passed threshold checks!")
        exit(0)
    else:
        log.warning("\n⚠️ Some models failed threshold checks")
        exit(1 if args.strict_mode else 0)


if __name__ == '__main__':
    main()
