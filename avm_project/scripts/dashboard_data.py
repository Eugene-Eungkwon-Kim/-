"""
대시보드 데이터 제공 API 엔드포인트

실시간 성능 모니터링 대시보드를 위한 데이터 제공:
- 성능 이력 조회
- 모델 정보
- 캐시 통계
- 알림 로그
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"


def get_performance_history(limit: int = 100) -> List[Dict]:
    """최근 성능 이력 조회"""
    perf_log = LOGS_DIR / "performance_history.jsonl"

    if not perf_log.exists():
        return []

    lines = perf_log.read_text().strip().split('\n')
    entries = [json.loads(line) for line in lines if line]

    return entries[-limit:]


def get_performance_stats() -> Dict:
    """성능 통계"""
    entries = get_performance_history()

    if not entries:
        return {
            "total_records": 0,
            "latest": None,
            "stats": None
        }

    r2_values = [e.get('test_r2', 0) for e in entries]
    rmse_values = [e.get('test_rmse', 0) for e in entries]

    latest = entries[-1]
    previous = entries[-2] if len(entries) > 1 else latest
    r2_change = latest.get('test_r2', 0) - previous.get('test_r2', 0)

    return {
        "total_records": len(entries),
        "latest": {
            "timestamp": latest.get('timestamp'),
            "model": latest.get('model_name'),
            "r2": round(latest.get('test_r2', 0), 6),
            "rmse": round(latest.get('test_rmse', 0), 2),
            "r2_change": round(r2_change, 6),
            "trend": "📈 향상" if r2_change > 0 else "📉 저하" if r2_change < 0 else "→ 유지"
        },
        "stats": {
            "best_r2": round(max(r2_values), 6),
            "worst_r2": round(min(r2_values), 6),
            "avg_r2": round(sum(r2_values) / len(r2_values), 6),
            "best_rmse": round(min(rmse_values), 2),
            "worst_rmse": round(max(rmse_values), 2),
            "avg_rmse": round(sum(rmse_values) / len(rmse_values), 2),
        }
    }


def get_champion_model() -> Dict:
    """현재 챔피언 모델"""
    registry_file = PROJECT_ROOT / "models" / "model_registry.json"

    if not registry_file.exists():
        return {"name": "None", "r2": 0, "status": "No model"}

    with open(registry_file) as f:
        registry = json.load(f)

    champion = registry.get("champion", {})

    return {
        "name": champion.get('name', 'N/A'),
        "r2": round(champion.get('test_r2', 0), 6),
        "rmse": round(champion.get('test_rmse', 0), 2),
        "promoted_at": champion.get('promoted_at', 'N/A'),
        "sha256": champion.get('sha256', '')[:16] + '...' if champion.get('sha256') else 'N/A',
    }


def get_alerts(limit: int = 10) -> List[Dict]:
    """최근 알림"""
    alert_log = LOGS_DIR / "alerts.log"

    if not alert_log.exists():
        return []

    lines = alert_log.read_text().strip().split('\n')
    entries = [json.loads(line) for line in lines if line]

    return entries[-limit:]


def get_dashboard_summary() -> Dict:
    """대시보드 종합 요약"""
    perf_stats = get_performance_stats()
    champion = get_champion_model()
    alerts = get_alerts(5)

    return {
        "timestamp": datetime.now().isoformat(),
        "performance": perf_stats,
        "champion": champion,
        "recent_alerts": alerts,
        "status": "healthy" if not alerts or alerts[-1].get('severity') != 'HIGH' else "warning"
    }
