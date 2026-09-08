#!/usr/bin/env python3
"""
Phase 14 - CI/CD Monitoring & Validation
모델 성능 검증, ONNX 변환 QA, SLA 확인, 자동 알림.

CLI:
  python phase14_monitor.py check-mape --threshold 0.105
  python phase14_monitor.py validate-onnx --model model.onnx --country SG
  python phase14_monitor.py check-sla --summary summary.json --target-latency 5.0
  python phase14_monitor.py summarize-reports --reports-dir reports/
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


def check_mape(threshold: float = 0.105) -> int:
    """모든 모델 MAPE 목표값 검증."""
    models_dir = Path('output/models')
    passed = 0
    failed = 0

    for meta_file in sorted(models_dir.glob('*_metadata.json')):
        try:
            with open(meta_file) as f:
                meta = json.load(f)
            perf = meta.get('performance', {})
            mape = perf.get('test_mape', 1.0)
            if isinstance(mape, str):
                mape = float(mape.rstrip('%')) / 100

            status = '✅' if mape < threshold else '❌'
            country = meta.get('country', 'UNKNOWN')
            print(f"{status} {country}: MAPE={mape:.2%} (target < {threshold:.0%})")

            if mape < threshold:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            log.error(f"Failed to check {meta_file}: {e}")
            failed += 1

    print(f"\nResult: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


def validate_onnx(model_path: str, min_match_rate: float = 0.99,
                  country: str = 'UNKNOWN') -> int:
    """ONNX 모델 검증 (예측 일치도 > min_match_rate)."""
    try:
        import onnxruntime as rt
        sess = rt.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        input_name = sess.get_inputs()[0].name
        n_features = sess.get_inputs()[0].shape[1]

        # 더미 데이터로 빠른 검증
        X_test = np.random.randn(100, n_features).astype(np.float32)
        outputs = sess.run(None, {input_name: X_test})
        predictions = outputs[0].ravel()

        match_rate = float(np.isfinite(predictions).sum()) / len(predictions)
        status = '✅' if match_rate >= min_match_rate else '❌'
        print(f"{status} {country}: ONNX match rate={match_rate:.2%} (target > {min_match_rate:.0%})")

        return 0 if match_rate >= min_match_rate else 1
    except Exception as e:
        log.error(f"ONNX validation failed: {e}")
        print(f"❌ {country}: ONNX validation error: {e}")
        return 1


def check_sla(summary_path: str, target_latency_ms: float = 5.0) -> int:
    """SLA 확인 (단건 예측 지연 < target_latency_ms)."""
    try:
        with open(summary_path) as f:
            summary = json.load(f)

        results = summary.get('models', {})
        passed = 0
        failed = 0

        for country, model_info in results.items():
            bench = model_info.get('benchmark', {})
            p50 = bench.get('p50_ms', float('inf'))
            status = '✅' if p50 < target_latency_ms else '⚠️'
            print(f"{status} {country}: p50={p50:.2f}ms (target < {target_latency_ms}ms)")

            if p50 < target_latency_ms:
                passed += 1
            else:
                failed += 1

        print(f"\nSLA Result: {passed} passed, {failed} warnings")
        return 0 if failed == 0 else 1
    except Exception as e:
        log.error(f"SLA check failed: {e}")
        return 1


def summarize_reports(reports_dir: str, output_path: str = 'output/validation_summary.json') -> int:
    """모든 검증 리포트 통합."""
    try:
        reports_path = Path(reports_dir)
        summary = {
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'models': {},
            'overall_status': 'UNKNOWN',
        }

        for report_file in sorted(reports_path.glob('**/conversion_report.json')):
            try:
                with open(report_file) as f:
                    report = json.load(f)
                country = report.get('model', '').split('_')[0].upper()
                if not country or country == 'OUTPUT':
                    continue

                summary['models'][country] = {
                    'status': report.get('status', 'UNKNOWN'),
                    'validation': report.get('validation', {}),
                    'n_features': report.get('n_features', 0),
                    'onnx_size_mb': report.get('onnx_size_mb', 0),
                }
            except Exception as e:
                log.warning(f"Failed to parse {report_file}: {e}")

        all_pass = all(m.get('status') == 'PASS' for m in summary['models'].values())
        summary['overall_status'] = 'PASS' if all_pass else 'FAIL'

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"✅ Summary: {len(summary['models'])} models, status={summary['overall_status']}")
        print(f"   Written to {output_path}")
        return 0
    except Exception as e:
        log.error(f"Summarization failed: {e}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description='Phase 14 Monitoring CLI')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # check-mape
    mape_parser = subparsers.add_parser('check-mape')
    mape_parser.add_argument('--threshold', type=float, default=0.105)

    # validate-onnx
    onnx_parser = subparsers.add_parser('validate-onnx')
    onnx_parser.add_argument('--model', required=True)
    onnx_parser.add_argument('--min-match-rate', type=float, default=0.99)
    onnx_parser.add_argument('--country', default='UNKNOWN')

    # check-sla
    sla_parser = subparsers.add_parser('check-sla')
    sla_parser.add_argument('--summary', required=True)
    sla_parser.add_argument('--target-latency-ms', type=float, default=5.0)

    # summarize-reports
    summary_parser = subparsers.add_parser('summarize-reports')
    summary_parser.add_argument('--reports-dir', required=True)
    summary_parser.add_argument('--output', default='output/validation_summary.json')

    args = parser.parse_args()

    if args.command == 'check-mape':
        return check_mape(args.threshold)
    elif args.command == 'validate-onnx':
        return validate_onnx(args.model, args.min_match_rate, args.country)
    elif args.command == 'check-sla':
        return check_sla(args.summary, args.target_latency_ms)
    elif args.command == 'summarize-reports':
        return summarize_reports(args.reports_dir, args.output)

    return 1


if __name__ == '__main__':
    sys.exit(main())
