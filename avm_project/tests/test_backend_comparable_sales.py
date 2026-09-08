"""backend/main.py 의 실거래 수집 데이터 연동 엔드포인트 검증.

기존 /data/quality, /data/price-distribution, /data/region-distribution
은 고정 예시값을 돌려주는 데모용 엔드포인트였다(관리자 화면이 실제
수집 현황을 보여주지 못했다). 이 테스트는 새로 추가한
/data/comparable-sales/* 가 app/db 에 실제로 적재된 데이터를 정확히
반영하는지 검증한다 — 수집 파이프라인(scripts/fetch_transactions_parallel.py
등)이 넣은 데이터가 관리자 화면까지 이어지는 경로다.
"""

import importlib
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test_backend.sqlite'}")
    import app.db.database as database_module
    importlib.reload(database_module)
    database_module.init_db()
    session = database_module.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def auth_headers():
    from fastapi.testclient import TestClient
    import backend.main as bm

    client = TestClient(bm.app)
    r = client.post("/auth/login", params={"email": "admin@avm.com", "password": "demo123"})
    token = r.json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}


class TestComparableSalesEndpoints:
    def test_summary_reflects_ingested_rows(self, db_session, auth_headers):
        from app.db.models import ComparableSale

        db_session.add(ComparableSale(
            subject_property_serial="11680-래미안", case_index=1,
            address_sido="서울", address_sigungu="강남구", property_type="아파트",
            building_area=84.5, trade_date=date(2025, 12, 1), trade_amount=1_200_000_000,
        ))
        db_session.add(ComparableSale(
            subject_property_serial="11710-잠실엘스", case_index=1,
            address_sido="서울", address_sigungu="송파구", property_type="아파트",
            building_area=100.0, trade_date=date(2025, 12, 5), trade_amount=1_800_000_000,
        ))
        db_session.commit()

        client, headers = auth_headers
        r = client.get("/data/comparable-sales/summary", headers=headers)

        assert r.status_code == 200
        body = r.json()
        assert body["total_rows"] == 2
        assert {"name": "아파트", "count": 2} in body["by_property_type"]
        assert {"name": "서울", "count": 2} in body["by_region"]

    def test_summary_aggregates_every_property_type_without_code_changes(self, db_session, auth_headers):
        """관리자 화면 연결이 '아파트 전용'이 아니라 자산유형 무관 일반
        로직임을 확인한다 — 공장·상가·토지 데이터가 들어오면 이 엔드포인트를
        고치지 않아도 자동으로 집계에 잡혀야 한다."""
        from app.db.models import ComparableSale

        seed = [
            ("서울", "강남구", "아파트", 1_200_000_000),
            ("서울", "송파구", "상가", 800_000_000),
            ("서울", "구로구", "공장창고", 2_000_000_000),
            ("경기도", "화성시", "토지", 900_000_000),
        ]
        for sido, sigungu, ptype, amount in seed:
            db_session.add(ComparableSale(
                case_index=1, address_sido=sido, address_sigungu=sigungu,
                address_full=f"{sido} {sigungu}", property_type=ptype,
                building_area=100.0, trade_date=date(2025, 12, 1), trade_amount=amount,
            ))
        db_session.commit()

        client, headers = auth_headers
        r = client.get("/data/comparable-sales/summary", headers=headers)

        assert r.status_code == 200
        body = r.json()
        assert body["total_rows"] == 4
        types = {row["name"] for row in body["by_property_type"]}
        assert types == {"아파트", "상가", "공장창고", "토지"}
        regions = {row["name"] for row in body["by_region"]}
        assert regions == {"서울", "경기도"}

    def test_price_distribution_buckets_are_computed_not_hardcoded(self, db_session, auth_headers):
        from app.db.models import ComparableSale

        db_session.add(ComparableSale(
            case_index=1, property_type="아파트", trade_amount=1_200_000_000,
            trade_date=date(2025, 12, 1),
        ))
        db_session.add(ComparableSale(
            case_index=1, property_type="아파트", trade_amount=1_800_000_000,
            trade_date=date(2025, 12, 5),
        ))
        db_session.commit()

        client, headers = auth_headers
        r = client.get("/data/comparable-sales/price-distribution", headers=headers)

        assert r.status_code == 200
        buckets = {row["range"]: row["count"] for row in r.json()["data"]}
        assert buckets["10-15억"] == 1
        assert buckets["15-20억"] == 1
        assert buckets["1-5억"] == 0

    def test_summary_on_empty_db_returns_zero_not_fake_demo_numbers(self, db_session, auth_headers):
        client, headers = auth_headers
        r = client.get("/data/comparable-sales/summary", headers=headers)

        assert r.status_code == 200
        assert r.json()["total_rows"] == 0

    def test_requires_auth(self):
        from fastapi.testclient import TestClient
        import backend.main as bm

        client = TestClient(bm.app)
        r = client.get("/data/comparable-sales/summary")
        assert r.status_code == 401

    def test_region_distribution_counts_by_sigungu(self, db_session, auth_headers):
        from app.db.models import ComparableSale

        for sgg in ("강남구", "강남구", "송파구"):
            db_session.add(ComparableSale(
                case_index=1, address_sido="서울", address_sigungu=sgg, property_type="아파트",
                building_area=84.0, trade_date=date(2025, 12, 1), trade_amount=1_000_000_000,
            ))
        db_session.commit()

        client, headers = auth_headers
        r = client.get("/data/comparable-sales/region-distribution", headers=headers)

        assert r.status_code == 200
        assert r.json()["data"] == [{"name": "강남구", "value": 2}, {"name": "송파구", "value": 1}]

    def test_quality_counts_missing_and_outliers_from_db(self, db_session, auth_headers):
        """고정값 0.992 가 아니라 실제 결측·이상치로 점수를 낸다."""
        from app.db.models import ComparableSale

        rows = [
            dict(building_area=84.0, trade_amount=1_000_000_000),   # 정상
            dict(building_area=None, land_area=None, trade_amount=500_000_000),  # 면적 결측
            dict(building_area=84.0, trade_amount=1_000),           # ㎡당 12원 → 이상치
            dict(land_area=1000.0, trade_amount=900_000_000),        # 토지: 대지면적 기준 정상
        ]
        for extra in rows:
            db_session.add(ComparableSale(case_index=1, property_type="아파트",
                                          trade_date=date(2025, 12, 1), **extra))
        db_session.commit()

        client, headers = auth_headers
        body = client.get("/data/comparable-sales/quality", headers=headers).json()

        assert body["total_rows"] == 4
        assert body["missing_values"] == 1
        assert body["outliers"] == 1
        assert body["quality_score"] == 0.5
        assert body["status"] == "needs_review"

    def test_quality_on_empty_db_reports_no_data(self, db_session, auth_headers):
        client, headers = auth_headers
        body = client.get("/data/comparable-sales/quality", headers=headers).json()
        assert body == {
            "total_rows": 0, "missing_values": 0, "missing_percentage": 0.0,
            "outliers": 0, "outlier_percentage": 0.0, "quality_score": 0.0, "status": "no_data",
        }

    def test_legacy_fixed_value_endpoints_are_marked_deprecated(self):
        import backend.main as bm

        deprecated = {r.path for r in bm.app.routes if getattr(r, "deprecated", False)}
        assert {"/data/quality", "/data/price-distribution", "/data/region-distribution"} <= deprecated
