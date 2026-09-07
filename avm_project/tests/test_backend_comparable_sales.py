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
