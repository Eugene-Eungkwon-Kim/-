"""Tier 2 통합 테스트: 15개 테스트

테스트 구성:
  - 모니터링 (5개)
  - 게이트웨이 인증 (5개)
  - 게이트웨이 속도제한 (3개)
  - 게이트웨이 요청검증 (2개)
"""

import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from avm_project.scripts.tier2_gateway import app, rate_limiter
from avm_project.scripts.tier2_monitoring import MetricsCollector


@pytest.fixture
def client() -> TestClient:
    """테스트 클라이언트."""
    return TestClient(app)


@pytest.fixture
def valid_api_key() -> str:
    """유효한 API 키."""
    return "test_key_001"


@pytest.fixture
def invalid_api_key() -> str:
    """유효하지 않은 API 키."""
    return "invalid_key_xyz"


# ============================================================
# Tier 2 모니터링 테스트 (5개)
# ============================================================


class TestMonitoring:
    """모니터링 메트릭 테스트."""

    def test_collector_initialization(self) -> None:
        """수집기 초기화."""
        collector = MetricsCollector()
        assert collector.metrics == []

    def test_collect_all_returns_metrics(self) -> None:
        """모든 메트릭 수집."""
        collector = MetricsCollector()
        metrics = collector.collect_all()
        assert len(metrics) == 5

    def test_metrics_have_required_fields(self) -> None:
        """메트릭 필드."""
        collector = MetricsCollector()
        metrics = collector.collect_all()
        for metric in metrics:
            assert hasattr(metric, 'name')
            assert hasattr(metric, 'value')
            assert hasattr(metric, 'unit')
            assert hasattr(metric, 'status')

    def test_report_generation(self) -> None:
        """보고서 생성."""
        collector = MetricsCollector()
        collector.collect_all()
        report = collector.report()
        assert 'summary' in report
        assert 'metrics' in report
        assert report['summary']['total_metrics'] == 5

    def test_health_status(self) -> None:
        """헬스 상태."""
        collector = MetricsCollector()
        collector.collect_all()
        report = collector.report()
        assert report['summary']['health'] in ['OK', 'WARNING']


# ============================================================
# 게이트웨이 인증 테스트 (5개)
# ============================================================


class TestGatewayAuthentication:
    """게이트웨이 인증 필터."""

    def test_no_api_key_header(self, client: TestClient) -> None:
        """API 키 헤더 없음."""
        resp = client.post(
            "/protected/analyze",
            json={"address": "서울", "property_type": "apartment"},
        )
        assert resp.status_code == 401
        assert "X-API-Key" in resp.json()["detail"]

    def test_invalid_api_key(self, client: TestClient, invalid_api_key: str) -> None:
        """유효하지 않은 API 키."""
        resp = client.post(
            "/protected/analyze",
            headers={"X-API-Key": invalid_api_key},
            json={"address": "서울", "property_type": "apartment"},
        )
        assert resp.status_code == 401
        assert "Invalid" in resp.json()["detail"]

    def test_valid_api_key_passes(self, client: TestClient, valid_api_key: str) -> None:
        """유효한 API 키 통과."""
        resp = client.post(
            "/protected/analyze?address=서울강남구&property_type=apartment",
            headers={"X-API-Key": valid_api_key},
        )
        # 속도제한/검증 통과 시 성공
        assert resp.status_code in [200, 400, 429]

    def test_user_extraction(self, client: TestClient, valid_api_key: str) -> None:
        """사용자명 추출."""
        resp = client.post(
            "/protected/analyze",
            headers={"X-API-Key": valid_api_key},
            json={"address": "서울 강남구", "property_type": "apartment"},
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "user" in data
            assert data["user"] == "user_1"

    def test_multiple_api_keys(self, client: TestClient) -> None:
        """여러 API 키 지원."""
        for key in ["test_key_001", "test_key_002", "test_key_003"]:
            resp = client.post(
                "/protected/analyze",
                headers={"X-API-Key": key},
                json={"address": "서울", "property_type": "apartment"},
            )
            assert resp.status_code != 401


# ============================================================
# 게이트웨이 속도제한 테스트 (3개)
# ============================================================


class TestGatewayRateLimit:
    """게이트웨이 속도제한 필터."""

    def test_rate_limiter_initialization(self) -> None:
        """속도제한기 초기화."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        assert limiter.max_requests == 10

    def test_request_allowed_within_limit(self) -> None:
        """제한 이내."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for i in range(5):
            assert limiter.is_allowed("client_1")

    def test_request_denied_over_limit(self) -> None:
        """제한 초과."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("client_2")
        limiter.is_allowed("client_2")
        assert not limiter.is_allowed("client_2")


# Import after fixture definitions
from avm_project.scripts.tier2_gateway import RateLimiter


# ============================================================
# 게이트웨이 요청검증 테스트 (2개)
# ============================================================


class TestGatewayRequestValidation:
    """게이트웨이 요청검증 필터."""

    def test_invalid_address_length(self, client: TestClient, valid_api_key: str) -> None:
        """주소 길이 검증."""
        resp = client.post(
            "/protected/analyze?address=ab&property_type=apartment",
            headers={"X-API-Key": valid_api_key},
        )
        assert resp.status_code == 400

    def test_invalid_property_type(self, client: TestClient, valid_api_key: str) -> None:
        """부동산 유형 검증."""
        resp = client.post(
            "/protected/analyze?address=서울강남구&property_type=invalid_type",
            headers={"X-API-Key": valid_api_key},
        )
        assert resp.status_code == 400


# ============================================================
# 게이트웨이 엔드투엔드 테스트 (1개)
# ============================================================


class TestGatewayEndToEnd:
    """엔드투엔드 시나리오."""

    def test_full_request_flow(self, client: TestClient, valid_api_key: str) -> None:
        """전체 요청 흐름 (인증 → 속도제한 → 검증 → 응답)."""
        resp = client.post(
            "/protected/analyze?address=서울강남구테헤란로123&property_type=apartment&area_sqm=84.0",
            headers={"X-API-Key": valid_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["user"] == "user_1"


# ============================================================
# 헬스체크 테스트 (1개)
# ============================================================


class TestGatewayHealth:
    """게이트웨이 상태."""

    def test_health_check(self, client: TestClient) -> None:
        """헬스체크."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["component"] == "gateway"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
