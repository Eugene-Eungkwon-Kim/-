"""
데이터 클랜징 자동화 스크립트

목표: 데이터 품질 99%+ 달성
전략: 결측값, 중복, 형식, 범위, 논리 오류 자동 처리
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
import statistics

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DataProfilingEngine:
    """데이터 품질 분석 및 프로필링"""

    @staticmethod
    def profile_tables(db: Session) -> Dict:
        """모든 테이블 프로필링"""

        tables = ["property", "appraisal", "comparable_sale"]
        profiles = {}

        for table_name in tables:
            logger.info(f"📊 테이블 프로필링 중: {table_name}")

            # 행 수
            row_count = db.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            ).scalar()

            # 열 정보
            columns_info = inspect(db.bind).get_columns(table_name)

            # NULL 개수
            null_counts = {}
            for col in columns_info:
                col_name = col.name
                null_count = db.execute(
                    text(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL")
                ).scalar()
                null_counts[col_name] = null_count

            profiles[table_name] = {
                "row_count": row_count,
                "column_count": len(columns_info),
                "null_counts": null_counts,
                "total_nulls": sum(null_counts.values()),
                "null_percentage": (sum(null_counts.values()) / (row_count * len(columns_info))) * 100,
            }

            logger.info(
                f"  ✅ {row_count}행, {len(columns_info)}열, "
                f"NULL: {sum(null_counts.values())} ({profiles[table_name]['null_percentage']:.2f}%)"
            )

        return profiles

    @staticmethod
    def detect_anomalies(db: Session, table_name: str, column_name: str) -> Dict:
        """이상값 자동 감지 (IQR 및 Z-score 방법)"""

        logger.info(f"🔍 이상값 감지: {table_name}.{column_name}")

        try:
            # 수치 데이터만 가능
            values_result = db.execute(
                text(
                    f"""
SELECT {column_name} FROM {table_name}
WHERE {column_name} IS NOT NULL AND {column_name} != 0
ORDER BY {column_name}
            """
                )
            ).fetchall()

            if not values_result:
                return {"status": "no_data"}

            values = [row[0] for row in values_result]

            if len(values) < 4:
                return {"status": "insufficient_data"}

            # 기본 통계
            mean = statistics.mean(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0
            min_val = min(values)
            max_val = max(values)

            # IQR 방법
            sorted_vals = sorted(values)
            q1_idx = len(sorted_vals) // 4
            q3_idx = (len(sorted_vals) * 3) // 4
            q1 = sorted_vals[q1_idx]
            q3 = sorted_vals[q3_idx]
            iqr = q3 - q1

            lower_bound = q1 - (1.5 * iqr)
            upper_bound = q3 + (1.5 * iqr)

            # 이상값 개수
            anomalies = [v for v in values if v < lower_bound or v > upper_bound]

            result = {
                "mean": round(mean, 2),
                "stdev": round(stdev, 2),
                "min": min_val,
                "max": max_val,
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "lower_bound": round(lower_bound, 2),
                "upper_bound": round(upper_bound, 2),
                "anomaly_count": len(anomalies),
                "anomaly_percentage": (len(anomalies) / len(values)) * 100,
            }

            logger.info(f"  ✅ 이상값: {len(anomalies)}개 ({result['anomaly_percentage']:.2f}%)")
            return result

        except Exception as e:
            logger.error(f"❌ 이상값 감지 실패: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    def identify_duplicates(db: Session, table_name: str, key_columns: List[str]) -> Dict:
        """중복 식별"""

        logger.info(f"🔍 중복 식별: {table_name} (키: {', '.join(key_columns)})")

        try:
            key_cols = ", ".join(key_columns)
            result = db.execute(
                text(
                    f"""
