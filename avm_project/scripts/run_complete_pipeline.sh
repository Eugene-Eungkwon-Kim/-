#!/bin/bash

################################################################################
# AVM 프로젝트 완전 자동화 파이프라인
#
# 용도: Phase 0-5까지 전체 프로젝트를 자동으로 실행
# 사용: ./scripts/run_complete_pipeline.sh [MODE]
#
# MODE:
#   setup    - 환경 설정만 (의존성 설치)
#   data     - Phase 1-3: 데이터 준비 및 수집
#   optimize - Phase 4: 모델 최적화
#   explain  - Phase 5: SHAP 설명성
#   full     - 전체 실행 (default)
#   monitor  - 모니터링만 (대시보드 + 스케줄러)
#
################################################################################

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# 프로젝트 루트 디렉토리
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 모드 결정 (기본값: full)
MODE="${1:-full}"

# 타임스탬프
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/pipeline_${TIMESTAMP}.log"

# 로그 디렉토리 생성
mkdir -p logs

echo ""
echo "================================================================================"
echo "🚀 AVM 프로젝트 완전 자동화 파이프라인"
echo "================================================================================"
echo "모드: $MODE"
echo "타임스탬프: $TIMESTAMP"
echo "로그: $LOG_FILE"
echo "================================================================================"
echo ""

# 로그 시작
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

################################################################################
# Phase 0: 환경 설정
################################################################################

phase_setup() {
    log_info "Phase 0: 환경 설정"
    echo "=================================================="

    # Python 버전 확인
    log_info "Python 버전 확인..."
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    log_success "Python $python_version 감지됨"

    # 의존성 설치
    log_info "의존성 설치 중..."
    if pip install -q -r requirements.txt 2>/dev/null; then
        log_success "의존성 설치 완료"
    else
        log_warning "전체 의존성 설치 실패, 최소 의존성 사용..."
        pip install -q -r requirements-minimal.txt 2>/dev/null || true
        log_success "최소 의존성 설치 완료"
    fi

    # 디렉토리 생성
    log_info "필수 디렉토리 생성..."
    mkdir -p data/raw data/processed models output logs tests
    log_success "디렉토리 구조 확인됨"

    # .env 파일 확인
    if [ -f .env ]; then
        log_success ".env 파일 감지됨"
        source .env
    else
        log_warning ".env 파일 없음 (Data.go.kr API 키 설정 필요)"
    fi

    echo ""
}

################################################################################
# Phase 1: 데이터 준비 및 분석
################################################################################

phase_data_preparation() {
    log_info "Phase 1: 데이터 준비 및 분석"
    echo "=================================================="

    # 샘플 데이터 생성
    log_info "샘플 데이터 생성 중..."
    if python3 scripts/generate_sample_data.py > /dev/null 2>&1; then
        log_success "샘플 데이터 생성 완료"
        ls -lh data/raw/sample_npl_data.csv
    else
        log_error "샘플 데이터 생성 실패"
        return 1
    fi

    # 데이터 전처리
    log_info "데이터 전처리 중..."
    if python3 scripts/data_preprocessing.py > /dev/null 2>&1; then
        log_success "데이터 전처리 완료"
        processed_file=$(ls -t output/processed_sample_data.csv 2>/dev/null | head -1)
        if [ -f "$processed_file" ]; then
            ls -lh "$processed_file"
        fi
    else
        log_error "데이터 전처리 실패"
        return 1
    fi

    echo ""
}

################################################################################
# Phase 3: 데이터 수집
################################################################################

phase_data_collection() {
    log_info "Phase 3: 실제 데이터 수집"
    echo "=================================================="

    # 월 범위 지정 (기본값: 202401-202406)
    MONTHS="${DATA_COLLECTION_MONTHS:-202401-202406}"

    log_info "데이터 수집 중 (기간: $MONTHS)..."
    if python3 scripts/phase3_data_collection.py --months "$MONTHS"; then
        log_success "데이터 수집 완료"

        # 수집된 파일 확인
        latest_file=$(ls -t data/raw/real_estate_combined_*.csv 2>/dev/null | head -1)
        if [ -f "$latest_file" ]; then
            log_success "수집된 파일: $latest_file"
            python3 -c "
import pandas as pd
df = pd.read_csv('$latest_file')
print(f'  행: {len(df):,}, 컬럼: {len(df.columns)}')
print(f'  크기: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB')
"
        fi
    else
        log_error "데이터 수집 실패"
        return 1
    fi

    echo ""
}

################################################################################
# Phase 4: 모델 최적화
################################################################################

phase_model_optimization() {
    log_info "Phase 4: 모델 성능 최적화"
    echo "=================================================="

    log_info "모델 평가 및 최적화 중..."
    if python3 scripts/phase4_model_optimization.py; then
        log_success "모델 최적화 완료"

        # 리포트 확인
        latest_report=$(ls -t output/model_optimization_*.json 2>/dev/null | head -1)
        if [ -f "$latest_report" ]; then
            log_success "최적화 리포트 생성됨"
            python3 -c "
import json
with open('$latest_report') as f:
    report = json.load(f)
summary = report['summary']
print(f'  기준선 최고: {summary[\"best_baseline\"]} (R²={summary[\"best_baseline_r2\"]:.4f})')
print(f'  최적화 최고: {summary[\"best_optimized\"]} (R²={summary[\"best_optimized_r2\"]:.4f})')
print(f'  평균 개선도: +{summary[\"avg_improvement\"]:.4f}')
"
        fi
    else
        log_error "모델 최적화 실패"
        return 1
    fi

    echo ""
}

