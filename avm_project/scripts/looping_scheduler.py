#!/usr/bin/env python3
"""
파이썬 기반 루핑 스케줄러 (Crontab 불가 환경 대체)

기능:
  - 주간 자동 재학습 (매주 목요일 10:00)
  - 성능 추적 (매번 재학습 후)
  - 실시간 모니터링 (선택적)
  - 자동 알림 (성능 급락 감지)
"""

import schedule
import time
import sys
import json
from pathlib import Path
from datetime import datetime
from subprocess import run, PIPE

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def run_auto_retraining():
    """자동 재학습 실행"""
    print(f"\n{'='*70}")
    print(f"🔄 자동 재학습 시작: {datetime.now().isoformat()}")
    print(f"{'='*70}")

    try:
        result = run(
            [sys.executable, str(SCRIPTS_DIR / "auto_retraining.py")],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            print(f"✅ 자동 재학습 완료")
            track_performance()
            check_performance_regression()
        else:
            print(f"❌ 자동 재학습 실패")
            print(result.stderr)

    except Exception as e:
        print(f"❌ 오류: {e}")


def track_performance():
    """성능 추적"""
    registry_file = PROJECT_ROOT / "models" / "model_registry.json"

    if not registry_file.exists():
        print("⚠️  모델 레지스트리 없음")
        return

    with open(registry_file) as f:
        registry = json.load(f)

    champion = registry.get("champion", {})

    perf_entry = {
        "timestamp": datetime.now().isoformat(),
        "model_name": champion.get("name"),
        "test_r2": champion.get("test_r2"),
        "test_rmse": champion.get("test_rmse"),
    }

    perf_log = LOGS_DIR / "performance_history.jsonl"
    with open(perf_log, "a") as f:
        f.write(json.dumps(perf_entry, ensure_ascii=False) + "\n")

    print(f"📊 성능 기록: {champion.get('name')} (R²={champion.get('test_r2', 0):.4f})")


def check_performance_regression():
    """성능 회귀 감지"""
    perf_log = LOGS_DIR / "performance_history.jsonl"

    if not perf_log.exists():
        return

    lines = perf_log.read_text().strip().split('\n')
    if len(lines) < 2:
        return

    entries = [json.loads(line) for line in lines if line]
    if len(entries) < 2:
        return

    latest = entries[-1].get('test_r2', 0)
    previous = entries[-2].get('test_r2', 0)
    regression = previous - latest

    if regression > 0.02:  # 2% 이상 회귀
        print(f"⚠️  성능 회귀 감지: {previous:.4f} → {latest:.4f} (-{regression:.4f})")
        alert_performance_regression(previous, latest, regression)
    elif regression > 0:
        print(f"📉 성능 소폭 감소: {previous:.4f} → {latest:.4f} (-{regression:.4f})")
    else:
        print(f"📈 성능 향상: {previous:.4f} → {latest:.4f} (+{-regression:.4f})")


def alert_performance_regression(previous, latest, regression):
    """성능 회귀 알림"""
    alert_log = LOGS_DIR / "alerts.log"
    alert_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "performance_regression",
        "previous_r2": previous,
        "latest_r2": latest,
        "regression": regression,
        "severity": "HIGH" if regression > 0.05 else "MEDIUM"
    }

    with open(alert_log, "a") as f:
        f.write(json.dumps(alert_entry, ensure_ascii=False) + "\n")

    print(f"🚨 알림 기록됨: {alert_log}")


def schedule_weekly_retraining():
    """주간 자동 재학습 스케줄"""
    # 매주 목요일 10:00에 실행
    schedule.every().thursday.at("10:00").do(run_auto_retraining)
    print(f"📅 스케줄 등록: 매주 목요일 10:00")


def run_scheduler(check_interval=60):
    """스케줄러 메인 루프"""
    print(f"\n{'='*70}")
    print(f"🚀 AVM 루핑 스케줄러 시작")
    print(f"{'='*70}")
    print(f"⏱️  체크 간격: {check_interval}초")
    print(f"📍 로그: {LOGS_DIR}")

    schedule_weekly_retraining()

    print(f"\n✅ 스케줄러 대기 중... (Ctrl+C로 종료)")

    try:
        while True:
            schedule.run_pending()
            time.sleep(check_interval)
    except KeyboardInterrupt:
        print(f"\n⏹  스케줄러 종료")
        sys.exit(0)


def run_monitoring_loop(interval=60):
    """실시간 API 모니터링"""
    import subprocess

    print(f"\n{'='*70}")
    print(f"📡 API 모니터링 시작 (interval={interval}초)")
    print(f"{'='*70}")

    iteration = 0
    while True:
        iteration += 1
        timestamp = datetime.now().isoformat()

        # API 헬스 체크
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:8000/health"],
                capture_output=True,
                timeout=5
            )
            api_status = "✅" if result.returncode == 0 else "❌"
        except Exception:
            api_status = "❌"

        # 모델 레지스트리 조회
        registry_file = PROJECT_ROOT / "models" / "model_registry.json"
        champion_info = "N/A"
        if registry_file.exists():
            with open(registry_file) as f:
                registry = json.load(f)
                champion = registry.get("champion", {})
                champion_info = f"{champion.get('name')} (R²={champion.get('test_r2', 0):.4f})"

        print(f"{api_status} [{iteration:04d}] {timestamp[:19]} | Champion: {champion_info}")

        time.sleep(interval)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AVM 루핑 스케줄러")
    parser.add_argument(
        "--mode",
        choices=["scheduler", "monitor"],
        default="scheduler",
        help="실행 모드 (기본: scheduler)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="체크 간격(스케줄러) 또는 모니터링 간격(monitor) (초)"
    )

    args = parser.parse_args()

    if args.mode == "scheduler":
        run_scheduler(check_interval=args.interval)
    elif args.mode == "monitor":
        run_monitoring_loop(interval=args.interval)
