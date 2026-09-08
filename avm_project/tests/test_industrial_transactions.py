"""공장/창고 실거래 수집(app/integrations/korea_api_industrial.py) 검증.

이 환경은 apis.data.go.kr 아웃바운드가 조직 정책으로 차단되어 있어(egress
403) 실제 API 응답으로는 검증할 수 없다. 여기서는 모듈 docstring에 적힌
'추정 태그명'을 반영한 합성 XML로 파싱 로직 자체의 정합성만 검증한다 —
실제 정부 API가 정말 이 태그명을 쓰는지는 이 테스트로 증명되지 않는다.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.integrations.korea_api_industrial import KoreaIndustrialTradeAPI

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>00</resultCode><resultMsg>OK</resultMsg></header>
  <body>
    <items>
      <item>
        <건물명>테스트물류센터</건물명>
        <법정동>가양동</법정동>
        <지번>100-1</지번>
        <년>2025</년>
        <월>12</월>
        <일>15</일>
        <거래금액>350,000</거래금액>
        <대지면적>1200.5</대지면적>
        <건물면적>2400.0</건물면적>
      </item>
      <item>
        <!-- 거래금액 없음 -> 스킵되어야 함 -->
        <건물명>불완전레코드</건물명>
        <법정동>가양동</법정동>
        <지번>200</지번>
        <년>2025</년>
        <월>12</월>
        <일>1</일>
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


class TestIndustrialXmlParsing:
    def test_parses_valid_item_and_converts_units(self):
        api = KoreaIndustrialTradeAPI(api_key="dummy")
        records = api._parse_xml(SAMPLE_XML, sgg_code="11680")

        assert len(records) == 1
        rec = records[0]
        assert rec.building_name == "테스트물류센터"
        assert rec.price_manwon == 350000
        assert rec.price_won == 3_500_000_000
        assert rec.land_area == pytest.approx(1200.5)
        assert rec.building_area == pytest.approx(2400.0)
        assert rec.contract_date.year == 2025 and rec.contract_date.month == 12

    def test_skips_item_missing_required_price(self):
        api = KoreaIndustrialTradeAPI(api_key="dummy")
        records = api._parse_xml(SAMPLE_XML, sgg_code="11680")
        names = [r.building_name for r in records]
        assert "불완전레코드" not in names

    def test_missing_area_fields_do_not_crash(self):
        xml_without_area = SAMPLE_XML.replace("<대지면적>1200.5</대지면적>", "") \
                                     .replace("<건물면적>2400.0</건물면적>", "")
        api = KoreaIndustrialTradeAPI(api_key="dummy")
        records = api._parse_xml(xml_without_area, sgg_code="11680")

        assert len(records) == 1
        assert records[0].land_area is None
        assert records[0].building_area is None

    def test_error_response_raises_with_message(self):
        api = KoreaIndustrialTradeAPI(api_key="dummy")
        with pytest.raises(RuntimeError, match="SERVICE KEY"):
            api._parse_xml(ERROR_XML, sgg_code="11680")


class TestIndustrialIngest:
    def test_ingest_maps_into_comparable_sale(self, tmp_path, monkeypatch):
        import importlib
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'industrial.sqlite'}")
        import app.db.database as database_module
        importlib.reload(database_module)
        database_module.init_db()
        db = database_module.SessionLocal()

        from app.integrations.db_ingest import bulk_ingest_industrial_transactions
        from app.integrations.korea_api_industrial import KoreaIndustrialTradeAPI

        api = KoreaIndustrialTradeAPI(api_key="dummy")
        records = api._parse_xml(SAMPLE_XML, sgg_code="11680")

        stats = bulk_ingest_industrial_transactions(db, records)
        assert stats == {"inserted": 1, "skipped": 0, "errors": 0}

        from app.db.models import ComparableSale
        row = db.query(ComparableSale).one()
        assert row.property_type == "공장창고"
        assert row.address_sido == "서울"
        assert row.address_sigungu == "강남구"
        assert row.land_area == pytest.approx(1200.5)
        assert row.trade_amount == 3_500_000_000

        # 재적재해도 중복되지 않아야 한다
        stats2 = bulk_ingest_industrial_transactions(db, records)
        assert stats2 == {"inserted": 0, "skipped": 1, "errors": 0}
        db.close()
