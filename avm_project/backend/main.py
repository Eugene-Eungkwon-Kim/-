#!/usr/bin/env python3
"""
AVM Dashboard Backend API
FastAPI 기반 REST API 서버
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, status, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# 모니터링 모듈 임포트
# 실행 방식에 따라 두 가지 임포트 경로 지원:
#  - `cd backend && uvicorn main:app` (문서 권장)  → 최상위 모듈
#  - `uvicorn backend.main:app` (avm_project 루트) → backend 패키지
try:
    from backend.ml_models import model_manager
    from backend.retraining_monitor import monitor
except ImportError:
    from ml_models import model_manager
    from retraining_monitor import monitor

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
# backend/ 는 avm_project/ 내부에 위치하므로 parent.parent == avm_project 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# ============================================
# WebSocket 메시지 타입
# ============================================
class MessageType(str, Enum):
    """WebSocket 메시지 타입"""
    DASHBOARD_UPDATE = "dashboard_update"
    DEGRADATION_ALERT = "degradation_alert"
    TRAINING_STATUS = "training_status"
    MODEL_PERFORMANCE = "model_performance"
    SYSTEM_HEALTH = "system_health"


# ============================================
# ConnectionManager - WebSocket 연결 관리
# ============================================
class ConnectionManager:
    """WebSocket 연결 관리자"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "dashboard": set(),
            "monitoring": set()
        }
        self.background_task = None

    async def connect(self, websocket: WebSocket, channel: str):
        """클라이언트 연결"""
        await websocket.accept()
        if channel in self.active_connections:
            self.active_connections[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        """클라이언트 연결 해제"""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)

    async def broadcast(self, channel: str, message: Dict[str, Any]):
        """채널에 메시지 브로드캐스트"""
        if channel not in self.active_connections:
            return

        disconnected = set()
        for websocket in self.active_connections[channel]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                disconnected.add(websocket)

        # 연결 끊긴 클라이언트 제거
        for ws in disconnected:
            self.active_connections[channel].discard(ws)

    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        """개별 메시지 전송"""
        try:
            await websocket.send_json(message)
        except Exception:
            pass


# 전역 ConnectionManager 인스턴스
connection_manager = ConnectionManager()


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
# WebSocket 엔드포인트
# ============================================
@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """대시보드 실시간 업데이트 WebSocket"""
    await connection_manager.connect(websocket, "dashboard")
    try:
        while True:
            # 클라이언트로부터 메시지 수신 대기
            data = await websocket.receive_text()
            if data == "ping":
                await connection_manager.send_personal(
                    websocket,
                    {"type": "pong", "timestamp": datetime.now().isoformat()}
                )
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, "dashboard")
    except Exception as e:
        connection_manager.disconnect(websocket, "dashboard")


@app.websocket("/ws/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    """모니터링 실시간 업데이트 WebSocket"""
    await connection_manager.connect(websocket, "monitoring")
    try:
        while True:
            # 클라이언트로부터 메시지 수신 대기
            data = await websocket.receive_text()
            if data == "ping":
                await connection_manager.send_personal(
                    websocket,
                    {"type": "pong", "timestamp": datetime.now().isoformat()}
                )
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, "monitoring")
    except Exception as e:
        connection_manager.disconnect(websocket, "monitoring")


# ============================================
# 백그라운드 업데이트 작업
# ============================================
async def broadcast_dashboard_updates():
    """대시보드 업데이트 브로드캐스트 (30초마다)"""
    while True:
        try:
            await asyncio.sleep(30)

            # 최신 재학습 결과 조회
            latest_result = monitor.get_latest_result()
            trend_data = monitor.get_trend_data(weeks=10)
            stats = monitor.get_statistics()

            message = {
                "type": MessageType.DASHBOARD_UPDATE,
                "timestamp": datetime.now().isoformat(),
                "latest_result": latest_result,
                "trend_data": trend_data,
                "statistics": stats
            }

            await connection_manager.broadcast("dashboard", message)

        except Exception as e:
            pass


async def broadcast_monitoring_updates():
    """모니터링 업데이트 브로드캐스트 (30초마다)"""
    while True:
        try:
            await asyncio.sleep(30)

            # 성능 저하 확인
            degradation = monitor.check_performance_degradation()

            # 다음 학습 시간 예측
            next_training = monitor.estimate_next_training()

            # 시스템 상태
            health_status = monitor.get_health_status()

            # 성능 저하 감지 시 알림
            if degradation and degradation.get("detected"):
                message = {
                    "type": MessageType.DEGRADATION_ALERT,
                    "timestamp": datetime.now().isoformat(),
                    "alert": degradation
                }
                await connection_manager.broadcast("monitoring", message)

            # 일반 모니터링 메시지
            message = {
                "type": MessageType.SYSTEM_HEALTH,
                "timestamp": datetime.now().isoformat(),
                "health_status": health_status,
                "next_training": next_training
            }

            await connection_manager.broadcast("monitoring", message)

        except Exception as e:
            pass


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 백그라운드 작업 시작"""
    # 백그라운드 작업 시작
    asyncio.create_task(broadcast_dashboard_updates())
    asyncio.create_task(broadcast_monitoring_updates())


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
