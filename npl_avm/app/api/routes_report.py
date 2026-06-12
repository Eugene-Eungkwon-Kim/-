import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.report_service import report_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportTemplateCreate(BaseModel):
    """리포트 템플릿 생성 요청"""
    name: str
    description: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    grouping: Optional[str] = None
    aggregations: Optional[List[Dict[str, Any]]] = None
    schedule: Optional[str] = None
    notify_slack: bool = False
    notify_email: bool = False
    webhook_url: Optional[str] = None


class ReportTemplateUpdate(BaseModel):
    """리포트 템플릿 수정 요청"""
    name: Optional[str] = None
    description: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    grouping: Optional[str] = None
    aggregations: Optional[List[Dict[str, Any]]] = None
    schedule: Optional[str] = None
    notify_slack: Optional[bool] = None
    notify_email: Optional[bool] = None
    webhook_url: Optional[str] = None
    enabled: Optional[bool] = None


class ReportTemplateOut(BaseModel):
    """리포트 템플릿 응답"""
    id: int
    name: str
    description: Optional[str]
    filters: Optional[Dict]
    grouping: Optional[str]
    aggregations: Optional[List[Dict]]
    schedule: Optional[str]
    enabled: bool
    notify_slack: bool
    notify_email: bool
    webhook_url: Optional[str]


@router.post(
    "/templates",
    response_model=ReportTemplateOut,
    summary="리포트 템플릿 생성",
)
def create_report_template(
    req: ReportTemplateCreate,
    db: Session = Depends(get_db),
):
    """
    새로운 리포트 템플릿을 생성합니다.

    **요청 본문**:
    ```json
    {
      "name": "월간 강남 신축",
      "description": "강남구의 신축 물건 월간 리포트",
      "filters": {
        "address_sigungu": {"operator": "eq", "value": "강남구"},
        "building_area": {"operator": "between", "value": [100, 150]}
      },
      "grouping": "property_type",
      "aggregations": [
        {"field": "appraisal_value", "func": "avg"},
        {"field": "hammer_rate", "func": "avg"}
      ],
      "schedule": "0 0 1 * *",
      "notify_slack": true
    }
    ```
    """
    try:
        template = report_service.create_template(
            db=db,
            name=req.name,
            description=req.description,
            filters=req.filters,
            grouping=req.grouping,
            aggregations=req.aggregations,
            schedule=req.schedule,
            notify_slack=req.notify_slack,
            notify_email=req.notify_email,
            webhook_url=req.webhook_url,
        )

        return ReportTemplateOut.from_orm(template)

    except Exception as e:
        logger.error(f"리포트 템플릿 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/templates",
    summary="리포트 템플릿 목록",
)
def list_report_templates(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    리포트 템플릿 목록을 조회합니다 (최신순).

    **쿼리 파라미터**:
    - `limit`: 조회 항목 수
    - `offset`: 시작 위치
    """
    try:
        templates, total = report_service.list_templates(db, limit, offset)

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "templates": [ReportTemplateOut.from_orm(t) for t in templates],
        }

    except Exception as e:
        logger.error(f"리포트 템플릿 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/templates/{template_id}",
    response_model=ReportTemplateOut,
    summary="리포트 템플릿 조회",
)
def get_report_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    """
    특정 리포트 템플릿을 조회합니다.
    """
    template = report_service.get_template(db, template_id)

    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"리포트 템플릿을 찾을 수 없음: {template_id}",
        )

    return ReportTemplateOut.from_orm(template)


@router.put(
    "/templates/{template_id}",
    response_model=ReportTemplateOut,
    summary="리포트 템플릿 수정",
)
def update_report_template(
    template_id: int,
    req: ReportTemplateUpdate,
    db: Session = Depends(get_db),
):
    """
    리포트 템플릿을 수정합니다.
    """
    try:
        # None 값 제외
        update_data = {k: v for k, v in req.dict().items() if v is not None}

        template = report_service.update_template(db, template_id, **update_data)

        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"리포트 템플릿을 찾을 수 없음: {template_id}",
            )

        return ReportTemplateOut.from_orm(template)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"리포트 템플릿 수정 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/templates/{template_id}",
    summary="리포트 템플릿 삭제",
)
def delete_report_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    """
    리포트 템플릿을 삭제합니다.
    """
    success = report_service.delete_template(db, template_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"리포트 템플릿을 찾을 수 없음: {template_id}",
        )

    return {"status": "deleted", "template_id": template_id}


@router.post(
    "/templates/{template_id}/execute",
    summary="리포트 템플릿 실행",
)
def execute_report_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    """
    리포트 템플릿을 즉시 실행합니다.

    **응답**:
    ```json
    {
      "template_id": 1,
      "execution_id": 123,
      "status": "success",
      "rows_processed": 500,
      "execution_time_ms": 1234.5,
      "data": [
        {
          "property_type": "아파트",
          "appraisal_value_avg": 500000000,
          "hammer_rate_avg": 0.85
        }
      ]
    }
    ```
    """
    try:
        result = report_service.execute_template(db, template_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"리포트 템플릿을 찾을 수 없음: {template_id}",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"리포트 실행 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/executions",
    summary="리포트 실행 히스토리",
)
def get_report_executions(
    template_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    """
    리포트 실행 히스토리를 조회합니다 (최신순).

    **쿼리 파라미터**:
    - `template_id`: 특정 템플릿만 조회 (선택)
    - `limit`: 조회 항목 수
    """
    executions = report_service.get_execution_history(
        db,
        template_id=template_id,
        limit=limit,
    )

    return {
        "total": len(executions),
        "executions": [
            {
                "id": e.id,
                "template_id": e.template_id,
                "status": e.status,
                "rows_processed": e.rows_processed,
                "execution_time_ms": e.execution_time_ms,
                "error_message": e.error_message,
                "executed_at": e.executed_at,
            }
            for e in executions
        ],
    }


@router.get(
    "/executions/{execution_id}",
    summary="리포트 실행 결과 조회",
)
def get_report_result(
    execution_id: int,
    db: Session = Depends(get_db),
):
    """
    리포트 실행 결과를 조회합니다.

    **응답**:
    ```json
    {
      "id": 123,
      "template_id": 1,
      "execution_id": 123,
      "data": [
        {
          "property_type": "아파트",
          "appraisal_value_avg": 500000000
        }
      ],
      "created_at": "2026-09-01T10:30:00"
    }
    ```
    """
    result = report_service.get_execution_result(db, execution_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"리포트 결과를 찾을 수 없음: {execution_id}",
        )

    return {
        "id": result.id,
        "template_id": result.template_id,
        "execution_id": result.execution_id,
        "data": result.data,
        "created_at": result.created_at,
    }
