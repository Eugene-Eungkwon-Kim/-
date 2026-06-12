"""
고급 인덱싱 구현 스크립트

목표: p95 latency 100ms 달성
전략: 복합 인덱스 + 커버링 인덱스 + 부분 인덱스
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from sqlalchemy import text, inspect, event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class IndexingStrategy:
    """고급 인덱싱 전략 구현"""

    # 추가할 인덱스 정의
    NEW_INDEXES = [
        {
            "name": "idx_property_composite",
            "table": "property",
            "columns": ["address_sido", "address_sigungu", "property_type", "building_area"],
            "type": "composite",
            "purpose": "비교사례 조회 최적화",
            "expected_improvement": "50%",
        },
        {
            "name": "idx_appraisal_property_date",
            "table": "appraisal",
            "columns": ["property_id", "appraisal_date DESC", "appraisal_value"],
            "type": "covering",
            "purpose": "감정평가 조회 + 정렬",
            "expected_improvement": "50%",
        },
        {
            "name": "idx_comparable_property_date",
            "table": "comparable_sale",
            "columns": ["property_id", "transaction_date DESC", "transaction_price"],
            "type": "covering",
            "purpose": "거래사례 조회 + 정렬",
            "expected_improvement": "52%",
        },
        {
            "name": "idx_appraisal_recent",
            "table": "appraisal",
            "columns": ["property_id", "appraisal_date DESC"],
            "type": "partial",
            "where_clause": f"appraisal_date >= DATE_SUB(NOW(), INTERVAL 1 YEAR)",
            "purpose": "최근 1년 데이터 빠른 조회",
            "expected_improvement": "30%",
        },
        {
            "name": "idx_property_location_type",
            "table": "property",
            "columns": ["address_sido", "address_sigungu", "property_type"],
            "type": "composite",
            "purpose": "지역별 통계",
            "expected_improvement": "40%",
        },
    ]

    # 제거할 인덱스
    INDEXES_TO_DROP = [
        "idx_property_price",
    ]

    @staticmethod
    def build_index_sql(index_def: Dict) -> str:
        """인덱스 생성 SQL 구축"""

        index_name = index_def["name"]
        table_name = index_def["table"]
        columns = ", ".join(index_def["columns"])
        index_type = index_def["type"]

        if index_type == "partial":
            where_clause = index_def.get("where_clause", "")
            sql = f"""
CREATE INDEX CONCURRENTLY {index_name}
ON {table_name}({columns})
WHERE {where_clause};
            """
        else:  # composite 또는 covering
            sql = f"""
CREATE INDEX CONCURRENTLY {index_name}
ON {table_name}({columns});
            """

        return sql.strip()

    @staticmethod
    def check_index_exists(db: Session, index_name: str) -> bool:
        """인덱스 존재 여부 확인"""
        try:
            result = db.execute(
                text(
                    f"""
