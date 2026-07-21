#!/usr/bin/env python3
"""
Phase 13.6.2 Quality Monitor Tests

Tests metrics parsing, trend calculation, and dashboard generation.
"""

import sys
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))


class TestQualityMetricParsing(unittest.TestCase):
    """Test parsing quality report JSON to metrics."""

    def test_parse_quality_report_success(self) -> None:
        """Parse valid quality report JSON."""
        from phase13_quality_monitor import parse_quality_report

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / 'test_quality_report.json'
            report_data = {
                'country': 'SG',
                'timestamp': datetime.now().isoformat(),
                'pass_rate': 0.95,
                'total_records': 1000,
                'passed_records': 950,
                'issues_by_type': {'price_out_of_range': 50},
            }
            with open(report_path, 'w') as f:
                json.dump(report_data, f)

            metric = parse_quality_report(report_path)

            self.assertIsNotNone(metric)
            self.assertEqual(metric.country, 'SG')
            self.assertEqual(metric.pass_rate, 0.95)
            self.assertEqual(metric.total_records, 1000)

    def test_parse_quality_report_missing_file(self) -> None:
        """Handle missing report file."""
        from phase13_quality_monitor import parse_quality_report

        metric = parse_quality_report(Path('/nonexistent/file.json'))
        self.assertIsNone(metric)


class TestLoadQualityHistory(unittest.TestCase):
    """Test loading quality history from directory."""

    def test_load_quality_history_empty_dir(self) -> None:
        """Handle empty directory."""
        from phase13_quality_monitor import load_quality_history

        with tempfile.TemporaryDirectory() as tmpdir:
            history = load_quality_history(Path(tmpdir))
            self.assertEqual(len(history), 0)

    def test_load_quality_history_multiple_reports(self) -> None:
        """Load multiple quality reports."""
        from phase13_quality_monitor import load_quality_history

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            for country in ['BR', 'SG']:
                report_path = tmpdir_path / f'{country}_quality_report.json'
                report_data = {
                    'country': country,
                    'timestamp': datetime.now().isoformat(),
                    'pass_rate': 0.90,
                    'total_records': 1000,
                    'passed_records': 900,
                    'issues_by_type': {},
                }
                with open(report_path, 'w') as f:
                    json.dump(report_data, f)

            history = load_quality_history(tmpdir_path)

            self.assertEqual(len(history), 2)
            self.assertIn('BR', history)
            self.assertIn('SG', history)

    def test_load_quality_history_time_window(self) -> None:
        """Filter by time window."""
        from phase13_quality_monitor import load_quality_history

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            old_time = (datetime.now() - timedelta(days=45)).isoformat()
            report_path = tmpdir_path / 'SG_quality_report.json'
            report_data = {
                'country': 'SG',
                'timestamp': old_time,
                'pass_rate': 0.90,
                'total_records': 1000,
                'passed_records': 900,
                'issues_by_type': {},
            }
            with open(report_path, 'w') as f:
                json.dump(report_data, f)

            history = load_quality_history(tmpdir_path, days=30)

            self.assertEqual(len(history), 0)


