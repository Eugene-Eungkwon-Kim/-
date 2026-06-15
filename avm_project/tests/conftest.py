"""
Pytest configuration and shared fixtures
"""

import pytest
from pathlib import Path
import tempfile
import json


@pytest.fixture
def temp_data_dir():
    """Create and provide a temporary data directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_property_data():
    """Sample property data for testing"""
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


@pytest.fixture
def invalid_property_data_negative_area():
    """Property data with invalid negative area"""
    return {
        "area_sqm": -100,  # Invalid: negative
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


@pytest.fixture
def invalid_property_data_future_year():
    """Property data with invalid future year"""
    return {
        "area_sqm": 84.5,
        "year_built": 2050,  # Invalid: future year
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


@pytest.fixture
def sample_csv_data(temp_data_dir):
    """Create sample CSV data for testing"""
    import pandas as pd

    data = {
        'area_sqm': [100, 150, 200],
        'year_built': [2010, 2015, 2020],
        'rooms': [3, 4, 5],
        'price': [450000, 550000, 650000]
    }

    df = pd.DataFrame(data)
    csv_file = temp_data_dir / 'sample.csv'
    df.to_csv(csv_file, index=False)

    return csv_file


@pytest.fixture
def sample_json_data(temp_data_dir):
    """Create sample JSON data for testing"""
    data = {
        'transaction_id': 'TRX001',
        'area_sqm': 84.5,
        'year_built': 2015,
        'price': 450000
    }

    json_file = temp_data_dir / 'sample.json'
    with open(json_file, 'w') as f:
        json.dump(data, f)

    return json_file
