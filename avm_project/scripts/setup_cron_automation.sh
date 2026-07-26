#!/bin/bash
#
# AVM Loop Engineering - Cron Automation Setup
# 자동 데이터 수집 및 모델 재학습 스케줄 설정
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AVM Loop Engineering - Cron Setup${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 프로젝트 루트 경로 설정
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_SCRIPT="${PROJECT_ROOT}/scripts/avm_orchestrator.py"
PYTHON_BIN="python3"

# API 키 확인
if [ -z "$DATAGOVKR_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  WARNING: DATAGOVKR_API_KEY environment variable not set${NC}"
    echo -e "${YELLOW}   Set it with: export DATAGOVKR_API_KEY='your-api-key'${NC}\n"
    read -p "Do you want to continue without setting the API key? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Python 버전 확인
echo -e "${BLUE}Step 1: Checking Python installation...${NC}"
if ! command -v $PYTHON_BIN &> /dev/null; then
    echo -e "${RED}❌ Python3 not found. Please install Python3.${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_BIN --version 2>&1)
echo -e "${GREEN}✅ Found: $PYTHON_VERSION${NC}\n"

# 필수 패키지 확인
echo -e "${BLUE}Step 2: Checking required Python packages...${NC}"
if [ -f "${PROJECT_ROOT}/requirements-minimal.txt" ]; then
    echo -e "${YELLOW}Installing required packages...${NC}"
    $PYTHON_BIN -m pip install -q -r "${PROJECT_ROOT}/requirements-minimal.txt"
    echo -e "${GREEN}✅ Packages installed${NC}\n"
fi

# Cron 스케줄 옵션
echo -e "${BLUE}Step 3: Setting up Cron Schedule${NC}"
echo "Available scheduling options:"
echo "  1) Weekly (Thursday 10:00 AM) - Default"
echo "  2) Daily (10:00 AM)"
echo "  3) Bi-weekly (Every other Thursday 10:00 AM)"
echo "  4) Monthly (First Thursday at 10:00 AM)"
echo "  5) Custom (Enter your own cron expression)"

read -p "Choose option (1-5) [default: 1]: " -r schedule_option
schedule_option=${schedule_option:-1}

case $schedule_option in
    1)
        # 목요일 10:00 AM (Weekly)
        CRON_SCHEDULE="0 10 * * 4"
        DESCRIPTION="Weekly (every Thursday at 10:00 AM)"
        ;;
    2)
        # 매일 10:00 AM
        CRON_SCHEDULE="0 10 * * *"
        DESCRIPTION="Daily (every day at 10:00 AM)"
        ;;
    3)
        # 격주 목요일
        CRON_SCHEDULE="0 10 * * 4 [ $(date +\%s | awk '{print $1 % 2}') -eq 0 ]"
        DESCRIPTION="Bi-weekly (every other Thursday at 10:00 AM)"
        ;;
    4)
        # 매월 첫 목요일
        CRON_SCHEDULE="0 10 ? * 5 */4"
        DESCRIPTION="Monthly (first Thursday at 10:00 AM)"
        ;;
    5)
        read -p "Enter cron expression (e.g., '0 10 * * 4'): " -r CRON_SCHEDULE
        DESCRIPTION="Custom: $CRON_SCHEDULE"
        ;;
    *)
        echo -e "${RED}❌ Invalid option. Using default (weekly).${NC}"
        CRON_SCHEDULE="0 10 * * 4"
        DESCRIPTION="Weekly (every Thursday at 10:00 AM)"
        ;;
esac

echo -e "${GREEN}✅ Selected: $DESCRIPTION${NC}\n"

# Cron 명령어 생성
CRON_COMMAND="cd ${PROJECT_ROOT} && ${PYTHON_BIN} scripts/avm_orchestrator.py >> logs/cron_execution.log 2>&1"

# 기존 Cron 작업 확인
echo -e "${BLUE}Step 4: Managing Cron Jobs${NC}"

CRON_TMP="/tmp/avm_cron_${RANDOM}.txt"
crontab -l > "$CRON_TMP" 2>/dev/null || true

# 기존 AVM Cron 제거
if grep -q "avm_orchestrator.py" "$CRON_TMP"; then
    echo -e "${YELLOW}⚠️  Found existing AVM Cron job. Removing it...${NC}"
    grep -v "avm_orchestrator.py" "$CRON_TMP" > "${CRON_TMP}.new"
    mv "${CRON_TMP}.new" "$CRON_TMP"
fi

# 새 Cron 작업 추가
echo "# AVM Loop Engineering - Automated Data Collection & Model Retraining" >> "$CRON_TMP"
echo "# Schedule: $DESCRIPTION" >> "$CRON_TMP"
echo "# Added: $(date)" >> "$CRON_TMP"
echo "$CRON_SCHEDULE $CRON_COMMAND" >> "$CRON_TMP"

# Cron 작업 설치
crontab "$CRON_TMP"
rm -f "$CRON_TMP"

echo -e "${GREEN}✅ Cron job installed${NC}\n"

# Cron 작업 확인
echo -e "${BLUE}Step 5: Verifying Cron Installation${NC}"
echo "Current AVM Cron jobs:"
crontab -l | grep "avm_orchestrator.py" || echo "No AVM cron jobs found"
echo ""

# 설정 파일 생성 옵션
echo -e "${BLUE}Step 6: Environment Configuration${NC}"
read -p "Do you want to set the API key in .bashrc? (y/n) [default: n]: " -r set_env
if [[ $set_env =~ ^[Yy]$ ]]; then
    read -p "Enter your Data.go.kr API key: " -r api_key
    if [ -n "$api_key" ]; then
        # .bashrc에 추가
        if ! grep -q "DATAGOVKR_API_KEY" ~/.bashrc; then
            echo "export DATAGOVKR_API_KEY='$api_key'" >> ~/.bashrc
            echo -e "${GREEN}✅ API key added to ~/.bashrc${NC}"
            echo -e "${YELLOW}⚠️  Run 'source ~/.bashrc' to apply changes${NC}\n"
        else
            echo -e "${YELLOW}API key already exists in ~/.bashrc${NC}\n"
        fi
    fi
fi

# 테스트 실행 옵션
echo -e "${BLUE}Step 7: Testing the Orchestrator${NC}"
read -p "Do you want to run a test execution now? (y/n) [default: n]: " -r run_test
if [[ $run_test =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Running test execution...${NC}"
    cd "${PROJECT_ROOT}"
    $PYTHON_BIN scripts/avm_orchestrator.py --start-date 202406 --end-date 202406
    echo -e "${GREEN}✅ Test execution completed${NC}\n"
fi

# 설정 요약
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Cron Automation Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo "Configuration Summary:"
echo "  Project Root: ${PROJECT_ROOT}"
echo "  Orchestrator Script: ${PYTHON_SCRIPT}"
echo "  Schedule: $DESCRIPTION"
echo "  Cron Expression: $CRON_SCHEDULE"
echo "  Log Location: ${PROJECT_ROOT}/logs/cron_execution.log"
echo ""

echo "Next Steps:"
echo "  1. Verify cron is running: crontab -l"
echo "  2. Monitor execution logs: tail -f logs/cron_execution.log"
echo "  3. Check orchestration reports: output/orchestration_report_*.json"
echo "  4. View full logs: logs/avm_orchestration_*.log"
echo ""

echo "To remove the cron job, run:"
echo "  (crontab -l | grep -v 'avm_orchestrator.py') | crontab -"
echo ""
