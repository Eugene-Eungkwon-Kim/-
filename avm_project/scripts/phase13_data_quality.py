#!/usr/bin/env python3
"""
Phase 13.6.2 - Data Quality & Streaming Pipeline
실시간 데이터 검증, 품질 모니터링, BigQuery 스트리밍.

실행:
    python scripts/phase13_data_quality.py --input data/raw/BR_real.csv --country BR
    python scripts/phase13_data_quality.py --input data/raw/SG_real.csv --report quality_report.json
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

COUNTRY_CONFIGS: Dict[str, Dict] = {
    'BR': {'min_price': 50_000, 'max_price': 5_000_000, 'currency': 'BRL'},
    'SG': {'min_price': 300_000, 'max_price': 3_000_000, 'currency': 'SGD'},
    'HK': {'min_price': 1_000_000, 'max_price': 50_000_000, 'currency': 'HKD'},
    'UK': {'min_price': 50_000, 'max_price': 2_000_000, 'currency': 'GBP'},
    'DE': {'min_price': 50_000, 'max_price': 1_000_000, 'currency': 'EUR'},
    'AU': {'min_price': 200_000, 'max_price': 2_000_000, 'currency': 'AUD'},
    'CA': {'min_price': 100_000, 'max_price': 2_000_000, 'currency': 'CAD'},
    'TH': {'min_price': 1_000_000, 'max_price': 100_000_000, 'currency': 'THB'},
}

CRITICAL_COLUMNS = ['property_id', 'price_local', 'area_m2', 'bedrooms', 'year_built']
NUMERIC_COLUMNS = ['price_local', 'area_m2', 'bedrooms', 'year_built', 'latitude', 'longitude']
GEOGRAPHIC_BOUNDS = {'lat_min': -90, 'lat_max': 90, 'lon_min': -180, 'lon_max': 180}


@dataclass
class ColumnQuality:
    """Single column quality metrics."""
    column: str
    dtype: str
    null_count: int
    null_pct: float
    issues: List[str]
    passed: bool


@dataclass
class QualityReport:
    """Complete quality validation report."""
    filename: str
    country: str
    total_records: int
    passed_records: int
    pass_rate: float
    timestamp: str
    issues_by_type: Dict[str, int]
    column_quality: List[Dict]
    overall_passed: bool
    recommendations: List[str]


def detect_outliers(series: pd.Series, column: str) -> Tuple[pd.Series, int]:
    """Detect outliers using IQR method."""
    q1, q3 = series.quantile([0.25, 0.75])
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers = (series < lower_bound) | (series > upper_bound)
    return outliers, outliers.sum()


def validate_schema(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Validate required columns and types."""
    issues = []
    for col in CRITICAL_COLUMNS:
        if col not in df.columns:
            issues.append(f"Missing critical column: {col}")
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            try:
                is_numeric = np.issubdtype(df[col].dtype, np.number)
                if not is_numeric:
                    issues.append(f"Column {col} not numeric: {df[col].dtype}")
            except TypeError:
                issues.append(f"Column {col} not numeric: {df[col].dtype}")
    return len(issues) == 0, issues


def check_null_values(df: pd.DataFrame, tolerance: float = 0.01) -> Tuple[bool, Dict[str, float], List[str]]:
    """Check for excessive null values."""
    null_pcts = (df.isnull().sum() / len(df)).to_dict()
    issues = []
    for col, pct in null_pcts.items():
        if col in CRITICAL_COLUMNS and pct > tolerance:
            issues.append(f"Critical column {col} has {pct:.1%} nulls (tolerance: {tolerance:.1%})")
    return len(issues) == 0, null_pcts, issues