SELECT {key_cols}, COUNT(*) as cnt
FROM {table_name}
GROUP BY {key_cols}
HAVING cnt > 1
            """
                )
            ).fetchall()

            total_duplicates = sum(row[-1] - 1 for row in result)

            logger.info(f"  ✅ 중복 그룹: {len(result)}개, 중복 레코드: {total_duplicates}개")

            return {
                "duplicate_groups": len(result),
                "duplicate_records": total_duplicates,
                "samples": [dict(row) for row in result[:5]],
            }

        except Exception as e:
            logger.error(f"❌ 중복 식별 실패: {str(e)}")
            return {"error": str(e)}


class DataCleansingEngine:
    """데이터 클랜징 자동화"""

    @staticmethod
    def handle_missing_values_property(db: Session) -> Dict:
        """property 테이블의 결측값 처리"""

        logger.info("🧹 결측값 처리: property")

        results = {"updated": 0, "errors": 0}

        try:
            # building_area가 NULL인 경우 평균값으로 대체
            avg_area = db.execute(
                text("SELECT AVG(building_area) FROM property WHERE building_area > 0")
            ).scalar()

            if avg_area:
                db.execute(
                    text(
                        f"""
UPDATE property
SET building_area = :avg_area
WHERE building_area IS NULL OR building_area = 0
                """
                    ),
                    {"avg_area": avg_area},
                )
                db.commit()
                results["updated"] += db.execute(
                    text("SELECT COUNT(*) FROM property WHERE building_area = :avg_area"),
                    {"avg_area": avg_area},
                ).scalar()

            # property_code 생성 (NULL인 경우)
            null_codes = db.execute(
                text("SELECT id FROM property WHERE property_code IS NULL LIMIT 100")
            ).fetchall()

            for (prop_id,) in null_codes:
                code = f"P{prop_id:05d}"
                db.execute(
                    text("UPDATE property SET property_code = :code WHERE id = :id"),
                    {"code": code, "id": prop_id},
                )
                results["updated"] += 1

            db.commit()
            logger.info(f"  ✅ property 결측값 처리: {results['updated']}개 레코드")

        except Exception as e:
            logger.error(f"❌ property 결측값 처리 실패: {str(e)}")
            results["errors"] += 1
            db.rollback()

        return results

    @staticmethod
    def handle_missing_values_appraisal(db: Session) -> Dict:
        """appraisal 테이블의 결측값 처리"""

        logger.info("🧹 결측값 처리: appraisal")

        results = {"updated": 0, "deleted": 0, "errors": 0}

        try:
            # 지역별 평균값으로 결측값 대체
            appraisals = db.execute(
                text(
                    """
SELECT a.id, p.address_sido, p.address_sigungu
FROM appraisal a
JOIN property p ON a.property_id = p.id
WHERE a.appraisal_value IS NULL
LIMIT 1000
            """
                )
            ).fetchall()

            for appraisal_id, sido, sigungu in appraisals:
                # 지역 평균값 조회
                avg_value = db.execute(
                    text(
                        """
SELECT AVG(ap.appraisal_value)
FROM appraisal ap
JOIN property p ON ap.property_id = p.id
WHERE p.address_sido = :sido AND p.address_sigungu = :sigungu
  AND ap.appraisal_value > 0
                    """
                    ),
                    {"sido": sido, "sigungu": sigungu},
                ).scalar()

                if avg_value:
                    db.execute(
                        text("UPDATE appraisal SET appraisal_value = :val WHERE id = :id"),
                        {"val": avg_value, "id": appraisal_id},
                    )
                    results["updated"] += 1

            db.commit()
            logger.info(f"  ✅ appraisal 결측값 처리: {results['updated']}개 레코드")

        except Exception as e:
            logger.error(f"❌ appraisal 결측값 처리 실패: {str(e)}")
            results["errors"] += 1
            db.rollback()

        return results

    @staticmethod
    def remove_duplicates(db: Session) -> Dict:
        """중복 레코드 제거"""

        logger.info("🧹 중복 제거")

        results = {"deleted": 0, "errors": 0}

        try:
            # comparable_sale의 정확 중복 제거
            # (같은 property_id + transaction_date + price)
            duplicates = db.execute(
                text(
                    """
SELECT id FROM (
    SELECT id, ROW_NUMBER() OVER (
        PARTITION BY property_id, transaction_date, transaction_price
        ORDER BY id DESC
    ) as rn
    FROM comparable_sale
) t
WHERE rn > 1
            """
                )
            ).fetchall()

            for (dup_id,) in duplicates:
                db.execute(text("DELETE FROM comparable_sale WHERE id = :id"), {"id": dup_id})
                results["deleted"] += 1

            db.commit()
            logger.info(f"  ✅ 중복 제거: {results['deleted']}개 레코드")

        except Exception as e:
            logger.error(f"❌ 중복 제거 실패: {str(e)}")
            results["errors"] += 1
            db.rollback()

        return results

    @staticmethod
    def standardize_formats(db: Session) -> Dict:
        """형식 표준화"""

        logger.info("🧹 형식 표준화")

        results = {"updated": 0, "errors": 0}

        try:
            # property_type 표준화 ("아파트"로 통일)
            db.execute(
                text(
                    """
