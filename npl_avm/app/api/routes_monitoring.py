import logging
from fastapi import APIRouter, Query
from app.monitoring.metrics import metrics_collector
from app.monitoring.anomaly_detector import anomaly_detector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get(
    "/health",
    summary="시스템 헬스 체크",
)
def health_check():
    """
    시스템 상태를 확인합니다.

    **응답**:
    ```json
    {
      "status": "healthy",
      "timestamp": "2026-09-01T10:00:00"
    }
    ```
    """
    return {
        "status": "healthy",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    }


@router.get(
    "/metrics/requests",
    summary="요청 메트릭",
    description="최근 요청 메트릭을 조회합니다",
)
def get_request_metrics(
    minutes: int = Query(5, ge=1, le=60, description="조회 기간 (분)"),
):
    """
    최근 요청 메트릭 통계를 조회합니다.

    **응답**:
    ```json
    {
      "period_minutes": 5,
      "total_requests": 120,
      "avg_latency_ms": 145.5,
      "p50_latency_ms": 120,
      "p95_latency_ms": 320,
      "p99_latency_ms": 450,
      "error_rate": 0.02,
      "requests_by_status": {
        "2xx": 110,
        "4xx": 8,
        "5xx": 2
      }
    }
    ```
    """
    return metrics_collector.get_request_stats(minutes=minutes)


@router.get(
    "/metrics/database",
    summary="데이터베이스 메트릭",
    description="최근 데이터베이스 메트릭을 조회합니다",
)
def get_database_metrics(
    minutes: int = Query(5, ge=1, le=60),
):
    """
    최근 데이터베이스 메트릭 통계를 조회합니다.

    **응답**:
    ```json
    {
      "period_minutes": 5,
      "total_queries": 250,
      "avg_execution_time_ms": 45.2,
      "p50_execution_time_ms": 20,
      "p95_execution_time_ms": 150,
      "p99_execution_time_ms": 300,
      "error_count": 0
    }
    ```
    """
    return metrics_collector.get_database_stats(minutes=minutes)


@router.get(
    "/metrics/system",
    summary="시스템 리소스 메트릭",
    description="CPU, 메모리, 디스크 사용량을 조회합니다",
)
def get_system_metrics(
    minutes: int = Query(5, ge=1, le=60),
):
    """
    최근 시스템 리소스 메트릭을 조회합니다.

    **응답**:
    ```json
    {
      "period_minutes": 5,
      "avg_cpu_percent": 35.5,
      "avg_memory_percent": 45.2,
      "avg_disk_percent": 60.0,
      "max_cpu_percent": 72.1,
      "max_memory_percent": 68.5,
      "max_disk_percent": 62.3
    }
    ```
    """
    return metrics_collector.get_system_stats(minutes=minutes)


@router.get(
    "/metrics/slow-queries",
    summary="느린 쿼리 목록",
    description="가장 느린 데이터베이스 쿼리를 조회합니다",
)
def get_slow_queries(
    limit: int = Query(10, ge=1, le=50),
):
    """
    실행 시간이 가장 긴 데이터베이스 쿼리 목록을 조회합니다.

    **응답**:
    ```json
    {
      "total": 3,
      "queries": [
        {
          "query": "SELECT * FROM precedents WHERE...",
          "execution_time_ms": 850.5,
          "timestamp": "2026-09-01T10:00:00"
        }
      ]
    }
    ```
    """
    queries = metrics_collector.get_slowest_queries(limit=limit)
    return {
        "total": len(queries),
        "queries": queries,
    }


@router.get(
    "/metrics/errors",
    summary="에러 요약",
    description="최근 발생한 에러를 조회합니다",
)
def get_error_summary():
    """
    최근 에러 요약을 조회합니다.

    **응답**:
    ```json
    {
      "total_errors": 5,
      "error_types": {
        "ValidationError": 2,
        "DatabaseError": 2,
        "TimeoutError": 1
      },
      "recent_errors": [
        {
          "endpoint": "/api/v1/avm/estimate",
          "error": "Address not found",
          "timestamp": "2026-09-01T10:00:00"
        }
      ]
    }
    ```
    """
    return metrics_collector.get_error_summary()


