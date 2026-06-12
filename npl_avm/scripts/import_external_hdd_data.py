"""
LG 외장하드 데이터 → NPL AVM DB 자동 통합

활용 데이터:
  1. RTMS 실거래 CSV → transactions 테이블
  2. 건물 레지스터 → complexes / units 테이블
  3. V-World 토지 권리 → properties 테이블
"""

import os
import sys
import json
import csv
import logging
from pathlib import Path
from datetime import date
from typing import List, Dict, Optional

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal, init_db
from app.db.models import Complex, Transaction, Unit, Property
from sqlalchemy.exc import IntegrityError

# 로깅
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/import_external_hdd.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ─── 경로 설정 ────────────────────────────────────

EXTERNAL_HDD = Path("D:")
LOAN4U_AVM_DATA = EXTERNAL_HDD / "loan4u_avm_data"


class RtmsImporter:
    """RTMS 실거래 데이터 적재"""

    def __init__(self, session):
        self.session = session

    def find_rtms_csv_files(self) -> List[Path]:
        """RTMS CSV 파일 찾기"""
        files = []
        if LOAN4U_AVM_DATA.exists():
            for root, dirs, filenames in os.walk(LOAN4U_AVM_DATA):
                for f in filenames:
                    if "rtms" in f.lower() and f.endswith((".csv", ".jsonl")):
                        files.append(Path(root) / f)
        return files

    def import_rtms_csv(self, csv_path: Path, property_type: str = "아파트") -> dict:
        """RTMS CSV → transactions 테이블 적재"""
        stats = {"inserted": 0, "skipped": 0, "errors": 0}

        try:
            logger.info(f"RTMS CSV 적재 시작: {csv_path.name} ({property_type})")

            # CSV 읽기
            df = pd.read_csv(csv_path, encoding="utf-8", low_memory=False)
            logger.info(f"  {len(df):,}건 거래 로드")

            for idx, row in df.iterrows():
                try:
                    # 필수 컬럼 확인
                    deal_date = self._parse_date(
                        row.get("거래년도"), row.get("거래월"), row.get("거래일")
                    )
                    if not deal_date:
                        stats["skipped"] += 1
                        continue

                    price_str = str(row.get("거래금액", "")).replace(",", "").strip()
                    if not price_str or price_str == "0":
                        stats["skipped"] += 1
                        continue

                    price = int(float(price_str)) * 10000  # 만원 → 원 변환

                    area = float(row.get("전용면적", 0))
                    if area <= 0:
                        stats["skipped"] += 1
                        continue

                    # 단지명
                    complex_name = str(row.get("아파트명", row.get("물건명", ""))).strip()
                    if not complex_name:
                        stats["skipped"] += 1
                        continue

                    # 주소
                    sido = str(row.get("시도", "")).strip()
                    sigungu = str(row.get("시군구", "")).strip()
                    dong = str(row.get("동", "")).strip()

                    # Complex 참조 확보 또는 생성
                    import hashlib
                    code_raw = f"{sido}|{sigungu}|{complex_name}"
                    auto_code = "RTMS-" + hashlib.md5(code_raw.encode()).hexdigest()[:12]

                    complex_obj = self.session.query(Complex).filter(
                        Complex.complex_code == auto_code
                    ).first()

                    if not complex_obj:
                        complex_obj = Complex(
                            complex_code=auto_code,
                            complex_name=complex_name,
                            property_type=property_type,
                            address_sido=sido,
                            address_sigungu=sigungu,
                            address_dong=dong,
                            source="rtms",
                        )
                        self.session.add(complex_obj)
                        self.session.flush()

                    # Transaction 생성
                    tx_key = f"{complex_name}|{area}|{deal_date}|{price}"
                    tx_hash = hashlib.md5(tx_key.encode()).hexdigest()

                    existing = self.session.query(Transaction).filter(
                        Transaction.transaction_key == tx_hash
                    ).first()

                    if not existing:
                        transaction = Transaction(
                            complex_id=complex_obj.id,
                            transaction_key=tx_hash,
                            contract_year=deal_date.year,
                            contract_month=deal_date.month,
                            contract_day=deal_date.day,
                            contract_date=deal_date,
                            price=price,
                            price_per_area=round(price / area, 2),
                            exclusive_area=area,
                            floor=int(row.get("층", 0)) if row.get("층") else None,
                            property_type=property_type,
                            sgg_code=row.get("시군구코드", ""),
                            source="rtms",
                        )
                        self.session.add(transaction)
                        stats["inserted"] += 1
                    else:
                        stats["skipped"] += 1

                    # 배치 커밋
                    if (idx + 1) % 500 == 0:
                        self.session.commit()
                        logger.debug(f"  진행: {idx+1:,}/{len(df):,}")

                except Exception as e:
                    logger.debug(f"  행 {idx} 오류: {e}")
                    stats["errors"] += 1
                    self.session.rollback()

            self.session.commit()
            logger.info(
                f"✓ RTMS CSV 적재 완료: "
                f"삽입 {stats['inserted']:,} / 중복 {stats['skipped']:,} / 오류 {stats['errors']:,}"
            )

        except Exception as e:
            logger.error(f"❌ RTMS CSV 적재 실패: {e}")

        return stats

    @staticmethod
    def _parse_date(year, month, day) -> Optional[date]:
        """날짜 파싱"""
        try:
            y = int(year) if year else None
            m = int(month) if month else None
            d = int(day) if day else None

            if y and m and d and 1 <= m <= 12 and 1 <= d <= 31:
                return date(y, m, d)
        except (ValueError, TypeError):
            pass
        return None


