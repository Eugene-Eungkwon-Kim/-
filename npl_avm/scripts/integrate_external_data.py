#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LG 외장하드 데이터 → NPL AVM DB 통합

전략:
  1. rtms_public_csv → transactions 적재
  2. rtech_housing_complexes → complexes 생성
  3. data_go_kr → transactions 적재
  4. vworld_land_rights → Property 토지정보 추가
"""

import os
import sys
import csv
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import hashlib

# 프로젝트 경로
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import SessionLocal, init_db
from app.db.models import Complex, Transaction, Property
from sqlalchemy.exc import IntegrityError

# 로깅
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "data" / "integrate_external_data.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# 외장하드 경로
EXTERNAL_HDD = Path("D:/")
LOAN4U = EXTERNAL_HDD / "loan4u_avm_data"


class RTMSImporter:
    """RTMS 실거래 CSV 적재"""

    def __init__(self, session):
        self.session = session
        self.csv_dir = LOAN4U / "rtms_public_csv"

    def run(self):
        """RTMS CSV 파일 적재"""
        if not self.csv_dir.exists():
            logger.warning(f"RTMS CSV 디렉토리 없음: {self.csv_dir}")
            return {"inserted": 0, "skipped": 0}

        stats = {"inserted": 0, "skipped": 0, "errors": 0}

        # CSV 파일 찾기
        csv_files = list(self.csv_dir.glob("**/*.csv"))
        logger.info(f"RTMS CSV 파일 발견: {len(csv_files)}개")

        for csv_file in csv_files[:5]:  # 처음 5개
            logger.info(f"  적재 중: {csv_file.name}")
            stats_file = self._import_csv(csv_file)
            for k in stats:
                stats[k] += stats_file.get(k, 0)

        logger.info(f"RTMS 적재 완료: 삽입 {stats['inserted']:,} / 중복 {stats['skipped']:,}")
        return stats

    def _import_csv(self, csv_file: Path) -> Dict:
        """단일 CSV 파일 적재"""
        stats = {"inserted": 0, "skipped": 0, "errors": 0}

        try:
            with open(csv_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                logger.debug(f"    {len(rows):,}건 로드")

                for row in rows:
                    try:
                        # 필수 필드 확인
                        complex_name = (row.get("아파트명") or row.get("건물명") or "").strip()
                        if not complex_name:
                            stats["skipped"] += 1
                            continue

                        price_str = str(row.get("거래금액", "")).replace(",", "").strip()
                        if not price_str or price_str == "0":
                            stats["skipped"] += 1
                            continue

                        price = int(float(price_str)) * 10000  # 만원 → 원
                        area = float(row.get("전용면적", 0))
                        if area <= 0:
                            stats["skipped"] += 1
                            continue

                        # 날짜
                        year = int(row.get("거래년도", 0))
                        month = int(row.get("거래월", 0))
                        day = int(row.get("거래일", 0))
                        if not (year and month and day):
                            stats["skipped"] += 1
                            continue

                        # 주소
                        sido = row.get("시도", "").strip()
                        sigungu = row.get("시군구", "").strip()
                        dong = row.get("동", "").strip()

                        # Complex 또는 생성
                        code_raw = f"{sido}|{sigungu}|{complex_name}"
                        auto_code = "RTMS-" + hashlib.md5(code_raw.encode()).hexdigest()[:12]

                        cx = self.session.query(Complex).filter(
                            Complex.complex_code == auto_code
                        ).first()

                        if not cx:
                            cx = Complex(
                                complex_code=auto_code,
                                complex_name=complex_name,
                                property_type="아파트",
                                address_sido=sido,
                                address_sigungu=sigungu,
                                address_dong=dong,
                                source="rtms_csv",
                            )
                            self.session.add(cx)
                            self.session.flush()

                        # Transaction 생성
                        tx_key = f"{sido}|{sigungu}|{complex_name}|{area}|{year}{month:02d}{day:02d}|{price}"
                        tx_hash = hashlib.md5(tx_key.encode()).hexdigest()

                        existing = self.session.query(Transaction).filter(
                            Transaction.transaction_key == tx_hash
                        ).first()

                        if not existing:
                            tx = Transaction(
                                complex_id=cx.id,
                                transaction_key=tx_hash,
                                contract_year=year,
                                contract_month=month,
                                contract_day=day,
                                contract_date=datetime(year, month, day).date(),
                                price=price,
                                price_per_area=round(price / area, 2),
                                exclusive_area=area,
                                floor=int(row.get("층", 0)) if row.get("층") else None,
                                property_type="아파트",
                                sgg_code=row.get("시군구코드", ""),
                                source="rtms_csv",
                            )
                            self.session.add(tx)
                            stats["inserted"] += 1
                        else:
                            stats["skipped"] += 1

                    except Exception as e:
                        logger.debug(f"      행 오류: {e}")
                        stats["errors"] += 1

                # 배치 커밋
                self.session.commit()

        except Exception as e:
            logger.error(f"  CSV 적재 실패 {csv_file.name}: {e}")

        return stats


class DataGoKrImporter:
    """국토부 공공데이터 적재"""

    def __init__(self, session):
        self.session = session
        self.data_dir = LOAN4U / "data_go_kr"

    def run(self):
        """공공데이터 CSV 적재"""
        if not self.data_dir.exists():
            logger.warning(f"공공데이터 디렉토리 없음: {self.data_dir}")
            return {"inserted": 0, "skipped": 0}

        stats = {"inserted": 0, "skipped": 0}

        csv_files = list(self.data_dir.glob("**/*.csv"))
        logger.info(f"공공데이터 CSV 파일 발견: {len(csv_files)}개")

        for csv_file in csv_files[:3]:  # 처음 3개
            logger.info(f"  적재 중: {csv_file.name}")
            # RTMS와 유사하게 처리
            stats_file = RTMSImporter(self.session)._import_csv(csv_file)
            for k in stats:
                stats[k] += stats_file.get(k, 0)

        logger.info(f"공공데이터 적재 완료: 삽입 {stats['inserted']:,}")
        return stats


class RtechComplexImporter:
    """rtech 단지 정보 적재"""

    def __init__(self, session):
        self.session = session
        self.data_dir = LOAN4U / "rtech_housing_complexes"

    def run(self):
        """rtech 단지 데이터 적재"""
        if not self.data_dir.exists():
            logger.warning(f"rtech 디렉토리 없음: {self.data_dir}")
            return {"inserted": 0, "skipped": 0}

        stats = {"inserted": 0, "skipped": 0}

        # JSON/JSONL 파일 찾기
        for json_file in self.data_dir.glob("**/*.json*"):
            logger.info(f"  적재 중: {json_file.name}")
            stats_file = self._import_json(json_file)
            for k in stats:
                stats[k] += stats_file.get(k, 0)

        logger.info(f"rtech 단지 적재 완료: 삽입 {stats['inserted']:,}")
        return stats

    def _import_json(self, json_file: Path) -> Dict:
        """단일 JSON 파일 적재"""
        stats = {"inserted": 0, "skipped": 0}

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                # JSONL 또는 JSON
                if json_file.suffix == ".jsonl":
                    for line in f:
                        if line.strip():
                            self._process_complex_record(json.loads(line), stats)
                else:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            self._process_complex_record(item, stats)
                    else:
                        self._process_complex_record(data, stats)

            self.session.commit()

        except Exception as e:
            logger.error(f"  JSON 적재 실패 {json_file.name}: {e}")

        return stats

    def _process_complex_record(self, record: Dict, stats: Dict):
        """단일 단지 레코드 처리"""
        try:
            complex_code = record.get("complex_id") or record.get("rtech_code") or record.get("code")
            complex_name = record.get("complex_name") or record.get("name")

            if not complex_code or not complex_name:
                return

            existing = self.session.query(Complex).filter(
                Complex.complex_code == complex_code
            ).first()

            if not existing:
                cx = Complex(
                    complex_code=complex_code,
                    complex_name=complex_name,
                    property_type=record.get("type", "아파트"),
                    address_sido=record.get("sido"),
                    address_sigungu=record.get("sigungu"),
                    address_dong=record.get("dong"),
                    build_year=record.get("build_year"),
                    total_units=record.get("total_units"),
                    source="rtech",
                )
                self.session.add(cx)
                stats["inserted"] += 1
            else:
                stats["skipped"] += 1

        except Exception as e:
            logger.debug(f"    레코드 처리 오류: {e}")


def main():
    print("\n" + "="*70)
    print("LG EXTERNAL HDD 데이터 → NPL AVM DB 통합")
    print("="*70)

    # DB 초기화
    init_db()
    session = SessionLocal()

    try:
        # 1단계: RTMS 실거래 CSV
        logger.info("\n[STEP 1] RTMS 실거래 CSV 적재")
        rtms_importer = RTMSImporter(session)
        stats_rtms = rtms_importer.run()

        # 2단계: rtech 단지 정보
        logger.info("\n[STEP 2] rtech 단지 정보 적재")
        rtech_importer = RtechComplexImporter(session)
        stats_rtech = rtech_importer.run()

        # 3단계: 국토부 공공데이터
        logger.info("\n[STEP 3] 국토부 공공데이터 적재")
        dg_importer = DataGoKrImporter(session)
        stats_dg = dg_importer.run()

        # 최종 결과
        total_inserted = (
            stats_rtms.get("inserted", 0)
            + stats_rtech.get("inserted", 0)
            + stats_dg.get("inserted", 0)
        )

        logger.info("\n" + "="*70)
        logger.info(f"통합 완료!")
        logger.info(f"  총 적재: {total_inserted:,}건")
        logger.info(f"  RTMS: {stats_rtms.get('inserted', 0):,}")
        logger.info(f"  rtech: {stats_rtech.get('inserted', 0):,}")
        logger.info(f"  공공API: {stats_dg.get('inserted', 0):,}")
        logger.info("="*70)

    finally:
        session.close()


if __name__ == "__main__":
    main()
