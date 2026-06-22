#!/usr/bin/env python3
"""
AVM Dashboard Backend API
FastAPI 기반 REST API 서버
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# ============================================
# 앱 설정
# ============================================
app = FastAPI(
    title="AVM Dashboard API",
    description="부동산 자동감정 모델 대시보드 API",
    version="1.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "avm_project" / "data"
LOGS_DIR = PROJECT_ROOT / "avm_project" / "logs"

# ============================================
# 모델 및 Schemas
# ============================================
class LoginRequest:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password


class DashboardSummary:
    def __init__(self):
        self.ensemble_r2 = 0.8450
        self.ensemble_rmse = 55200000
        self.ensemble_mae = 42300000
        self.status = "healthy"


# ============================================
# 인증 관련
# ============================================
async def verify_token(authorization: Optional[str] = Header(None)):
    """토큰 검증"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")
        # 토큰 검증 로직 (현재는 간단히 통과)
        if not token:
            raise ValueError("Empty token")
        return token
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )


# ============================================
# 헬스 체크
# ============================================
@app.get("/health", tags=["Health"])
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


# ============================================
# 인증 API
# ============================================
@app.post("/auth/login", tags=["Auth"])
async def login(email: str, password: str):
    """로그인"""
    # 간단한 인증 (실제로는 데이터베이스 검증 필요)
    if email == "admin@avm.com" and password == "demo123":
        return {
            "access_token": "demo_token_12345",
            "token_type": "bearer",
            "user": {
                "email": email,
                "name": "관리자",
                "role": "admin"
            }
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


@app.post("/auth/logout", tags=["Auth"])
async def logout(token: str = Depends(verify_token)):
    """로그아웃"""
    return {"message": "Logged out successfully"}


@app.get("/auth/me", tags=["Auth"])
async def get_current_user(token: str = Depends(verify_token)):
    """현재 사용자 정보"""
    return {
        "email": "admin@avm.com",
        "name": "관리자",
        "role": "admin",
        "avatar": "A"
    }


# ============================================
# 대시보드 API
# ============================================
@app.get("/dashboard/summary", tags=["Dashboard"])
async def get_dashboard_summary(token: str = Depends(verify_token)):
    """대시보드 요약 정보"""
    return {
        "ensemble_r2": 0.8450,
        "ensemble_rmse": 55200000,
        "ensemble_mae": 42300000,
        "status": "healthy",
        "last_updated": datetime.now().isoformat(),
        "previous_r2": 0.8420,
        "change_rate": 0.12
    }


@app.get("/dashboard/trend", tags=["Dashboard"])
async def get_trend_data(weeks: int = 10, token: str = Depends(verify_token)):
    """R² 추세 데이터"""
    trend_data = []
    base_r2 = 0.8200

    for i in range(weeks):
        r2 = base_r2 + (i * 0.0025)
        trend_data.append({
            "week": f"{i+1}주",
            "r2": round(r2, 4)
        })

    return {"data": trend_data}


@app.get("/dashboard/recent-trainings", tags=["Dashboard"])
async def get_recent_trainings(limit: int = 10, token: str = Depends(verify_token)):
    """최근 재학습 기록"""
    trainings = [
        {
            "date": (datetime.now() - timedelta(days=i*7)).strftime("%Y-%m-%d"),
            "status": "success" if i % 3 != 0 else "warning",
            "r2": 0.8450 - (i * 0.003),
            "rmse": 55200000 + (i * 600000),
            "duration": f"{11 + i}분"
        }
        for i in range(min(limit, 5))
    ]

    return {"data": trainings}


@app.get("/dashboard/statistics", tags=["Dashboard"])
async def get_statistics(token: str = Depends(verify_token)):
    """통계 정보"""
    return {
        "highest_r2": 0.8450,
        "average_r2": 0.8325,
        "improvement": "2.7%",
        "training_count": 52
    }


# ============================================
# 모델 API
# ============================================
@app.get("/models", tags=["Models"])
async def list_models(token: str = Depends(verify_token)):
    """모델 목록"""
    return {
        "data": [
            {
                "id": "xgboost_001",
                "name": "XGBoost",
                "r2": 0.8420,
                "created": "2026-06-19T10:00:00",
                "status": "active"
            },
            {
                "id": "lightgbm_001",
                "name": "LightGBM",
                "r2": 0.8410,
                "created": "2026-06-19T10:00:00",
                "status": "active"
            }
        ]
    }


@app.get("/models/{model_id}", tags=["Models"])
async def get_model_details(model_id: str, token: str = Depends(verify_token)):
    """모델 상세 정보"""
    return {
        "id": model_id,
        "name": "XGBoost v20260619_100000",
        "type": "Gradient Boosting",
        "created": "2026-06-19T10:00:00",
        "last_training": "2026-06-19T10:15:00",
        "data_size": 5000,
        "features": 17,
        "r2": 0.8420,
        "mae": 42500000,
        "rmse": 55800000,
        "mape": 0.052
    }


@app.get("/models/{model_id}/feature-importance", tags=["Models"])
async def get_feature_importance(model_id: str, token: str = Depends(verify_token)):
    """특성 중요도"""
    features = [
        {"name": "면적", "importance": 38.2},
        {"name": "지역", "importance": 28.5},
        {"name": "거래일", "importance": 15.8},
        {"name": "위도", "importance": 8.0},
        {"name": "경도", "importance": 4.7},
        {"name": "주변_주유소", "importance": 3.2},
        {"name": "건축년도", "importance": 2.5},
        {"name": "평균_가격", "importance": 0.8},
        {"name": "층수", "importance": 0.3},
        {"name": "주차장", "importance": 0.1},
    ]

    return {"data": features}


@app.post("/models/{model_id}/deploy", tags=["Models"])
async def deploy_model(model_id: str, token: str = Depends(verify_token)):
    """모델 배포"""
    return {
        "status": "success",
        "message": f"Model {model_id} deployed successfully",
        "deployed_at": datetime.now().isoformat()
    }


@app.delete("/models/{model_id}", tags=["Models"])
async def delete_model(model_id: str, token: str = Depends(verify_token)):
    """모델 삭제"""
    return {
        "status": "success",
        "message": f"Model {model_id} deleted successfully"
    }


# ============================================
# 데이터 분석 API
# ============================================
@app.get("/data/quality", tags=["Data"])
async def get_data_quality(token: str = Depends(verify_token)):
    """데이터 품질 정보"""
    return {
        "total_rows": 5000,
        "missing_values": 15,
        "missing_percentage": 0.3,
        "outliers": 125,
        "outlier_percentage": 2.5,
        "quality_score": 0.992,
        "status": "excellent"
    }


@app.get("/data/price-distribution", tags=["Data"])
async def get_price_distribution(token: str = Depends(verify_token)):
    """거래금액 분포"""
    return {
        "data": [
            {"range": "1-5억", "count": 850},
            {"range": "5-10억", "count": 1200},
            {"range": "10-15억", "count": 1500},
            {"range": "15-20억", "count": 900},
            {"range": "20억+", "count": 550},
        ]
    }


@app.get("/data/region-distribution", tags=["Data"])
async def get_region_distribution(token: str = Depends(verify_token)):
    """지역별 분포"""
    return {
        "data": [
            {"name": "강남구", "value": 1200},
            {"name": "서초구", "value": 950},
            {"name": "송파구", "value": 1100},
            {"name": "강서구", "value": 800},
            {"name": "기타", "value": 950},
        ]
    }


# ============================================
# 설정 API
# ============================================
@app.get("/settings", tags=["Settings"])
async def get_settings(token: str = Depends(verify_token)):
    """설정 조회"""
    return {
        "auto_retrain": True,
        "retrain_schedule": "thursday_10:00",
        "performance_threshold": 0.95,
        "email_alert": True,
        "email_address": "admin@avm.com",
        "slack_alert": False,
        "log_level": "INFO"
    }


@app.put("/settings", tags=["Settings"])
async def update_settings(settings: Dict[str, Any], token: str = Depends(verify_token)):
    """설정 업데이트"""
    return {
        "status": "success",
        "message": "Settings updated successfully",
        "settings": settings
    }


# ============================================
# 재학습 API
# ============================================
@app.post("/retraining/start", tags=["Retraining"])
async def start_retraining(token: str = Depends(verify_token)):
    """재학습 시작"""
    return {
        "status": "started",
        "message": "Retraining started",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/retraining/status", tags=["Retraining"])
async def get_retraining_status(token: str = Depends(verify_token)):
    """재학습 상태"""
    return {
        "status": "idle",
        "last_training": datetime.now().isoformat(),
        "next_training": (datetime.now() + timedelta(days=7)).isoformat()
    }


@app.get("/retraining/history", tags=["Retraining"])
async def get_retraining_history(limit: int = 50, token: str = Depends(verify_token)):
    """재학습 이력"""
    history = []
    for i in range(min(limit, 10)):
        history.append({
            "date": (datetime.now() - timedelta(days=i*7)).isoformat(),
            "status": "success",
            "r2": 0.8450 - (i * 0.003),
            "duration_minutes": 12
        })

    return {"data": history}


# ============================================
# 에러 핸들러
# ============================================
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# ============================================
# 메인
# ============================================
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