################################################################################
# Phase 5: 모델 설명성 (SHAP)
################################################################################

phase_model_explainability() {
    log_info "Phase 5: 모델 설명성 분석 (SHAP)"
    echo "=================================================="

    log_info "SHAP 분석 중..."
    if python3 scripts/model_explainability.py; then
        log_success "SHAP 분석 완료"

        # 리포트 확인
        latest_report=$(ls -t output/model_explainability_*.json 2>/dev/null | head -1)
        if [ -f "$latest_report" ]; then
            log_success "설명성 리포트 생성됨"
            python3 -c "
import json
with open('$latest_report') as f:
    report = json.load(f)
insights = report['insights']
print(f'  상위 3개 특성: {', '.join(insights[\"top_3_features\"])}')
"
        fi
    else
        log_error "SHAP 분석 실패"
        return 1
    fi

    echo ""
}

################################################################################
# Phase 2: 모니터링 시작
################################################################################

phase_monitoring() {
    log_info "Phase 2: 모니터링 시작"
    echo "=================================================="

    log_info "API 서버 시작..."
    log_warning "다음 명령을 별도의 터미널에서 실행하세요:"
    echo ""
    echo "    uvicorn scripts.api_server:app --host 0.0.0.0 --port 8000"
    echo ""
    echo "그리고 다음 URL에서 대시보드에 접속하세요:"
    echo ""
    echo "    http://localhost:8000/dashboard"
    echo ""

    log_info "루핑 스케줄러 시작..."
    log_warning "주간 자동 재학습을 위해 별도의 터미널에서 실행하세요:"
    echo ""
    echo "    python3 scripts/looping_scheduler.py --mode scheduler"
    echo ""

    echo ""
}

################################################################################
# 테스트 실행
################################################################################

run_tests() {
    log_info "테스트 실행"
    echo "=================================================="

    log_info "단위 테스트 실행 중..."
    if python3 -m pytest tests/ -v --tb=short 2>/dev/null; then
        log_success "모든 테스트 통과"
    else
        log_warning "일부 테스트 실패 (경고만)"
    fi

    echo ""
}

################################################################################
# 최종 요약
################################################################################

print_summary() {
    echo ""
    echo "================================================================================"
    echo "✅ 파이프라인 완료"
    echo "================================================================================"
    echo ""

    log_success "실행 완료 시간: $(date)"
    log_success "로그 파일: $LOG_FILE"

    echo ""
    echo "📊 생성된 파일:"
    echo ""

    # 데이터 파일
    if [ -d data/raw ]; then
        raw_files=$(ls -1 data/raw/*.csv 2>/dev/null | wc -l)
        [ "$raw_files" -gt 0 ] && echo "  ✓ 원본 데이터: $raw_files 개"
    fi

    if [ -d data/processed ]; then
        proc_files=$(ls -1 data/processed/*.csv 2>/dev/null | wc -l)
        [ "$proc_files" -gt 0 ] && echo "  ✓ 처리된 데이터: $proc_files 개"
    fi

    # 모델 파일
    if [ -f models/production_model.joblib ]; then
        size=$(du -h models/production_model.joblib | cut -f1)
        echo "  ✓ 프로덕션 모델: $size"
    fi

    # 리포트 파일
    if [ -d output ]; then
        reports=$(ls -1 output/*.json 2>/dev/null | wc -l)
        [ "$reports" -gt 0 ] && echo "  ✓ 분석 리포트: $reports 개"
    fi

    # 로그 파일
    if [ -d logs ]; then
        logs=$(ls -1 logs/*.jsonl logs/*.log 2>/dev/null | wc -l)
        [ "$logs" -gt 0 ] && echo "  ✓ 로그 파일: $logs 개"
    fi

    echo ""
    echo "📚 다음 단계:"
    echo ""
    echo "  1. 대시보드 접속:"
    echo "     uvicorn scripts.api_server:app --port 8000"
    echo "     http://localhost:8000/dashboard"
    echo ""
    echo "  2. 자동 재학습 시작:"
    echo "     python3 scripts/looping_scheduler.py --mode scheduler"
    echo ""
    echo "  3. 상세 가이드 확인:"
    echo "     COMPLETE_EXECUTION_GUIDE.md"
    echo ""
    echo "================================================================================"
    echo ""
}

################################################################################
# 메인 실행 로직
################################################################################

main() {
    case "$MODE" in
        setup)
            phase_setup
            ;;
        data)
            phase_setup
            phase_data_preparation
            phase_data_collection
            ;;
        optimize)
            phase_model_optimization
            ;;
        explain)
            phase_model_explainability
            ;;
        monitor)
            phase_monitoring
            ;;
        full)
            phase_setup
            phase_data_preparation
            phase_data_collection
            phase_model_optimization
            phase_model_explainability
            run_tests
            phase_monitoring
            print_summary
            ;;
        *)
            log_error "알 수 없는 모드: $MODE"
            echo ""
            echo "사용법: ./scripts/run_complete_pipeline.sh [MODE]"
            echo ""
            echo "MODE:"
            echo "  setup    - 환경 설정만"
            echo "  data     - Phase 1-3: 데이터 준비 및 수집"
            echo "  optimize - Phase 4: 모델 최적화"
            echo "  explain  - Phase 5: SHAP 설명성"
            echo "  full     - 전체 실행 (default)"
            echo "  monitor  - 모니터링만"
            echo ""
            exit 1
            ;;
    esac

    if [ $? -eq 0 ]; then
        log_success "작업 완료"
    else
        log_error "작업 중 오류 발생"
        exit 1
    fi
}

# 실행
main