@router.get(
    "/anomalies/check",
    summary="이상 탐지",
    description="현재 메트릭에서 이상을 탐지합니다",
)
def check_anomalies(
    check_historical: bool = Query(True, description="히스토리 데이터도 확인"),
):
    """
    현재 메트릭을 분석하여 이상을 탐지합니다.

    **응답**:
    ```json
    {
      "anomaly_count": 2,
      "has_critical": true,
      "anomalies": [
        {
          "type": "threshold",
          "rule": "p99_latency_high",
          "severity": "critical",
          "metric": "p99_latency_ms",
          "value": 1250.5,
          "threshold": 1000,
          "message": "p99_latency_high: 1250.5 > 1000"
        },
        {
          "type": "statistical",
          "metric": "latency_ms",
          "value": 450.2,
          "mean": 145.3,
          "std": 50.1,
          "message": "latency_ms의 비정상 값: 450.2"
        }
      ]
    }
    ```
    """
    # 현재 메트릭 수집
    request_stats = metrics_collector.get_request_stats(minutes=5)
    system_stats = metrics_collector.get_system_stats(minutes=5)

    current_metrics = {
        "p95_latency_ms": request_stats.get("p95_latency_ms", 0),
        "p99_latency_ms": request_stats.get("p99_latency_ms", 0),
        "error_rate": request_stats.get("error_rate", 0),
        "cpu_percent": system_stats.get("avg_cpu_percent", 0),
        "memory_percent": system_stats.get("avg_memory_percent", 0),
    }

    # 히스토리 데이터 (선택사항)
    historical_data = None
    if check_historical:
        historical_data = {
            "p95_latency_ms": [
                m.latency_ms for m in metrics_collector.request_metrics[-100:]
            ],
        }

    # 이상 탐지
    result = anomaly_detector.detect_all(
        metrics=current_metrics,
        historical_data=historical_data,
    )

    return result


@router.get(
    "/alerts/rules",
    summary="알림 규칙 목록",
    description="설정된 이상 탐지 규칙을 조회합니다",
)
def get_alert_rules():
    """
    설정된 이상 탐지 규칙 목록을 조회합니다.

    **응답**:
    ```json
    {
      "total": 5,
      "rules": [
        {
          "name": "p95_latency_high",
          "metric": "p95_latency_ms",
          "operator": ">",
          "threshold": 500,
          "severity": "warning"
        }
      ]
    }
    ```
    """
    rules = [
        {
            "name": rule.name,
            "metric": rule.metric,
            "operator": rule.operator,
            "threshold": rule.threshold,
            "severity": rule.severity,
        }
        for rule in anomaly_detector.rules
    ]

    return {
        "total": len(rules),
        "rules": rules,
    }


@router.post(
    "/metrics/clear",
    summary="메트릭 초기화",
    description="오래된 메트릭 데이터를 정리합니다",
)
def clear_old_metrics(
    days: int = Query(7, ge=1, le=30, description="며칠 이상 된 데이터 제거"),
):
    """
    지정된 기간 이상 된 메트릭 데이터를 삭제합니다.

    **쿼리 파라미터**:
    - `days`: 며칠 이상 된 데이터를 제거할지 (기본: 7일)

    **응답**:
    ```json
    {
      "status": "cleared",
      "days": 7,
      "message": "7일 이상 된 메트릭 데이터를 정리했습니다"
    }
    ```
    """
    metrics_collector.clear_old_metrics(days=days)

    return {
        "status": "cleared",
        "days": days,
        "message": f"{days}일 이상 된 메트릭 데이터를 정리했습니다",
    }
