"""KoreaLandAPI 단위 테스트"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.integrations.korea_api import KoreaLandAPI, TransactionRecord

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <거래금액>33,000</거래금액>
        <전용면적>84.97</전용면적>
        <층>5</층>
        <년>2026</년>
        <월>5</월>
        <일>10</일>
        <아파트>테스트아파트</아파트>
        <법정동>봉담읍</법정동>
        <지번>100</지번>
        <건축년도>2005</건축년도>
      </item>
    </items>
    <numOfRows>1</numOfRows>
    <pageNo>1</pageNo>
    <totalCount>1</totalCount>
  </body>
</response>
"""

ERROR_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>99</resultCode>
    <resultMsg>SERVICE ERROR</resultMsg>
  </header>
  <body><items/></body>
</response>
"""


@pytest.fixture
def api():
    return KoreaLandAPI(api_key="test_key")


def test_fetch_apt_transactions_success(api):
    """정상 XML 응답 파싱"""
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_XML
    mock_resp.raise_for_status = MagicMock()

    with patch.object(api.session, "get", return_value=mock_resp):
        records = api.fetch_apt_transactions("41590", 2026, 5)

    assert len(records) == 1
    assert isinstance(records[0], TransactionRecord)
    assert records[0].price_manwon == 33000
    assert records[0].exclusive_area == 84.97


def test_fetch_apt_transactions_error_response(api):
    """에러 응답 코드 시 빈 리스트"""
    mock_resp = MagicMock()
    mock_resp.text = ERROR_XML
    mock_resp.raise_for_status = MagicMock()

    with patch.object(api.session, "get", return_value=mock_resp):
        records = api.fetch_apt_transactions("41590", 2026, 5)

    assert records == []


def test_transaction_record_price_won():
    """price_won 변환 확인"""
    rec = TransactionRecord(
        sgg_code="41590",
        property_type="아파트",
        complex_name="테스트",
        address_dong="봉담읍",
        address_jibun="100",
        contract_year=2026,
        contract_month=5,
        contract_day=10,
        price_manwon=33000,
        exclusive_area=84.97,
        floor=5,
    )
    assert rec.price_won == 330_000_000


def test_transaction_record_key_uniqueness():
    """동일 레코드는 동일 key"""
    base = dict(
        sgg_code="41590",
        property_type="아파트",
        complex_name="테스트",
        address_dong="봉담읍",
        address_jibun="100",
        contract_year=2026,
        contract_month=5,
        contract_day=10,
        price_manwon=33000,
        exclusive_area=84.97,
        floor=5,
    )
    r1 = TransactionRecord(**base)
    r2 = TransactionRecord(**base)
    assert r1.transaction_key == r2.transaction_key


def test_fetch_multi_transactions_returns_list(api):
    """다세대 API 호출 타입 확인"""
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_XML
    mock_resp.raise_for_status = MagicMock()

    with patch.object(api.session, "get", return_value=mock_resp):
        records = api.fetch_multi_transactions("41590", 2026, 5)

    assert isinstance(records, list)
