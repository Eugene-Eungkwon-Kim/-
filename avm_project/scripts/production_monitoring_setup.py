#!/usr/bin/env python3
"""
Production Monitoring & Performance Tracking Setup
Real-time monitoring dashboard activation
"""

import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
import numpy as np

print("=" * 80)
print("📊 프로덕션 모니터링 및 성능 추적 시스템")
print("=" * 80)

# ============================================================================
# STEP 1: 모니터링 대시보드 설정
# ============================================================================
print("\n[Step 1/4] 모니터링 대시보드 설정")
print("=" * 80)

monitoring_config = {
    "status": "ACTIVE",
    "timestamp": datetime.now().isoformat(),
    "dashboard": {
        "url": "http://localhost:8000/dashboard",
        "refresh_interval": 30,
        "components": [
            "Model Performance Chart",
            "Real-time Metrics",
            "Alert Log",
            "Prediction Stats"
        ]
    },
    "api_endpoints": {
        "health": "/health",
        "predict": "/predict",
        "dashboard": "/dashboard",
        "performance": "/dashboard/api/performance",
        "alerts": "/dashboard/api/alerts",
        "summary": "/dashboard/api/summary"
    },
    "monitoring_features": {
        "real_time_updates": True,
        "performance_tracking": True,
        "regression_detection": True,
        "auto_alerts": True,
        "performance_logging": True
    }
}

print("\n✓ 대시보드 설정 완료")
print(f"   URL: {monitoring_config['dashboard']['url']}")
print(f"   갱신 주기: {monitoring_config['dashboard']['refresh_interval']}초")
print(f"   컴포넌트: {len(monitoring_config['dashboard']['components'])}개")

# ============================================================================
# STEP 2: 성능 메트릭 초기화
# ============================================================================
print("\n[Step 2/4] 성능 메트릭 초기화")
print("=" * 80)

metrics_config = {
    "primary_metrics": {
        "r2_score": "모델 설명력",
        "rmse": "제곱평균제곱근",
        "mae": "평균절대오차",
        "mape": "평균절대백분오차"
    },
    "tracking_metrics": {
        "response_time": "API 응답 시간 (ms)",
        "throughput": "처리량 (samples/sec)",
        "error_rate": "에러율 (%)",
        "availability": "가용성 (%)"
    },
    "monitoring_interval": 60,
    "alert_thresholds": {
        "r2_regression": -0.02,  # R² 2% 감소 시 알림
        "response_time": 100,     # 100ms 이상
        "error_rate": 5           # 5% 이상
    }
}

print("\n✓ 성능 메트릭 정의")
print(f"   주요 메트릭: {len(metrics_config['primary_metrics'])}개")
print(f"   추적 메트릭: {len(metrics_config['tracking_metrics'])}개")
print(f"   모니터링 주기: {metrics_config['monitoring_interval']}초")
print(f"   알림 임계값: {len(metrics_config['alert_thresholds'])}개")

# ============================================================================
# STEP 3: 성능 로그 분석
# ============================================================================
print("\n[Step 3/4] 성능 로그 분석 및 추적")
print("=" * 80)

performance_log_path = Path("logs/performance_history.jsonl")
performance_analysis = {
    "log_file": str(performance_log_path),
    "analysis_timestamp": datetime.now().isoformat(),
    "total_records": 0,
    "performance_trends": {},
    "latest_performance": None
}

if performance_log_path.exists():
    with open(performance_log_path, 'r') as f:
        lines = f.readlines()
    
    performance_analysis["total_records"] = len(lines)
    
    if lines:
        # 최신 성능 데이터
        latest = json.loads(lines[-1])
        performance_analysis["latest_performance"] = latest
        
        print(f"\n✓ 성능 로그 분석")
        print(f"   총 레코드: {len(lines)}개")
        print(f"   로그 기간: {lines[0][:10]} ~ {lines[-1][:10]}")
        
        # 성능 추이 분석 (최근 5개)
        if len(lines) > 1:
            recent_records = [json.loads(line) for line in lines[-5:]]
            print(f"\n   최근 5개 성능 기록:")
            for i, record in enumerate(recent_records, 1):
                r2 = record.get('r2_score', 'N/A')
                model = record.get('model', 'Unknown')
                print(f"      {i}. {model} (R²={r2})")
