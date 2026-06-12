from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class BatchAVMItem(BaseModel):
    """배치 요청 항목"""
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    address_sido: str
    address_sigungu: str
    property_type: str
    land_area: Optional[float] = None
    building_area: Optional[float] = None
    max_comparables: int = 10


class BatchAVMRequest(BaseModel):
    """배치 처리 요청"""
    items: List[BatchAVMItem] = Field(..., max_items=1000)
    timeout_seconds: int = Field(300, ge=30, le=600)


class BatchAVMItemResult(BaseModel):
    """배치 항목 결과"""
    item_id: str
    status: str  # "success" | "error" | "timeout"
    estimated_value: Optional[int] = None
    confidence: Optional[str] = None
    comparable_count: Optional[int] = None
    error: Optional[str] = None
    processing_time_ms: float


class BatchAVMResponse(BaseModel):
    """배치 처리 응답"""
    batch_id: str
    status: str  # "completed" | "processing" | "failed"
    total_items: int
    completed_items: int
    failed_items: int
    results: List[BatchAVMItemResult]
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_time_ms: float


class BatchStatus(BaseModel):
    """배치 상태 조회 응답"""
    batch_id: str
    status: str
    progress: str  # "50 of 100"
    completed_items: int
    failed_items: int
    total_items: int
    started_at: datetime
    estimated_completion_at: Optional[datetime] = None


class BatchHistoryItem(BaseModel):
    """배치 히스토리"""
    batch_id: str
    status: str
    total_items: int
    completed_items: int
    failed_items: int
    created_at: datetime
    completed_at: Optional[datetime] = None
