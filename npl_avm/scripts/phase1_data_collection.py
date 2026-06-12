#!/usr/bin/env python3
"""
Phase 1: 데이터 수집 스크립트
목표: 기존 데이터(500행) → 1,000+ 행으로 확대
"""

import sys
from pathlib import Path
import logging

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 프로젝트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.database import SessionLocal, Base, engine
from app.db.models import Property, ComparableSale, Auction, Deal, Complex, Unit, Transaction, Appraisal


class Phase1DataCollector:
    """Phase 1 데이터 수집 클래스."""

    def __init__(self):
        """초기화."""
        self.db = SessionLocal()
        logger.info("Database session initialized")

    def check_current_data(self):
        """
        현재 데이터 상태 조회.

        Returns:
            dict: 테이블별 행 수
        """
        try:
            counts = {
                "Deal": self.db.query(Deal).count(),
                "Property": self.db.query(Property).count(),
                "Complex": self.db.query(Complex).count(),
                "Unit": self.db.query(Unit).count(),
                "Auction": self.db.query(Auction).count(),
                "ComparableSale": self.db.query(ComparableSale).count(),
                "Appraisal": self.db.query(Appraisal).count(),
                "Transaction": self.db.query(Transaction).count(),
            }

            logger.info("=" * 60)
            logger.info("📊 현재 데이터 상태 (Before Collection)")
            logger.info("=" * 60)

            total = 0
            for table, count in counts.items():
                logger.info(f"  {table:20s}: {count:6d} rows")
                total += count

            logger.info("=" * 60)
            logger.info(f"  {'Total':20s}: {total:6d} rows")
            logger.info("=" * 60)

            return counts

        except Exception as e:
            logger.error(f"Error checking data: {e}")
            raise

    def check_data_quality(self):
        """데이터 품질 확인."""
        try:
            logger.info("\n🔍 데이터 품질 검사")
            logger.info("-" * 60)

            # 1. ComparableSale의 가격 범위
            comparables = self.db.query(ComparableSale).all()
            if comparables:
                prices = [c.hammer_price for c in comparables if c.hammer_price]
                logger.info(f"  ComparableSale 거래가")
                logger.info(f"    - 최소: ₩{min(prices):,.0f}")
                logger.info(f"    - 최대: ₩{max(prices):,.0f}")
                logger.info(f"    - 평균: ₩{sum(prices)/len(prices):,.0f}")

            # 2. Property의 면적 범위
            properties = self.db.query(Property).all()
            if properties:
                areas = [p.area_sqm for p in properties if p.area_sqm]
                logger.info(f"  Property 면적")
                logger.info(f"    - 최소: {min(areas):,.0f} ㎡")
                logger.info(f"    - 최대: {max(areas):,.0f} ㎡")
                logger.info(f"    - 평균: {sum(areas)/len(areas):,.0f} ㎡")

            # 3. 결측치 확인
            total_properties = len(properties)
            if total_properties > 0:
                missing_area = sum(1 for p in properties if not p.area_sqm)
                missing_type = sum(1 for p in properties if not p.property_type)
                logger.info(f"  결측치 (Property)")
                logger.info(f"    - area_sqm: {missing_area}/{total_properties}")
                logger.info(f"    - property_type: {missing_type}/{total_properties}")

            logger.info("-" * 60)

        except Exception as e:
            logger.error(f"Error checking quality: {e}")

    def analyze_missing_data(self):
        """결측치 분석."""
        try:
            logger.info("\n📈 상세 분석")
            logger.info("-" * 60)

            # ComparableSale의 거래일자 범위
            comparables = self.db.query(ComparableSale).filter(
                ComparableSale.reference_date.isnot(None)
            ).all()

            if comparables:
                dates = [c.reference_date for c in comparables]
                min_date = min(dates)
                max_date = max(dates)
                logger.info(f"  ComparableSale 거래일자 범위")
                logger.info(f"    - 최초: {min_date}")
                logger.info(f"    - 최신: {max_date}")

            logger.info("-" * 60)

        except Exception as e:
            logger.error(f"Error analyzing: {e}")

    def generate_report(self, before, after):
        """수집 결과 리포트."""
        logger.info("\n📊 수집 결과 리포트")
        logger.info("=" * 60)

        for table in before:
            diff = after[table] - before[table]
            pct = (diff / before[table] * 100) if before[table] > 0 else 0

            if diff > 0:
                logger.info(
                    f"  {table:20s}: {before[table]:6d} → {after[table]:6d} "
                    f"(+{diff:6d}, +{pct:5.1f}%)"
                )
            else:
                logger.info(
                    f"  {table:20s}: {before[table]:6d} → {after[table]:6d} "
                    f"(no change)"
                )

        logger.info("=" * 60)

        total_before = sum(before.values())
        total_after = sum(after.values())
        total_diff = total_after - total_before
        total_pct = (total_diff / total_before * 100) if total_before > 0 else 0

        logger.info(
            f"  {'Total':20s}: {total_before:6d} → {total_after:6d} "
            f"(+{total_diff:6d}, +{total_pct:5.1f}%)"
        )
        logger.info("=" * 60)

    def run(self):
        """메인 실행."""
        try:
            logger.info("\n" + "=" * 60)
            logger.info("🚀 Phase 1 데이터 수집 시작")
            logger.info("=" * 60)

            # 1. 현재 데이터 확인
            logger.info("\n[Step 1/3] 현재 데이터 상태 조회...")
            before = self.check_current_data()

            # 2. 데이터 품질 확인
            logger.info("\n[Step 2/3] 데이터 품질 검사...")
            self.check_data_quality()
            self.analyze_missing_data()

            # 3. 추가 데이터 수집 (현재는 기존 데이터만 사용)
            logger.info("\n[Step 3/3] 현재 데이터 상태 재확인...")
            after = self.check_current_data()

            # 리포트
            self.generate_report(before, after)

            # 다음 단계
            total_records = sum(after.values())
            if total_records < 1000:
                logger.warning(f"\n⚠️  데이터가 부족합니다: {total_records} < 1,000")
                logger.warning("  → 추가 데이터 수집 또는 생성 필요")
                logger.warning("  → 외부 API 연동 또는 샘플 데이터 생성 고려")
            else:
                logger.info(f"\n✅ 데이터 수집 목표 달성: {total_records} >= 1,000")
                logger.info("  → 다음 단계: 데이터 전처리 진행")

            logger.info("\n" + "=" * 60)
            logger.info("✅ 데이터 수집 완료")
            logger.info("=" * 60)

            return after

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise
        finally:
            self.db.close()


def main():
    """메인 함수."""
    collector = Phase1DataCollector()
    collector.run()


if __name__ == "__main__":
    main()
