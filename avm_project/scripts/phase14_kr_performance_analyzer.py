#!/usr/bin/env python3
"""
Phase 14.KR - Korea Performance Analyzer
월간 모델 성능 분석 및 HTML 리포트 생성

실행:
    python scripts/phase14_kr_performance_analyzer.py --models-dir output/models/korea --output reports/korea/performance.html
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


def analyze_model_performance(models_dir: Path) -> Dict:
    """분석: 모든 모델의 성능 지표 수집"""
    performance = {}

    for metadata_file in models_dir.glob('*_metadata.json'):
        with open(metadata_file) as f:
            metadata = json.load(f)
            model_id = metadata['model_id']
            performance[model_id] = {
                'scope': metadata['scope'],
                'region': metadata.get('region', 'nationwide'),
                'n_samples': metadata['n_samples'],
                'n_features': metadata['n_features'],
                'mape': metadata['performance']['test_mape'],
                'r2': metadata['performance']['test_r2'],
                'training_sec': metadata['training_sec'],
                'model_size_mb': metadata['model_size_mb'],
                'target_met': metadata['target_met'],
                'created_date': metadata['created_date'],
            }

    return performance


def generate_html_report(performance: Dict, output_path: Path) -> bool:
    """생성: HTML 성능 리포트"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort by MAPE (best first)
    sorted_models = sorted(performance.items(), key=lambda x: x[1]['mape'])

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phase 14.KR Korea AVM Performance Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}

        header {{ background: linear-gradient(135deg, #c60c30 0%, #e63946 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; }}
        header h1 {{ font-size: 28px; margin-bottom: 5px; }}
        header p {{ opacity: 0.9; font-size: 14px; }}

        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .summary-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .summary-card h3 {{ font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 10px; }}
        .summary-card .value {{ font-size: 28px; font-weight: bold; color: #c60c30; }}

        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 30px; }}
        th {{ background: #c60c30; color: white; padding: 15px; text-align: left; font-weight: 600; }}
        td {{ padding: 15px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f9f9f9; }}
        tr:last-child td {{ border-bottom: none; }}

        .status-pass {{ color: #2e7d32; font-weight: 600; }}
        .status-review {{ color: #f57c00; font-weight: 600; }}
        .status-fail {{ color: #c62828; font-weight: 600; }}

        .chart {{ margin-bottom: 30px; }}
        .chart-container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .chart-title {{ font-size: 16px; font-weight: 600; margin-bottom: 15px; }}

        .footer {{ text-align: center; margin-top: 40px; padding: 20px; font-size: 12px; color: #999; border-top: 1px solid #eee; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🇰🇷 Korea AVM Performance Report</h1>
            <p>Phase 14.KR Monthly Model Retrain • Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <div class="summary">
            <div class="summary-card">
                <h3>Total Models</h3>
                <div class="value">{len(performance)}</div>
            </div>
            <div class="summary-card">
                <h3>Avg MAPE</h3>
                <div class="value">{sum(m['mape'] for m in performance.values()) / len(performance) * 100:.1f}%</div>
            </div>
            <div class="summary-card">
                <h3>Target Met</h3>
                <div class="value">{sum(1 for m in performance.values() if m['target_met'])}/{len(performance)}</div>
            </div>
            <div class="summary-card">
                <h3>Avg R²</h3>
                <div class="value">{sum(m['r2'] for m in performance.values()) / len(performance):.3f}</div>
            </div>
        </div>

        <div class="chart-container">
            <div class="chart-title">📊 Model Performance Rankings (by MAPE)</div>
            <table>
                <thead>
                    <tr>
                        <th>Model ID</th>
                        <th>Scope</th>
                        <th>Samples</th>
                        <th>MAPE</th>
                        <th>R²</th>
                        <th>Status</th>
                        <th>Size (MB)</th>
                    </tr>
                </thead>
                <tbody>
"""

    for model_id, metrics in sorted_models:
        status_class = 'status-pass' if metrics['target_met'] else 'status-review'
        status_text = '✅ PASS' if metrics['target_met'] else '⚠️ REVIEW'

        html += f"""                    <tr>
                        <td><strong>{model_id}</strong></td>
                        <td>{metrics['scope']}</td>
                        <td>{metrics['n_samples']:,}</td>
                        <td><strong>{metrics['mape']*100:.2f}%</strong></td>
                        <td>{metrics['r2']:.4f}</td>
                        <td class="{status_class}">{status_text}</td>
                        <td>{metrics['model_size_mb']:.1f}</td>
                    </tr>
"""

    html += """                </tbody>
            </table>
        </div>

        <div class="chart-container">
            <div class="chart-title">🎯 Performance Analysis</div>
            <p>
                <strong>Average MAPE:</strong> """
    html += f"{sum(m['mape'] for m in performance.values()) / len(performance) * 100:.2f}%<br/>"
    html += f"<strong>Target MAPE:</strong> 11.0%<br/>"
    html += f"<strong>Target Achievement:</strong> {sum(1 for m in performance.values() if m['target_met'])} of {len(performance)} models<br/>"
    html += f"<strong>Average Training Time:</strong> {sum(m['training_sec'] for m in performance.values()) / len(performance):.1f}s<br/>"
    html += """            </p>
        </div>

        <footer>
            <p>📈 Phase 14.KR Monthly Retrain Pipeline</p>
            <p>🔄 Next retrain: """
    html += datetime.now().strftime('%B 1, %Y at 00:00 UTC')
    html += """</p>
        </footer>
    </div>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return True


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description='Phase 14.KR Performance Analyzer')
    parser.add_argument('--models-dir', required=True, help='Directory with trained models')
    parser.add_argument('--output', default='reports/korea/performance_report.html')
    args = parser.parse_args()

    models_dir = Path(args.models_dir)
    if not models_dir.exists():
        log.error(f"Models directory not found: {models_dir}")
        return

    log.info("📊 Analyzing model performance...")
    performance = analyze_model_performance(models_dir)

    if not performance:
        log.error("No models found to analyze")
        return

    log.info(f"✅ Analyzed {len(performance)} models")

    output_path = Path(args.output)
    success = generate_html_report(performance, output_path)

    if success:
        log.info(f"✅ Report generated: {output_path}")
    else:
        log.error("Report generation failed")


if __name__ == '__main__':
    main()
