"""
DB 연결 풀 최적화 모듈

성능 목표:
  - 동시 처리: 1600 rps → 2000 rps (25% 향상)
  - 연결 대기: 최소화
  - 메모리: 효율적 관리
"""

import logging
from sqlalchemy import create_engine, event
from sqlalchemy.pool import QueuePool, NullPool
from typing import Optional

logger = logging.getLogger(__name__)


class PoolConfig:
    """연결 풀 설정"""

    # 기본 파라미터 (기존)
    POOL_SIZE_OLD = 5
    MAX_OVERFLOW_OLD = 10

    # 최적화된 파라미터 (Tuesday 튜닝)
    POOL_SIZE_NEW = 20  # 기본 연결 수: 5 → 20
    MAX_OVERFLOW_NEW = 20  # 추가 연결: 10 → 20
    POOL_TIMEOUT = 30  # 연결 대기 타임아웃: 30초
    POOL_RECYCLE = 3600  # 연결 재활용 간격: 1시간
    POOL_PRE_PING = True  # 연결 상태 검증
    ECHO_POOL = False  # 풀 디버그 로깅 (프로덕션: False)


class DatabasePoolManager:
    """DB 연결 풀 관리"""

    _engine = None
    _session_factory = None

    @classmethod
    def initialize_optimized_pool(
        cls,
        database_url: str,
        pool_size: int = PoolConfig.POOL_SIZE_NEW,
        max_overflow: int = PoolConfig.MAX_OVERFLOW_NEW,
        pool_timeout: int = PoolConfig.POOL_TIMEOUT,
        pool_recycle: int = PoolConfig.POOL_RECYCLE,
    ):
        """
        최적화된 연결 풀로 엔진 초기화

        Args:
            database_url: DB 연결 문자열 (sqlite:///... 또는 postgresql://...)
            pool_size: 기본 연결 수 (default: 20)
            max_overflow: 추가 연결 수 (default: 20)
            pool_timeout: 연결 대기 타임아웃 (초)
            pool_recycle: 연결 재활용 간격 (초)
        """

        try:
            # ✅ Issue 6 수정: DB 타입 자동 감지
            is_sqlite = "sqlite" in database_url.lower()
            is_postgresql = "postgresql" in database_url.lower()

            # ✅ Issue 6 수정: DB별 설정 분기
            if is_sqlite:
                # SQLite는 단일 연결만 지원
                poolclass = NullPool
                actual_pool_size = 1
                actual_max_overflow = 0
                actual_pool_recycle = None
                connect_args = {
                    "timeout": 10,
                    "check_same_thread": False,
                }
            else:  # PostgreSQL 등
                poolclass = QueuePool
                actual_pool_size = pool_size
                actual_max_overflow = max_overflow
                actual_pool_recycle = pool_recycle
                connect_args = {
                    "connect_timeout": 10,
                    "application_name": "avm_system",
                }

            cls._engine = create_engine(
                database_url,
                # 연결 풀 설정
                poolclass=poolclass,
                pool_size=actual_pool_size,
                max_overflow=actual_max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=actual_pool_recycle,
                pool_pre_ping=PoolConfig.POOL_PRE_PING,
                echo=False,
                echo_pool=PoolConfig.ECHO_POOL,
                # 연결 최적화
                connect_args=connect_args,
            )

            # 연결 풀 이벤트 리스너 등록
            cls._register_pool_listeners()

            logger.info(
                f"""
✅ DB 연결 풀 최적화 초기화
  - Pool Size: {pool_size}
  - Max Overflow: {max_overflow}
  - Pool Timeout: {pool_timeout}s
  - Pool Recycle: {pool_recycle}s
  - Pre-Ping: {PoolConfig.POOL_PRE_PING}
                """
            )

            return cls._engine

        except Exception as e:
            logger.error(f"❌ DB 연결 풀 초기화 실패: {str(e)}")
            raise

    @classmethod
    def _register_pool_listeners(cls):
        """연결 풀 이벤트 리스너 등록"""

        @event.listens_for(cls._engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """새 연결 생성 시"""
            logger.debug("✅ DB 연결 생성")

        @event.listens_for(cls._engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """연결을 풀로 반환 시"""
            logger.debug("📤 DB 연결 반환")

        @event.listens_for(cls._engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """풀에서 연결 대여 시"""
            logger.debug("📥 DB 연결 대여")

        @event.listens_for(cls._engine, "pool_connect")
        def receive_pool_connect(dbapi_conn, connection_record):
            """풀에서 새 연결 생성 시"""
            pass

        @event.listens_for(cls._engine, "pool_detach")
        def receive_pool_detach(dbapi_conn, connection_record):
            """연결을 풀에서 분리 시"""
            logger.warning("⚠️ DB 연결 풀 분리")

        @event.listens_for(cls._engine, "close")
        def receive_close(dbapi_conn, connection_record):
            """연결 종료 시"""
            logger.debug("❌ DB 연결 종료")

    @classmethod
    def get_pool_stats(cls) -> dict:
        """연결 풀 통계"""

        if not cls._engine:
            return {"status": "not_initialized"}

        pool = cls._engine.pool

        return {
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": pool.size() + pool.overflow(),
            "queue_size": pool.queue.qsize() if hasattr(pool, "queue") else 0,
        }

    @classmethod
    def dispose_all_connections(cls):
        """모든 연결 종료 (graceful shutdown)"""

        if cls._engine:
            cls._engine.dispose()
            logger.info("🔌 모든 DB 연결 종료")

    @classmethod
    def get_engine(cls):
        """엔진 반환"""
        if not cls._engine:
            raise RuntimeError("Engine not initialized. Call initialize_optimized_pool() first.")
        return cls._engine


class PoolOptimizationMonitor:
    """연결 풀 성능 모니터링"""

    # 성능 기준
    TARGET_RPS = 2000  # 목표: 2000 rps
    TARGET_P95_LATENCY_MS = 100  # 목표 p95: 100ms
    POOL_UTILIZATION_THRESHOLD = 0.8  # 경고: 80% 이상 사용

    @staticmethod
    def check_pool_health() -> dict:
        """연결 풀 상태 확인"""

        stats = DatabasePoolManager.get_pool_stats()

        if stats.get("status") == "not_initialized":
            return {"status": "not_initialized"}

        pool_size = stats.get("pool_size", 0)
        total_connections = stats.get("total_connections", 0)

        utilization = (
            (stats.get("checked_out", 0) / total_connections * 100)
            if total_connections > 0
            else 0
        )

        health_status = "healthy"
        if utilization > PoolOptimizationMonitor.POOL_UTILIZATION_THRESHOLD * 100:
            health_status = "warning"
        if utilization > 95:
            health_status = "critical"

        return {
            "status": health_status,
            "pool_size": pool_size,
            "checked_out": stats.get("checked_out", 0),
            "overflow": stats.get("overflow", 0),
            "total_connections": total_connections,
            "utilization_percent": round(utilization, 2),
            "target_rps": PoolOptimizationMonitor.TARGET_RPS,
        }

    @staticmethod
    def log_pool_stats():
        """연결 풀 통계 로깅"""

        health = PoolOptimizationMonitor.check_pool_health()

        if health.get("status") == "not_initialized":
            logger.warning("연결 풀이 초기화되지 않음")
            return

        logger.info(
            f"""
📊 ===== DB 연결 풀 상태 =====
상태: {health.get('status')}
기본 풀 크기: {health.get('pool_size')}
대출 중: {health.get('checked_out')}
오버플로우: {health.get('overflow')}
총 연결: {health.get('total_connections')}
사용률: {health.get('utilization_percent')}%
목표 RPS: {PoolOptimizationMonitor.TARGET_RPS}
============================
        """
        )

    @staticmethod
    def get_optimization_recommendations() -> list:
        """최적화 권장사항"""

        health = PoolOptimizationMonitor.check_pool_health()
        recommendations = []

        if health.get("status") == "not_initialized":
            recommendations.append("🔴 DB 연결 풀이 초기화되지 않음")
            return recommendations

        utilization = health.get("utilization_percent", 0)

        if utilization > 80:
            recommendations.append(f"🟡 연결 풀 사용률 높음 ({utilization}%)")
            recommendations.append("   → pool_size 증가 고려 또는 쿼리 최적화")

        if health.get("overflow", 0) > 5:
            recommendations.append(
                f"🟡 오버플로우 연결 많음 ({health.get('overflow')}개)"
            )
            recommendations.append("   → 동시 요청 증가 또는 느린 쿼리 확인")

        if not recommendations:
            recommendations.append("✅ DB 연결 풀이 최적 상태입니다")

        return recommendations


# 사용 예
if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    # 1. 최적화된 풀로 초기화
    engine = DatabasePoolManager.initialize_optimized_pool(
        "sqlite:///avm.db",
        pool_size=20,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
    )

    # 2. 연결 풀 상태 확인
    PoolOptimizationMonitor.log_pool_stats()

    # 3. 권장사항 확인
    recommendations = PoolOptimizationMonitor.get_optimization_recommendations()
    for rec in recommendations:
        logger.info(rec)

    # 4. Graceful shutdown
    DatabasePoolManager.dispose_all_connections()
