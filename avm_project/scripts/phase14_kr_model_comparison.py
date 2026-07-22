#!/usr/bin/env python3
"""
Phase 14.KR - Model Comparison
현재 모델과 이전 모델 비교 분석

실행:
    python scripts/phase14_kr_model_comparison.py --current-models output/models/korea --output reports/korea/comparison.json
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
                'created_date': data['created_date'],
                'target_met': data.get('target_met', False),
            }

    return metadata


def compare_models(current: Dict, previous: Dict = None) -> Dict:
    """모델 비교: 성능 개선도 계산"""
    comparison = {
        'timestamp': datetime.now().isoformat(),
        'current_models': current,
        'improvements': {},
        'regressions': {},
        'new_models': {},
    }

    if not previous:
        log.info("No previous models for comparison (first run)")
        comparison['new_models'] = {k: v for k, v in current.items()}
        return comparison

    # Compare metrics
    for model_id, current_metrics in current.items():
        if model_id in previous:
            prev_metrics = previous[model_id]
            mape_change = (current_metrics['mape'] - prev_metrics['mape']) * 100
            r2_change = current_metrics['r2'] - prev_metrics['r2']

            if mape_change < 0:  # MAPE improvement (lower is better)
                comparison['improvements'][model_id] = {
                    'mape_improvement': abs(mape_change),
                    'r2_change': r2_change,
                    'previous_mape': prev_metrics['mape'],
                    'current_mape': current_metrics['mape'],
                }
            elif mape_change > 0:  # MAPE regression (higher is worse)
                comparison['regressions'][model_id] = {
                    'mape_regression': mape_change,
                    'r2_change': r2_change,
                    'previous_mape': prev_metrics['mape'],
                    'current_mape': current_metrics['mape'],
                }
        else:
            comparison['new_models'][model_id] = current_metrics

    return comparison


def generate_comparison_report(comparison: Dict, output_path: Path) -> bool:
    """비교 리포트 생성"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create summary statistics
    summary = {
        'total_models': len(comparison['current_models']),
        'improvements_count': len(comparison['improvements']),
        'regressions_count': len(comparison['regressions']),
        'new_models_count': len(comparison['new_models']),
        'avg_current_mape': sum(m['mape'] for m in comparison['current_models'].values()) / len(comparison['current_models']),
    }

    report = {
        'timestamp': comparison['timestamp'],
        'summary': summary,
        'comparison': comparison,
    }

    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    return True


def print_comparison_report(comparison: Dict) -> None:
    """콘솔 리포트 출력"""
    log.info("\n" + "=" * 70)
    log.info("Model Comparison Report")
    log.info("=" * 70)

    if comparison['improvements']:
        log.info(f"\n✅ IMPROVEMENTS ({len(comparison['improvements'])} models)")
        for model_id, metrics in comparison['improvements'].items():
            log.info(f"  {model_id}:")
            log.info(f"    MAPE: {metrics['previous_mape']*100:.2f}% → {metrics['current_mape']*100:.2f}% (↓ {metrics['mape_improvement']:.2f}pp)")
            log.info(f"    R²: {metrics['r2_change']:+.4f}")

    if comparison['regressions']:
        log.info(f"\n⚠️ REGRESSIONS ({len(comparison['regressions'])} models)")
        for model_id, metrics in comparison['regressions'].items():
            log.info(f"  {model_id}:")
            log.info(f"    MAPE: {metrics['previous_mape']*100:.2f}% → {metrics['current_mape']*100:.2f}% (↑ {metrics['mape_regression']:.2f}pp)")
            log.info(f"    R²: {metrics['r2_change']:+.4f}")

    if comparison['new_models']:
        log.info(f"\n🆕 NEW MODELS ({len(comparison['new_models'])} models)")
        for model_id, metrics in comparison['new_models'].items():
            log.info(f"  {model_id}: MAPE {metrics['mape']*100:.2f}%, R² {metrics['r2']:.4f}")

    log.info("\n" + "=" * 70)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description='Phase 14.KR Model Comparison')
    parser.add_argument('--current-models', required=True, help='Directory with current models')
    parser.add_argument('--previous-models', default=None, help='Directory with previous models (optional)')
    parser.add_argument('--output', default='reports/korea/model_comparison.json')
    args = parser.parse_args()

    current_dir = Path(args.current_models)
    if not current_dir.exists():
        log.error(f"Current models directory not found: {current_dir}")
        return

    log.info("📈 Loading current models...")
    current = load_model_metadata(current_dir)

    previous = None
    if args.previous_models:
        previous_dir = Path(args.previous_models)
        if previous_dir.exists():
            log.info("📈 Loading previous models...")
            previous = load_model_metadata(previous_dir)

    comparison = compare_models(current, previous)
    print_comparison_report(comparison)

    output_path = Path(args.output)
    success = generate_comparison_report(comparison, output_path)

    if success:
        log.info(f"✅ Comparison report saved: {output_path}")
    else:
        log.error("Comparison report generation failed")


if __name__ == '__main__':
    main()
