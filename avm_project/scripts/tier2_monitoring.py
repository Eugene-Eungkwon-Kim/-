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
import sys
import psutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

# avm_paths는 scripts/ 안의 형제 모듈이다. `python scripts/tier2_monitoring.py`로
# 실행하면 scripts/가 sys.path에 오르지만, 테스트처럼
# `avm_project.scripts.tier2_monitoring` 패키지 경로로 임포트하면 오르지 않아
# ModuleNotFoundError가 났다 — 두 경로 모두에서 찾히도록 직접 올린다.
sys.path.insert(0, str(Path(__file__).parent))

from avm_paths import DB_PATH, LEDGER_PATH  # noqa: E402

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)


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

    def _record(self, name: str, value: float, unit: str, threshold: float) -> None:
        self.metrics.append(Metric(
            name=name, value=value, unit=unit, threshold=threshold,
            status="OK" if value < threshold else "WARNING",
            measured_at=datetime.now().isoformat(),
        ))

    def _record_unavailable(self, name: str, unit: str, threshold: float, error: Exception) -> None:
        # 측정 실패를 조용히 빠뜨리면 보고서에서 그 메트릭 자체가 사라져 장애를
        # 못 본다 — UNAVAILABLE 상태로 남겨 5개 메트릭이 항상 보고되게 한다.
        log.warning(f"{name} 측정 실패: {error}")
        self.metrics.append(Metric(
            name=name, value=0.0, unit=unit, threshold=threshold,
            status="UNAVAILABLE", measured_at=datetime.now().isoformat(),
        ))

    @staticmethod
    def _connect_readonly() -> sqlite3.Connection:
        # 모니터링은 읽기 전용이다 — 기본 connect()는 DB가 없으면 빈 파일을 만들어 버린다.
        return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    def _query_scalar(self, sql: str) -> Any:
        conn = self._connect_readonly()
        try:
            row = conn.execute(sql).fetchone()
        finally:
            conn.close()
        return row[0] if row else None

    def _collect_collection_latency(self) -> None:
        """데이터 수집 지연시간 (ms)."""
        try:
            latency_ms = self._query_scalar(
                "SELECT CAST((julianday(MAX(collected_at)) - julianday(MIN(collected_at)))"
                " * 24 * 60 * 1000 AS INTEGER) FROM layer1_search20"
            )
            self._record("collection_latency", latency_ms or 0, "ms", 60000)  # 60초
        except Exception as e:
            self._record_unavailable("collection_latency", "ms", 60000, e)

    def _collect_api_error_rate(self) -> None:
        """API 오류율 (%)."""
        try:
            error_count = self._query_scalar("SELECT COUNT(*) FROM api_call_log WHERE http_status != 200")
            total_count = self._query_scalar("SELECT COUNT(*) FROM api_call_log")
            error_rate = (error_count / total_count * 100) if total_count else 0
            self._record("api_error_rate", error_rate, "%", 5.0)  # 5% 임계값
        except Exception as e:
            self._record_unavailable("api_error_rate", "%", 5.0, e)

    def _collect_p99_latency(self) -> None:
        """P99 응답시간 (ms)."""
        try:
            p99_ms = self._query_scalar(
                "SELECT CAST(call_time_ms AS FLOAT) FROM api_call_log"
                " WHERE call_time_ms IS NOT NULL ORDER BY call_time_ms DESC"
                " LIMIT 1 OFFSET (SELECT COUNT(*) / 100 FROM api_call_log)"
            )
            self._record("p99_latency", p99_ms or 0, "ms", 300)  # 300ms 목표
        except Exception as e:
            self._record_unavailable("p99_latency", "ms", 300, e)

    def _collect_memory_usage(self) -> None:
        """메모리 사용량 (MB)."""
        try:
            memory_mb = self.process.memory_info().rss / (1024 * 1024)
            self._record("memory_usage", memory_mb, "MB", 200.0)  # 200MB 임계값
        except Exception as e:
            self._record_unavailable("memory_usage", "MB", 200.0, e)

    def _collect_db_connection_pool(self) -> None:
        """DB 연결 상태 (SQLite는 연결 풀이 없어 파일 크기 + 접근 성공 여부로 판정)."""
        try:
            db_size_mb = DB_PATH.stat().st_size / (1024 * 1024)
            self._connect_readonly().close()
            self._record("db_connection_status", db_size_mb, "MB", 50.0)  # 50MB 제한
        except Exception as e:
            self._record_unavailable("db_connection_status", "MB", 50.0, e)

    def report(self) -> Dict[str, Any]:
        """메트릭 보고서 생성.

        Returns:
            보고서 딕셔너리
        """
        ok_count = sum(1 for m in self.metrics if m.status == "OK")
        warning_count = sum(1 for m in self.metrics if m.status == "WARNING")
        unavailable_count = sum(1 for m in self.metrics if m.status == "UNAVAILABLE")

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_metrics": len(self.metrics),
                "ok": ok_count,
                "warning": warning_count,
                "unavailable": unavailable_count,
                "health": "OK" if warning_count + unavailable_count == 0 else "WARNING",
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