def validate_price_range(df: pd.DataFrame, country: str) -> Tuple[bool, int, List[str]]:
    """Check price values within country-specific ranges."""
    if country not in COUNTRY_CONFIGS:
        return True, 0, [f"Unknown country: {country}"]
    config = COUNTRY_CONFIGS[country]
    min_p, max_p = config['min_price'], config['max_price']

    out_of_range = ((df['price_local'] < min_p) | (df['price_local'] > max_p)).sum()
    issues = [f"{out_of_range} records outside price range [{min_p:,}, {max_p:,}]"] if out_of_range > 0 else []
    return out_of_range == 0, out_of_range, issues


def validate_geographic_bounds(df: pd.DataFrame) -> Tuple[bool, int, List[str]]:
    """Validate latitude/longitude bounds."""
    invalid_lat = ((df['latitude'] < -90) | (df['latitude'] > 90)).sum()
    invalid_lon = ((df['longitude'] < -180) | (df['longitude'] > 180)).sum()
    issues = []
    if invalid_lat > 0:
        issues.append(f"{invalid_lat} records with invalid latitude")
    if invalid_lon > 0:
        issues.append(f"{invalid_lon} records with invalid longitude")
    return invalid_lat == 0 and invalid_lon == 0, invalid_lat + invalid_lon, issues


def validate_year_built(df: pd.DataFrame) -> Tuple[bool, int, List[str]]:
    """Validate year_built range (1980-2026)."""
    invalid_years = ((df['year_built'] < 1980) | (df['year_built'] > 2026)).sum()
    issues = [f"{invalid_years} records with invalid year_built (1980-2026)"] if invalid_years > 0 else []
    return invalid_years == 0, invalid_years, issues


def detect_duplicates(df: pd.DataFrame) -> Tuple[int, List[str]]:
    """Detect duplicate property IDs."""
    duplicates = df['property_id'].duplicated().sum()
    dup_ids = df[df['property_id'].duplicated()]['property_id'].unique().tolist()[:5]
    issues = [f"{duplicates} duplicate property_ids (e.g., {dup_ids})"] if duplicates > 0 else []
    return duplicates, issues


def analyze_column_quality(df: pd.DataFrame) -> List[ColumnQuality]:
    """Analyze quality for each column."""
    qualities = []
    for col in df.columns:
        null_count = df[col].isnull().sum()
        null_pct = null_count / len(df)
        issues = []

        if null_pct > 0.01:
            issues.append(f"High nulls: {null_pct:.1%}")
        if col in NUMERIC_COLUMNS and np.issubdtype(df[col].dtype, np.number):
            _, outlier_count = detect_outliers(df[col], col)
            if outlier_count > len(df) * 0.05:
                issues.append(f"High outliers: {outlier_count} ({outlier_count/len(df):.1%})")

        qualities.append(ColumnQuality(
            column=col,
            dtype=str(df[col].dtype),
            null_count=int(null_count),
            null_pct=float(null_pct),
            issues=issues,
            passed=len(issues) == 0
        ))
    return qualities


def validate_dataframe(df: pd.DataFrame, country: str) -> Tuple[int, Dict[str, int], List[str]]:
    """Run all validation checks and return passed record count."""
    all_issues = []
    issue_counts: Dict[str, int] = {}
    passed_mask = pd.Series([True] * len(df), index=df.index)

    # Schema validation
    schema_ok, schema_issues = validate_schema(df)
    if not schema_ok:
        all_issues.extend(schema_issues)
        issue_counts['schema'] = len(schema_issues)
        return 0, issue_counts, all_issues

    # Null check
    null_ok, null_pcts, null_issues = check_null_values(df)
    all_issues.extend(null_issues)
    if null_issues:
        issue_counts['null_values'] = len(null_issues)

    # Price validation
    price_ok, price_invalid, price_issues = validate_price_range(df, country)
    all_issues.extend(price_issues)
    passed_mask &= ~((df['price_local'] < COUNTRY_CONFIGS[country]['min_price']) |
                      (df['price_local'] > COUNTRY_CONFIGS[country]['max_price']))
    if price_issues:
        issue_counts['price_out_of_range'] = price_invalid

    # Geographic bounds
    geo_ok, geo_invalid, geo_issues = validate_geographic_bounds(df)
    all_issues.extend(geo_issues)
    passed_mask &= (df['latitude'].between(-90, 90)) & (df['longitude'].between(-180, 180))
    if geo_issues:
        issue_counts['geographic_bounds'] = geo_invalid

    # Year validation
    year_ok, year_invalid, year_issues = validate_year_built(df)
    all_issues.extend(year_issues)
    passed_mask &= df['year_built'].between(1980, 2026)
    if year_issues:
        issue_counts['year_built'] = year_invalid

    # Duplicate check
    dup_count, dup_issues = detect_duplicates(df)
    all_issues.extend(dup_issues)
    if dup_issues:
        issue_counts['duplicate_ids'] = dup_count

    passed_records = passed_mask.sum()
    return int(passed_records), issue_counts, all_issues


