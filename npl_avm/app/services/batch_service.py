import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import uuid

from sqlalchemy.orm import Session
from app.avm import engine as avm
from app.schemas.batch_schemas import (
    BatchAVMItem,
    BatchAVMItemResult,
    BatchAVMResponse,
    BatchStatus,
)

logger = logging.getLogger(__name__)


class BatchProcessor:
    """배치 처리 엔진"""

    def __init__(self, max_workers: int = 10, chunk_size: int = 100):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.chunk_size = chunk_size
        self.batch_cache: Dict[str, Dict] = {}

    def process_batch(
        self,
        items: List[BatchAVMItem],
        db: Session,
        timeout_seconds: int = 300,
    ) -> BatchAVMResponse:
        """배치 처리 실행"""
        batch_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        logger.info(f"배치 시작: {batch_id}, {len(items)}개 항목")

        results: List[BatchAVMItemResult] = []

        try:
            # 청크 단위로 처리 (메모리 효율)
            for chunk in self._chunk_items(items, self.chunk_size):
                chunk_results = self._process_chunk(chunk, db, timeout_seconds)
                results.extend(chunk_results)

        except Exception as e:
            logger.error(f"배치 처리 실패: {batch_id}, {str(e)}")
            raise

        completed_at = datetime.utcnow()
        total_time_ms = (completed_at - started_at).total_seconds() * 1000

        # 배치 결과 캐시 저장
        batch_result = {
            "batch_id": batch_id,
            "status": "completed",
            "total_items": len(items),
            "completed_items": sum(1 for r in results if r.status == "success"),
            "failed_items": sum(1 for r in results if r.status == "error"),
            "results": results,
            "started_at": started_at,
            "completed_at": completed_at,
            "total_time_ms": total_time_ms,
        }

        self.batch_cache[batch_id] = batch_result

        logger.info(
            f"배치 완료: {batch_id}, "
            f"성공: {batch_result['completed_items']}/{len(items)}, "
            f"소요시간: {total_time_ms:.0f}ms"
        )

        return BatchAVMResponse(**batch_result)

    def _chunk_items(
        self, items: List[BatchAVMItem], chunk_size: int
    ) -> List[List[BatchAVMItem]]:
        """아이템을 청크로 분할"""
        for i in range(0, len(items), chunk_size):
            yield items[i : i + chunk_size]

    def _process_chunk(
        self,
        chunk: List[BatchAVMItem],
        db: Session,
        timeout_seconds: int,
    ) -> List[BatchAVMItemResult]:
        """청크 단위 처리"""
        results = []

        for item in chunk:
            try:
                result = self._estimate_single(item, db, timeout_seconds)
                results.append(result)
            except Exception as e:
                logger.warning(f"항목 처리 실패: {item.id}, {str(e)}")
                results.append(
                    BatchAVMItemResult(
                        item_id=item.id,
                        status="error",
                        error=str(e),
                        processing_time_ms=0,
                    )
                )

        return results

    def _estimate_single(
        self,
        item: BatchAVMItem,
        db: Session,
        timeout_seconds: int,
    ) -> BatchAVMItemResult:
        """개별 항목 추정"""
        start_time = datetime.utcnow()

        try:
            result = avm.estimate(
                db=db,
                address_sido=item.address_sido,
                address_sigungu=item.address_sigungu,
                property_type=item.property_type,
                land_area=item.land_area,
                building_area=item.building_area,
                max_comparables=item.max_comparables,
            )

            processing_time_ms = (
                datetime.utcnow() - start_time
            ).total_seconds() * 1000

            return BatchAVMItemResult(
                item_id=item.id,
                status="success",
                estimated_value=result.estimated_value,
                confidence=result.confidence,
                comparable_count=result.comparable_count,
                processing_time_ms=processing_time_ms,
            )

        except TimeoutError:
            processing_time_ms = (
                datetime.utcnow() - start_time
            ).total_seconds() * 1000
            return BatchAVMItemResult(
                item_id=item.id,
                status="timeout",
                error="Processing timeout",
                processing_time_ms=processing_time_ms,
            )
        except Exception as e:
            processing_time_ms = (
                datetime.utcnow() - start_time
            ).total_seconds() * 1000
            return BatchAVMItemResult(
                item_id=item.id,
                status="error",
                error=str(e),
                processing_time_ms=processing_time_ms,
            )

    def get_batch_status(self, batch_id: str) -> Optional[BatchStatus]:
        """배치 상태 조회"""
        if batch_id not in self.batch_cache:
            return None

        batch_data = self.batch_cache[batch_id]
        completed_items = batch_data["completed_items"]
        total_items = batch_data["total_items"]

        # 진행 시간 기반 완료 시간 추정
        if batch_data["status"] == "processing":
            elapsed = (datetime.utcnow() - batch_data["started_at"]).total_seconds()
            rate = completed_items / elapsed if elapsed > 0 else 0
            remaining = total_items - completed_items
            estimated_remaining = remaining / rate if rate > 0 else 0
            estimated_completion_at = datetime.utcnow() + timedelta(
                seconds=estimated_remaining
            )
        else:
            estimated_completion_at = batch_data.get("completed_at")

        return BatchStatus(
            batch_id=batch_id,
            status=batch_data["status"],
            progress=f"{completed_items} of {total_items}",
            completed_items=completed_items,
            failed_items=batch_data["failed_items"],
            total_items=total_items,
            started_at=batch_data["started_at"],
            estimated_completion_at=estimated_completion_at,
        )

    def get_batch_history(self, limit: int = 10) -> List[Dict]:
        """배치 히스토리 조회 (최근순)"""
        items = sorted(
            self.batch_cache.values(),
            key=lambda x: x["started_at"],
            reverse=True,
        )
        return items[:limit]

    def cleanup_old_batches(self, days: int = 7):
        """오래된 배치 데이터 정리"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        batch_ids_to_remove = [
            bid
            for bid, data in self.batch_cache.items()
            if data["started_at"] < cutoff_time
        ]

        for bid in batch_ids_to_remove:
            del self.batch_cache[bid]

        logger.info(f"오래된 배치 정리: {len(batch_ids_to_remove)}개")


# 글로벌 배치 프로세서 인스턴스
batch_processor = BatchProcessor(max_workers=10, chunk_size=100)
