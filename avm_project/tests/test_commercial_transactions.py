"""상업업무용 실거래 수집(app/integrations/korea_api_commercial.py) 검증.

공장/창고 테스트(test_industrial_transactions.py)와 같은 이유로 합성
XML만 쓴다 — 이 환경은 apis.data.go.kr 아웃바운드가 차단되어 있어 실제
API 응답으로는 검증할 수 없다.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.integrations.korea_api_commercial import KoreaCommercialTradeAPI

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>00</resultCode><resultMsg>OK</resultMsg></header>
  <body>
    <items>
      <item>
        <건물명>테스트상가빌딩</건물명>
        <법정동>역삼동</법정동>
        <지번>50-3</지번>
        <년>2025</년>
        <월>11</월>
        <일>20</일>
        <거래금액>820,000</거래금액>
        <대지면적>300.0</대지면적>
        <건물면적>950.0</건물면적>
      </item>
    </items>
  </body>
</response>
"""

ERROR_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>30</resultCode><resultMsg>SERVICE KEY IS NOT REGISTERED</resultMsg></header>
</response>
"""


class TestCommercialXmlParsing:
    def test_parses_valid_item(self):
        api = KoreaCommercialTradeAPI(api_key="dummy")
        records = api._parse_xml(SAMPLE_XML, sgg_code="11680")

        assert len(records) == 1
        rec = records[0]
        assert rec.building_name == "테스트상가빌딩"
        assert rec.price_won == 8_200_000_000
        assert rec.land_area == pytest.approx(300.0)
        assert rec.building_area == pytest.approx(950.0)

    def test_error_response_raises(self):
        api = KoreaCommercialTradeAPI(api_key="dummy")
        with pytest.raises(RuntimeError, match="SERVICE KEY"):
            api._parse_xml(ERROR_XML, sgg_code="11680")


class TestCommercialIngest:
    def test_ingest_maps_into_comparable_sale_and_dedupes(self, tmp_path, monkeypatch):
        import importlib
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'commercial.sqlite'}")
        import app.db.database as database_module
        importlib.reload(database_module)
        database_module.init_db()
        db = database_module.SessionLocal()

        from app.integrations.db_ingest import bulk_ingest_commercial_transactions

        api = KoreaCommercialTradeAPI(api_key="dummy")
        records = api._parse_xml(SAMPLE_XML, sgg_code="11680")

        stats = bulk_ingest_commercial_transactions(db, records)
        assert stats == {"inserted": 1, "skipped": 0, "errors": 0}

        from app.db.models import ComparableSale
        row = db.query(ComparableSale).one()
        assert row.property_type == "상가"
        assert row.trade_amount == 8_200_000_000

        stats2 = bulk_ingest_commercial_transactions(db, records)
        assert stats2 == {"inserted": 0, "skipped": 1, "errors": 0}
        db.close()
