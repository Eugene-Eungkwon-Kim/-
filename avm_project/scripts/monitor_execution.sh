#!/bin/bash

# 실시간 실행 상황 모니터링 스크립트

echo "🚀 AVM 프로젝트 실시간 모니터링 시작"
echo "=================================="
echo ""

while true; do
    clear
    echo "🔄 실시간 모니터링 - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "================================================"
    echo ""

    # OPTION 2 진행 상황
    echo "📊 OPTION 2 (모델 최적화) 상태"
    echo "---"

    if [ -f "logs/hyperparameter_tuning.log" ]; then
        # 마지막 10줄 표시
        tail -10 logs/hyperparameter_tuning.log
    else
        echo "로그 파일 아직 생성 전..."
    fi

    echo ""
    echo "📁 생성 파일 확인"
    echo "---"

    # 생성된 파일 확인
    if [ -f "output/hyperparameter_tuning_results.json" ]; then
        echo "✅ hyperparameter_tuning_results.json ($(ls -lh output/hyperparameter_tuning_results.json | awk '{print $5}'))"
        # 모델별 최적 R² 표시
        echo "   최적화된 모델:"
        jq -r 'to_entries[] | "   - \(.key): Train R²=\(.value.best_train_r2) Val R²=\(.value.val_r2)"' output/hyperparameter_tuning_results.json 2>/dev/null || echo "   (파싱 대기 중...)"
    else
        echo "⏳ hyperparameter_tuning_results.json (아직 생성 전...)"
    fi

    if [ -f "output/model_comparison_tuned.csv" ]; then
        echo "✅ model_comparison_tuned.csv ($(ls -lh output/model_comparison_tuned.csv | awk '{print $5}'))"
        echo "   내용:"
        head -3 output/model_comparison_tuned.csv | awk '{print "   " $0}'
    else
        echo "⏳ model_comparison_tuned.csv (아직 생성 전...)"
    fi

    echo ""
    echo "💾 튜닝된 모델 파일"
    echo "---"
    ls -lh models/*_tuned.pkl 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}' || echo "   (아직 생성 전...)"

    echo ""
    echo "================================================"
    echo "엔터를 눌러 새로고침 (Ctrl+C로 종료)"
    read
done