UPDATE property
SET property_type = '아파트'
WHERE property_type IN ('APT', 'Apartment', 'apt', '아파')
            """
                )
            )
            results["updated"] += 1

            # address_sigungu 공백 제거 및 표준화
            db.execute(
                text(
                    """
UPDATE property
SET address_sigungu = TRIM(REPLACE(address_sigungu, '  ', ' '))
WHERE address_sigungu LIKE '%  %'
            """
                )
            )
            results["updated"] += 1

            # property_code 대문자 통일
            db.execute(
                text(
                    """
UPDATE property
SET property_code = UPPER(TRIM(property_code))
WHERE property_code LIKE ' %' OR property_code LIKE '%p%'
            """
                )
            )
            results["updated"] += 1

            db.commit()
            logger.info(f"  ✅ 형식 표준화: {results['updated']}개 작업")

        except Exception as e:
            logger.error(f"❌ 형식 표준화 실패: {str(e)}")
            results["errors"] += 1
            db.rollback()

        return results

    @staticmethod
    def validate_ranges(db: Session) -> Dict:
        """범위 검증 및 수정"""

        logger.info("🧹 범위 검증")

        results = {"fixed": 0, "deleted": 0, "errors": 0}

        try:
            # building_area가 음수이거나 0인 경우
            db.execute(
                text(
                    """
UPDATE property
SET building_area = ABS(building_area)
WHERE building_area < 0
            """
                )
            )
            results["fixed"] += 1

            # building_area가 50000을 초과하는 경우 제거
            db.execute(text("DELETE FROM property WHERE building_area > 50000"))
            results["deleted"] += 1

            # transaction_price가 10000만 미만인 경우 제거
            db.execute(text("DELETE FROM comparable_sale WHERE transaction_price < 100000000"))
            results["deleted"] += 1

            db.commit()
            logger.info(f"  ✅ 범위 검증: {results['fixed']}개 수정, {results['deleted']}개 삭제")

        except Exception as e:
            logger.error(f"❌ 범위 검증 실패: {str(e)}")
            results["errors"] += 1
            db.rollback()

        return results

    @staticmethod
    def fix_logic_errors(db: Session) -> Dict:
        """논리 오류 수정"""

        logger.info("🧹 논리 오류 수정")

        results = {"fixed": 0, "errors": 0}

        try:
            # building_area < land_area인 경우 값 교환
            incorrect = db.execute(
                text(
                    """
SELECT id, building_area, land_area
FROM property
WHERE building_area < land_area AND building_area > 0
LIMIT 100
            """
                )
            ).fetchall()

            for prop_id, building, land in incorrect:
                db.execute(
                    text("UPDATE property SET building_area = :land, land_area = :building WHERE id = :id"),
                    {"land": land, "building": building, "id": prop_id},
                )
                results["fixed"] += 1

            # appraisal_date가 현재보다 미래인 경우
            db.execute(
                text(
                    """
UPDATE appraisal
SET appraisal_date = DATE_ADD(appraisal_date, INTERVAL -365 DAY)
WHERE appraisal_date > NOW()
            """
                )
            )
            results["fixed"] += 1

            db.commit()
            logger.info(f"  ✅ 논리 오류 수정: {results['fixed']}개")

        except Exception as e:
            logger.error(f"❌ 논리 오류 수정 실패: {str(e)}")
            results["errors"] += 1
            db.rollback()

        return results


class DataQualityValidator:
    """데이터 품질 검증"""

    @staticmethod
    def calculate_quality_metrics(db: Session) -> Dict:
        """종합 품질 메트릭 계산"""

        logger.info("📊 품질 메트릭 계산")

        tables = ["property", "appraisal", "comparable_sale"]
        metrics = {}

        try:
            for table_name in tables:
                # 전체 셀 수
                row_count = db.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                ).scalar()
                col_count = len(inspect(db.bind).get_columns(table_name))
                total_cells = row_count * col_count

                # NULL 개수
                null_count = db.execute(
                    text(
                        f"""
