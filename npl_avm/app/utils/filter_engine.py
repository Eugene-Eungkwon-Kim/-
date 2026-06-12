import logging
import re
from typing import Any, Dict, List, Optional
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import BinaryExpression

logger = logging.getLogger(__name__)


class FilterOperator:
    """필터 연산자 정의"""

    EQ = "eq"  # 같음
    NE = "ne"  # 다름
    GT = "gt"  # 초과
    GTE = "gte"  # 이상
    LT = "lt"  # 미만
    LTE = "lte"  # 이하
    LIKE = "like"  # 포함 (문자열)
    REGEX = "regex"  # 정규식
    IN = "in"  # 포함 (목록)
    NOT_IN = "not_in"  # 제외
    BETWEEN = "between"  # 범위
    IS_NULL = "is_null"  # NULL 여부
    CONTAINS = "contains"  # 포함 (배열)


class FilterCondition:
    """단일 필터 조건"""

    def __init__(
        self,
        field: str,
        operator: str,
        value: Any,
    ):
        self.field = field
        self.operator = operator
        self.value = value

    def __repr__(self):
        return f"FilterCondition({self.field} {self.operator} {self.value})"


class FilterExpression:
    """복합 필터 표현식 (AND/OR/NOT)"""

    def __init__(self, operator: str, conditions: List[Any]):
        self.operator = operator  # "and", "or", "not"
        self.conditions = conditions

    def __repr__(self):
        return f"FilterExpression({self.operator}: {self.conditions})"


class FilterParser:
    """필터 문자열 파싱"""

    @staticmethod
    def parse(filter_str: str) -> FilterCondition:
        """
        필터 문자열 파싱
        형식: field:operator:value
        예: building_area:between:100,200
        """
        parts = filter_str.split(":", 2)
        if len(parts) < 3:
            raise ValueError(f"잘못된 필터 형식: {filter_str}")

        field, operator, value = parts
        return FilterCondition(field.strip(), operator.strip(), value.strip())

    @staticmethod
    def parse_value(value_str: str, operator: str) -> Any:
        """값 파싱 (연산자에 따라)"""
        if operator in [FilterOperator.IN, FilterOperator.NOT_IN]:
            # 쉼표로 구분된 목록
            return [v.strip() for v in value_str.split(",")]
        elif operator == FilterOperator.BETWEEN:
            # 범위 (시작, 끝)
            parts = value_str.split(",")
            if len(parts) != 2:
                raise ValueError(f"BETWEEN은 두 개의 값이 필요합니다: {value_str}")
            return [float(parts[0].strip()), float(parts[1].strip())]
        elif operator == FilterOperator.IS_NULL:
            return value_str.lower() in ["true", "1", "yes"]
        elif operator in [
            FilterOperator.GT,
            FilterOperator.GTE,
            FilterOperator.LT,
            FilterOperator.LTE,
        ]:
            try:
                return float(value_str)
            except ValueError:
                return value_str
        else:
            return value_str


