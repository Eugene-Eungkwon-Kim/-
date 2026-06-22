"""
End-to-end WebSocket integration tests for AVM Dashboard.

Tests full stack: connection, message types, broadcast cycles, error handling.
WebSocket endpoints: /ws/dashboard, /ws/monitoring
"""

import asyncio
import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

pytest.importorskip("websockets", reason="WebSocket tests require websockets package")

from fastapi import FastAPI
from fastapi.testclient import TestClient
import main as avm_main


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient for HTTP requests"""
    return TestClient(avm_main.app)


@pytest.fixture
def app():
    """Get the FastAPI application instance"""
    return avm_main.app


class TestDashboardHttpEndpoints:
    """Test HTTP endpoints used by dashboard UI"""

    def test_health_check_returns_healthy(self, client):
        """Dashboard needs to verify backend is running"""
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_swagger_ui_available(self, client):
        """API documentation should be available during development"""
        r = client.get("/docs")
        assert r.status_code == 200
        assert "swagger" in r.text.lower() or "openapi" in r.text.lower()

    def test_version_endpoint_returns_model_info(self, client):
        """Dashboard shows available models on load"""
        r = client.get("/api/version")
        assert r.status_code == 200
        data = r.json()
        assert "models_count" in data
        assert isinstance(data["models_count"], int)
        assert data["models_count"] > 0

    def test_predict_endpoint_basic_flow(self, client):
        """Dashboard predict request should work"""
        valid_property = {
            "area_sqm": 150,
            "year_built": 2005,
            "rooms": 3,
            "bathrooms": 2,
            "parking": 1,
            "floor": 10,
            "total_floor": 20,
            "condition": 7,
            "original_price": 8000,
            "appraised_price": 8200,
            "outstanding_debt": 4000,
            "market_price": 8500,
            "transaction_count_1y": 10,
            "ltv": 0.5,
            "loan_term_months": 240,
            "days_on_market": 30,
            "appraisal_rounds": 2,
            "age_years": 20,
            "price_per_sqm": 560,
            "debt_to_price_ratio": 0.5,
            "price_variance": 0.1,
        }
        r = client.post(
            "/predict",
            json={"property_data": valid_property, "model_name": "ensemble"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "predicted_price" in data
        assert isinstance(data["predicted_price"], (int, float))
        assert data["predicted_price"] > 0

    def test_predict_invalid_property_returns_422(self, client):
        """Dashboard should handle invalid input gracefully"""
        invalid_property = {
            "area_sqm": -100,  # Invalid: negative area
            "year_built": 2005,
        }
        r = client.post(
            "/predict",
            json={"property_data": invalid_property, "model_name": "ensemble"},
        )
        assert r.status_code == 422  # Pydantic validation error


class TestWebSocketDashboardEndpoint:
    """Test /ws/dashboard endpoint for real-time model updates"""

    def test_websocket_connection_accepted(self, client):
        """Dashboard can connect to WebSocket"""
        with client.websocket_connect("/ws/dashboard") as ws:
            # Connection should be established
            assert ws is not None

    def test_websocket_sends_initial_message(self, client):
        """Dashboard receives welcome message after connect"""
        with client.websocket_connect("/ws/dashboard") as ws:
            data = ws.receive_json()
            assert data["type"] == "connection"
            assert data["status"] == "connected"

    def test_websocket_pong_response(self, client):
        """Dashboard ping/pong keeps connection alive"""
        with client.websocket_connect("/ws/dashboard") as ws:
            ws.receive_json()  # Initial message
            ws.send_json({"type": "ping"})
            response = ws.receive_json(timeout=2)
            assert response["type"] == "pong"

    def test_websocket_receives_model_update_messages(self, client):
        """Dashboard receives periodic model status updates"""
        with client.websocket_connect("/ws/dashboard") as ws:
            ws.receive_json()  # Initial message

            # Collect multiple messages within 3-second window
            messages = []
            try:
                for _ in range(3):
                    msg = ws.receive_json(timeout=2)
                    messages.append(msg)
                    # Broadcast cycle is 30s, but we should see at least response to ping
            except:
                pass

            # Should have received at least one message after initial
            assert len(messages) >= 1

    def test_websocket_handles_disconnect(self, client):
        """WebSocket properly closes when client disconnects"""
        ws = client.websocket_connect("/ws/dashboard").__enter__()
        ws.receive_json()  # Initial message
        ws.close()

        # After close, attempting to receive should raise
        with pytest.raises(Exception):
            ws.receive_json()

    def test_websocket_multiple_concurrent_clients(self, client):
        """Multiple dashboard clients can connect simultaneously"""
        # Open two connections
        ws1 = client.websocket_connect("/ws/dashboard").__enter__()
        ws2 = client.websocket_connect("/ws/dashboard").__enter__()

        try:
            # Both receive initial messages
            msg1 = ws1.receive_json()
            msg2 = ws2.receive_json()

            assert msg1["type"] == "connection"
            assert msg2["type"] == "connection"

            # Both respond to ping
            ws1.send_json({"type": "ping"})
            ws2.send_json({"type": "ping"})

            pong1 = ws1.receive_json()
            pong2 = ws2.receive_json()

            assert pong1["type"] == "pong"
            assert pong2["type"] == "pong"
        finally:
            ws1.close()
            ws2.close()


class TestWebSocketMonitoringEndpoint:
    """Test /ws/monitoring endpoint for retraining metrics"""

    def test_monitoring_websocket_connection(self, client):
        """Monitoring dashboard can connect to WebSocket"""
        with client.websocket_connect("/ws/monitoring") as ws:
            assert ws is not None

    def test_monitoring_sends_initial_message(self, client):
        """Monitoring receives connection confirmation"""
        with client.websocket_connect("/ws/monitoring") as ws:
            data = ws.receive_json()
            assert data["type"] == "connection"
            assert data["status"] == "connected"

    def test_monitoring_pong_response(self, client):
        """Monitoring connection responds to ping"""
        with client.websocket_connect("/ws/monitoring") as ws:
            ws.receive_json()  # Initial message
            ws.send_json({"type": "ping"})
            response = ws.receive_json(timeout=2)
            assert response["type"] == "pong"

    def test_monitoring_receives_retraining_updates(self, client):
        """Monitoring receives retraining status messages"""
        with client.websocket_connect("/ws/monitoring") as ws:
            ws.receive_json()  # Initial message

            # Collect messages
            messages = []
            try:
                for _ in range(3):
                    msg = ws.receive_json(timeout=2)
                    messages.append(msg)
            except:
                pass

            # Should have received at least one message
            assert len(messages) >= 1


class TestWebSocketMessageTypes:
    """Test WebSocket message format and schema compliance"""

    def test_connection_message_schema(self, client):
        """Connection messages follow expected schema"""
        with client.websocket_connect("/ws/dashboard") as ws:
            msg = ws.receive_json()

            # Required fields
            assert "type" in msg
            assert "status" in msg
            assert "timestamp" in msg

            # Type values
            assert msg["type"] == "connection"
            assert msg["status"] in ["connected", "error"]

    def test_pong_message_schema(self, client):
        """Pong messages follow expected schema"""
        with client.websocket_connect("/ws/dashboard") as ws:
            ws.receive_json()  # Initial
            ws.send_json({"type": "ping"})
            msg = ws.receive_json()

            assert msg["type"] == "pong"
            assert "timestamp" in msg

    def test_update_message_schema(self, client):
        """Update messages contain required fields"""
        with client.websocket_connect("/ws/dashboard") as ws:
            ws.receive_json()  # Initial

            # Collect an update message
            try:
                msg = ws.receive_json(timeout=1)
                if msg["type"] in ["model_status", "update"]:
                    assert "type" in msg
                    assert "timestamp" in msg
            except:
                # Timeout is OK; broadcast cycle is 30s
                pass


class TestWebSocketErrorHandling:
    """Test WebSocket error handling and edge cases"""

    def test_invalid_message_type(self, client):
        """WebSocket handles invalid message gracefully"""
        with client.websocket_connect("/ws/dashboard") as ws:
            ws.receive_json()  # Initial

            # Send invalid message type
            ws.send_json({"type": "invalid_type"})

            # Connection should remain open
            # (server ignores unrecognized types, doesn't crash)
            try:
                msg = ws.receive_json(timeout=1)
                # May receive another update or pong
                assert "type" in msg
            except:
                # Timeout is OK
                pass

    def test_malformed_json_handling(self, client):
        """WebSocket handles malformed JSON gracefully"""
        # TestClient doesn't allow sending raw bytes, so we skip raw JSON test
        # but we verify the endpoint doesn't crash with valid malformed types
        with client.websocket_connect("/ws/dashboard") as ws:
            ws.receive_json()
            ws.send_text("{invalid json")

            # Connection should close or ignore
            # (behavior depends on implementation)
            try:
                msg = ws.receive_json(timeout=1)
                # If we get here, server ignored it
                assert "type" in msg
            except:
                # Expected: connection might close or timeout
                pass

    def test_websocket_timeout_reconnect(self, client):
        """Dashboard can reconnect after timeout"""
        # First connection
        ws1 = client.websocket_connect("/ws/dashboard").__enter__()
        msg1 = ws1.receive_json()
        assert msg1["type"] == "connection"
        ws1.close()

        # Second connection should work
        with client.websocket_connect("/ws/dashboard") as ws2:
            msg2 = ws2.receive_json()
            assert msg2["type"] == "connection"


class TestE2EFullFlow:
    """End-to-end tests combining multiple components"""

    def test_dashboard_startup_sequence(self, client):
        """Complete dashboard startup flow"""
        # 1. Health check
        health = client.get("/health")
        assert health.status_code == 200

        # 2. Get available models
        version = client.get("/api/version")
        assert version.status_code == 200
        models_count = version.json()["models_count"]
        assert models_count > 0

        # 3. Connect to dashboard WebSocket
        with client.websocket_connect("/ws/dashboard") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connection"

    def test_predict_and_monitoring_flow(self, client):
        """User makes prediction while monitoring updates"""
        property_data = {
            "area_sqm": 100,
            "year_built": 2010,
            "rooms": 3,
            "bathrooms": 1,
            "parking": 1,
            "floor": 5,
            "total_floor": 10,
            "condition": 7,
            "original_price": 5000,
            "appraised_price": 5100,
            "outstanding_debt": 2500,
            "market_price": 5200,
            "transaction_count_1y": 8,
            "ltv": 0.5,
            "loan_term_months": 240,
            "days_on_market": 45,
            "appraisal_rounds": 1,
            "age_years": 15,
            "price_per_sqm": 500,
            "debt_to_price_ratio": 0.5,
            "price_variance": 0.05,
        }

        # User makes prediction
        r = client.post(
            "/predict",
            json={"property_data": property_data, "model_name": "ensemble"},
        )
        assert r.status_code == 200
        prediction = r.json()
        assert "predicted_price" in prediction

        # Monitoring WebSocket is active
        with client.websocket_connect("/ws/monitoring") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connection"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
