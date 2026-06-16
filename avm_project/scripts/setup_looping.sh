#!/bin/bash
# PHASE 2 - 루핑 자동화 설정 스크립트
#
# 기능:
#   1. Cron 작업 등록 (주간 자동 재학습)
#   2. 모니터링 루프 (지속적 API 상태 감시)
#   3. 성능 추적 (모델 성능 변화 기록)

set -e

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPTS_DIR="$PROJECT_ROOT/scripts"
LOGS_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOGS_DIR"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}AVM 자동화 루핑 설정 (PHASE 2-3)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ============================================================================
# 1. Cron 작업 등록
# ============================================================================
echo -e "\n${GREEN}[1/3] Cron 자동 재학습 등록${NC}"
echo "       주간 스케줄: 매주 목요일 10:00 (UTC)"

CRON_SCHEDULE="0 10 * * 4"
CRON_COMMAND="cd $PROJECT_ROOT && python3 scripts/auto_retraining.py >> $LOGS_DIR/cron_auto_retraining.log 2>&1"

# 기존 cron 확인
EXISTING_CRON=$(crontab -l 2>/dev/null | grep "auto_retraining.py" || true)
if [ -z "$EXISTING_CRON" ]; then
    # 새 cron 작업 추가
    (crontab -l 2>/dev/null || true; echo "$CRON_SCHEDULE $CRON_COMMAND") | crontab -
    echo -e "   ${GREEN}✓${NC} Cron 작업 등록 완료"
else
    echo -e "   ${YELLOW}⚠${NC} Cron 작업 이미 등록됨"
fi

# ============================================================================
# 2. 모니터링 루프 함수
# ============================================================================
echo -e "\n${GREEN}[2/3] 모니터링 루프 설정${NC}"
echo "       실시간 API 상태 감시"

cat > "$SCRIPTS_DIR/monitoring_loop.py" << 'EOF'
#!/usr/bin/env python3
"""
실시간 모니터링 루프 - API 상태, 모델 성능, 캐시 통계 추적
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime
import subprocess

PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def get_api_health():
    """API 헬스 체크"""
    try:
        import subprocess
        result = subprocess.run(
            ["curl", "-s", "http://localhost:8000/health"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return {"status": "healthy", "response": "OK"}
        else:
            return {"status": "unhealthy", "error": "no response"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def get_cache_stats():
    """캐시 통계"""
    try:
        import subprocess
        result = subprocess.run(
            ["curl", "-s", "http://localhost:8000/cache/stats"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"error": "no response"}
    except Exception as e:
        return {"error": str(e)}

def get_model_registry():
    """모델 레지스트리 조회"""
    registry_file = PROJECT_ROOT / "models" / "model_registry.json"
    if registry_file.exists():
        with open(registry_file) as f:
            return json.load(f)
    return {"champion": None}

def log_monitoring(interval=60):
    """지속적 모니터링 (interval초마다)"""
    print(f"\n🔄 모니터링 루프 시작 (interval={interval}초)")
    print(f"   로그: {LOGS_DIR}/monitoring.log")

    iteration = 0
    while True:
        iteration += 1
        timestamp = datetime.now().isoformat()

        health = get_api_health()
        cache = get_cache_stats()
        registry = get_model_registry()
        champion = registry.get("champion", {})

        log_entry = {
            "timestamp": timestamp,
            "iteration": iteration,
            "api_health": health,
            "cache": cache.get("cache"),
            "champion_model": champion.get("name"),
            "champion_r2": champion.get("test_r2"),
        }

        # 로그 저장
        log_file = LOGS_DIR / "monitoring.log"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        # 콘솔 출력
        status_icon = "✅" if health["status"] == "healthy" else "❌"
        print(f"{status_icon} [{iteration}] {timestamp[:19]} | "
              f"API: {health['status']} | "
              f"Cache: {cache.get('cache', {}).get('hit_rate', 0):.2%} | "
              f"Champion: {champion.get('name', 'N/A')} (R²={champion.get('test_r2', 0):.4f})")

        time.sleep(interval)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=60, help="모니터링 간격 (초)")
    args = parser.parse_args()

    try:
        log_monitoring(interval=args.interval)
    except KeyboardInterrupt:
        print("\n⏹  모니터링 종료")
        sys.exit(0)
EOF

chmod +x "$SCRIPTS_DIR/monitoring_loop.py"
echo -e "   ${GREEN}✓${NC} monitoring_loop.py 생성 완료"

# ============================================================================
# 3. 성능 추적
# ============================================================================
echo -e "\n${GREEN}[3/3] 성능 추적 루프 설정${NC}"
echo "       모델 성능 변화 기록"

cat > "$SCRIPTS_DIR/performance_tracker.py" << 'EOF'
#!/usr/bin/env python3
"""
성능 추적 - 모델 성능 변화를 시계열로 기록
"""

import json
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def track_performance():
    """최신 모델 성능을 추적 로그에 기록"""
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
        "sha256": champion.get("sha256", ""),
    }

    # 성능 추적 로그
    perf_log = LOGS_DIR / "performance_history.jsonl"
    with open(perf_log, "a") as f:
        f.write(json.dumps(perf_entry, ensure_ascii=False) + "\n")

    print(f"✅ 성능 기록: {champion.get('name')} (R²={champion.get('test_r2', 0):.4f})")

    # 통계 출력
    lines = perf_log.read_text().strip().split('\n') if perf_log.exists() else []
    if lines:
        entries = [json.loads(line) for line in lines if line]
        r2_values = [e.get('test_r2', 0) for e in entries if e.get('test_r2')]
        if r2_values:
            print(f"   최고: {max(r2_values):.4f}, 최저: {min(r2_values):.4f}, "
                  f"평균: {sum(r2_values)/len(r2_values):.4f}")

if __name__ == "__main__":
    track_performance()
EOF

chmod +x "$SCRIPTS_DIR/performance_tracker.py"
echo -e "   ${GREEN}✓${NC} performance_tracker.py 생성 완료"

# ============================================================================
# 요약
# ============================================================================
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 루핑 자동화 설정 완료${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n${YELLOW}실행 가능 명령어:${NC}"
echo -e "  1️⃣  ${GREEN}자동 재학습 확인:${NC}"
echo -e "     crontab -l | grep auto_retraining"
echo -e ""
echo -e "  2️⃣  ${GREEN}모니터링 루프 시작 (수동):${NC}"
echo -e "     python3 scripts/monitoring_loop.py --interval 30"
echo -e ""
echo -e "  3️⃣  ${GREEN}성능 추적 기록:${NC}"
echo -e "     python3 scripts/performance_tracker.py"
echo -e ""
echo -e "  4️⃣  ${GREEN}모니터링 로그 확인:${NC}"
echo -e "     tail -f logs/monitoring.log"
echo -e ""
echo -e "  5️⃣  ${GREEN}성능 이력 조회:${NC}"
echo -e "     tail -20 logs/performance_history.jsonl | jq ."

echo -e "\n${YELLOW}루핑 상태:${NC}"
echo -e "  ${GREEN}✓${NC} Cron 자동 재학습: 매주 목요일 10:00"
echo -e "  ${GREEN}✓${NC} API 모니터링: 명령어로 활성화 가능"
echo -e "  ${GREEN}✓${NC} 성능 추적: 자동 재학습 후 기록"
