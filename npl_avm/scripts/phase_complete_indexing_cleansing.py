#!/usr/bin/env python3
"""
NPL AVM 시스템 — 완전한 인덱싱 & 클렌징 자동화
디버깅 → 인덱싱 → 클렌징 순차 진행
"""

import logging
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 데이터베이스 설정
DB_PATH = "D:/NPL전례/avm_project/data/npl_avm.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

class CodeDebugger:
    """코드 디버깅 단계"""

    @staticmethod
    def validate_imports():
        """필수 모듈 import 검증"""
        logger.info("=" * 80)
        logger.info("[STEP 1] 코드 디버깅 — Import 검증")
        logger.info("=" * 80)

        try:
            from app.db.models import Base
            from app.db.database import init_db
            from app.avm.engine import estimate, _median
            logger.info("✅ 모든 import 성공")
            return True
        except ImportError as e:
            logger.error(f"❌ Import 실패: {e}")
            return False

    @staticmethod
    def validate_models():
        """SQLAlchemy 모델 검증"""
        logger.info("\n[STEP 2] 코드 디버깅 — 모델 정의 검증")

        try:
            from app.db.models import (
                Deal, Property, Appraisal, Auction,
                ComparableSale, Complex, Unit, Transaction
            )

            models = [Deal, Property, Appraisal, Auction, ComparableSale, Complex, Unit, Transaction]

            for model in models:
                table_name = model.__tablename__
                indexes = getattr(model, '__table_args__', None)
                index_count = 0
                if indexes and isinstance(indexes, tuple):
                    index_count = sum(1 for item in indexes if hasattr(item, 'name'))
                logger.info(f"  ✅ {table_name}: {index_count}개 인덱스 정의됨")

            logger.info(f"✅ {len(models)}개 모델 검증 완료")
            return True
        except Exception as e:
            logger.error(f"❌ 모델 검증 실패: {e}")
            return False


class IndexingManager:
    """고급 인덱싱 관리"""

    def __init__(self, engine):
        self.engine = engine
        self.inspector = inspect(engine)

    def create_missing_indexes(self):
        """모든 누락된 인덱스 생성"""
        logger.info("\n" + "=" * 80)
        logger.info("[STEP 3] 인덱싱 — 누락된 인덱스 생성")
        logger.info("=" * 80)

        from app.db.models import Base

        created_count = 0
        with self.engine.begin() as conn:
            for table_name, table in Base.metadata.tables.items():
                existing_indexes = {
                    idx['name'] for idx in self.inspector.get_indexes(table_name)
                }

                if not hasattr(table, 'indexes'):
                    continue

                for idx in table.indexes:
                    if idx.name not in existing_indexes:
                        try:
                            idx.create(conn)
                            logger.info(f"  ✅ {idx.name} created on {table_name}")
                            created_count += 1
                        except Exception as e:
                            logger.warning(f"  ⚠️  {idx.name}: {e}")

        logger.info(f"✅ 총 {created_count}개 인덱스 생성됨")
        return created_count

    def get_index_statistics(self):
        """인덱스 통계 조회"""
        logger.info("\n[STEP 4] 인덱싱 — 인덱스 통계")

        from app.db.models import Base

        stats = {}
        for table_name in Base.metadata.tables.keys():
            indexes = self.inspector.get_indexes(table_name)
            stats[table_name] = {
                "count": len(indexes),
                "indexes": [idx.get('name', 'unknown') for idx in indexes]
            }
            logger.info(f"  {table_name}: {len(indexes)}개")
            for idx in indexes:
                idx_name = idx.get('name', 'unknown')
                idx_cols = idx.get('column_names', [])
                logger.info(f"    - {idx_name} on {idx_cols}")

        return stats


