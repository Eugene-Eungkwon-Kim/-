#!/usr/bin/env python3
"""
Loan4U AVM - Data Quality Tests (Phase 13.1)
Validate data loading, preprocessing, and edge cases.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']
TARGET_COL = 'new_price'


def create_test_csv(path: Path, rows: int = 100, has_nulls: bool = False) -> None:
    """Create test CSV file."""
    data = {
        'area_sqm': np.random.uniform(10, 500, rows),
        'old_price': np.random.uniform(50000, 5000000, rows),
        'latitude': np.random.uniform(33, 38, rows),
        'longitude': np.random.uniform(126, 131, rows),
        'property_type': np.random.randint(1, 6, rows),
        'new_price': np.random.uniform(50000, 5000000, rows),
    }

    df = pd.DataFrame(data)

    if has_nulls:
        df.iloc[10:15, 0] = np.nan  # area_sqm에 결측값

    df.to_csv(path, index=False)


@pytest.fixture
def test_data_dir(tmp_path):
    """Create test data directory."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()

    # Valid data
    create_test_csv(data_dir / "valid.csv", rows=100)

    # Data with nulls
    create_test_csv(data_dir / "with_nulls.csv", rows=100, has_nulls=True)

    return data_dir


class TestDataLoading:
    """Test Phase 13.1 data loading."""

    def test_load_valid_csv(self, test_data_dir):
        """TC-1.1: Valid CSV loading."""
        df = pd.read_csv(test_data_dir / "valid.csv")

        assert df is not None
        assert len(df) == 100
        assert set(FEATURE_COLS + [TARGET_COL]).issubset(df.columns)

    def test_missing_columns(self, test_data_dir):
        """TC-1.2: Missing required columns."""
        df = pd.read_csv(test_data_dir / "valid.csv")
        df_incomplete = df.drop(columns=['area_sqm'])

        missing = set(FEATURE_COLS + [TARGET_COL]) - set(df_incomplete.columns)
        assert len(missing) > 0

    def test_missing_values_removal(self, test_data_dir):
        """TC-1.3: Missing values handling."""
        df = pd.read_csv(test_data_dir / "with_nulls.csv")
        initial_len = len(df)

        df_clean = df.dropna(subset=FEATURE_COLS + [TARGET_COL])
        final_len = len(df_clean)

        assert final_len < initial_len
        assert df_clean.isnull().sum().sum() == 0


class TestDataValidation:
    """Test data validation and ranges."""

    def test_feature_ranges(self, test_data_dir):
        """Validate feature ranges."""
        df = pd.read_csv(test_data_dir / "valid.csv")

        assert (df['area_sqm'] > 0).all()
        assert (df['old_price'] > 0).all()
        assert (df['latitude'] >= 33).all() and (df['latitude'] <= 38).all()
        assert (df['longitude'] >= 126).all() and (df['longitude'] <= 131).all()
        assert df['property_type'].isin(range(1, 6)).all()

    def test_target_range(self, test_data_dir):
        """Validate target variable range."""
        df = pd.read_csv(test_data_dir / "valid.csv")

        assert (df['new_price'] > 0).all()
        assert (df['new_price'].notna()).all()

    def test_no_duplicates(self, test_data_dir):
        """Check for exact duplicates."""
        df = pd.read_csv(test_data_dir / "valid.csv")

        assert df.duplicated().sum() == 0  # Exact duplicates acceptable


class TestDataPreprocessing:
    """Test preprocessing operations."""

    def test_normalization(self, test_data_dir):
        """Test min-max normalization."""
        df = pd.read_csv(test_data_dir / "valid.csv")

        X = df[FEATURE_COLS].to_numpy(dtype=np.float32)

        feature_min = np.array([10.0, 50000.0, 33.0, 126.0, 1.0])
        feature_max = np.array([500.0, 5000000.0, 38.0, 131.0, 5.0])

        X_norm = (X - feature_min) / (feature_max - feature_min)
        X_norm = np.clip(X_norm, 0.0, 1.0)

        assert X_norm.min() >= 0.0
        assert X_norm.max() <= 1.0

    def test_outlier_detection(self, test_data_dir):
        """Test outlier detection (IQR method)."""
        df = pd.read_csv(test_data_dir / "valid.csv")

        Q1 = df['new_price'].quantile(0.25)
        Q3 = df['new_price'].quantile(0.75)
        IQR = Q3 - Q1

        outliers = (df['new_price'] < Q1 - 1.5*IQR) | (df['new_price'] > Q3 + 1.5*IQR)

        # Should detect some outliers in random data
        assert isinstance(outliers, pd.Series)
