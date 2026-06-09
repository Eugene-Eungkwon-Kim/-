"""rtech 크롤러 단위 테스트"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.rtech_crawler import ComplexMeta, RtechCrawler, TransactionDTO, UnitMeta


@pytest.fixture
def mock_session():
    session = MagicMock()
    return session


@pytest.fixture
def crawler(mock_session):
    return RtechCrawler(mock_session)


@pytest.mark.asyncio
async def test_fetch_complex_masters_empty_page(crawler):
    """빈 페이지에서 루프 탈출 확인"""
    mock_resp = AsyncMock()
    mock_resp.text = AsyncMock(return_value="<html><body></body></html>")
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    crawler.session.get = MagicMock(return_value=mock_resp)

    result = await crawler.fetch_complex_masters()
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_fetch_complex_masters_parses_rows(crawler):
    """HTML 파싱 시 ComplexMeta 생성 확인"""
    html = """
    <html><body>
      <tr class="list-item">
        <td class="code">12345</td>
        <td class="name">테스트단지</td>
        <td class="address">경기도 화성시 봉담읍</td>
        <td class="year">2000</td>
        <td class="units">300</td>
      </tr>
    </body></html>
    """
    mock_resp = AsyncMock()
    mock_resp.text = AsyncMock(side_effect=[html, "<html></html>"] * 20)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    crawler.session.get = MagicMock(return_value=mock_resp)

    result = await crawler.fetch_complex_masters()
    # 각 시도에서 1개씩 파싱 가능
    assert len(result) >= 1
    assert all(isinstance(c, ComplexMeta) for c in result)


@pytest.mark.asyncio
async def test_fetch_complex_units_returns_list(crawler):
    """호실 정보 수집 결과 타입 확인"""
    mock_resp = AsyncMock()
    mock_resp.text = AsyncMock(return_value="<html><body></body></html>")
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    crawler.session.get = MagicMock(return_value=mock_resp)

    result = await crawler.fetch_complex_units("99999")
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_fetch_recent_transactions_returns_list(crawler):
    """거래 수집 결과 타입 확인"""
    mock_resp = AsyncMock()
    mock_resp.text = AsyncMock(return_value="<html><body></body></html>")
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    crawler.session.get = MagicMock(return_value=mock_resp)

    result = await crawler.fetch_recent_transactions("99999", months=3)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_fetch_complex_masters_handles_network_error(crawler):
    """네트워크 오류 시 빈 리스트 반환 (중단 없음)"""
    crawler.session.get = MagicMock(side_effect=Exception("connection error"))

    result = await crawler.fetch_complex_masters()
    assert result == []
