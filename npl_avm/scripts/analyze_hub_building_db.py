#!/usr/bin/env python3
# coding: utf-8

import sqlite3
import sys
from pathlib import Path

HUB_DB = Path("D:/hub_building_register.sqlite")


def analyze_hub_db():
    """hub_building_register.sqlite 스키마 분석"""

    print("\n" + "="*70)
    print("HUB Building Register DB Analysis")
    print("="*70)

    if not HUB_DB.exists():
        print(f"\nERROR: DB file not found: {HUB_DB}")
        return False

    try:
        conn = sqlite3.connect(str(HUB_DB))
        cursor = conn.cursor()

        # 1. 테이블 목록
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        print(f"\nDatabase: {HUB_DB.name}")
        print(f"Tables found: {len(tables)}\n")

        for table_name in tables:
            # 레코드 수
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]

            # 컬럼 정보
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            print(f"[{table_name}] {count:,} records, {len(columns)} columns")

            for col in columns[:15]:
                col_name, col_type = col[1], col[2]
                print(f"  ├─ {col_name:30} {col_type}")

            if len(columns) > 15:
                print(f"  └─ ... ({len(columns)-15} more columns)")
            print()

        # 2. NPL 매핑 가능 필드 식별
        print("="*70)
        print("Possible Mapping Fields for NPL Integration")
        print("="*70)

        mapping_keywords = [
            'address', 'sido', 'sigungu', 'dong', 'complex', 'unit', 'area',
            'building', 'property', 'apartment', 'name', 'code'
        ]

        print("\nSearching for mapping-compatible columns...\n")

        for table_name in tables:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            matching_cols = [
                col[1] for col in columns
                if any(kw in col[1].lower() for kw in mapping_keywords)
            ]

            if matching_cols:
                print(f"[{table_name}]")
                for col in matching_cols:
                    print(f"  ├─ {col}")
                print()

        conn.close()
        return True

    except Exception as e:
        print(f"\nERROR: Analysis failed - {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = analyze_hub_db()
    sys.exit(0 if success else 1)
