"""AVMAgent 단위 테스트 (Anthropic API 모킹)"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.agent.avm_agent import AVMAgent
from app.db.models import Complex, Property, Transaction


@pytest.fixture
def db_session():
    return MagicMock()


@pytest.fixture
def agent(db_session):
    return AVMAgent(api_key="test-key", db=db_session)


def test_tools_defined(agent):
    """4개 tool 정의 확인"""
    assert len(agent.tools) == 4
    names = {t["name"] for t in agent.tools}
    assert "search_property_by_address" in names
    assert "estimate_avm" in names
    assert "find_comparable_sales" in names
    assert "analyze_market_trends" in names


def test_execute_tool_search_property(agent, db_session):
    """search_property_by_address tool 실행"""
    prop = MagicMock(spec=Property)
    prop.id = 1
    prop.address_full = "경기도 화성시 봉담읍 테스트로 1"
    prop.property_type = "아파트"
    prop.building_area = 84.0

    db_session.execute.return_value.scalars.return_value.all.return_value = [prop]

    result = agent._execute_tool(
        "search_property_by_address",
        {"address": "화성시"},
    )

    assert result["count"] == 1
    assert result["properties"][0]["id"] == 1


def test_execute_tool_estimate_avm_not_found(agent, db_session):
    """존재하지 않는 property_id → error 반환"""
    db_session.get.return_value = None

    result = agent._execute_tool("estimate_avm", {"property_id": 9999})
    assert "error" in result


def test_execute_tool_find_comparable_sales(agent, db_session):
    """find_comparable_sales tool 실행"""
    tx = MagicMock(spec=Transaction)
    tx.price = 300_000_000
    tx.report_date = date(2026, 5, 1)
    tx.exclusive_area = 84.0
    complex_mock = MagicMock(spec=Complex)
    complex_mock.address_full = "경기도 화성시 봉담읍"
    tx.complex = complex_mock

    db_session.execute.return_value.scalars.return_value.all.return_value = [tx]

    result = agent._execute_tool(
        "find_comparable_sales",
        {"sido": "경기도", "sigungu": "화성시"},
    )

    assert result["count"] == 1
    assert result["sales"][0]["price"] == 300_000_000


def test_execute_tool_analyze_market_trends(agent, db_session):
    """analyze_market_trends tool 실행"""
    tx = MagicMock(spec=Transaction)
    tx.price = 400_000_000
    tx.report_date = date(2026, 4, 1)

    db_session.execute.return_value.scalars.return_value.all.return_value = [tx]

    result = agent._execute_tool(
        "analyze_market_trends",
        {"sido": "서울특별시", "months": 6},
    )

    assert result["transaction_count"] == 1
    assert result["avg_price"] == 400_000_000


def test_query_end_turn(agent):
    """end_turn 응답 시 텍스트 반환"""
    text_block = MagicMock()
    text_block.text = "테스트 답변입니다."

    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [text_block]

    with patch.object(agent.client.messages, "create", return_value=mock_response):
        result = agent.query("경기도 화성시 아파트 시세는?")

    assert result == "테스트 답변입니다."