class TestCalculateTrend(unittest.TestCase):
    """Test trend calculation."""

    def test_calculate_trend_empty_metrics(self) -> None:
        """Handle empty metrics list."""
        from phase13_quality_monitor import calculate_trend, QualityMetric

        trend = calculate_trend([])

        self.assertEqual(trend.avg_pass_rate, 0.0)
        self.assertEqual(len(trend.metrics), 0)

    def test_calculate_trend_single_metric(self) -> None:
        """Calculate trend from single metric."""
        from phase13_quality_monitor import calculate_trend, QualityMetric

        metric = QualityMetric(
            country='SG',
            timestamp=datetime.now().isoformat(),
            pass_rate=0.95,
            total_records=1000,
            passed_records=950,
            issues={},
        )

        trend = calculate_trend([metric])

        self.assertEqual(trend.country, 'SG')
        self.assertEqual(trend.avg_pass_rate, 0.95)
        self.assertEqual(trend.min_pass_rate, 0.95)
        self.assertEqual(trend.max_pass_rate, 0.95)

    def test_calculate_trend_multiple_metrics(self) -> None:
        """Calculate trend from multiple metrics."""
        from phase13_quality_monitor import calculate_trend, QualityMetric

        metrics = [
            QualityMetric('SG', datetime.now().isoformat(), 0.90, 1000, 900, {}),
            QualityMetric('SG', datetime.now().isoformat(), 0.95, 1000, 950, {}),
            QualityMetric('SG', datetime.now().isoformat(), 0.92, 1000, 920, {}),
        ]

        trend = calculate_trend(metrics)

        self.assertAlmostEqual(trend.avg_pass_rate, 0.9233333, places=5)
        self.assertEqual(trend.min_pass_rate, 0.90)
        self.assertEqual(trend.max_pass_rate, 0.95)

    def test_calculate_trend_direction(self) -> None:
        """Detect trend direction."""
        from phase13_quality_monitor import calculate_trend, QualityMetric

        metrics = [
            QualityMetric('SG', datetime.now().isoformat(), 0.85, 1000, 850, {}),
            QualityMetric('SG', datetime.now().isoformat(), 0.87, 1000, 870, {}),
            QualityMetric('SG', datetime.now().isoformat(), 0.90, 1000, 900, {}),
            QualityMetric('SG', datetime.now().isoformat(), 0.92, 1000, 920, {}),
            QualityMetric('SG', datetime.now().isoformat(), 0.95, 1000, 950, {}),
            QualityMetric('SG', datetime.now().isoformat(), 0.94, 1000, 940, {}),
        ]

        trend = calculate_trend(metrics)

        self.assertIn(trend.trend_direction, ['📈', '📉', '→'])


class TestDashboardGeneration(unittest.TestCase):
    """Test HTML dashboard generation."""

    def test_generate_dashboard_html_success(self) -> None:
        """Generate dashboard HTML successfully."""
        from phase13_quality_monitor import generate_dashboard_html, CountryTrend, QualityMetric

        metrics = [
            QualityMetric('SG', datetime.now().isoformat(), 0.95, 1000, 950, {}),
        ]
        trend = CountryTrend('SG', metrics, 0.95, 0.95, 0.95, '→')

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'dashboard.html'
            result = generate_dashboard_html([trend], output_path)

            self.assertTrue(result)
            self.assertTrue(output_path.exists())

    def test_generate_dashboard_html_multiple_countries(self) -> None:
        """Generate dashboard with multiple countries."""
        from phase13_quality_monitor import generate_dashboard_html, CountryTrend, QualityMetric

        trends = []
        for country in ['BR', 'SG', 'HK']:
            metric = QualityMetric(country, datetime.now().isoformat(), 0.90, 1000, 900, {})
            trend = CountryTrend(country, [metric], 0.90, 0.90, 0.90, '→')
            trends.append(trend)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'dashboard.html'
            result = generate_dashboard_html(trends, output_path)

            self.assertTrue(result)
            with open(output_path) as f:
                html = f.read()
                self.assertIn('BR', html)
                self.assertIn('SG', html)
                self.assertIn('HK', html)

    def test_dashboard_html_contains_key_elements(self) -> None:
        """Dashboard HTML contains expected elements."""
        from phase13_quality_monitor import generate_dashboard_html, CountryTrend, QualityMetric

        metric = QualityMetric('SG', datetime.now().isoformat(), 0.95, 1000, 950, {})
        trend = CountryTrend('SG', [metric], 0.95, 0.90, 0.95, '📈')

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'dashboard.html'
            generate_dashboard_html([trend], output_path)

            with open(output_path) as f:
                html = f.read()
                self.assertIn('Quality Monitoring Dashboard', html)
                self.assertIn('95.0%', html)
                self.assertIn('📈', html)


if __name__ == '__main__':
    unittest.main()