class BuildingRegisterImporter:
    """건물 레지스터 데이터 적재"""

    def __init__(self, session):
        self.session = session

    def find_building_files(self) -> List[Path]:
        """건물 레지스터 파일 찾기"""
        files = []
        if LOAN4U_AVM_DATA.exists():
            for root, dirs, filenames in os.walk(LOAN4U_AVM_DATA):
                for f in filenames:
                    if "building" in f.lower() and f.endswith((".json", ".jsonl")):
                        files.append(Path(root) / f)
        return files

    def import_building_jsonl(self, jsonl_path: Path) -> dict:
        """건물 레지스터 JSONL → complexes/units 적재"""
        stats = {"complexes": 0, "units": 0, "errors": 0}

        try:
            logger.info(f"건물 레지스터 적재 시작: {jsonl_path.name}")

            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f):
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)

                        # 단지 정보
                        complex_code = data.get("complex_id") or data.get("건물코드")
                        complex_name = data.get("complex_name") or data.get("건물명")

                        if not complex_code or not complex_name:
                            continue

                        complex_obj = self.session.query(Complex).filter(
                            Complex.complex_code == complex_code
                        ).first()

                        if not complex_obj:
                            complex_obj = Complex(
                                complex_code=complex_code,
                                complex_name=complex_name,
                                address_sido=data.get("sido"),
                                address_sigungu=data.get("sigungu"),
                                build_year=data.get("build_year"),
                                total_units=data.get("total_units"),
                                source="building_register",
                            )
                            self.session.add(complex_obj)
                            self.session.flush()
                            stats["complexes"] += 1

                        # 호실 정보
                        units = data.get("units", [])
                        for unit_data in units:
                            unit_code = (
                                f"{complex_code}-{unit_data.get('dong')}-"
                                f"{unit_data.get('unit_num')}"
                            )

                            existing_unit = self.session.query(Unit).filter(
                                Unit.unit_code == unit_code
                            ).first()

                            if not existing_unit:
                                unit = Unit(
                                    complex_id=complex_obj.id,
                                    unit_code=unit_code,
                                    dong=unit_data.get("dong"),
                                    floor=unit_data.get("floor"),
                                    unit_num=unit_data.get("unit_num"),
                                    exclusive_area=unit_data.get("exclusive_area"),
                                )
                                self.session.add(unit)
                                stats["units"] += 1

                        # 배치 커밋
                        if (line_idx + 1) % 100 == 0:
                            self.session.commit()
                            logger.debug(f"  진행: {line_idx+1:,}건")

                    except Exception as e:
                        logger.debug(f"  라인 {line_idx} 오류: {e}")
                        stats["errors"] += 1
                        self.session.rollback()

            self.session.commit()
            logger.info(
                f"✓ 건물 레지스터 적재 완료: "
                f"단지 {stats['complexes']:,} / 호실 {stats['units']:,} / 오류 {stats['errors']:,}"
            )

        except Exception as e:
            logger.error(f"❌ 건물 레지스터 적재 실패: {e}")

        return stats


def main():
    print("\n" + "="*60)
    print("🔗 LG 외장하드 데이터 NPL AVM DB 통합")
    print("="*60)

    # DB 초기화
    init_db()
    session = SessionLocal()

    try:
        # 1단계: RTMS 실거래 적재
        logger.info("\n[STEP 1] RTMS 실거래 데이터 적재")
        rtms_importer = RtmsImporter(session)
        rtms_files = rtms_importer.find_rtms_csv_files()

        if rtms_files:
            logger.info(f"발견된 RTMS 파일: {len(rtms_files)}개")
            for rtms_file in rtms_files[:5]:  # 처음 5개만
                rtms_importer.import_rtms_csv(rtms_file)
        else:
            logger.warning("RTMS CSV 파일을 찾을 수 없습니다.")

        # 2단계: 건물 레지스터 적재
        logger.info("\n[STEP 2] 건물 레지스터 데이터 적재")
        building_importer = BuildingRegisterImporter(session)
        building_files = building_importer.find_building_files()

        if building_files:
            logger.info(f"발견된 건물 레지스터 파일: {len(building_files)}개")
            for building_file in building_files[:5]:  # 처음 5개만
                building_importer.import_building_jsonl(building_file)
        else:
            logger.warning("건물 레지스터 파일을 찾을 수 없습니다.")

        # 최종 결과
        logger.info("\n" + "="*60)
        logger.info("✅ 데이터 통합 완료")
        logger.info("="*60)

    finally:
        session.close()


if __name__ == "__main__":
    main()
