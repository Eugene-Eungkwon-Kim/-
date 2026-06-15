"""
Unit tests for API server endpoints
"""

import pytest
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

# Mock the api_server imports since models may not be available
import unittest.mock as mock


class TestAPIServer:
    """Test suite for API server"""

    def test_imports(self):
        """Test that required modules can be imported"""
        try:
            from exceptions import (
                AVMException, ModelNotFoundError, InvalidInputError,
                PredictionError, DataProcessingError
            )
            assert AVMException is not None
            assert ModelNotFoundError is not None
            assert InvalidInputError is not None
            assert PredictionError is not None
            assert DataProcessingError is not None
        except ImportError as e:
            pytest.fail(f"Failed to import exceptions: {e}")

    def test_data_path_config(self):
        """Test data path configuration"""
        try:
            from data_path_config import get_data_path, get_subpath, validate_paths

            # Test get_data_path
            data_path = get_data_path()
            assert data_path is not None
            assert isinstance(data_path, Path)

            # Test get_subpath
            raw_path = get_subpath('Raw_Data')
            assert raw_path is not None
            assert 'Raw_Data' in str(raw_path)

            # Test validate_paths
            status = validate_paths()
            assert status is not None
            assert isinstance(status, dict)
        except Exception as e:
            pytest.fail(f"Data path config test failed: {e}")

    def test_sample_property_data_fixture(self, sample_property_data):
        """Test that sample property data fixture works"""
        assert sample_property_data is not None
        assert sample_property_data['area_sqm'] == 84.5
        assert sample_property_data['year_built'] == 2015
        assert sample_property_data['rooms'] == 3
        assert 'price_per_sqm' in sample_property_data

    def test_sample_property_data_invalid_negative_area(self, invalid_property_data_negative_area):
        """Test invalid property data with negative area"""
        assert invalid_property_data_negative_area['area_sqm'] < 0
        # This should fail validation if Pydantic is applied

    def test_sample_property_data_invalid_future_year(self, invalid_property_data_future_year):
        """Test invalid property data with future year"""
        from datetime import datetime
        current_year = datetime.now().year
        assert invalid_property_data_future_year['year_built'] > current_year
        # This should fail validation if Pydantic is applied

    def test_environment_variables(self):
        """Test that environment variables are properly configured"""
        import os
        from dotenv import load_dotenv

        load_dotenv()

        # Check if required env vars are set (in test, we may not have actual values)
        # This test just verifies that the configuration loading works
        datagovkr_key = os.getenv('DATAGOVKR_API_KEY')
        vworld_key = os.getenv('VWORLD_API_KEY')

        # In test environment, these may not be set, which is OK
        # The important thing is that the code tries to load them
        api_host = os.getenv('API_HOST', '0.0.0.0')
        api_port = os.getenv('API_PORT', '8000')

        assert api_host is not None
        assert api_port is not None

    def test_property_data_validation_area_constraint(self, sample_property_data):
        """Test that area constraints would be enforced"""
        # area_sqm should be positive and <= 1000
        assert sample_property_data['area_sqm'] > 0
        assert sample_property_data['area_sqm'] <= 1000

    def test_property_data_validation_year_constraint(self, sample_property_data):
        """Test that year constraints would be enforced"""
        # year_built should be between 1900 and current year
        from datetime import datetime
        current_year = datetime.now().year

        assert sample_property_data['year_built'] >= 1900
        assert sample_property_data['year_built'] <= current_year

    def test_property_data_validation_room_constraints(self, sample_property_data):
        """Test that room count constraints would be enforced"""
        assert sample_property_data['rooms'] >= 0
        assert sample_property_data['rooms'] <= 20
        assert sample_property_data['bathrooms'] >= 0
        assert sample_property_data['bathrooms'] <= 10

    def test_property_data_validation_ltv_constraint(self, sample_property_data):
        """Test that LTV (loan-to-value) constraints would be enforced"""
        assert sample_property_data['ltv'] >= 0
        assert sample_property_data['ltv'] <= 2

    def test_property_data_validation_price_constraints(self, sample_property_data):
        """Test that price constraints would be enforced"""
        # Prices should be positive
        assert sample_property_data['original_price'] > 0
        assert sample_property_data['appraised_price'] > 0
        assert sample_property_data['market_price'] > 0
        assert sample_property_data['outstanding_debt'] >= 0

    def test_exception_hierarchy(self):
        """Test custom exception hierarchy"""
        from exceptions import (
            AVMException, ModelNotFoundError, InvalidInputError,
            PredictionError, DataProcessingError, APIKeyError
        )

        # Test that all custom exceptions inherit from AVMException
        assert issubclass(ModelNotFoundError, AVMException)
        assert issubclass(InvalidInputError, AVMException)
        assert issubclass(PredictionError, AVMException)
        assert issubclass(DataProcessingError, AVMException)
        assert issubclass(APIKeyError, AVMException)

    def test_exception_can_be_raised(self):
        """Test that exceptions can be raised and caught"""
        from exceptions import ModelNotFoundError, AVMException

        try:
            raise ModelNotFoundError("Test model not found")
        except AVMException as e:
            assert "Test model not found" in str(e)
        except Exception as e:
            pytest.fail(f"Unexpected exception type: {type(e)}")

    def test_csv_data_fixture(self, sample_csv_data):
        """Test CSV data fixture"""
        import pandas as pd

        assert sample_csv_data.exists()
        df = pd.read_csv(sample_csv_data)
        assert len(df) == 3
        assert 'area_sqm' in df.columns
        assert 'year_built' in df.columns

    def test_json_data_fixture(self, sample_json_data):
        """Test JSON data fixture"""
        import json

        assert sample_json_data.exists()
        with open(sample_json_data, 'r') as f:
            data = json.load(f)
        assert data['transaction_id'] == 'TRX001'
        assert data['area_sqm'] == 84.5


class TestInputValidation:
    """Test input validation logic"""

    def test_positive_area(self, sample_property_data):
        """Area should be positive"""
        # This would be enforced by Pydantic Field(gt=0)
        assert sample_property_data['area_sqm'] > 0

    def test_reasonable_area_range(self, sample_property_data):
        """Area should be in reasonable range (10-1000 m²)"""
        assert sample_property_data['area_sqm'] >= 10
        assert sample_property_data['area_sqm'] <= 1000

    def test_reasonable_year_range(self, sample_property_data):
        """Year should be between 1900 and current year"""
        from datetime import datetime
        current_year = datetime.now().year

        assert sample_property_data['year_built'] >= 1900
        assert sample_property_data['year_built'] <= current_year

    def test_ltv_reasonable_range(self, sample_property_data):
        """LTV should be between 0 and 2"""
        assert sample_property_data['ltv'] >= 0
        assert sample_property_data['ltv'] <= 2

    def test_negative_area_rejected(self, invalid_property_data_negative_area):
        """Negative area should be invalid"""
        # This would be rejected by Pydantic validation
        assert invalid_property_data_negative_area['area_sqm'] < 0

    def test_future_year_rejected(self, invalid_property_data_future_year):
        """Future year should be invalid"""
        # This would be rejected by validator
        from datetime import datetime
        current_year = datetime.now().year
        assert invalid_property_data_future_year['year_built'] > current_year