def generate_quality_report(
    df: pd.DataFrame, country: str, filename: str
) -> QualityReport:
    """Generate comprehensive quality report."""
    from datetime import datetime

    passed_records, issue_counts, all_issues = validate_dataframe(df, country)
    pass_rate = passed_records / len(df) if len(df) > 0 else 0.0

    column_qualities = analyze_column_quality(df)
    recommendations = _generate_recommendations(issue_counts, pass_rate, len(df))

    return QualityReport(
        filename=filename,
        country=country,
        total_records=len(df),
        passed_records=int(passed_records),
        pass_rate=float(pass_rate),
        timestamp=datetime.now().isoformat(),
        issues_by_type=issue_counts,
        column_quality=[asdict(q) for q in column_qualities],
        overall_passed=pass_rate >= 0.95,
        recommendations=recommendations
    )


def _generate_recommendations(issue_counts: Dict[str, int], pass_rate: float, total: int) -> List[str]:
    """Generate actionable recommendations."""
    recs = []
    if pass_rate < 0.90:
        recs.append("⚠️  Pass rate <90%; review failed records before training")
    if 'duplicate_ids' in issue_counts:
        recs.append("Remove or deduplicate property records before model training")
    if 'price_out_of_range' in issue_counts:
        recs.append("Investigate prices outside expected ranges; may indicate data errors")
    if 'geographic_bounds' in issue_counts:
        recs.append("Check latitude/longitude for data entry errors or formatting issues")
    if pass_rate >= 0.95:
        recs.append("✅ Data quality acceptable for model training")
    return recs


def save_report(report: QualityReport, output_path: Path) -> None:
    """Save quality report to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_dict = asdict(report)
    report_dict = json.loads(json.dumps(report_dict, default=str))
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False)
    log.info(f"✅ Report saved: {output_path}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description='Phase 13.6.2 Data Quality Validator')
    parser.add_argument('--input', required=True, help='Input CSV file')
    parser.add_argument('--country', required=True, choices=list(COUNTRY_CONFIGS.keys()))
    parser.add_argument('--report', default='quality_report.json', help='Output report path')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        log.error(f"❌ File not found: {input_path}")
        exit(1)

    log.info(f"📊 Validating: {input_path} ({args.country})")
    df = pd.read_csv(input_path)
    log.info(f"Loaded {len(df):,} records")

    report = generate_quality_report(df, args.country, str(input_path))
    save_report(report, Path(args.report))

    log.info(f"\n{args.country} Quality Report:")
    log.info(f"  Total: {report.total_records:,}")
    log.info(f"  Passed: {report.passed_records:,}")
    log.info(f"  Pass Rate: {report.pass_rate:.1%}")
    log.info(f"  Status: {'✅ PASS' if report.overall_passed else '❌ REVIEW'}")

    if report.issues_by_type:
        log.info(f"\nIssues:")
        for issue_type, count in report.issues_by_type.items():
            log.info(f"  • {issue_type}: {count}")

    for rec in report.recommendations:
        log.info(f"  {rec}")

    exit(0 if report.overall_passed else 1)


if __name__ == '__main__':
    main()
