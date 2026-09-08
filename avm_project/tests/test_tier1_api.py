"""Tier 1 API 서버 통합 테스트.

12개 테스트 케이스:
1. Health check
2-4. Geocoding (성공/실패/유효성검사)
5-7. Price analysis (성공/실패/요청검증)
8-10. Quality score (조회/없음/바운더리)
11-12. Root/docs
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from avm_project.scripts.tier1_api_server_types import app


@pytest.fixture
def client() -> TestClient:
    """TestClient 픽스처."""
    return TestClient(app)


class TestHealthCheck:
    """헬스체크 엔드포인트 테스트."""

    def test_health_check_ok(self, client: TestClient) -> None:
        """정상 헬스체크."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["database"] == "ok"
        assert "timestamp" in data

    def test_health_check_schema(self, client: TestClient) -> None:
        """헬스체크 응답 스키마."""
        resp = client.get("/health")
        data = resp.json()
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)


class TestGeocoding:
    """지오코딩 엔드포인트 테스트."""

    def test_geocode_valid_address(self, client: TestClient) -> None:
        """유효한 주소 지오코딩."""
        resp = client.post(
            "/geocode",
            json={"address": "서울특별시 종로구 세종대로 209", "search_type": "address"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "data" in data
        assert data["data"]["lat"] is not None
        assert data["data"]["lon"] is not None

    def test_geocode_coordinates_valid(self, client: TestClient) -> None:
        """반환 좌표 유효성."""
        resp = client.post(
            "/geocode", json={"address": "서울 강남구"}
        )
        data = resp.json()
        lat = data["data"]["lat"]
        lon = data["data"]["lon"]
        assert -90 <= lat <= 90, "위도 범위 검증"
        assert -180 <= lon <= 180, "경도 범위 검증"

    def test_geocode_empty_address(self, client: TestClient) -> None:
        """빈 주소 검증."""
        resp = client.post("/geocode", json={"address": ""})
        assert resp.status_code == 422  # Pydantic validation


class TestPriceAnalysis:
    """가격 분석 엔드포인트 테스트."""

    def test_analyze_price_apartment(self, client: TestClient) -> None:
        """아파트 가격 분석."""
        resp = client.post(
            "/analyze-price",
            json={
                "address": "서울 강남구 테헤란로 123",
                "property_type": "apartment",
                "area_sqm": 84.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["estimated_price"]["estimated_value"] > 0
        assert 0 <= data["estimated_price"]["confidence"] <= 1

    def test_analyze_price_response_schema(self, client: TestClient) -> None:
        """응답 스키마 검증."""
        resp = client.post(
            "/analyze-price",
            json={
                "address": "서울 서초구",
                "property_type": "house",
            },
        )
        data = resp.json()
        assert "estimated_price" in data
        assert "quality_score" in data
        assert "analysis_date" in data
        assert isinstance(data["analysis_date"], str)

    def test_analyze_price_invalid_type(self, client: TestClient) -> None:
        """유효하지 않은 부동산 유형."""
        resp = client.post(
            "/analyze-price",
            json={
                "address": "서울",
                "property_type": "invalid_type",
            },
        )
        # property_type은 자유 텍스트이므로 200 (비즈니스 로직 검증 필요)
        assert resp.status_code in [200, 422]

    def test_analyze_price_negative_area(self, client: TestClient) -> None:
        """음수 면적 검증."""
        resp = client.post(
            "/analyze-price",
            json={
                "address": "서울",
                "property_type": "apartment",
                "area_sqm": -10.0,
            },
        )
        assert resp.status_code == 422  # Validation error


class TestQualityScore:
    """품질점수 엔드포인트 테스트."""

    def test_quality_score_valid_pnu(self, client: TestClient) -> None:
        """유효한 PNU로 조회."""
        pnu = "1111011001001010001"  # 19자리 더미
        resp = client.get(f"/quality-score?pnu={pnu}")
        assert resp.status_code == 200
        data = resp.json()
        assert 0 <= data["score"] <= 100
        assert data["rating"] in ["A", "B", "C", "D"]

    def test_quality_score_no_pnu(self, client: TestClient) -> None:
        """PNU 없음."""
        resp = client.get("/quality-score")
        assert resp.status_code == 400

    def test_quality_score_pnu_length(self, client: TestClient) -> None:
        """PNU 길이 검증."""
        resp = client.get("/quality-score?pnu=123")
        assert resp.status_code == 422  # 길이 부족

    def test_quality_score_factors(self, client: TestClient) -> None:
        """품질 요인 검증."""
        pnu = "1111011001001010001"
        resp = client.get(f"/quality-score?pnu={pnu}")
        data = resp.json()
        assert "factors" in data
        for factor_name, factor_value in data["factors"].items():
            assert isinstance(factor_name, str)
            assert isinstance(factor_value, (int, float))


class TestRootEndpoint:
    """루트 및 문서 엔드포인트 테스트."""

    def test_root_endpoint(self, client: TestClient) -> None:
        """루트 엔드포인트."""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "version" in data

    def test_docs_available(self, client: TestClient) -> None:
        """자동 문서 생성 가능."""
        resp = client.get("/docs")
        assert resp.status_code == 200
        assert "swagger" in resp.text.lower()


class TestErrorHandling:
    """에러 처리 테스트."""

    def test_invalid_json(self, client: TestClient) -> None:
        """유효하지 않은 JSON."""
        resp = client.post(
            "/analyze-price",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_missing_required_field(self, client: TestClient) -> None:
        """필수 필드 누락."""
        resp = client.post("/analyze-price", json={"property_type": "apartment"})
        assert resp.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
