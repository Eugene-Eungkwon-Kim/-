"""
Pydantic 모델 및 데이터 스키마
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


# ============================================
# 인증 관련 모델
# ============================================
class LoginRequest(BaseModel):
    """로그인 요청"""
    email: str = Field(..., example="admin@avm.com")
    password: str = Field(..., example="demo123")


class LoginResponse(BaseModel):
    """로그인 응답"""
    access_token: str
    token_type: str = "bearer"
    user: "UserInfo"


class UserInfo(BaseModel):
    """사용자 정보"""
    email: str
    name: str
    role: str


# ============================================
# 대시보드 관련 모델
# ============================================
class DashboardSummary(BaseModel):
    """대시보드 요약"""
    ensemble_r2: float = Field(..., example=0.8450)
    ensemble_rmse: float = Field(..., example=55200000)
    ensemble_mae: float = Field(..., example=42300000)
    status: str = Field(..., example="healthy")
    last_updated: datetime
    previous_r2: Optional[float] = None
    change_rate: Optional[float] = None


class TrendData(BaseModel):
    """추세 데이터"""
    week: str = Field(..., example="1주")
    r2: float = Field(..., example=0.8200)


class TrendResponse(BaseModel):
    """추세 응답"""
    data: List[TrendData]


class TrainingRecord(BaseModel):
    """재학습 기록"""
    date: str
    status: str = Field(..., example="success")
    r2: float
    rmse: float
    duration: str


class RecentTrainingsResponse(BaseModel):
    """최근 재학습 응답"""
    data: List[TrainingRecord]


class Statistics(BaseModel):
    """통계 정보"""
    highest_r2: float
    average_r2: float
    improvement: str
    training_count: int


# ============================================
# 모델 관련 모델
# ============================================
class ModelInfo(BaseModel):
    """모델 정보"""
    id: str
    name: str
    type: str
    created: datetime
    last_training: datetime
    data_size: int
    features: int
    r2: float
    mae: float
    rmse: float
    mape: float


class FeatureImportance(BaseModel):
    """특성 중요도"""
    name: str
    importance: float


class FeatureImportanceResponse(BaseModel):
    """특성 중요도 응답"""
    data: List[FeatureImportance]


class DeploymentStatus(BaseModel):
    """배포 상태"""
    status: str
    message: str
    deployed_at: datetime


# ============================================
# 데이터 관련 모델
# ============================================
class DataQuality(BaseModel):
    """데이터 품질"""
    total_rows: int
    missing_values: int
    missing_percentage: float
    outliers: int
    outlier_percentage: float
    quality_score: float
    status: str


class PriceDistribution(BaseModel):
    """가격 분포"""
    range: str
    count: int


class PriceDistributionResponse(BaseModel):
    """가격 분포 응답"""
    data: List[PriceDistribution]


class RegionDistribution(BaseModel):
    """지역 분포"""
    name: str
    value: int


class RegionDistributionResponse(BaseModel):
    """지역 분포 응답"""
    data: List[RegionDistribution]


# ============================================
# 설정 관련 모델
# ============================================
class ModelSettings(BaseModel):
    """모델 설정"""
    auto_retrain: bool
    retrain_schedule: str
    performance_threshold: float
    alert_on_degradation: bool


class DataSettings(BaseModel):
    """데이터 설정"""
    data_path: str
    preprocessing_enabled: bool
    feature_engineering_enabled: bool


class NotificationSettings(BaseModel):
    """알림 설정"""
    email_alert: bool
    email_address: Optional[str] = None
    slack_alert: bool
    slack_webhook: Optional[str] = None


class SystemSettings(BaseModel):
    """시스템 설정"""
    log_level: str
    backup_frequency: str
    api_timeout: int


class FullSettings(BaseModel):
    """전체 설정"""
    auto_retrain: bool
    retrain_schedule: str
    performance_threshold: float
    email_alert: bool
    email_address: Optional[str]
    slack_alert: bool
    log_level: str


# ============================================
# 재학습 관련 모델
# ============================================
class RetrainingStatus(BaseModel):
    """재학습 상태"""
    status: str = Field(..., example="idle")
    last_training: datetime
    next_training: datetime
    progress: Optional[int] = None


class RetrainingHistory(BaseModel):
    """재학습 이력"""
    date: str
    status: str
    r2: float
    duration_minutes: int


class RetrainingHistoryResponse(BaseModel):
    """재학습 이력 응답"""
    data: List[RetrainingHistory]


# ============================================
# 모니터링 관련 모델
# ============================================
class PerformanceMetrics(BaseModel):
    """성능 메트릭"""
    ensemble_r2: float
    ensemble_rmse: float
    ensemble_mae: float
    timestamp: datetime


class Alert(BaseModel):
    """알림"""
    id: str
    type: str
    message: str
    severity: str = Field(..., example="warning")
    timestamp: datetime


class AlertsResponse(BaseModel):
    """알림 응답"""
    data: List[Alert]


class HealthStatus(BaseModel):
    """헬스 상태"""
    status: str
    timestamp: datetime
    version: str


# ============================================
# 예측 관련 모델
# ============================================
class PredictionInput(BaseModel):
    """예측 입력"""
    features: Dict[str, Any]
    model_id: Optional[str] = None


class PredictionOutput(BaseModel):
    """예측 출력"""
    prediction: float
    model_id: str
    timestamp: datetime
    confidence: Optional[float] = None


# ============================================
# 에러 응답 모델
# ============================================
class ErrorResponse(BaseModel):
    """에러 응답"""
    detail: str
    status_code: int
    timestamp: datetime
    request_id: Optional[str] = None