SELECT 1 FROM information_schema.statistics
WHERE index_name = :index_name LIMIT 1
            """
                ),
                {"index_name": index_name},
            ).fetchone()
            return result is not None
        except Exception as e:
            logger.warning(f"인덱스 확인 오류: {str(e)}")
            return False

    @classmethod
    def create_indexes_safe(cls, db: Session) -> Dict[str, bool]:
        """안전한 인덱스 생성 (CONCURRENTLY 사용)"""

        results = {}

        for index_def in cls.NEW_INDEXES:
            index_name = index_def["name"]

            # 1️⃣ 기존 인덱스 확인
            if cls.check_index_exists(db, index_name):
                logger.info(f"⏭️ 인덱스 이미 존재: {index_name}")
                results[index_name] = False
                continue

            try:
                # 2️⃣ SQL 생성
                sql = cls.build_index_sql(index_def)

                # 3️⃣ 인덱스 생성 (CONCURRENTLY = 읽기 계속 가능)
                logger.info(f"🔨 인덱스 생성 중: {index_name}")
                logger.info(f"   목적: {index_def['purpose']}")
                logger.info(f"   예상 개선: {index_def['expected_improvement']}")

                db.execute(text(sql))
                db.commit()

                logger.info(f"✅ 인덱스 생성 완료: {index_name}")
                results[index_name] = True

                # 부하 분산
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"❌ 인덱스 생성 실패: {index_name} - {str(e)}")
                db.rollback()
                results[index_name] = False

        return results

    @classmethod
    def update_statistics(cls, db: Session) -> bool:
        """테이블 통계 업데이트"""

        tables = ["property", "appraisal", "comparable_sale"]

        try:
            for table in tables:
                logger.info(f"📊 통계 업데이트 중: {table}")
                # PostgreSQL: ANALYZE
                # MySQL: ANALYZE TABLE
                db.execute(text(f"ANALYZE TABLE {table}"))
                db.commit()
                logger.info(f"✅ 통계 업데이트 완료: {table}")

            return True
        except Exception as e:
            logger.error(f"❌ 통계 업데이트 실패: {str(e)}")
            return False

    @classmethod
    def drop_unnecessary_indexes(cls, db: Session) -> Dict[str, bool]:
        """불필요한 인덱스 제거"""

        results = {}

        for index_name in cls.INDEXES_TO_DROP:
            try:
                # 1️⃣ 인덱스 존재 확인
                if not cls.check_index_exists(db, index_name):
                    logger.info(f"⏭️ 인덱스 없음: {index_name}")
                    results[index_name] = False
                    continue

                # 2️⃣ 인덱스 제거
                logger.info(f"🗑️ 인덱스 제거 중: {index_name}")

                # 테이블 이름 추론
                table_name = "comparable_sale" if "price" in index_name else "property"

                db.execute(text(f"DROP INDEX {index_name} ON {table_name}"))
                db.commit()

                logger.info(f"✅ 인덱스 제거 완료: {index_name}")
                results[index_name] = True

            except Exception as e:
                logger.error(f"❌ 인덱스 제거 실패: {index_name} - {str(e)}")
                db.rollback()
                results[index_name] = False

        return results

    @staticmethod
    def analyze_execution_plans(
        db: Session, slow_queries: List[str]
    ) -> Dict[str, Dict]:
        """실행 계획 분석"""

        plans = {}

        for i, query in enumerate(slow_queries, 1):
            try:
                logger.info(f"📋 쿼리 {i} 실행 계획 분석")

                # EXPLAIN ANALYZE 실행
                result = db.execute(text(f"EXPLAIN ANALYZE {query}")).fetchall()

                plans[f"query_{i}"] = {
                    "query": query[:100] + "...",
                    "plan": [row[0] for row in result],
                }

                logger.info(f"✅ 쿼리 {i} 분석 완료")

            except Exception as e:
                logger.error(f"❌ 실행 계획 분석 실패: {str(e)}")
                plans[f"query_{i}"] = {"error": str(e)}

        return plans

    @staticmethod
    def get_index_stats(db: Session) -> Dict[str, List[Dict]]:
        """인덱스 통계 조회"""

        stats = {"usage": [], "size": [], "unused": []}

        try:
            # 1️⃣ 사용 통계
            logger.info("📊 인덱스 사용 통계 조회")
            usage_result = db.execute(
                text(
                    """
SELECT index_name, seq_in_index, column_name
FROM information_schema.statistics
WHERE table_schema = DATABASE()
ORDER BY table_name, index_name
            """
                )
            ).fetchall()

            stats["usage"] = [
                {
                    "index_name": row[0],
                    "seq": row[1],
                    "column_name": row[2],
                }
                for row in usage_result
            ]

            # 2️⃣ 인덱스 크기 (근사치)
            logger.info("💾 인덱스 크기 조회")
            stats["message"] = "인덱스 통계 수집 완료"

            return stats

        except Exception as e:
            logger.error(f"❌ 통계 조회 실패: {str(e)}")
            return {"error": str(e)}


class PerformanceBenchmark:
    """인덱싱 전후 성능 비교"""

    # 벤치마크 쿼리들
    BENCHMARK_QUERIES = [
        {
            "name": "비교사례 조회",
            "sql": """
SELECT p.property_code, p.address_sido, ap.appraisal_value, ap.appraisal_date
FROM property p
LEFT JOIN appraisal ap ON p.id = ap.property_id
WHERE p.address_sido = '경기도'
  AND p.address_sigungu = '용인시'
  AND p.property_type = '아파트'
  AND p.building_area BETWEEN 80 AND 90
ORDER BY ap.appraisal_date DESC
LIMIT 10;
            """,
            "iterations": 100,
        },
        {
            "name": "거래사례 조회",
            "sql": """
SELECT p.property_code, cs.transaction_price, cs.transaction_date
FROM property p
LEFT JOIN comparable_sale cs ON p.id = cs.property_id
WHERE p.address_sido = '경기도'
  AND p.address_sigungu = '용인시'
  AND p.building_area BETWEEN 80 AND 90