class FilterEngine:
    """필터 엔진"""

    @staticmethod
    def apply_filter(
        query,
        model_class,
        conditions: List[FilterCondition],
    ):
        """
        필터 조건을 쿼리에 적용

        Args:
            query: SQLAlchemy query 객체
            model_class: 모델 클래스
            conditions: 필터 조건 리스트
        """
        for condition in conditions:
            query = FilterEngine._apply_single_condition(
                query, model_class, condition
            )
        return query

    @staticmethod
    def _apply_single_condition(
        query,
        model_class,
        condition: FilterCondition,
    ):
        """단일 필터 조건 적용"""
        field_name = condition.field
        operator = condition.operator
        value = FilterParser.parse_value(condition.value, operator)

        if not hasattr(model_class, field_name):
            raise ValueError(f"모델에 필드가 없습니다: {field_name}")

        column = getattr(model_class, field_name)

        if operator == FilterOperator.EQ:
            query = query.filter(column == value)
        elif operator == FilterOperator.NE:
            query = query.filter(column != value)
        elif operator == FilterOperator.GT:
            query = query.filter(column > value)
        elif operator == FilterOperator.GTE:
            query = query.filter(column >= value)
        elif operator == FilterOperator.LT:
            query = query.filter(column < value)
        elif operator == FilterOperator.LTE:
            query = query.filter(column <= value)
        elif operator == FilterOperator.LIKE:
            # 패턴 매칭 (대소문자 구분 안 함)
            query = query.filter(column.ilike(f"%{value}%"))
        elif operator == FilterOperator.REGEX:
            # 정규식 (데이터베이스 지원에 따라 다름)
            try:
                query = query.filter(column.regexp_match(value))
            except Exception:
                logger.warning(f"정규식 필터는 해당 DB에서 지원하지 않을 수 있습니다")
        elif operator == FilterOperator.IN:
            query = query.filter(column.in_(value))
        elif operator == FilterOperator.NOT_IN:
            query = query.filter(~column.in_(value))
        elif operator == FilterOperator.BETWEEN:
            query = query.filter(column.between(value[0], value[1]))
        elif operator == FilterOperator.IS_NULL:
            if value:
                query = query.filter(column.is_(None))
            else:
                query = query.filter(column.isnot(None))
        else:
            raise ValueError(f"지원하지 않는 연산자: {operator}")

        return query

    @staticmethod
    def build_complex_filter(
        model_class,
        filter_dict: Dict[str, Any],
    ) -> BinaryExpression:
        """
        복합 필터 빌드

        Args:
            model_class: 모델 클래스
            filter_dict: 필터 딕셔너리
                {
                  "building_area": {"operator": "between", "value": [100, 200]},
                  "property_type": {"operator": "in", "value": ["아파트", "오피스"]}
                }
        """
        conditions = []

        for field_name, filter_spec in filter_dict.items():
            if not hasattr(model_class, field_name):
                logger.warning(f"필드가 없습니다: {field_name}")
                continue

            operator = filter_spec.get("operator", "eq")
            value = filter_spec.get("value")

            column = getattr(model_class, field_name)

            if operator == FilterOperator.EQ:
                conditions.append(column == value)
            elif operator == FilterOperator.NE:
                conditions.append(column != value)
            elif operator == FilterOperator.GT:
                conditions.append(column > value)
            elif operator == FilterOperator.GTE:
                conditions.append(column >= value)
            elif operator == FilterOperator.LT:
                conditions.append(column < value)
            elif operator == FilterOperator.LTE:
                conditions.append(column <= value)
            elif operator == FilterOperator.LIKE:
                conditions.append(column.ilike(f"%{value}%"))
            elif operator == FilterOperator.IN:
                conditions.append(column.in_(value))
            elif operator == FilterOperator.NOT_IN:
                conditions.append(~column.in_(value))
            elif operator == FilterOperator.BETWEEN:
                conditions.append(column.between(value[0], value[1]))

        if not conditions:
            return None

        return and_(*conditions)


class FuzzySearch:
    """모호성 검색 (대략적인 일치)"""

    @staticmethod
    def fuzzy_match(
        query,
        model_class,
        field_name: str,
        search_term: str,
        threshold: float = 0.8,
    ):
        """
        모호성 검색 (Levenshtein 거리 기반)

        주의: 데이터베이스가 지원해야 함 (PostgreSQL의 경우 fuzzystrmatch 확장)
        """
        column = getattr(model_class, field_name)

        try:
            # PostgreSQL의 similarity 함수 사용
            from sqlalchemy import func

            query = query.filter(
                func.similarity(column, search_term) > threshold
            ).order_by(func.similarity(column, search_term).desc())
        except Exception as e:
            logger.warning(f"모호성 검색 실패: {str(e)}")
            # Fallback: 일반 LIKE 검색
            query = query.filter(column.ilike(f"%{search_term}%"))

        return query


filter_engine = FilterEngine()
filter_parser = FilterParser()
fuzzy_search = FuzzySearch()
