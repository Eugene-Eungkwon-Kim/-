"""
API 엔드포인트 통합 테스트 (TestClient 실호출).

기존 test_api_server.py는 하위 모듈만 검증하고 엔드포인트를 실제로
호출하지 않아 런타임 버그(예: 미정의 전역 참조)를 잡지 못했다.
이 테스트는 FastAPI TestClient로 엔드포인트를 직접 호출해 회귀를 방지한다.

httpx/python-dotenv 미설치 환경에서는 자동으로 skip된다.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# 선택적 의존성 — 없으면 전체 모듈 skip
pytest.importorskip("httpx", reason="TestClient는 httpx가 필요합니다")
pytest.importorskip("dotenv", reason="api_server는 python-dotenv가 필요합니다")

from fastapi.testclient import TestClient  # noqa: E402

import api_server  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(api_server.app, raise_server_exceptions=False)


@pytest.fixture
def valid_property():
    """예제 부동산 데이터 (단위: 만원)"""
    return {
        "area_sqm": 150, "year_built": 2005, "rooms": 3, "bathrooms": 2,
        "parking": 1, "floor": 10, "total_floor": 20, "condition": 7,
        "original_price": 8000, "appraised_price": 8200, "outstanding_debt": 4000,  # 8000/8200/4000만원
        "market_price": 8500, "transaction_count_1y": 10, "ltv": 0.5,  # 8500만원
        "loan_term_months": 240, "days_on_market": 30, "appraisal_rounds": 2,
        "age_years": 20, "price_per_sqm": 560, "debt_to_price_ratio": 0.5,  # m²당 560만원
        "price_variance": 0.1,
    }


class TestInfoEndpoints:
    def test_root_ok(self, client):
        assert client.get("/").status_code == 200

    def test_health_ok(self, client):
        assert client.get("/health").status_code == 200

    def test_version_models_count(self, client):
        r = client.get("/api/version")
        assert r.status_code == 200
        # 회귀 방지: 과거 NameError(model_metadata 미정의) 지점
        assert r.json()["models_count"] >= 0

    def test_cache_stats(self, client):
        r = client.get("/cache/stats")
        assert r.status_code == 200
        assert "cache" in r.json()


class TestPredictEndpoint:
    def test_predict_returns_price(self, client, valid_property):
        r = client.post(
            "/predict",
            json={"property_data": valid_property, "model_name": "LGBMRegressor"},
        )
        assert r.status_code == 200, r.json()
        assert "predicted_price" in r.json()

    def test_predict_unknown_model_404(self, client, valid_property):
        r = client.post(
            "/predict",
            json={"property_data": valid_property, "model_name": "does_not_exist"},
        )
        assert r.status_code == 404

    def test_predict_invalid_input_422(self, client, valid_property):
        bad = dict(valid_property, area_sqm=-5)  # 음수 면적 → Pydantic 검증 실패
        r = client.post(
            "/predict", json={"property_data": bad, "model_name": "LGBMRegressor"}
        )
        assert r.status_code == 422


class TestConfidenceEndpoint:
    def test_confidence_interval(self, client, valid_property):
        r = client.post(
            "/predict/confidence?confidence=0.95",
            json={"property_data": valid_property, "model_name": "RandomForestRegressor"},
        )
        assert r.status_code == 200, r.json()
        body = r.json()
        assert body["lower_bound"] <= body["prediction"] <= body["upper_bound"]

    def test_confidence_invalid_level_400(self, client, valid_property):
        r = client.post(
            "/predict/confidence?confidence=0.5",
            json={"property_data": valid_property, "model_name": "LGBMRegressor"},
        )
        assert r.status_code == 400
