"""rtech 크롤러 단위 테스트"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.rtech_crawler import ComplexMaster, RtechCrawler


@pytest.fixture
def crawler():
    return RtechCrawler()


def test_fetch_complex_masters_empty_page(crawler):
    """빈 페이지에서 빈 리스트 반환"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body></body></html>"
    mock_resp.raise_for_status = MagicMock()

    with patch.object(crawler.session, "get", return_value=mock_resp):
        result = crawler.fetch_complex_masters(sido="서울특별시")

    assert isinstance(result, list)


def test_fetch_complex_masters_network_error(crawler):
    """네트워크 오류 시 빈 리스트 반환"""
    with patch.object(crawler.session, "get", side_effect=Exception("conn error")):
        result = crawler.fetch_complex_masters(sido="서울특별시")

    assert result == []


def test_complex_master_dataclass():
    """ComplexMaster 데이터클래스 생성"""
    c = ComplexMaster(
        complex_name="테스트단지",
        address_sido="경기도",
        address_sigungu="화성시",
        address_dong="봉담읍",
        build_year=2000,
        total_units=300,
    )
    assert c.complex_name == "테스트단지"
    assert c.total_units == 300


def test_complex_master_auto_code():
    """complex_code 없으면 자동 생성"""
    c = ComplexMaster(
        complex_name="테스트단지",
        address_sido="경기도",
        address_sigungu="화성시",
        address_dong="봉담읍",
        build_year=2000,
        total_units=300,
    )
    assert c.complex_code.startswith("AUTO-")


def test_fetch_complex_masters_all_sidos(crawler):
    """sido=None 시 전체 시도 순회 시도"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body></body></html>"
    mock_resp.raise_for_status = MagicMock()

    with patch.object(crawler.session, "get", return_value=mock_resp):
        result = crawler.fetch_complex_masters()

    assert isinstance(result, list)
