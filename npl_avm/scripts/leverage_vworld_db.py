#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V-World 토지 권리 DB (loan4u_avm_data/vworld_land_rights.sqlite)
→ NPL AVM DB 직접 연동

전략:
  1. vworld DB 스키마 분석
  2. 토지 정보 추출
  3. NPL Property와 연결
"""

import os
import sys
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import SessionLocal, engine
from sqlalchemy import inspect as sa_inspect

# 경로
LOAN4U = Path("D:/loan4u_avm_data")
VWORLD_DB = LOAN4U / "vworld_land_rights.sqlite"


def analyze_vworld_schema():
    """V-World DB 스키마 분석"""
    print("\n" + "="*70)
    print("V-World 토지 권리 DB 스키마 분석")
    print("="*70)

    if not VWORLD_DB.exists():
        print(f"❌ DB 파일 없음: {VWORLD_DB}")
        return

    try:
        conn = sqlite3.connect(str(VWORLD_DB))
        cursor = conn.cursor()

        # 테이블 목록
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        print(f"\n발견된 테이블 ({len(tables)}개):")
        for table_name in tables:
            # 레코드 수
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]

            # 컬럼 정보
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            print(f"\n  [{table_name}] {count:,}건")
            for col in columns[:10]:  # 처음 10개 컬럼만
                col_name, col_type = col[1], col[2]
                print(f"    - {col_name}: {col_type}")
            if len(columns) > 10:
                print(f"    ... 외 {len(columns)-10}개")

        conn.close()

    except Exception as e:
        print(f"❌ 분석 오류: {e}")


def check_npl_avm_db():
    """현재 NPL AVM DB 상태 확인"""
    print("\n" + "="*70)
    print("NPL AVM DB 현재 상태")
    print("="*70)

    session = SessionLocal()

    try:
        from app.db.models import Property, Complex, Transaction

        # 현황
        prop_count = session.query(Property).count()
        cx_count = session.query(Complex).count()
        tx_count = session.query(Transaction).count()

        print(f"\nProperties (NPL):   {prop_count:>10,}건")
        print(f"Complexes (단지):    {cx_count:>10,}개")
        print(f"Transactions (거래): {tx_count:>10,}건")

        # 단계 제안
        print("\n" + "="*70)
        print("다음 단계 권장")
        print("="*70)

        if tx_count == 0:
            print("""
Step 2-A: 공공API 실거래 데이터 수집
  - KOREA_API_KEY 설정 → fetch_transactions.py 실행
  - 25M+ 거래 데이터 적재 (12-24시간)

Step 2-B: loan4u_avm_data 내 정제된 exports 폴더 활용
  - D:\\loan4u_avm_data\\exports\\* 파일 탐색
  - 기 정제된 단지/거래 정보 직접 사용

Step 3: V-World 토지 권리 DB 통합
  - vworld_land_rights.sqlite → Property 토지정보 추가
  - 토지 소유자, 권리 정보 연계
            """)

    finally:
        session.close()


def explore_loan4u_exports():
    """loan4u_avm_data 내 exports 폴더 탐색"""
    print("\n" + "="*70)
    print("loan4u_avm_data/exports 폴더 탐색")
    print("="*70)

    exports_dir = LOAN4U / "exports"
    if not exports_dir.exists():
        print(f"❌ 폴더 없음: {exports_dir}")
        return

    print(f"\n발견된 파일 ({len(list(exports_dir.glob('*.*')))}개):")

    for file_path in sorted(exports_dir.glob("*.*"))[:20]:
        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"  - {file_path.name:60} {size_mb:>8.2f} MB")


def main():
    print("\n파이썬 코드 퍼스트 - LG 외장하드 데이터 활용 계획")

    # 1단계: V-World DB 분석
    analyze_vworld_schema()

    # 2단계: NPL AVM DB 상태
    check_npl_avm_db()

    # 3단계: 대안 데이터 탐색
    explore_loan4u_exports()


if __name__ == "__main__":
    main()
