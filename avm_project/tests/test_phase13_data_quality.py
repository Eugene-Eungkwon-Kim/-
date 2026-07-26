#!/usr/bin/env python3
"""
Phase 13.6.2 Data Quality Validator Tests

Tests all validation functions: schema, nulls, prices, geographic bounds, years, duplicates.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from phase13_data_quality import (
    validate_schema,
    check_null_values,
    validate_price_range,
    validate_geographic_bounds,
    validate_year_built,
    detect_duplicates,
    detect_outliers,
    generate_quality_report,
)


class TestSchemaValidation(unittest.TestCase):
    """Test schema validation."""

    def test_valid_schema(self) -> None:
        """Valid schema passes."""
        df = pd.DataFrame({
            'property_id': ['A1', 'A2'],
            'price_local': [100_000.0, 200_000.0],
            'area_m2': [50.0, 100.0],
            'bedrooms': [1, 2],
            'year_built': [2000, 2010],
            'latitude': [1.0, 2.0],
            'longitude': [103.0, 104.0],
        })
        passed, issues = validate_schema(df)
        self.assertTrue(passed)
        self.assertEqual(len(issues), 0)

    def test_missing_critical_column(self) -> None:
        """Missing critical column fails."""
        df = pd.DataFrame({
            'property_id': ['A1'],
            'price_local': [100_000.0],
        })
        passed, issues = validate_schema(df)
        self.assertFalse(passed)
        self.assertGreater(len(issues), 0)

    def test_non_numeric_price_column(self) -> None:
        """Non-numeric price column fails."""
        df = pd.DataFrame({
            'property_id': ['A1'],
            'price_local': ['100k'],
            'area_m2': [50.0],
            'bedrooms': [1],
            'year_built': [2000],
            'latitude': [1.0],
            'longitude': [103.0],
        })
        passed, issues = validate_schema(df)
        self.assertFalse(passed)


class TestNullValidation(unittest.TestCase):
    """Test null value detection."""

    def test_no_nulls(self) -> None:
        """No nulls passes."""
        df = pd.DataFrame({
            'property_id': ['A1', 'A2'],
            'price_local': [100_000.0, 200_000.0],
        })
        passed, pcts, issues = check_null_values(df, tolerance=0.01)
        self.assertTrue(passed)
        self.assertEqual(len(issues), 0)

    def test_critical_column_null_exceeds_tolerance(self) -> None:
        """Critical column null >1% fails."""
        df = pd.DataFrame({
            'property_id': ['A1', 'A2', 'A3', 'A4', 'A5'],
            'price_local': [100_000.0, np.nan, 200_000.0, 300_000.0, 400_000.0],
        })
        passed, pcts, issues = check_null_values(df, tolerance=0.01)
        self.assertFalse(passed)
        self.assertGreater(len(issues), 0)


class TestPriceValidation(unittest.TestCase):
    """Test price range validation."""

    def test_prices_in_range(self) -> None:
        """Prices within range pass."""
        df = pd.DataFrame({
            'price_local': [500_000, 1_000_000, 2_000_000],
        })
        passed, invalid, issues = validate_price_range(df, 'SG')
        self.assertTrue(passed)
        self.assertEqual(invalid, 0)

    def test_prices_out_of_range(self) -> None:
        """Prices outside range fail."""
        df = pd.DataFrame({
            'price_local': [100_000, 10_000_000],  # Both out of range for SG
        })
        passed, invalid, issues = validate_price_range(df, 'SG')
        self.assertFalse(passed)
        self.assertEqual(invalid, 2)

    def test_unknown_country(self) -> None:
        """Unknown country returns success with warning."""
        df = pd.DataFrame({'price_local': [100_000]})
        passed, invalid, issues = validate_price_range(df, 'XX')
        self.assertTrue(passed)
        self.assertGreater(len(issues), 0)


class TestGeographicValidation(unittest.TestCase):
    """Test geographic bounds validation."""

    def test_valid_coordinates(self) -> None:
        """Valid coordinates pass."""
        df = pd.DataFrame({
            'latitude': [1.3, 22.3, 51.5],
            'longitude': [103.8, 114.2, -0.1],
        })
        passed, invalid, issues = validate_geographic_bounds(df)
        self.assertTrue(passed)
        self.assertEqual(invalid, 0)

    def test_invalid_latitude(self) -> None:
        """Latitude >90 fails."""
        df = pd.DataFrame({
            'latitude': [1.3, 95.0, 51.5],
            'longitude': [103.8, 114.2, -0.1],
        })
        passed, invalid, issues = validate_geographic_bounds(df)
        self.assertFalse(passed)
        self.assertGreater(invalid, 0)

    def test_invalid_longitude(self) -> None:
        """Longitude >180 fails."""
        df = pd.DataFrame({
            'latitude': [1.3, 22.3, 51.5],
            'longitude': [103.8, 200.0, -0.1],
        })
        passed, invalid, issues = validate_geographic_bounds(df)
        self.assertFalse(passed)


class TestYearValidation(unittest.TestCase):
    """Test year_built validation."""

    def test_valid_years(self) -> None:
        """Years 1980-2026 pass."""
        df = pd.DataFrame({
            'year_built': [1980, 2000, 2020, 2026],
        })
        passed, invalid, issues = validate_year_built(df)
        self.assertTrue(passed)
        self.assertEqual(invalid, 0)

    def test_year_too_old(self) -> None:
        """Year <1980 fails."""
        df = pd.DataFrame({
            'year_built': [1950, 2000],
        })
        passed, invalid, issues = validate_year_built(df)
        self.assertFalse(passed)
        self.assertGreater(invalid, 0)

    def test_year_too_new(self) -> None:
        """Year >2026 fails."""
        df = pd.DataFrame({
            'year_built': [2000, 2030],
        })
        passed, invalid, issues = validate_year_built(df)
        self.assertFalse(passed)


class TestDuplicateDetection(unittest.TestCase):
    """Test duplicate property ID detection."""

    def test_no_duplicates(self) -> None:
        """No duplicates pass."""
        df = pd.DataFrame({
            'property_id': ['P001', 'P002', 'P003'],
        })
        dup_count, issues = detect_duplicates(df)
        self.assertEqual(dup_count, 0)
        self.assertEqual(len(issues), 0)

    def test_duplicates_detected(self) -> None:
        """Duplicates are detected."""
        df = pd.DataFrame({
            'property_id': ['P001', 'P002', 'P001', 'P003'],
        })
        dup_count, issues = detect_duplicates(df)
        self.assertGreater(dup_count, 0)
        self.assertGreater(len(issues), 0)


class TestOutlierDetection(unittest.TestCase):
    """Test IQR-based outlier detection."""

    def test_no_outliers(self) -> None:
        """Normal distribution has few outliers."""
        series = pd.Series(np.random.normal(100, 10, 100))
        outliers, count = detect_outliers(series, 'test')
        self.assertLess(count, 10)

    def test_clear_outliers(self) -> None:
        """Extreme values detected as outliers."""
        series = pd.Series([1, 2, 3, 4, 5, 1000])
        outliers, count = detect_outliers(series, 'test')
        self.assertGreater(count, 0)


class TestQualityReport(unittest.TestCase):
    """Test full quality report generation."""

    def test_valid_data_quality_report(self) -> None:
        """Valid data generates passing report."""
        df = pd.DataFrame({
            'property_id': [f'P{i:04d}' for i in range(100)],
            'price_local': np.random.uniform(500_000, 2_000_000, 100),
            'area_m2': np.random.uniform(50, 300, 100),
            'bedrooms': np.random.choice([1, 2, 3, 4], 100),
            'year_built': np.random.randint(1990, 2023, 100),
            'latitude': np.random.uniform(1, 2, 100),
            'longitude': np.random.uniform(103, 104, 100),
        })
        report = generate_quality_report(df, 'SG', 'test.csv')

        self.assertEqual(report.total_records, 100)
        self.assertGreater(report.passed_records, 90)
        self.assertGreater(report.pass_rate, 0.9)

    def test_poor_quality_data_report(self) -> None:
        """Poor data generates failing report."""
        df = pd.DataFrame({
            'property_id': ['P001', 'P002'],
            'price_local': [100_000, 50_000_000],  # Out of range
            'area_m2': [50.0, 100.0],
            'bedrooms': [1, 2],
            'year_built': [2000, 1950],  # 1950 is out of range
            'latitude': [200.0, 2.0],  # 200 is invalid
            'longitude': [103.0, 104.0],
        })
        report = generate_quality_report(df, 'SG', 'test.csv')

        self.assertFalse(report.overall_passed)
        self.assertGreater(len(report.issues_by_type), 0)


class TestReportSerialization(unittest.TestCase):
    """Test report JSON serialization."""

    def test_report_saves_to_json(self) -> None:
        """Report can be saved and loaded."""
        from phase13_data_quality import save_report

        df = pd.DataFrame({
            'property_id': ['P001', 'P002'],
            'price_local': [500_000, 1_000_000],
            'area_m2': [50.0, 100.0],
            'bedrooms': [1, 2],
            'year_built': [2000, 2010],
            'latitude': [1.0, 2.0],
            'longitude': [103.0, 104.0],
        })
        report = generate_quality_report(df, 'SG', 'test.csv')

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / 'report.json'
            save_report(report, report_path)

            self.assertTrue(report_path.exists())
            with open(report_path) as f:
                import json
                loaded = json.load(f)
                self.assertEqual(loaded['country'], 'SG')
                self.assertEqual(loaded['total_records'], 2)


if __name__ == '__main__':
    unittest.main()
