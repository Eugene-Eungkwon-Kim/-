import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RequestMetric:
    """요청 메트릭"""
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None


@dataclass
class SystemMetric:
    """시스템 메트릭"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DatabaseMetric:
    """데이터베이스 메트릭"""
    query: str
    execution_time_ms: float
    rows_affected: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None


class MetricsCollector:
    """메트릭 수집기"""

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.request_metrics: List[RequestMetric] = []
        self.system_metrics: List[SystemMetric] = []
        self.database_metrics: List[DatabaseMetric] = []

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
        error: Optional[str] = None,
    ):
        """요청 메트릭 기록"""
        metric = RequestMetric(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            latency_ms=latency_ms,
            error=error,
        )
        self.request_metrics.append(metric)

        # 히스토리 크기 제한
        if len(self.request_metrics) > self.max_history:
            self.request_metrics = self.request_metrics[-self.max_history :]

    def record_system(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float,
    ):
        """시스템 메트릭 기록"""
        metric = SystemMetric(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
        )
        self.system_metrics.append(metric)

        if len(self.system_metrics) > self.max_history:
            self.system_metrics = self.system_metrics[-self.max_history :]

    def record_database(
        self,
        query: str,
        execution_time_ms: float,
        rows_affected: int = 0,
        error: Optional[str] = None,
    ):
        """데이터베이스 메트릭 기록"""
        metric = DatabaseMetric(
            query=query[:100],  # 쿼리 제한
            execution_time_ms=execution_time_ms,
            rows_affected=rows_affected,
            error=error,
        )
        self.database_metrics.append(metric)

        if len(self.database_metrics) > self.max_history:
            self.database_metrics = self.database_metrics[-self.max_history :]

    def get_request_stats(self, minutes: int = 5) -> Dict:
        """요청 통계 (최근 N분)"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent = [m for m in self.request_metrics if m.timestamp > cutoff_time]

        if not recent:
            return {
                "period_minutes": minutes,
                "total_requests": 0,
                "p50_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
                "error_rate": 0,
                "avg_latency_ms": 0,
            }

        latencies = sorted([m.latency_ms for m in recent])
        errors = sum(1 for m in recent if m.status_code >= 400)
        error_rate = errors / len(recent) if recent else 0

        return {
            "period_minutes": minutes,
            "total_requests": len(recent),
            "p50_latency_ms": latencies[len(latencies) // 2],
            "p95_latency_ms": latencies[int(len(latencies) * 0.95)],
            "p99_latency_ms": latencies[int(len(latencies) * 0.99)],
            "error_rate": error_rate,
            "avg_latency_ms": sum(latencies) / len(latencies),
            "requests_by_status": {
                "2xx": sum(1 for m in recent if 200 <= m.status_code < 300),
                "4xx": sum(1 for m in recent if 400 <= m.status_code < 500),
                "5xx": sum(1 for m in recent if 500 <= m.status_code < 600),
            },
        }

    def get_database_stats(self, minutes: int = 5) -> Dict:
        """데이터베이스 통계 (최근 N분)"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent = [m for m in self.database_metrics if m.timestamp > cutoff_time]

        if not recent:
            return {
                "period_minutes": minutes,
                "total_queries": 0,
                "p50_execution_time_ms": 0,
                "p95_execution_time_ms": 0,
                "p99_execution_time_ms": 0,
                "error_count": 0,
                "avg_execution_time_ms": 0,
            }

        times = sorted([m.execution_time_ms for m in recent])
        errors = sum(1 for m in recent if m.error)

        return {
            "period_minutes": minutes,
            "total_queries": len(recent),
            "p50_execution_time_ms": times[len(times) // 2],
            "p95_execution_time_ms": times[int(len(times) * 0.95)],
            "p99_execution_time_ms": times[int(len(times) * 0.99)],
            "error_count": errors,
            "avg_execution_time_ms": sum(times) / len(times),
        }

    def get_system_stats(self, minutes: int = 5) -> Dict:
        """시스템 통계 (최근 N분)"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent = [m for m in self.system_metrics if m.timestamp > cutoff_time]

        if not recent:
            return {
                "period_minutes": minutes,
                "avg_cpu_percent": 0,
                "avg_memory_percent": 0,
                "avg_disk_percent": 0,
                "max_cpu_percent": 0,
                "max_memory_percent": 0,
                "max_disk_percent": 0,
            }

        cpus = [m.cpu_percent for m in recent]
        mems = [m.memory_percent for m in recent]
        disks = [m.disk_percent for m in recent]

        return {
            "period_minutes": minutes,
            "avg_cpu_percent": sum(cpus) / len(cpus),
            "avg_memory_percent": sum(mems) / len(mems),
            "avg_disk_percent": sum(disks) / len(disks),
            "max_cpu_percent": max(cpus),
            "max_memory_percent": max(mems),
            "max_disk_percent": max(disks),
        }

    def get_slowest_queries(self, limit: int = 10) -> List[Dict]:
        """가장 느린 쿼리"""
        sorted_queries = sorted(
            self.database_metrics,
            key=lambda x: x.execution_time_ms,
            reverse=True,
        )[:limit]

        return [
            {
                "query": q.query,
                "execution_time_ms": q.execution_time_ms,
                "timestamp": q.timestamp,
            }
            for q in sorted_queries
        ]

    def get_error_summary(self) -> Dict:
        """에러 요약"""
        errors = [m for m in self.request_metrics if m.error]

        error_types = {}
        for error in errors:
            error_type = type(error).__name__
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "recent_errors": [
                {"endpoint": e.endpoint, "error": e.error, "timestamp": e.timestamp}
                for e in errors[-10:]
            ],
        }

    def clear_old_metrics(self, days: int = 7):
        """오래된 메트릭 정리"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        self.request_metrics = [
            m for m in self.request_metrics if m.timestamp > cutoff_time
        ]
        self.system_metrics = [
            m for m in self.system_metrics if m.timestamp > cutoff_time
        ]
        self.database_metrics = [
            m for m in self.database_metrics if m.timestamp > cutoff_time
        ]

        logger.info(f"메트릭 정리 완료 ({days}일 이상 제거)")


# 글로벌 메트릭 수집기
metrics_collector = MetricsCollector()
