"""app/integrations/rtms_paging.py 검증 + 네 수집기가 페이지·해제 처리를 공유하는지.

네트워크 없이 가짜 세션으로 검증한다. 실제 API 의 페이지 상한·태그명은
라이브 미검증(LIMITATIONS §12) — 여기서 보는 건 "totalCount 가 있으면 끝까지
넘기고, 해제된 거래는 어느 수집기에서든 버린다"는 계약이다.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.integrations.korea_api import KoreaLandAPI
from app.integrations.korea_api_commercial import KoreaCommercialTradeAPI
from app.integrations.korea_api_industrial import KoreaIndustrialTradeAPI
from app.integrations.korea_api_land import KoreaLandTradeAPI
from app.integrations.rtms_paging import fetch_all_pages, is_cancelled


def _xml(items_xml: str, total=None) -> str:
    total_tag = f"<totalCount>{total}</totalCount>" if total is not None else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?><response>'
        "<header><resultCode>00</resultCode><resultMsg>OK</resultMsg></header>"
        f"<body><items>{items_xml}</items>{total_tag}</body></response>"
    )


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        pass


class FakeSession:
    def __init__(self, pages: list) -> None:
        self.pages = pages
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(dict(params))
        return FakeResponse(self.pages[params["pageNo"] - 1])


DATE = "<년>2025</년><월>12</월><일>{d}</일><거래금액>100,000</거래금액>"
COMM_ITEM = "<item><건물명>상가</건물명><법정동>역삼동</법정동><지번>{d}</지번>" + DATE + "</item>"
INDU_ITEM = "<item><건물명>공장</건물명><법정동>수서동</법정동><지번>{d}</지번>" + DATE + "</item>"
LAND_ITEM = "<item><법정동>율현동</법정동><지번>{d}</지번><지목>전</지목><거래면적>100</거래면적>" + DATE + "</item>"
APT_ITEM = ("<item><아파트>래미안</아파트><법정동>대치동</법정동><지번>{d}</지번>"
            "<전용면적>84.9</전용면적><층>3</층>" + DATE + "</item>")


class TestFetchAllPages:
    def test_follows_total_count_across_pages(self):
        pages = [_xml(COMM_ITEM.format(d=1) + COMM_ITEM.format(d=2), total=3),
                 _xml(COMM_ITEM.format(d=3), total=3)]
        session = FakeSession(pages)

        got = fetch_all_pages(session, "http://x", {"a": 1}, label="t", page_size=2)

        assert len(got) == 2
        assert [c["pageNo"] for c in session.calls] == [1, 2]
        assert all(c["numOfRows"] == 2 and c["a"] == 1 for c in session.calls)

    def test_single_page_when_total_count_missing(self):
        session = FakeSession([_xml(COMM_ITEM.format(d=1))])
        assert len(fetch_all_pages(session, "http://x", {}, label="t")) == 1

    def test_stops_on_empty_page_even_if_total_says_more(self):
        session = FakeSession([_xml("", total=5)])
        assert len(fetch_all_pages(session, "http://x", {}, label="t")) == 1

    def test_retries_then_raises_without_leaking_key(self, monkeypatch, caplog):
        class Boom:
            calls = 0

            def get(self, url, params=None, timeout=None):
                Boom.calls += 1
                raise requests.ConnectionError("serviceKey=SECRET123 failed")

        monkeypatch.setattr("app.integrations.rtms_paging.time.sleep", lambda s: None)
        with pytest.raises(RuntimeError, match="최대 재시도"):
            fetch_all_pages(Boom(), "http://x", {}, retry=2, label="t")

        assert Boom.calls == 2
        assert "SECRET123" not in caplog.text


class TestIsCancelled:
    def test_korean_and_english_tags(self):
        assert is_cancelled(ET.fromstring("<item><해제여부>O</해제여부></item>"))
        assert is_cancelled(ET.fromstring("<item><cdealType>o</cdealType></item>"))
        assert not is_cancelled(ET.fromstring("<item><해제여부></해제여부></item>"))
        assert not is_cancelled(ET.fromstring("<item><거래금액>1</거래금액></item>"))


class TestCollectorsShareBehaviour:
    """네 수집기 모두 (1) 페이지를 끝까지 합치고 (2) 해제 거래를 버려야 한다."""

    @staticmethod
    def _pages_for(item_fmt: str) -> list:
        cancelled = item_fmt.format(d=2).replace("</item>", "<해제여부>O</해제여부></item>")
        return [_xml(item_fmt.format(d=1) + cancelled, total=3), _xml(item_fmt.format(d=3), total=3)]

    @pytest.mark.parametrize("make_api,item_fmt", [
        (lambda: KoreaCommercialTradeAPI(api_key="k"), COMM_ITEM),
        (lambda: KoreaIndustrialTradeAPI(api_key="k"), INDU_ITEM),
        (lambda: KoreaLandTradeAPI(api_key="k"), LAND_ITEM),
    ])
    def test_building_and_land_collectors(self, make_api, item_fmt):
        api = make_api()
        api.session = FakeSession(self._pages_for(item_fmt))

        records = api.fetch("11680", 2025, 12)

        assert [r.contract_day for r in records] == [1, 3]

    def test_residential_collector(self):
        api = KoreaLandAPI(api_key="k")
        api.session = FakeSession(self._pages_for(APT_ITEM))

        records = api.fetch_apt_transactions("11680", 2025, 12)

        assert [r.contract_day for r in records] == [1, 3]
