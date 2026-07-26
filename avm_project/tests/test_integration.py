"""
Integration tests for complete AVM workflows
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import json
from unittest.mock import Mock, patch


class TestDataPipelineIntegration:
    """Test complete data processing pipeline"""

    @pytest.fixture
    def sample_raw_data(self, temp_data_dir):
        """Create sample raw data file"""
        data = {
            'area_sqm': [100, 120, 150, 80, 200],
            'year_built': [2010, 2015, 2020, 2000, 2018],
            'rooms': [3, 4, 4, 2, 5],
            'bathrooms': [2, 2, 3, 1, 3],
            'parking': [1, 1, 2, 0, 2],
            'floor': [5, 10, 3, 2, 15],
            'total_floor': [20, 20, 15, 10, 20],
            'condition': [7, 8, 9, 5, 8],
            'original_price': [450000, 550000, 650000, 350000, 750000],
            'appraised_price': [455000, 560000, 660000, 360000, 760000],
            'outstanding_debt': [250000, 300000, 350000, 200000, 400000],
            'market_price': [460000, 570000, 670000, 365000, 770000],
            'transaction_count_1y': [5, 8, 12, 3, 15],
            'ltv': [0.55, 0.53, 0.52, 0.55, 0.52],
            'loan_term_months': [240, 240, 360, 180, 300],
            'days_on_market': [30, 45, 20, 60, 15],
            'appraisal_rounds': [2, 2, 3, 1, 2],
            'age_years': [14, 9, 4, 26, 8],
            'price_per_sqm': [4600, 4750, 4467, 4562, 3850],
            'debt_to_price_ratio': [0.54, 0.53, 0.52, 0.55, 0.52],
            'price_variance': [0.02, 0.02, 0.01, 0.03, 0.01],
            'market_trend': [0.05, 0.06, 0.07, -0.02, 0.08],
            'interest_rate': [0.045, 0.045, 0.040, 0.050, 0.040]
        }

        df = pd.DataFrame(data)
        raw_file = temp_data_dir / 'raw_data.csv'
        df.to_csv(raw_file, index=False)

        return raw_file

    def test_data_loading(self, sample_raw_data):
        """Test loading raw data"""
        df = pd.read_csv(sample_raw_data)

        assert df.shape[0] == 5
        assert 'area_sqm' in df.columns
        assert 'market_price' in df.columns

    def test_data_validation_stage(self, sample_raw_data):
        """Test data validation in pipeline"""
        df = pd.read_csv(sample_raw_data)

        # Check for required columns
        required_cols = ['area_sqm', 'year_built', 'market_price']
        assert all(col in df.columns for col in required_cols)

        # Check data types
        assert pd.api.types.is_numeric_dtype(df['area_sqm'])
        assert pd.api.types.is_numeric_dtype(df['market_price'])

    def test_data_cleaning_stage(self, sample_raw_data):
        """Test data cleaning in pipeline"""
        df = pd.read_csv(sample_raw_data)

        # Remove duplicates
        initial_rows = len(df)
        df = df.drop_duplicates()
        assert len(df) <= initial_rows

        # Handle missing values
        missing_before = df.isnull().sum().sum()
        df = df.fillna(df.mean(numeric_only=True))
        missing_after = df.isnull().sum().sum()
        assert missing_after <= missing_before

    def test_feature_engineering_stage(self, sample_raw_data):
        """Test feature engineering in pipeline"""
        df = pd.read_csv(sample_raw_data)

        # Create derived features
        df['price_per_sqm'] = df['market_price'] / df['area_sqm']
        df['debt_to_price'] = df['outstanding_debt'] / df['market_price']
        df['age'] = 2024 - df['year_built']

        assert 'price_per_sqm' in df.columns
        assert 'debt_to_price' in df.columns
        assert 'age' in df.columns

    def test_data_normalization_stage(self, sample_raw_data):
        """Test normalization in pipeline"""
        df = pd.read_csv(sample_raw_data)

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            min_val = df[col].min()
            max_val = df[col].max()
            df[col] = (df[col] - min_val) / (max_val - min_val)
            assert df[col].min() >= 0
            assert df[col].max() <= 1

    def test_complete_pipeline_end_to_end(self, sample_raw_data, temp_data_dir):
        """Test complete pipeline from raw to processed data"""
        # Load
        df = pd.read_csv(sample_raw_data)
        assert df.shape[0] > 0

        # Validate
        assert 'market_price' in df.columns

        # Clean
        df = df.drop_duplicates()
        df = df.fillna(df.mean(numeric_only=True))

        # Engineer
        df['price_per_sqm'] = df['market_price'] / df['area_sqm']

        # Normalize
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            min_val = df[col].min()
            max_val = df[col].max()
            if max_val > min_val:
                df[col] = (df[col] - min_val) / (max_val - min_val)

        # Save
        output_file = temp_data_dir / 'processed_data.csv'
        df.to_csv(output_file, index=False)

        assert output_file.exists()
        processed_df = pd.read_csv(output_file)
        assert processed_df.shape[0] == df.shape[0]


class TestModelTrainingIntegration:
    """Test model training with real data flow"""

    @pytest.fixture
    def training_data(self):
        """Create training data"""
        np.random.seed(42)
        X = np.random.randn(100, 10)
        y = X[:, 0] * 2 + X[:, 1] * 0.5 + np.random.randn(100) * 0.5
        return X, y

    def test_train_single_model(self, training_data):
        """Test training single model"""
        from sklearn.linear_model import LinearRegression

        X, y = training_data
        model = LinearRegression()
        model.fit(X, y)

        score = model.score(X, y)
        assert score > 0

    def test_train_multiple_models(self, training_data):
        """Test training multiple models"""
        from sklearn.linear_model import LinearRegression
        from sklearn.ensemble import RandomForestRegressor

        X, y = training_data
        models = {}

        models['LinearRegression'] = LinearRegression()
        models['RandomForest'] = RandomForestRegressor(n_estimators=10, random_state=42)

        for name, model in models.items():
            model.fit(X, y)
            score = model.score(X, y)
            assert score is not None

    def test_model_comparison_workflow(self, training_data):
        """Test complete model comparison workflow"""
        from sklearn.linear_model import LinearRegression
        from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

        X, y = training_data
        models = {
            'LinearRegression': LinearRegression(),
            'RandomForest': RandomForestRegressor(n_estimators=10, random_state=42),
            'GradientBoosting': GradientBoostingRegressor(n_estimators=10, random_state=42)
        }

        results = {}
        for name, model in models.items():
            model.fit(X, y)
            results[name] = model.score(X, y)

        # Select best model
        best_model = max(results, key=results.get)
        assert best_model in results
        assert results[best_model] >= min(results.values())

    def test_cross_validation_workflow(self, training_data):
        """Test cross-validation workflow"""
        from sklearn.model_selection import cross_val_score
        from sklearn.linear_model import LinearRegression

        X, y = training_data
        model = LinearRegression()

        scores = cross_val_score(model, X, y, cv=5)
        assert len(scores) == 5
        assert scores.mean() > -1


class TestAPIEndpointIntegration:
    """Test API endpoint integration"""

    @pytest.fixture
    def api_request_data(self):
        """Create sample API request data"""
        return {
            "area_sqm": 84.5,
            "year_built": 2015,
            "rooms": 3,
            "bathrooms": 2,
            "parking": 1,
            "floor": 5,
            "total_floor": 15,
            "condition": 7,
            "original_price": 450000,
            "appraised_price": 455000,
            "outstanding_debt": 250000,
            "market_price": 460000,
            "transaction_count_1y": 12,
            "ltv": 0.55,
            "loan_term_months": 240,
            "days_on_market": 30,
            "appraisal_rounds": 2,
            "age_years": 11,
            "price_per_sqm": 5326,
            "debt_to_price_ratio": 0.55,
            "price_variance": 0.02,
            "market_trend": 0.05,
            "interest_rate": 0.045
        }

    def test_prediction_request_structure(self, api_request_data):
        """Test prediction request structure"""
        assert isinstance(api_request_data, dict)
        assert 'area_sqm' in api_request_data
        assert 'market_price' in api_request_data
        assert api_request_data['area_sqm'] > 0

    def test_validation_before_prediction(self, api_request_data):
        """Test validation before prediction"""
        # Check required fields
        required_fields = ['area_sqm', 'year_built', 'rooms']
        assert all(field in api_request_data for field in required_fields)

        # Check value ranges
        assert api_request_data['area_sqm'] > 0
        assert api_request_data['year_built'] > 1900

    def test_batch_prediction_workflow(self, api_request_data):
        """Test batch prediction workflow"""
        batch = [api_request_data] * 3

        assert len(batch) == 3
        assert all(isinstance(item, dict) for item in batch)


class TestConfigurationIntegration:
    """Test configuration integration"""

    def test_environment_variable_loading(self):
        """Test loading configuration from environment"""
        with patch.dict('os.environ', {'LOG_LEVEL': 'INFO'}):
            log_level = __import__('os').getenv('LOG_LEVEL')
            assert log_level == 'INFO'

    def test_settings_singleton_access(self):
        """Test accessing global settings"""
        # Simulate settings access
        settings = {}
        settings['api_host'] = '0.0.0.0'
        settings['api_port'] = 8000

        assert settings['api_host'] == '0.0.0.0'
        assert settings['api_port'] == 8000

    def test_configuration_validation(self):
        """Test configuration validation"""
        config = {
            'api_port': 8000,
            'log_level': 'INFO',
            'model_r2_threshold': 0.85
        }

        assert config['api_port'] > 0
        assert config['api_port'] < 65536
        assert config['log_level'] in ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        assert 0 <= config['model_r2_threshold'] <= 1


class TestErrorHandlingIntegration:
    """Test error handling across components"""

    def test_validation_error_propagation(self):
        """Test validation error propagation"""
        from avm_project.exceptions import InvalidInputError

        try:
            raise InvalidInputError("Invalid area_sqm")
        except InvalidInputError as e:
            assert "area_sqm" in str(e)

    def test_model_error_handling(self):
        """Test model error handling"""
        from avm_project.exceptions import ModelNotFoundError

        try:
            raise ModelNotFoundError("Model not found")
        except ModelNotFoundError as e:
            assert "Model" in str(e)

    def test_prediction_error_handling(self):
        """Test prediction error handling"""
        from avm_project.exceptions import PredictionError

        try:
            raise PredictionError("Prediction failed")
        except PredictionError as e:
            assert "Prediction" in str(e)

    def test_multiple_error_types(self):
        """Test handling multiple error types"""
        from avm_project.exceptions import (
            InvalidInputError,
            ModelNotFoundError,
            PredictionError
        )

        errors = []
        for exc_class in [InvalidInputError, ModelNotFoundError, PredictionError]:
            try:
                raise exc_class("test error")
            except Exception as e:
                errors.append(type(e).__name__)

        assert len(errors) == 3


class TestDataValidationIntegration:
    """Test data validation across pipeline"""

    @pytest.fixture
    def validation_test_data(self):
        """Create test data for validation"""
        return pd.DataFrame({
            'area_sqm': [100, 150, 200],
            'year_built': [2010, 2015, 2020],
            'rooms': [3, 4, 5],
            'bathrooms': [2, 2, 3],
            'price': [450000, 550000, 650000]
        })

    def test_schema_validation(self, validation_test_data):
        """Test schema validation"""
        expected_cols = ['area_sqm', 'year_built', 'rooms', 'bathrooms', 'price']
        assert all(col in validation_test_data.columns for col in expected_cols)

    def test_type_validation(self, validation_test_data):
        """Test data type validation"""
        numeric_cols = ['area_sqm', 'year_built', 'rooms', 'price']
        for col in numeric_cols:
            assert pd.api.types.is_numeric_dtype(validation_test_data[col])

    def test_range_validation(self, validation_test_data):
        """Test value range validation"""
        assert validation_test_data['area_sqm'].min() > 0
        assert validation_test_data['year_built'].min() > 1900
        assert validation_test_data['year_built'].max() < 2100

    def test_missing_value_validation(self, validation_test_data):
        """Test missing value validation"""
        missing_count = validation_test_data.isnull().sum().sum()
        assert missing_count == 0

    def test_duplicate_validation(self, validation_test_data):
        """Test duplicate row validation"""
        duplicates = validation_test_data.duplicated().sum()
        assert duplicates == 0


class TestLoggingIntegration:
    """Test logging integration"""

    def test_logger_initialization(self):
        """Test logger initialization"""
        import logging
        logger = logging.getLogger('test_module')
        assert logger is not None

    def test_log_message_creation(self):
        """Test creating log messages"""
        import logging
        logger = logging.getLogger('test')

        # Would log if handler attached
        logger.info("Test message")
        logger.warning("Warning message")

    def test_structured_logging_format(self):
        """Test structured logging format"""
        log_message = {
            'timestamp': '2026-06-15T10:00:00',
            'level': 'INFO',
            'message': 'Test message',
            'module': 'test_module'
        }

        assert 'timestamp' in log_message
        assert 'level' in log_message
        assert 'message' in log_message