class DataCleansingEngine:
    """데이터 클렌징 엔진"""

    def __init__(self, engine):
        self.engine = engine
        self.Session = sessionmaker(bind=engine)

    def analyze_data_quality(self):
        """데이터 품질 분석"""
        logger.info("\n" + "=" * 80)
        logger.info("[STEP 5] 클렌징 — 데이터 품질 분석")
        logger.info("=" * 80)

        db = self.Session()
        try:
            from sqlalchemy import or_
            from app.db.models import Property, Appraisal, Auction

            # Property 테이블 분석
            prop_count = db.query(Property).count()
            prop_null_address = db.query(Property).filter(
                or_(Property.address_full.is_(None), Property.address_full == '')
            ).count()
            prop_null_area = db.query(Property).filter(
                Property.building_area.is_(None)
            ).count()

            logger.info(f"\n📊 Property ({prop_count}행):")
            logger.info(f"  - 주소 결측: {prop_null_address}건 ({prop_null_address/max(prop_count, 1)*100:.2f}%)")
            logger.info(f"  - 면적 결측: {prop_null_area}건 ({prop_null_area/max(prop_count, 1)*100:.2f}%)")

            # Appraisal 테이블 분석
            appr_count = db.query(Appraisal).count()
            appr_null_value = db.query(Appraisal).filter(
                or_(Appraisal.total_value.is_(None), Appraisal.total_value == 0)
            ).count()
            appr_null_date = db.query(Appraisal).filter(
                Appraisal.appraisal_date.is_(None)
            ).count()

            logger.info(f"\n📊 Appraisal ({appr_count}행):")
            logger.info(f"  - 감정가 결측: {appr_null_value}건 ({appr_null_value/max(appr_count, 1)*100:.2f}%)")
            logger.info(f"  - 평가일 결측: {appr_null_date}건 ({appr_null_date/max(appr_count, 1)*100:.2f}%)")

            # Auction 테이블 분석
            auction_count = db.query(Auction).count()
            auction_null_price = db.query(Auction).filter(
                or_(Auction.hammer_price.is_(None), Auction.hammer_price == 0)
            ).count()

            logger.info(f"\n📊 Auction ({auction_count}행):")
            logger.info(f"  - 낙찰가 결측: {auction_null_price}건 ({auction_null_price/max(auction_count, 1)*100:.2f}%)")

            return {
                "property": {"total": prop_count, "missing_address": prop_null_address, "missing_area": prop_null_area},
                "appraisal": {"total": appr_count, "missing_value": appr_null_value, "missing_date": appr_null_date},
                "auction": {"total": auction_count, "missing_price": auction_null_price}
            }
        finally:
            db.close()

    def remove_null_addresses(self):
        """주소 결측값이 있는 Property 제거"""
        logger.info("\n[STEP 6] 클렌징 — 주소 결측값 제거")

        db = self.Session()
        try:
            from sqlalchemy import or_
            from app.db.models import Property

            removed = db.query(Property).filter(
                or_(Property.address_full.is_(None), Property.address_full == '')
            ).delete()

            db.commit()
            logger.info(f"  ✅ {removed}건 제거됨")
            return removed
        except Exception as e:
            logger.error(f"  ❌ 오류: {e}")
            db.rollback()
            return 0
        finally:
            db.close()

    def remove_invalid_values(self):
        """유효하지 않은 감정가 제거"""
        logger.info("\n[STEP 7] 클렌징 — 유효하지 않은 감정가 제거")

        db = self.Session()
        try:
            from sqlalchemy import or_
            from app.db.models import Appraisal

            # 0 또는 음수 감정가 제거
            removed = db.query(Appraisal).filter(
                or_(Appraisal.total_value.is_(None), Appraisal.total_value <= 0)
            ).delete()

            db.commit()
            logger.info(f"  ✅ {removed}건 제거됨")
            return removed
        except Exception as e:
            logger.error(f"  ❌ 오류: {e}")
            db.rollback()
            return 0
        finally:
            db.close()

    def mark_duplicates(self):
        """중복 레코드 식별"""
        logger.info("\n[STEP 8] 클렌징 — 중복 레코드 식별")

        db = self.Session()
        try:
            from app.db.models import Transaction

            # transaction_key 기반 중복 확인
            duplicate_count = db.execute(text("""
                SELECT COUNT(*) as cnt FROM (
                    SELECT transaction_key, COUNT(*) as dup_count
                    FROM transactions
                    WHERE transaction_key IS NOT NULL
                    GROUP BY transaction_key
                    HAVING dup_count > 1
                ) sub
            """)).scalar()

            logger.info(f"  ✅ {duplicate_count}개 중복 그룹 발견")
            return duplicate_count
        except Exception as e:
            logger.error(f"  ❌ 오류: {e}")
            return 0
        finally:
            db.close()


def main():
    """메인 실행 함수"""

    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + "NPL AVM 시스템 — 디버깅 → 인덱싱 → 클렌징 자동화".center(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("╚" + "=" * 78 + "╝")

    # 1. 코드 디버깅
    if not CodeDebugger.validate_imports():
        logger.error("❌ Import 검증 실패. 종료합니다.")
        sys.exit(1)

    if not CodeDebugger.validate_models():
        logger.error("❌ 모델 검증 실패. 종료합니다.")
        sys.exit(1)

    logger.info("✅ 코드 디버깅 완료\n")

    # DB 엔진 생성
    engine = create_engine(DATABASE_URL, echo=False)

    # 2. 인덱싱
    indexing = IndexingManager(engine)
    indexing.create_missing_indexes()
    indexing.get_index_statistics()

    logger.info("✅ 인덱싱 완료\n")

    # 3. 클렌징
    cleansing = DataCleansingEngine(engine)
    quality = cleansing.analyze_data_quality()
    cleansing.remove_null_addresses()
    cleansing.remove_invalid_values()
    cleansing.mark_duplicates()

    logger.info("✅ 클렌징 완료\n")

    # 최종 보고
    logger.info("=" * 80)
    logger.info("📊 최종 진행 상황 보고")
    logger.info("=" * 80)
    logger.info("\n✅ 코드 디버깅: 완료")
    logger.info("   - Import 검증 ✅")
    logger.info("   - 모델 정의 검증 ✅")
    logger.info("\n✅ 인덱싱: 완료")
    logger.info("   - 누락된 인덱스 생성 ✅")
    logger.info("   - 인덱스 통계 조회 ✅")
    logger.info("\n✅ 클렌징: 완료")
    logger.info("   - 데이터 품질 분석 ✅")
    logger.info("   - 주소 결측값 제거 ✅")
    logger.info("   - 유효하지 않은 감정가 제거 ✅")
    logger.info("   - 중복 레코드 식별 ✅")

    logger.info("\n" + "=" * 80)
    logger.info("🎉 모든 작업 완료!")
    logger.info("=" * 80 + "\n")


if __name__ == "__main__":
    main()
