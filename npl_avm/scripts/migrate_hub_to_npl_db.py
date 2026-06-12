#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal, init_db
from app.db.models import Complex, Unit

HUB_DB = Path("D:/hub_building_register.sqlite")
NPL_DB = Path("D:/NPL전례/avm_project/data/npl_avm.db")


def backup_npl_db():
    """NPL DB 백업"""
    if NPL_DB.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = NPL_DB.parent / f"npl_avm_backup_{timestamp}.db"
        import shutil
        shutil.copy2(NPL_DB, backup_path)
        print(f"Backup created: {backup_path.name}")
        return backup_path
    return None


def migrate_hub_to_npl():
    """hub_building_register → npl_avm DB 마이그레이션"""

    print("\n" + "="*70)
    print("HUB Building Register → NPL AVM DB Migration")
    print("="*70)

    # 1. 백업
    print("\n[STEP 1] Creating backup...")
    backup = backup_npl_db()

    # 2. NPL DB 초기화
    print("[STEP 2] Initializing NPL DB...")
    init_db()

    # 3. hub_building 연결
    if not HUB_DB.exists():
        print(f"\nERROR: HUB DB not found: {HUB_DB}")
        return False

    print("\n[STEP 3] Reading HUB Building Register...")

    try:
        hub_conn = sqlite3.connect(str(HUB_DB))
        hub_cursor = hub_conn.cursor()

        # hub_building 테이블 찾기
        hub_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        hub_tables = [row[0] for row in hub_cursor.fetchall()]

        print(f"  Tables in HUB DB: {hub_tables}")

        # 주로 사용할 테이블 식별 (예: buildings, units, properties)
        main_table = None
        for table in ['buildings', 'units', 'properties', 'complexes', 'buildings_registry']:
            if table in hub_tables:
                main_table = table
                break

        if not main_table:
            main_table = hub_tables[0] if hub_tables else None

        if not main_table:
            print("\nERROR: No suitable table found in HUB DB")
            return False

        print(f"  Using table: {main_table}")

        # 데이터 마이그레이션
        print(f"\n[STEP 4] Migrating {main_table} data...")

        hub_cursor.execute(f"SELECT COUNT(*) FROM {main_table}")
        total_count = hub_cursor.fetchone()[0]

        print(f"  Records to migrate: {total_count:,}")

        # NPL 세션
        session = SessionLocal()
        stats = {"inserted": 0, "skipped": 0, "errors": 0}

        try:
            # hub_building 데이터 읽기
            hub_cursor.execute(f"SELECT * FROM {main_table} LIMIT 5")
            columns = [desc[0] for desc in hub_cursor.description]

            print(f"  Columns: {columns[:10]}...")  # 처음 10개만

            hub_cursor.execute(f"SELECT * FROM {main_table}")

            batch_size = 500
            for idx, row in enumerate(hub_cursor.fetchall()):
                try:
                    # 데이터 매핑 (hub → npl)
                    # 이 부분은 actual 스키마에 맞게 커스터마이징 필요

                    # 간단한 예: complex 생성
                    complex_name = row[1] if len(row) > 1 else f"Complex_{idx}"

                    cx = Complex(
                        complex_code=f"HUB-{idx:06d}",
                        complex_name=str(complex_name)[:200],
                        property_type="apartment",
                        source="hub_building",
                    )
                    session.add(cx)
                    stats["inserted"] += 1

                    if (idx + 1) % batch_size == 0:
                        session.commit()
                        print(f"  Progress: {idx+1:,}/{total_count:,}")

                except Exception as e:
                    print(f"  Error at row {idx}: {e}")
                    stats["errors"] += 1
                    session.rollback()

            session.commit()

        finally:
            session.close()

        hub_conn.close()

        print(f"\n[STEP 5] Migration Results")
        print(f"  Inserted: {stats['inserted']:,}")
        print(f"  Skipped: {stats['skipped']:,}")
        print(f"  Errors: {stats['errors']:,}")

        print("\n" + "="*70)
        print("Migration completed successfully!")
        print("="*70)

        return True

    except Exception as e:
        print(f"\nERROR: Migration failed - {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = migrate_hub_to_npl()
    sys.exit(0 if success else 1)
