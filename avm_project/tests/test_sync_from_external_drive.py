"""scripts/sync_from_external_drive.py 검증.

실제 외장하드는 이 환경에 연결할 수 없다. 여기서는 (1) 드라이브 루트
후보들 사이에서 알려진 상대경로로 파일을 찾아내는 로직, (2) 진짜
SQLite 파일(onbid_auction_results 스키마와 동일하게 구성)을 읽어
app/db 로 적재하는 경로를 검증한다 — CSV 를 거치지 않고 sqlite3 를
직접 읽는 이 스크립트만의 새 코드 경로다.
"""

import importlib
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from sync_from_external_drive import NPL_DB_SUFFIX, find_file, sync_onbid


class TestFindFile:
    def test_finds_file_at_known_suffix_under_one_of_several_roots(self, tmp_path):
        drive_d = tmp_path / "D"
        drive_e = tmp_path / "E"
        drive_d.mkdir()
        drive_e.mkdir()

        target = drive_e / NPL_DB_SUFFIX
        target.parent.mkdir(parents=True)
        target.write_text("dummy")

        found = find_file([drive_d, drive_e], [NPL_DB_SUFFIX])
        assert found == target

    def test_returns_none_when_not_found_anywhere(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        assert find_file([empty], [NPL_DB_SUFFIX]) is None


class TestSyncOnbid:
    def _make_onbid_sqlite(self, path: Path, rows: list[tuple]) -> None:
        conn = sqlite3.connect(str(path))
        conn.execute("""
            CREATE TABLE onbid_auction_results (
                id INTEGER PRIMARY KEY, address_sido TEXT, address_sigungu TEXT,
                address_raw TEXT, building_area_sqm REAL, appraisal_amount REAL,
                hammer_price REAL, hammer_rate REAL, asset_type_norm TEXT
            )
        """)
        conn.executemany(
            "INSERT INTO onbid_auction_results VALUES (?,?,?,?,?,?,?,?,?)", rows,
        )
        conn.commit()
        conn.close()

    def test_reads_real_sqlite_file_and_imports_without_csv_step(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.sqlite'}")
        import app.db.database as database_module
        importlib.reload(database_module)

        onbid_path = tmp_path / "npl_avm.db"
        self._make_onbid_sqlite(onbid_path, [
            (1001, "서울", "강남구", "서울 강남구 역삼동 1", 84.3,
             600_000_000, 420_000_000, 0.7, "주거용건물"),
        ])

        inserted = sync_onbid(onbid_path)
        assert inserted == 1

        from app.db.models import Property
        db = database_module.SessionLocal()
        try:
            prop = db.query(Property).filter_by(property_serial="onbid-1001").one()
            assert prop.property_type == "주거"
        finally:
            db.close()

    def test_missing_table_reports_zero_instead_of_crashing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app2.sqlite'}")
        import app.db.database as database_module
        importlib.reload(database_module)

        wrong_schema = tmp_path / "not_onbid.db"
        conn = sqlite3.connect(str(wrong_schema))
        conn.execute("CREATE TABLE something_else (x INTEGER)")
        conn.commit()
        conn.close()

        assert sync_onbid(wrong_schema) == 0
