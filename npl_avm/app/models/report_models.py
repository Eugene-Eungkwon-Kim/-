from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Float
from datetime import datetime
from app.db.models import Base


class ReportTemplate(Base):
    """리포트 템플릿 모델"""

    __tablename__ = "report_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String(1024))
    filters = Column(JSON)  # 필터 조건
    grouping = Column(String(255))  # 그룹핑 필드
    aggregations = Column(JSON)  # 집계 함수 리스트
    schedule = Column(String(255))  # Cron 형식 (예: "0 0 1 * *")
    enabled = Column(Boolean, default=True)
    notify_slack = Column(Boolean, default=False)
    notify_email = Column(Boolean, default=False)
    webhook_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReportExecution(Base):
    """리포트 실행 기록"""

    __tablename__ = "report_executions"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, nullable=False)
    status = Column(String(50))  # "success", "failed", "running"
    rows_processed = Column(Integer)
    execution_time_ms = Column(Float)
    error_message = Column(String(1024))
    executed_at = Column(DateTime, default=datetime.utcnow)


class ReportResult(Base):
    """리포트 결과 저장"""

    __tablename__ = "report_results"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, nullable=False)
    execution_id = Column(Integer, nullable=False)
    data = Column(JSON)  # 결과 데이터
    created_at = Column(DateTime, default=datetime.utcnow)
