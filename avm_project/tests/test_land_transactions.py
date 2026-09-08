"""토지 실거래 수집(app/integrations/korea_api_land.py) 검증.

공장/상가 테스트와 같은 이유로 합성 XML만 쓴다 — 이 환경은
apis.data.go.kr 아웃바운드가 차단되어 실제 API 응답으로는 검증할 수 없다.
서비스 코드 자체가 미확정 후보라는 점은 모듈 docstring 참고.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.integrations.korea_api_land import KoreaLandTradeAPI

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>00</resultCode><resultMsg>OK</resultMsg></header>
  <body>
    <items>
      <item>
        <법정동>율현동</법정동>
        <지번>123-4</지번>
        <지목>전</지목>
        <용도지역>자연녹지지역</용도지역>
        <거래면적>1,250.5</거래면적>
        <년>2025</년>
        <월>10</월>
        <일>7</일>
        <거래금액>450,000</거래금액>
        <지분거래구분></지분거래구분>
        <해제여부></해제여부>
      </item>
      <item>
        <법정동>세곡동</법정동>
        <지번>77</지번>
        <지목>대</지목>
        <용도지역>제2종일반주거지역</용도지역>
        <거래면적>300</거래면적>
        <년>2025</년>
        <월>10</월>
        <일>15</일>
        <거래금액>900,000</거래금액>
        <해제여부>O</해제여부>
      </item>
    </items>
  </body>
</response>
"""

ENGLISH_TAG_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>000</resultCode><resultMsg>OK</resultMsg></header>
  <body><items><item>
    <umdNm>율현동</umdNm><jibun>9</jibun><jimok>답</jimok><landUse>계획관리지역</landUse>
    <dealArea>800</dealArea><dealYear>2025</dealYear><dealMonth>9</dealMonth><dealDay>2</dealDay>
    <dealAmount>120,000</dealAmount><shareDealingType>지분</shareDealingType>
  </item></items></body>
</response>
"""

ERROR_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>30</resultCode><resultMsg>SERVICE KEY IS NOT REGISTERED</resultMsg></header>
</response>
"""


class TestLandXmlParsing:
    def test_parses_valid_item_and_drops_cancelled_deal(self):
        records = KoreaLandTradeAPI(api_key="dummy")._parse_xml(SAMPLE_XML, sgg_code="11680")

        assert len(records) == 1, "해제여부 'O' 인 두 번째 거래는 버려져야 한다"
        rec = records[0]
        assert rec.address_dong == "율현동"
        assert rec.land_category == "전"
        assert rec.use_zone == "자연녹지지역"
        assert rec.land_area == pytest.approx(1250.5)
        assert rec.price_won == 4_500_000_000
        assert rec.contract_date.isoformat() == "2025-10-07"

    def test_parses_english_tags(self):
        records = KoreaLandTradeAPI(api_key="dummy")._parse_xml(ENGLISH_TAG_XML, sgg_code="11680")

        assert len(records) == 1
        assert records[0].land_category == "답"
        assert records[0].share_deal == "지분"
        assert records[0].land_area == pytest.approx(800.0)

    def test_error_response_raises(self):
        with pytest.raises(RuntimeError, match="SERVICE KEY"):
            KoreaLandTradeAPI(api_key="dummy")._parse_xml(ERROR_XML, sgg_code="11680")


class TestLandIngest:
    def test_ingest_maps_into_comparable_sale_and_dedupes(self, tmp_path, monkeypatch):
        import importlib
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'land.sqlite'}")
        import app.db.database as database_module
        importlib.reload(database_module)
        database_module.init_db()
        db = database_module.SessionLocal()

        from app.integrations.db_ingest import bulk_ingest_land_transactions

        records = KoreaLandTradeAPI(api_key="dummy")._parse_xml(SAMPLE_XML, sgg_code="11680")

        stats = bulk_ingest_land_transactions(db, records)
        assert stats == {"inserted": 1, "skipped": 0, "errors": 0}

        from app.db.models import ComparableSale
        row = db.query(ComparableSale).one()
        assert row.property_type == "토지"
        assert row.use_zone == "자연녹지지역"
        assert row.land_area == pytest.approx(1250.5)
        assert row.building_area is None
        assert row.trade_amount == 4_500_000_000
        assert row.note == "전"

        stats2 = bulk_ingest_land_transactions(db, records)
        assert stats2 == {"inserted": 0, "skipped": 1, "errors": 0}
        db.close()
