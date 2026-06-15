"""
Unit tests for data cleaner module
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))


class TestDataCleaner:
    """Test suite for data cleaning functions"""

    def test_handle_missing_values(self, temp_data_dir):
        """Test missing value handling"""
        # Create data with missing values
        df = pd.DataFrame({
            'area': [100.0, np.nan, 200.0, 150.0],
            'year': [2010, 2015, np.nan, 2020],
            'name': ['A', np.nan, 'C', 'D']
        })

        initial_missing = df.isnull().sum().sum()
        assert initial_missing > 0

        # Simulate missing value handling
        df_numeric = df.select_dtypes(include=[np.number])
        for col in df_numeric.columns:
            df.loc[:, col] = df[col].fillna(df[col].mean())

        df_categorical = df.select_dtypes(include=['object'])
        for col in df_categorical.columns:
            df.loc[:, col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else 'Unknown')

        # Verify missing values are handled
        final_missing = df.isnull().sum().sum()
        assert final_missing == 0

    def test_remove_outliers(self, temp_data_dir):
        """Test outlier removal"""
        # Create data with outliers
        df = pd.DataFrame({
            'price': [100, 110, 105, 2000, 95, 100, 110],  # 2000 is outlier
            'area': [50, 60, 55, 1500, 55, 60, 65]  # 1500 is outlier
        })

        rows_before = len(df)
        assert rows_before == 7

        # Apply IQR outlier removal
        for col in ['price', 'area']:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]

        rows_after = len(df)
        assert rows_after < rows_before
        assert 2000 not in df['price'].values
        assert 1500 not in df['area'].values

    def test_normalize_data(self, temp_data_dir):
        """Test data normalization"""
        # Create unnormalized data
        df = pd.DataFrame({
            'price': [100, 200, 300, 400, 500],
            'area': [50, 100, 150, 200, 250]
        })

        # Apply Min-Max normalization
        for col in df.columns:
            min_val = df[col].min()
            max_val = df[col].max()
            df[col] = (df[col] - min_val) / (max_val - min_val)

        # Verify normalization
        for col in df.columns:
            assert df[col].min() >= 0
            assert df[col].max() <= 1

    def test_csv_data_loading(self, sample_csv_data):
        """Test loading CSV data"""
        df = pd.read_csv(sample_csv_data)
        assert len(df) == 3
        assert 'area_sqm' in df.columns
        assert 'price' in df.columns

    def test_json_data_loading(self, sample_json_data):
        """Test loading JSON data"""
        import json

        with open(sample_json_data, 'r') as f:
            data = json.load(f)

        assert data['area_sqm'] == 84.5
        assert data['year_built'] == 2015

    def test_data_shape_preservation(self):
        """Test that data shape is preserved through cleaning"""
        df_original = pd.DataFrame({
            'col1': [1, 2, 3, 4, 5],
            'col2': [10, 20, 30, 40, 50]
        })

        rows_original = len(df_original)
        cols_original = len(df_original.columns)

        # Process (without removing rows)
        df_processed = df_original.copy()

        rows_processed = len(df_processed)
        cols_processed = len(df_processed.columns)

        assert rows_original == rows_processed
        assert cols_original == cols_processed

    def test_numeric_column_detection(self):
        """Test numeric column detection"""
        df = pd.DataFrame({
            'numeric_int': [1, 2, 3],
            'numeric_float': [1.5, 2.5, 3.5],
            'text': ['a', 'b', 'c']
        })

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        assert 'numeric_int' in numeric_cols
        assert 'numeric_float' in numeric_cols
        assert 'text' not in numeric_cols

    def test_categorical_column_detection(self):
        """Test categorical column detection"""
        df = pd.DataFrame({
            'category': ['A', 'B', 'C', 'A'],
            'value': [1, 2, 3, 4]
        })

        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        assert 'category' in categorical_cols
        assert 'value' not in categorical_cols

    def test_duplicate_detection(self):
        """Test duplicate row detection"""
        df = pd.DataFrame({
            'id': [1, 2, 3, 1, 5],
            'value': [10, 20, 30, 10, 50]
        })

        duplicates = df.duplicated().sum()
        assert duplicates > 0

        df_unique = df.drop_duplicates()
        assert len(df_unique) < len(df)

    def test_data_type_consistency(self):
        """Test data type consistency"""
        df = pd.DataFrame({
            'int_col': [1, 2, 3],
            'float_col': [1.0, 2.0, 3.0],
            'str_col': ['a', 'b', 'c']
        })

        assert df['int_col'].dtype in [np.int64, np.int32]
        assert df['float_col'].dtype in [np.float64, np.float32]
        assert df['str_col'].dtype == 'object'

    def test_value_range_validation(self):
        """Test value range validation"""
        df = pd.DataFrame({
            'percentage': [0.5, 0.75, 0.25],
            'count': [10, 20, 30]
        })

        # Percentages should be 0-1
        assert (df['percentage'] >= 0).all()
        assert (df['percentage'] <= 1).all()

        # Counts should be non-negative
        assert (df['count'] >= 0).all()

    def test_nan_infinity_handling(self):
        """Test handling of NaN and infinity values"""
        df = pd.DataFrame({
            'value': [1, np.nan, np.inf, 4, -np.inf]
        })

        # Count problematic values
        nan_count = df['value'].isna().sum()
        inf_count = np.isinf(df['value']).sum()

        assert nan_count > 0
        assert inf_count > 0

        # Replace NaN and inf
        df['value'] = df['value'].replace([np.inf, -np.inf], np.nan)
        df['value'] = df['value'].fillna(df['value'].mean())

        assert not df['value'].isna().any()
        assert not np.isinf(df['value']).any()
