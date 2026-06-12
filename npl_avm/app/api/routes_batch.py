import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.batch_schemas import (
    BatchAVMRequest,
    BatchAVMResponse,
    BatchStatus,
)
from app.services.batch_service import batch_processor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch", tags=["batch"])


@router.post(
    "/estimate",
    response_model=BatchAVMResponse,
    summary="배치 AVM 감정가 추정",
    description="여러 물건을 한 번에 처리 (최대 1000건)",
)
def batch_estimate(
    req: BatchAVMRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
) -> BatchAVMResponse:
    """
    배치 모드로 여러 물건의 감정가를 동시에 추정합니다.

    **요청 예시**:
    ```json
    {
      "items": [
        {
          "address_sido": "경기도",
          "address_sigungu": "용인시",
          "property_type": "아파트",
          "building_area": 84.5
        },
        {
          "address_sido": "서울시",
          "address_sigungu": "강남구",
          "property_type": "아파트",
          "building_area": 113.2
        }
      ],
      "timeout_seconds": 300
    }
    ```

    **응답**:
    ```json
    {
      "batch_id": "abc123def",
      "status": "completed",
      "total_items": 2,
      "completed_items": 2,
      "failed_items": 0,
      "results": [
        {
          "item_id": "item1",
          "status": "success",
          "estimated_value": 450000000,
          "confidence": "high",
          "comparable_count": 5,
          "processing_time_ms": 145.5
        }
      ],
      "started_at": "2026-09-01T09:00:00",
      "completed_at": "2026-09-01T09:05:12",
      "total_time_ms": 312456.0
    }
    ```
    """
    try:
        response = batch_processor.process_batch(
            items=req.items,
            db=db,
            timeout_seconds=req.timeout_seconds,
        )

        logger.info(
            f"배치 처리 완료: {response.batch_id}, "
            f"성공: {response.completed_items}/{response.total_items}"
        )

        # 정기 정리 작업 스케줄 (7일 이상 된 배치 삭제)
        if background_tasks:
            background_tasks.add_task(batch_processor.cleanup_old_batches, days=7)

        return response

    except Exception as e:
        logger.error(f"배치 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{batch_id}/status",
    response_model=BatchStatus,
    summary="배치 처리 상태 조회",
    description="배치 ID로 진행 상황을 확인합니다",
)
def get_batch_status(batch_id: str) -> BatchStatus:
    """
    배치 처리의 현재 상태를 조회합니다.

    **경로 파라미터**:
    - `batch_id`: 배치 고유 ID (처리 결과에서 반환)

    **응답**:
    ```json
    {
      "batch_id": "abc123def",
      "status": "processing",
      "progress": "50 of 100",
      "completed_items": 50,
      "failed_items": 2,
      "total_items": 100,
      "started_at": "2026-09-01T09:00:00",
      "estimated_completion_at": "2026-09-01T09:10:30"
    }
    ```
    """
    status = batch_processor.get_batch_status(batch_id)

    if status is None:
        raise HTTPException(
            status_code=404, detail=f"배치를 찾을 수 없음: {batch_id}"
        )

    return status


@router.get(
    "/history",
    summary="배치 처리 히스토리",
    description="최근 배치 처리 기록을 조회합니다 (최대 10개)",
)
def get_batch_history(limit: int = 10):
    """
    최근 배치 처리 히스토리를 조회합니다 (기본 10개).

    **쿼리 파라미터**:
    - `limit`: 조회 항목 수 (기본: 10, 최대: 100)

    **응답**:
    ```json
    {
      "batches": [
        {
          "batch_id": "abc123def",
          "status": "completed",
          "total_items": 100,
          "completed_items": 98,
          "failed_items": 2,
          "started_at": "2026-09-01T09:00:00",
          "completed_at": "2026-09-01T09:05:12"
        }
      ]
    }
    ```
    """
    limit = min(limit, 100)  # 최대 100개 제한
    history = batch_processor.get_batch_history(limit=limit)

    return {
        "total": len(history),
        "batches": history,
    }
