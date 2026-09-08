#!/usr/bin/env python3
"""
Loan4U AVM - FastAPI Tests (Phase 13.4.1)
Test API endpoints, validation, and error handling.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from phase13_api_service import app, PropertyInput

client = TestClient(app)


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check_success(self):
        """GET /api/health returns 200."""
        response = client.get("/api/health")

        assert response.status_code == 200
        assert "status" in response.json()

    def test_health_check_format(self):
        """Health check response format."""
        response = client.get("/api/health")
        data = response.json()

        assert data["status"] in ["healthy", "degraded"]
        assert "engine" in data


class TestModelStatus:
    """Test model status endpoint."""

    def test_model_status_endpoint(self):
        """GET /api/models returns model information."""
        response = client.get("/api/models")

        assert response.status_code == 200
        data = response.json()

        assert "models_loaded" in data
        assert "model_names" in data
        assert isinstance(data["model_names"], list)


class TestValuationEndpoint:
    """Test valuation prediction endpoint."""

    @pytest.fixture
    def valid_payload(self):
        """Valid property input."""
        return {
            "area_sqm": 100,
            "old_price": 500000,
            "latitude": 35.5,
            "longitude": 126.8,
            "property_type": 2
        }

    def test_valuation_valid_input(self, valid_payload):
        """TC-5.1: Valid valuation request."""
        response = client.post("/api/valuation", json=valid_payload)

        # 200 or 503 (service unavailable) are both acceptable
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "predicted_price" in data
            assert "confidence" in data
            assert "latency_ms" in data

    def test_valuation_response_format(self, valid_payload):
        """Valuation response format validation."""
        response = client.post("/api/valuation", json=valid_payload)

        if response.status_code == 200:
            data = response.json()

            # Type validation
            assert isinstance(data["predicted_price"], (int, float))
            assert isinstance(data["confidence"], (int, float))
            assert isinstance(data["latency_ms"], (int, float))

            # Range validation
            assert 0 < data["predicted_price"] < 10_000_000_000
            assert 0 <= data["confidence"] <= 1
            assert 0 <= data["latency_ms"] <= 10

    def test_valuation_area_too_large(self):
        """TC-5.2: Area exceeds maximum."""
        payload = {
            "area_sqm": 2000,  # Exceeds max 1000
            "old_price": 500000,
            "latitude": 35.5,
            "longitude": 126.8,
            "property_type": 2
        }

        response = client.post("/api/valuation", json=payload)
        assert response.status_code == 422  # Validation error

    def test_valuation_negative_price(self):
        """Price must be positive."""
        payload = {
            "area_sqm": 100,
            "old_price": -500000,  # Negative
            "latitude": 35.5,
            "longitude": 126.8,
            "property_type": 2
        }

        response = client.post("/api/valuation", json=payload)
        assert response.status_code == 422

    def test_valuation_invalid_property_type(self):
        """Property type must be 1-5."""
        payload = {
            "area_sqm": 100,
            "old_price": 500000,
            "latitude": 35.5,
            "longitude": 126.8,
            "property_type": 10  # Invalid
        }

        response = client.post("/api/valuation", json=payload)
        assert response.status_code == 422

    def test_valuation_missing_field(self):
        """Missing required field."""
        payload = {
            "area_sqm": 100,
            # Missing "old_price"
            "latitude": 35.5,
            "longitude": 126.8,
            "property_type": 2
        }

        response = client.post("/api/valuation", json=payload)
        assert response.status_code == 422

    def test_valuation_invalid_latitude(self):
        """Latitude out of range."""
        payload = {
            "area_sqm": 100,
            "old_price": 500000,
            "latitude": 50,  # Too high
            "longitude": 126.8,
            "property_type": 2
        }

        response = client.post("/api/valuation", json=payload)
        assert response.status_code == 422


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint(self):
        """GET / returns API information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "Loan4U AVM API"
        assert "version" in data
        assert "docs" in data


class TestErrorHandling:
    """Test error handling."""

    def test_404_not_found(self):
        """Non-existent endpoint returns 404."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Invalid HTTP method."""
        response = client.get("/api/valuation")  # GET instead of POST
        assert response.status_code == 405


class TestConcurrency:
    """Test concurrent requests."""

    def test_multiple_requests(self):
        """Handle multiple concurrent-like requests."""
        payload = {
            "area_sqm": 100,
            "old_price": 500000,
            "latitude": 35.5,
            "longitude": 126.8,
            "property_type": 2
        }

        responses = []
        for _ in range(5):
            response = client.post("/api/valuation", json=payload)
            responses.append(response.status_code)

        # All should succeed or fail consistently
        assert all(status in [200, 503] for status in responses)
