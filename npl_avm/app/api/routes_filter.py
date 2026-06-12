import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import Property, Appraisal
from app.utils.filter_engine import (
    FilterParser,
    FilterEngine,
    FuzzySearch,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/filter", tags=["filter"])


class FilterRequest(BaseModel):
    """복합 필터 요청"""

    conditions: dict  # {"field": {"operator": "value"}}
    limit: int = 100
    offset: int = 0


@router.get(
    "/properties",
    summary="고급 필터링 검색",
    description="정규식, 범위, 포함 등의 고급 필터로 물건을 검색합니다",
)
def filter_properties(
    filters: Optional[str] = Query(
        None,
        description='필터 문자열 (예: building_area:between:100,200&property_type:in:아파트,오피스)',
    ),
    search: Optional[str] = Query(None, description="모호성 검색 (주소)"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    sort_by: Optional[str] = Query("id", regex="^[a-z_]+$"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """
    고급 필터링으로 물건을 검색합니다.

    **필터 형식**:
    - `eq` (같음): `field:eq:value`
    - `gt` (초과): `field:gt:100`
    - `gte` (이상): `field:gte:100`
    - `lt` (미만): `field:lt:200`
    - `lte` (이하): `field:lte:200`
    - `like` (포함): `field:like:강남`
    - `in` (포함): `field:in:값1,값2`
    - `between` (범위): `field:between:100,200`

    **예시**:
    ```
    GET /api/v1/filter/properties?filters=building_area:between:100,200&filters=property_type:in:아파트,오피스&limit=50
    ```

    **응답**:
    ```json
    {
      "total": 523,
      "limit": 50,
      "offset": 0,
      "results": [
        {
          "id": 1,
          "address_sido": "경기도",
          "address_sigungu": "용인시",
          "property_type": "아파트",
          "land_area": 2000.0,
          "building_area": 84.5
        }
      ]
    }
    ```
    """
    try:
        query = db.query(Property)

        # 필터 적용
        if filters:
            filter_list = filters.split("&")
            for filter_str in filter_list:
                if not filter_str.strip():
                    continue

                try:
                    condition = FilterParser.parse(filter_str)
                    query = FilterEngine.apply_filter(query, Property, [condition])
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))

        # 모호성 검색 (주소)
        if search:
            query = FuzzySearch.fuzzy_match(query, Property, "address_sigungu", search)

        # 전체 개수 (페이지네이션 전)
        total = query.count()

        # 정렬 및 페이지네이션
        if hasattr(Property, sort_by):
            sort_column = getattr(Property, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column)

        results = query.offset(offset).limit(limit).all()

        # 응답 변환
        data = [
            {
                "id": r.id,
                "address_sido": r.address_sido,
                "address_sigungu": r.address_sigungu,
                "property_type": r.property_type,
                "land_area": r.land_area,
                "building_area": r.building_area,
            }
            for r in results
        ]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "results": data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"필터링 검색 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/properties/advanced",
    summary="복합 필터링 검색",
    description="JSON 형식의 복합 필터로 검색합니다",
)
def filter_properties_advanced(
    req: FilterRequest,
    db: Session = Depends(get_db),
):
    """
    JSON 형식의 복합 필터로 검색합니다.

    **요청 본문**:
    ```json
    {
      "conditions": {
        "building_area": {"operator": "between", "value": [100, 200]},
        "property_type": {"operator": "in", "value": ["아파트", "오피스"]},
        "address_sigungu": {"operator": "like", "value": "강남"}
      },
      "limit": 50,
      "offset": 0
    }
    ```

    **지원 연산자**:
    - eq, ne, gt, gte, lt, lte
    - like (ILIKE, 대소문자 구분 안 함)
    - in, not_in
    - between (범위)
    """
    try:
        query = db.query(Property)

        # 복합 필터 적용
        filter_expr = FilterEngine.build_complex_filter(Property, req.conditions)
        if filter_expr is not None:
            query = query.filter(filter_expr)

        # 전체 개수
        total = query.count()

        # 페이지네이션
        results = query.offset(req.offset).limit(req.limit).all()

        data = [
            {
                "id": r.id,
                "address": f"{r.address_sido} {r.address_sigungu}",
                "property_type": r.property_type,
                "land_area": r.land_area,
                "building_area": r.building_area,
            }
            for r in results
        ]

        return {
            "total": total,
            "limit": req.limit,
            "offset": req.offset,
            "results": data,
        }

    except Exception as e:
        logger.error(f"복합 필터링 검색 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/operators",
    summary="지원 필터 연산자 목록",
)
def get_filter_operators():
    """
    지원하는 필터 연산자 목록을 반환합니다.

    **응답**:
    ```json
    {
      "operators": [
        {"name": "eq", "description": "같음", "example": "field:eq:value"},
        {"name": "gt", "description": "초과", "example": "field:gt:100"},
        {"name": "between", "description": "범위", "example": "field:between:100,200"}
      ]
    }
    ```
    """
    operators = [
        {
            "name": "eq",
            "description": "같음",
            "example": "building_area:eq:84.5",
        },
        {
            "name": "ne",
            "description": "다름",
            "example": "property_type:ne:주택",
        },
        {
            "name": "gt",
            "description": "초과",
            "example": "building_area:gt:100",
        },
        {
            "name": "gte",
            "description": "이상",
            "example": "building_area:gte:100",
        },
        {
            "name": "lt",
            "description": "미만",
            "example": "building_area:lt:200",
        },
        {
            "name": "lte",
            "description": "이하",
            "example": "building_area:lte:200",
        },
        {
            "name": "like",
            "description": "포함 (문자열)",
            "example": "address_sigungu:like:강남",
        },
        {
            "name": "in",
            "description": "포함 (목록)",
            "example": "property_type:in:아파트,오피스",
        },
        {
            "name": "not_in",
            "description": "제외",
            "example": "property_type:not_in:주택",
        },
        {
            "name": "between",
            "description": "범위",
            "example": "building_area:between:100,200",
        },
    ]

    return {"operators": operators}