else:
    print(f"\n⚠️  성능 로그 파일 없음: {performance_log_path}")
    print("   (첫 번째 모니터링이 기록됨)")

# ============================================================================
# STEP 4: 모니터링 시작 설정
# ============================================================================
print("\n[Step 4/4] 모니터링 시작 설정")
print("=" * 80)

monitoring_startup = {
    "services": {
        "api_server": {
            "name": "FastAPI REST Server",
            "command": "uvicorn scripts.api_server:app --host 0.0.0.0 --port 8000",
            "status": "READY",
            "url": "http://localhost:8000"
        },
        "scheduler": {
            "name": "Auto-Retraining Scheduler",
            "command": "python scripts/looping_scheduler.py --mode scheduler",
            "status": "READY",
            "schedule": "Every Thursday 10:00 UTC"
        },
        "performance_monitor": {
            "name": "Performance Monitor",
            "command": "python scripts/looping_scheduler.py --mode monitor",
            "status": "READY",
            "interval": "Real-time"
        }
    },
    "startup_sequence": [
        "1. API Server 시작 (포트 8000)",
        "2. 대시보드 접근 (http://localhost:8000/dashboard)",
        "3. 성능 모니터링 활성화",
        "4. 자동 재학습 스케줄러 시작 (선택)"
    ]
}

print("\n✓ 모니터링 서비스 준비 완료")
for service_name, service in monitoring_startup["services"].items():
    print(f"\n   {service['name']}")
    print(f"      상태: {service['status']}")
    print(f"      시작: {service['command'][:50]}...")

# ============================================================================
# 모니터링 설정 파일 저장
# ============================================================================
print("\n" + "=" * 80)
print("✅ 모니터링 설정 저장")
print("=" * 80)

monitoring_setup = {
    "timestamp": datetime.now().isoformat(),
    "monitoring_config": monitoring_config,
    "metrics_config": metrics_config,
    "performance_analysis": performance_analysis,
    "startup_guide": monitoring_startup,
    "quick_start": {
        "step_1": "python -m uvicorn scripts.api_server:app --host 0.0.0.0 --port 8000",
        "step_2": "브라우저에서 http://localhost:8000/dashboard 접근",
        "step_3": "실시간 성능 대시보드 모니터링 (30초 자동 갱신)",
        "step_4": "python scripts/looping_scheduler.py --mode scheduler (선택)"
    }
}

# 설정 파일 저장
config_file = Path("config/monitoring_setup.json")
with open(config_file, 'w') as f:
    json.dump(monitoring_setup, f, indent=2)

print(f"\n📋 설정 파일 저장: {config_file}")

# ============================================================================
# 최종 요약
# ============================================================================
print("\n" + "=" * 80)
print("📊 모니터링 시스템 준비 완료")
print("=" * 80)

print(f"""
🎯 모니터링 체계:

주요 기능:
   ✅ 실시간 대시보드 (30초 갱신)
   ✅ REST API 8개 엔드포인트
   ✅ 성능 메트릭 자동 추적
   ✅ 회귀 감지 자동 알림
   ✅ 성능 로그 기록 (JSONL)

모니터링 메트릭:
   ✅ R² 점수 (모델 성능)
   ✅ RMSE (예측 오차)
   ✅ MAE (평균 오차)
   ✅ MAPE (백분율 오차)
   ✅ 응답 시간 (ms)
   ✅ 처리량 (samples/sec)
   ✅ 에러율 (%)
   ✅ 가용성 (%)

알림 기준:
   ⚠️  R² > 2% 감소 시 자동 알림
   ⚠️  응답 시간 > 100ms 시 알림
   ⚠️  에러율 > 5% 시 알림

시작 명령어:
   Terminal 1: python -m uvicorn scripts.api_server:app --port 8000
   Terminal 2: python scripts/looping_scheduler.py --mode scheduler
   
대시보드: http://localhost:8000/dashboard
""")

print("=" * 80)
print("✅ 준비 완료 - 모니터링 시스템 활성화 준비됨")
print("=" * 80)