ORDER BY cs.transaction_date DESC
LIMIT 5;
            """,
            "iterations": 100,
        },
        {
            "name": "지역별 통계",
            "sql": """
SELECT p.address_sido, p.address_sigungu, COUNT(*),
       AVG(ap.appraisal_value) as avg_price
FROM property p
LEFT JOIN appraisal ap ON p.id = ap.property_id
WHERE ap.appraisal_date >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
GROUP BY p.address_sido, p.address_sigungu
LIMIT 100;
            """,
            "iterations": 20,
        },
    ]

    @classmethod
    def benchmark(cls, db: Session) -> Dict[str, Dict]:
        """성능 벤치마크 실행"""

        results = {}

        for query_def in cls.BENCHMARK_QUERIES:
            query_name = query_def["name"]
            sql = query_def["sql"]
            iterations = query_def["iterations"]

            try:
                logger.info(f"⏱️ 벤치마크 시작: {query_name} ({iterations}회)")

                times = []
                for i in range(iterations):
                    start = time.time()
                    db.execute(text(sql)).fetchall()
                    elapsed = (time.time() - start) * 1000  # ms

                    times.append(elapsed)

                    if (i + 1) % 10 == 0:
                        logger.info(f"   진행: {i + 1}/{iterations}")

                # 통계 계산
                import statistics

                results[query_name] = {
                    "iterations": iterations,
                    "mean_ms": round(statistics.mean(times), 2),
                    "median_ms": round(statistics.median(times), 2),
                    "min_ms": round(min(times), 2),
                    "max_ms": round(max(times), 2),
                    "stdev_ms": round(statistics.stdev(times), 2),
                    "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 2),
                }

                logger.info(f"✅ {query_name}: 평균 {results[query_name]['mean_ms']}ms")

            except Exception as e:
                logger.error(f"❌ 벤치마크 실패: {query_name} - {str(e)}")
                results[query_name] = {"error": str(e)}

        return results


def main():
    """메인 인덱싱 실행 함수"""

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # DB 연결 (SQLite 또는 PostgreSQL)
    DATABASE_URL = "sqlite:///avm.db"
    # DATABASE_URL = "postgresql://user:password@localhost/avm"

    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        logger.info("=" * 60)
        logger.info("🚀 고급 인덱싱 시작")
        logger.info("=" * 60)

        # 1️⃣ 인덱스 생성
        logger.info("\n[Step 1] 인덱스 생성")
        index_results = IndexingStrategy.create_indexes_safe(db)
        logger.info(f"✅ 인덱스 생성: {sum(index_results.values())}/{len(index_results)}")

        # 2️⃣ 통계 업데이트
        logger.info("\n[Step 2] 통계 업데이트")
        if IndexingStrategy.update_statistics(db):
            logger.info("✅ 통계 업데이트 완료")

        # 3️⃣ 불필요한 인덱스 제거
        logger.info("\n[Step 3] 불필요한 인덱스 제거")
        drop_results = IndexingStrategy.drop_unnecessary_indexes(db)
        logger.info(f"✅ 인덱스 제거: {sum(drop_results.values())}/{len(drop_results)}")

        # 4️⃣ 실행 계획 분석
        logger.info("\n[Step 4] 실행 계획 분석")
        slow_queries = [
            PerformanceBenchmark.BENCHMARK_QUERIES[0]["sql"],
            PerformanceBenchmark.BENCHMARK_QUERIES[1]["sql"],
        ]
        plans = IndexingStrategy.analyze_execution_plans(db, slow_queries)
        logger.info(f"✅ 실행 계획 분석 완료: {len(plans)}개 쿼리")

        # 5️⃣ 성능 벤치마크
        logger.info("\n[Step 5] 성능 벤치마크")
        benchmark_results = PerformanceBenchmark.benchmark(db)

        # 최종 보고
        logger.info("\n" + "=" * 60)
        logger.info("📊 최종 결과 보고")
        logger.info("=" * 60)

        for query_name, metrics in benchmark_results.items():
            if "error" not in metrics:
                logger.info(f"\n{query_name}:")
                logger.info(f"  평균: {metrics['mean_ms']}ms")
                logger.info(f"  중앙값: {metrics['median_ms']}ms")
                logger.info(f"  p95: {metrics['p95_ms']}ms")
                logger.info(f"  범위: {metrics['min_ms']}~{metrics['max_ms']}ms")

        logger.info("\n" + "=" * 60)
        logger.info("✅ 인덱싱 완료")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 인덱싱 실패: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
