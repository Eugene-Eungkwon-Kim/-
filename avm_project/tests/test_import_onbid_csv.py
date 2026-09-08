"""scripts/import_onbid_csv.py 검증.

실제 npl_avm.db 는 외장하드에 있어 이 환경에서 접근할 수 없다. 여기서는
phase7_grounded_avm.py 가 실제로 쓰는 쿼리
(SELECT id, address_sido, address_sigungu, address_raw, building_area_sqm,
appraisal_amount, hammer_price, hammer_rate, asset_type_norm
FROM onbid_auction_results)와 같은 모양의 합성 CSV로 '가져오기 로직'만
검증한다.
"""

import csv
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

FIELDNAMES = ["id", "address_sido", "address_sigungu", "address_raw",
             "building_area_sqm", "appraisal_amount", "hammer_price",
             "hammer_rate", "asset_type_norm"]


def _write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'onbid_test.sqlite'}")
    import app.db.database as database_module
    importlib.reload(database_module)
    database_module.init_db()
    session = database_module.SessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestOnbidImport:
    def test_imports_residential_row_with_correct_type_mapping(self, db_session):
        from scripts.import_onbid_csv import import_rows

        rows = [{
            "id": "1001", "address_sido": "서울", "address_sigungu": "강남구",
            "address_raw": "서울 강남구 역삼동 123", "building_area_sqm": "84.3",
            "appraisal_amount": "600000000", "hammer_price": "420000000",
            "hammer_rate": "0.7", "asset_type_norm": "주거용건물",
        }]

        stats = import_rows(db_session, rows)
        assert stats == {"inserted": 1, "skipped": 0, "errors": 0}

        from app.db.models import Property, Appraisal, Auction
        prop = db_session.query(Property).filter_by(property_serial="onbid-1001").one()
        assert prop.property_type == "주거"  # asset_type_norm 매핑 확인
        assert prop.address_sido == "서울"

        appr = db_session.query(Appraisal).filter_by(property_id=prop.id).one()
        assert appr.total_value == pytest.approx(600_000_000)

        auction = db_session.query(Auction).filter_by(property_id=prop.id).one()
        assert auction.hammer_price == pytest.approx(420_000_000)
        assert auction.final_result == "낙찰"

    def test_reimporting_same_id_is_deduplicated(self, db_session):
        from scripts.import_onbid_csv import import_rows

        row = {
            "id": "2002", "address_sido": "부산", "address_sigungu": "해운대구",
            "address_raw": "부산 해운대구", "building_area_sqm": "50",
            "appraisal_amount": "300000000", "hammer_price": "", "hammer_rate": "",
            "asset_type_norm": "상업용건물",
        }

        first = import_rows(db_session, [row])
        assert first == {"inserted": 1, "skipped": 0, "errors": 0}

        second = import_rows(db_session, [row])
        assert second == {"inserted": 0, "skipped": 1, "errors": 0}

    def test_row_without_hammer_price_still_imports_property_and_appraisal(self, db_session):
        """유찰(낙찰가 없음) 사례도 비교사례로서 감정가 정보는 가치가 있다."""
        from scripts.import_onbid_csv import import_rows

        row = {
            "id": "3003", "address_sido": "대구", "address_sigungu": "수성구",
            "address_raw": "대구 수성구", "building_area_sqm": "70",
            "appraisal_amount": "400000000", "hammer_price": "", "hammer_rate": "",
            "asset_type_norm": "토지",
        }
        stats = import_rows(db_session, [row])
        assert stats["inserted"] == 1

        from app.db.models import Property, Auction
        prop = db_session.query(Property).filter_by(property_serial="onbid-3003").one()
        assert prop.property_type == "토지"
        assert db_session.query(Auction).filter_by(property_id=prop.id).count() == 0

    def test_row_missing_appraisal_amount_is_skipped_not_errored(self, db_session):
        from scripts.import_onbid_csv import import_rows

        row = {
            "id": "4004", "address_sido": "서울", "address_sigungu": "종로구",
            "address_raw": "서울 종로구", "building_area_sqm": "60",
            "appraisal_amount": "", "hammer_price": "", "hammer_rate": "",
            "asset_type_norm": "주거용건물",
        }
        stats = import_rows(db_session, [row])
        assert stats == {"inserted": 0, "skipped": 1, "errors": 0}

    def test_imported_data_becomes_a_real_comparable_via_engine_estimate(self, db_session):
        """OnBid 로 들여온 데이터가 기존 AVM 비교사례 검색에 실제로 잡히는지 —
        이게 이 임포터의 존재 이유다: 연결 작업 없이 자동으로 인식돼야 한다."""
        from scripts.import_onbid_csv import import_rows
        from app.avm import engine as avm

        rows = [{
            "id": "5005", "address_sido": "서울", "address_sigungu": "강남구",
            "address_raw": "서울 강남구 대치동", "building_area_sqm": "84.0",
            "appraisal_amount": "550000000", "hammer_price": "400000000",
            "hammer_rate": "0.73", "asset_type_norm": "주거용건물",
        }]
        import_rows(db_session, rows)

        result = avm.estimate(db=db_session, address_sido="서울",
                              address_sigungu="강남구", property_type="주거")

        assert result.comparable_count == 1
        assert result.comparables[0].hammer_price == pytest.approx(400_000_000)