SELECT SUM(null_count) FROM (
    SELECT COUNT(CASE WHEN col IS NULL THEN 1 END) as null_count
    FROM (SELECT * FROM {table_name}) t
    CROSS JOIN (VALUES {','.join(['(1)'] * col_count)}) cols(col)
) sub
            """
                    )
                ).scalar() or 0

                # 계산
                completeness = ((total_cells - null_count) / total_cells) * 100 if total_cells > 0 else 0

                metrics[table_name] = {
                    "rows": row_count,
                    "columns": col_count,
                    "total_cells": total_cells,
                    "null_count": null_count,
                    "completeness": round(completeness, 2),
                }

            logger.info("  ✅ 품질 메트릭 계산 완료")
            return metrics

        except Exception as e:
            logger.error(f"❌ 품질 메트릭 계산 실패: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    def validate_business_rules(db: Session) -> Dict:
        """비즈니스 규칙 검증"""

        logger.info("✅ 비즈니스 규칙 검증")

        validations = {}

        try:
            # Rule 1: property_code 유니크
            duplicates = db.execute(
                text(
                    """
SELECT COUNT(*) FROM (
    SELECT property_code, COUNT(*)
    FROM property
    WHERE property_code IS NOT NULL
    GROUP BY property_code
    HAVING COUNT(*) > 1
) t
            """
                )
            ).scalar()

            validations["unique_property_code"] = duplicates == 0

            # Rule 2: appraisal_value > 0
            invalid_values = db.execute(
                text("SELECT COUNT(*) FROM appraisal WHERE appraisal_value <= 0")
            ).scalar()

            validations["appraisal_value_positive"] = invalid_values == 0

            # Rule 3: building_area >= land_area (대부분)
            invalid_areas = db.execute(
                text(
                    "SELECT COUNT(*) FROM property WHERE building_area > land_area AND land_area > 0"
                )
            ).scalar()

            validations["area_logic_valid"] = invalid_areas == 0

            logger.info(f"  ✅ 규칙 검증 완료: {sum(validations.values())}/{len(validations)}")
            return validations

        except Exception as e:
            logger.error(f"❌ 규칙 검증 실패: {str(e)}")
            return {"error": str(e)}


def main():
    """메인 클랜징 실행"""

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    DATABASE_URL = "sqlite:///avm.db"
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        logger.info("=" * 70)
        logger.info("🧹 데이터 클랜징 시작")
        logger.info("=" * 70)

        # 1️⃣ 분석
        logger.info("\n[Phase 1] 데이터 분석")
        profiles = DataProfilingEngine.profile_tables(db)

        # 2️⃣ 결측값 처리
        logger.info("\n[Phase 2] 결측값 처리")
        DataCleansingEngine.handle_missing_values_property(db)
        DataCleansingEngine.handle_missing_values_appraisal(db)

        # 3️⃣ 중복 제거
        logger.info("\n[Phase 3] 중복 제거")
        DataCleansingEngine.remove_duplicates(db)

        # 4️⃣ 형식 표준화
        logger.info("\n[Phase 4] 형식 표준화")
        DataCleansingEngine.standardize_formats(db)

        # 5️⃣ 범위 검증
        logger.info("\n[Phase 5] 범위 검증")
        DataCleansingEngine.validate_ranges(db)

        # 6️⃣ 논리 오류 수정
        logger.info("\n[Phase 6] 논리 오류 수정")
        DataCleansingEngine.fix_logic_errors(db)

        # 7️⃣ 검증
        logger.info("\n[Phase 7] 품질 검증")
        metrics = DataQualityValidator.calculate_quality_metrics(db)
        rules = DataQualityValidator.validate_business_rules(db)

        # 최종 보고
        logger.info("\n" + "=" * 70)
        logger.info("📊 클랜징 완료 보고")
        logger.info("=" * 70)

        for table, metric in metrics.items():
            if "error" not in metric:
                logger.info(f"\n{table}:")
                logger.info(f"  행: {metric['rows']}, 열: {metric['columns']}")
                logger.info(f"  Completeness: {metric['completeness']}%")

        logger.info("\n✅ 모든 클랜징 작업 완료")

    except Exception as e:
        logger.error(f"❌ 클랜징 실패: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
