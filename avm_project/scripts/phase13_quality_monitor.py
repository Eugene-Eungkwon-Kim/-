#!/usr/bin/env python3
"""
Phase 13.6.2 - Quality Monitoring Dashboard
실시간 데이터 품질 모니터링 및 경고 시스템.

실행:
    python scripts/phase13_quality_monitor.py --reports-dir data/raw --output reports/quality_dashboard.html
    python scripts/phase13_quality_monitor.py --reports-dir data/raw --window 7  # Last 7 days
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


@dataclass
class QualityMetric:
    """Time-stamped quality metric for tracking."""
    country: str
    timestamp: str
    pass_rate: float
    total_records: int
    passed_records: int
    issues: Dict[str, int]


@dataclass
class CountryTrend:
    """Quality trend for single country."""
    country: str
    metrics: List[QualityMetric]
    avg_pass_rate: float
    min_pass_rate: float
    max_pass_rate: float
    trend_direction: str


def parse_quality_report(report_path: Path) -> Optional[QualityMetric]:
    """Parse quality report JSON to metrics."""
    try:
        with open(report_path) as f:
            report = json.load(f)

        return QualityMetric(
            country=report['country'],
            timestamp=report['timestamp'],
            pass_rate=float(report['pass_rate']),
            total_records=int(report['total_records']),
            passed_records=int(report['passed_records']),
            issues=report.get('issues_by_type', {}),
        )
    except Exception as e:
        log.warning(f"Failed to parse {report_path}: {e}")
        return None


def load_quality_history(reports_dir: Path, days: int = 30) -> Dict[str, List[QualityMetric]]:
    """Load quality metrics from all reports in directory."""
    history: Dict[str, List[QualityMetric]] = {}
    cutoff_date = datetime.now() - timedelta(days=days)

    if not reports_dir.exists():
        log.warning(f"Reports directory not found: {reports_dir}")
        return history

    for report_file in reports_dir.glob('*_quality_report.json'):
        metric = parse_quality_report(report_file)
        if metric:
            metric_time = datetime.fromisoformat(metric.timestamp)
            if metric_time >= cutoff_date:
                if metric.country not in history:
                    history[metric.country] = []
                history[metric.country].append(metric)

    for metrics in history.values():
        metrics.sort(key=lambda m: m.timestamp)

    return history


def calculate_trend(metrics: List[QualityMetric]) -> CountryTrend:
    """Calculate trend statistics for country."""
    if not metrics:
        return CountryTrend(
            country='Unknown',
            metrics=[],
            avg_pass_rate=0.0,
            min_pass_rate=0.0,
            max_pass_rate=0.0,
            trend_direction='N/A'
        )

    pass_rates = [m.pass_rate for m in metrics]
    avg_rate = sum(pass_rates) / len(pass_rates)
    min_rate = min(pass_rates)
    max_rate = max(pass_rates)

    if len(metrics) >= 2:
        recent_avg = sum(pass_rates[-5:]) / len(pass_rates[-5:])
        older_avg = sum(pass_rates[:5]) / len(pass_rates[:5])
        trend = '📈' if recent_avg > older_avg else '📉' if recent_avg < older_avg else '→'
    else:
        trend = '→'

    return CountryTrend(
        country=metrics[0].country,
        metrics=metrics,
        avg_pass_rate=avg_rate,
        min_pass_rate=min_rate,
        max_pass_rate=max_rate,
        trend_direction=trend,
    )


def generate_dashboard_html(trends: List[CountryTrend], output_path: Path) -> bool:
    """Generate HTML quality dashboard."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AVM Phase 13.6.2 - Quality Monitoring Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}

        header {{ background: linear-gradient(135deg, #1f4e78 0%, #2e5c8a 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; }}
        header h1 {{ font-size: 28px; margin-bottom: 5px; }}
        header p {{ opacity: 0.9; font-size: 14px; }}

        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .summary-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .summary-card h3 {{ font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 10px; }}
        .summary-card .value {{ font-size: 24px; font-weight: bold; color: #1f4e78; }}

        .countries-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
        .country-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1f4e78; }}
        .country-card.warning {{ border-left-color: #ff9800; }}
        .country-card.critical {{ border-left-color: #f44336; }}

        .country-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee; }}
        .country-header h3 {{ font-size: 16px; font-weight: 600; }}
        .trend-badge {{ font-size: 20px; }}

        .metric-row {{ display: flex; justify-content: space-between; align-items: center; margin: 10px 0; padding: 8px 0; border-bottom: 1px solid #f5f5f5; }}
        .metric-label {{ font-size: 13px; color: #666; }}
        .metric-value {{ font-weight: 600; font-size: 14px; color: #333; }}

        .pass-rate-bar {{ width: 100%; height: 8px; background: #e0e0e0; border-radius: 4px; margin-top: 10px; overflow: hidden; }}
        .pass-rate-fill {{ height: 100%; background: linear-gradient(90deg, #f44336, #ff9800, #4caf50); transition: width 0.3s; }}

        .status-badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
        .status-excellent {{ background: #c8e6c9; color: #2e7d32; }}
        .status-good {{ background: #bbdefb; color: #1565c0; }}
        .status-fair {{ background: #ffe0b2; color: #e65100; }}
        .status-poor {{ background: #ffcdd2; color: #c62828; }}

        .issues-list {{ margin-top: 15px; padding-top: 10px; border-top: 1px solid #eee; }}
        .issue-item {{ font-size: 12px; color: #666; margin: 5px 0; }}

        footer {{ text-align: center; margin-top: 40px; padding: 20px; font-size: 12px; color: #999; border-top: 1px solid #eee; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 AVM Quality Monitoring Dashboard</h1>
            <p>Phase 13.6.2 Real-Time Data Quality Metrics • Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <div class="summary">
            <div class="summary-card">
                <h3>Countries Tracked</h3>
                <div class="value">{len(trends)}</div>
            </div>
            <div class="summary-card">
                <h3>Avg Pass Rate</h3>
                <div class="value">{sum(t.avg_pass_rate for t in trends) / len(trends) * 100:.1f}%</div>
            </div>
            <div class="summary-card">
                <h3>⚠️ Alerts</h3>
                <div class="value">{sum(1 for t in trends if t.avg_pass_rate < 0.90)}</div>
            </div>
            <div class="summary-card">
                <h3>✅ Excellent</h3>
                <div class="value">{sum(1 for t in trends if t.avg_pass_rate >= 0.95)}</div>
            </div>
        </div>

        <div class="countries-grid">
"""

    for trend in sorted(trends, key=lambda t: t.avg_pass_rate, reverse=True):
        status_class = 'excellent' if trend.avg_pass_rate >= 0.95 else 'good' if trend.avg_pass_rate >= 0.80 else 'fair' if trend.avg_pass_rate >= 0.60 else 'poor'
        status_badge = f'status-{status_class}'
        card_class = 'country-card'
        if trend.avg_pass_rate < 0.90:
            card_class += ' warning'
        if trend.avg_pass_rate < 0.70:
            card_class += ' critical'

        html_content += f"""            <div class="{card_class}">
                <div class="country-header">
                    <h3>{trend.country}</h3>
                    <span class="trend-badge">{trend.trend_direction}</span>
                </div>

                <div class="metric-row">
                    <span class="metric-label">Average Pass Rate</span>
                    <span class="status-badge {status_badge}">{trend.avg_pass_rate*100:.1f}%</span>
                </div>

                <div class="pass-rate-bar">
                    <div class="pass-rate-fill" style="width: {trend.avg_pass_rate*100}%"></div>
                </div>

                <div class="metric-row" style="margin-top: 15px;">
                    <span class="metric-label">Min / Max</span>
                    <span class="metric-value">{trend.min_pass_rate*100:.1f}% / {trend.max_pass_rate*100:.1f}%</span>
                </div>

                <div class="metric-row">
                    <span class="metric-label">Records Checked</span>
                    <span class="metric-value">{sum(m.total_records for m in trend.metrics):,}</span>
                </div>
"""

        if trend.metrics[-1].issues:
            html_content += '                <div class="issues-list"><strong>Recent Issues:</strong>'
            for issue_type, count in list(trend.metrics[-1].issues.items())[:3]:
                html_content += f'<div class="issue-item">• {issue_type}: {count}</div>'
            html_content += '</div>'

        html_content += '            </div>\n'

    html_content += """        </div>

        <footer>
            <p>📊 Quality metrics updated continuously as validation reports are generated</p>
            <p>🔄 Refresh this page to see latest data • ⚠️ Alert threshold: <90% pass rate</p>
        </footer>
    </div>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return True


def print_console_report(trends: List[CountryTrend]) -> None:
    """Print quality summary to console."""
    log.info("\n" + "=" * 70)
    log.info("Quality Monitoring Report")
    log.info("=" * 70)

    for trend in sorted(trends, key=lambda t: t.avg_pass_rate, reverse=True):
        status = '✅' if trend.avg_pass_rate >= 0.95 else '⚠️' if trend.avg_pass_rate >= 0.80 else '❌'
        log.info(f"\n{trend.country} {trend.trend_direction}")
        log.info(f"  Average: {trend.avg_pass_rate*100:.1f}% {status}")
        log.info(f"  Range: {trend.min_pass_rate*100:.1f}% - {trend.max_pass_rate*100:.1f}%")
        log.info(f"  Records: {sum(m.total_records for m in trend.metrics):,} validated")

        if trend.metrics[-1].issues:
            log.info(f"  Latest Issues: {trend.metrics[-1].issues}")

    log.info("\n" + "=" * 70)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description='Phase 13.6.2 Quality Monitoring')
    parser.add_argument('--reports-dir', required=True, help='Directory with quality reports')
    parser.add_argument('--output', default='output/quality_dashboard.html', help='Output dashboard path')
    parser.add_argument('--window', type=int, default=30, help='Days of history to include')
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    history = load_quality_history(reports_dir, args.window)

    if not history:
        log.warning(f"No quality reports found in {reports_dir}")
        return

    trends = [calculate_trend(metrics) for metrics in history.values()]
    print_console_report(trends)

    output_path = Path(args.output)
    success = generate_dashboard_html(trends, output_path)

    if success:
        log.info(f"\n✅ Dashboard generated: {output_path}")
    else:
        log.error(f"❌ Dashboard generation failed")


if __name__ == '__main__':
    main()
