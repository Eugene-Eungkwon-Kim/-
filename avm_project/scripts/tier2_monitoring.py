"""Tier 2 모니터링: 5개 메트릭 추적

메트릭:
  1. 데이터 수집 지연시간
  2. API 오류율
  3. P99 응답시간
  4. 메모리 사용량
  5. DB 연결 풀

실행:
    python scripts/tier2_monitoring.py
"""

import time
import logging
import sqlite3
import psutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

DB_PATH = Path(r"D:\loan4u_avm_data\vworld_wfs_multi_layer\db\vworld_wfs_multi_layer.sqlite")
LEDGER_PATH = Path(r"D:\loan4u_avm_data\vworld_wfs_multi_layer\ledger")


@dataclass
class Metric:
    """모니터링 메트릭."""

    name: str
    value: float
    unit: str
    threshold: float
    status: str
    measured_at: str


class MetricsCollector:
    """메트릭 수집기."""

    def __init__(self) -> None:
        """초기화."""
        self.metrics: List[Metric] = []
        self.process = psutil.Process()

    def collect_all(self) -> List[Metric]:
        """모든 메트릭 수집.

        Returns:
            메트릭 리스트
        """
        self.metrics = []

        # 1. 데이터 수집 지연시간
        self._collect_collection_latency()

        # 2. API 오류율
        self._collect_api_error_rate()

        # 3. P99 응답시간
        self._collect_p99_latency()

        # 4. 메모리 사용량
        self._collect_memory_usage()

        # 5. DB 연결 풀
        self._collect_db_connection_pool()

        return self.metrics

    def _collect_collection_latency(self) -> None:
        """데이터 수집 지연시간 (ms)."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT CAST((julianday(MAX(collected_at)) - julianday(MIN(collected_at))) * 24 * 60 * 1000 AS INTEGER)
                FROM layer1_search20
                """
            )
            result = cursor.fetchone()
            conn.close()

            latency_ms = result[0] if result[0] else 0

            metric = Metric(
                name="collection_latency",
                value=latency_ms,
                unit="ms",
                threshold=60000,  # 60초
                status="OK" if latency_ms < 60000 else "WARNING",
                measured_at=datetime.now().isoformat(),
            )
            self.metrics.append(metric)

        except Exception as e:
            log.warning(f"수집 지연시간 측정 실패: {e}")

    def _collect_api_error_rate(self) -> None:
        """API 오류율 (%)."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM api_call_log WHERE http_status != 200")
            error_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM api_call_log")
            total_count = cursor.fetchone()[0]
            conn.close()

            error_rate = (error_count / total_count * 100) if total_count > 0 else 0

            metric = Metric(
                name="api_error_rate",
                value=error_rate,
                unit="%",
                threshold=5.0,  # 5% 임계값
                status="OK" if error_rate < 5.0 else "WARNING",
                measured_at=datetime.now().isoformat(),
            )
            self.metrics.append(metric)

        except Exception as e:
            log.warning(f"API 오류율 측정 실패: {e}")

    def _collect_p99_latency(self) -> None:
        """P99 응답시간 (ms)."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # 상위 1% 응답시간 (P99)
            cursor.execute(
                """
                SELECT CAST(call_time_ms AS FLOAT) FROM api_call_log
                WHERE call_time_ms IS NOT NULL
                ORDER BY call_time_ms DESC
                LIMIT 1 OFFSET (SELECT COUNT(*) / 100 FROM api_call_log)
                """
            )
            result = cursor.fetchone()
            conn.close()

            p99_ms = result[0] if result else 0

            metric = Metric(
                name="p99_latency",
                value=p99_ms,
                unit="ms",
                threshold=300,  # 300ms 목표
                status="OK" if p99_ms < 300 else "WARNING",
                measured_at=datetime.now().isoformat(),
            )
            self.metrics.append(metric)

        except Exception as e:
            log.warning(f"P99 지연시간 측정 실패: {e}")

    def _collect_memory_usage(self) -> None:
        """메모리 사용량 (MB)."""
        try:
            memory_mb = self.process.memory_info().rss / (1024 * 1024)

            metric = Metric(
                name="memory_usage",
                value=memory_mb,
                unit="MB",
                threshold=200.0,  # 200MB 임계값
                status="OK" if memory_mb < 200 else "WARNING",
                measured_at=datetime.now().isoformat(),
            )
            self.metrics.append(metric)

        except Exception as e:
            log.warning(f"메모리 사용량 측정 실패: {e}")

    def _collect_db_connection_pool(self) -> None:
        """DB 연결 풀 (활성 연결 수)."""
        try:
            # SQLite는 단순 카운트 (연결 풀 없음)
            # 대신 DB 파일 크기 및 접근 성공 여부로 판정
            db_size_mb = DB_PATH.stat().st_size / (1024 * 1024)

            conn = sqlite3.connect(DB_PATH)
            conn.close()

            metric = Metric(
                name="db_connection_status",
                value=db_size_mb,
                unit="MB",
                threshold=50.0,  # 50MB 제한
                status="OK" if db_size_mb < 50 else "WARNING",
                measured_at=datetime.now().isoformat(),
            )
            self.metrics.append(metric)

        except Exception as e:
            log.warning(f"DB 연결 상태 측정 실패: {e}")

    def report(self) -> Dict[str, Any]:
        """메트릭 보고서 생성.

        Returns:
            보고서 딕셔너리
        """
        ok_count = sum(1 for m in self.metrics if m.status == "OK")
        warning_count = sum(1 for m in self.metrics if m.status == "WARNING")

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_metrics": len(self.metrics),
                "ok": ok_count,
                "warning": warning_count,
                "health": "OK" if warning_count == 0 else "WARNING",
            },
            "metrics": [asdict(m) for m in self.metrics],
        }


def main() -> None:
    """Tier 2 모니터링 메인."""
    log.info("\nDay 8: Tier 2 모니터링 수집 시작\n")

    collector = MetricsCollector()
    collector.collect_all()
    report = collector.report()

    log.info("=" * 60)
    log.info(f"모니터링 결과: {report['summary']['ok']}/{report['summary']['total_metrics']} OK")
    log.info(f"상태: {report['summary']['health']}")
    log.info("=" * 60)

    # 보고서 저장
    LEDGER_PATH.mkdir(parents=True, exist_ok=True)
    log_path = LEDGER_PATH / f"tier2_monitoring_{datetime.now():%Y%m%d_%H%M%S}.json"
    log_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info(f"보고서: {log_path}")


if __name__ == "__main__":
    main()
