#!/usr/bin/env python3
"""
AVM Dashboard Backend API
FastAPI 기반 REST API 서버
"""

import logging
import os
import sys
import json
import asyncio
from datetime import datetime
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
    from backend.database import history_manager
except ImportError:
    from ml_models import model_manager
    from retraining_monitor import monitor
    from database import history_manager

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
# retraining_monitor.RetrainingMonitor가 이미 이 파일에서 performance_threshold를
# 읽고 있다 — /settings 도 새 저장소를 만들지 않고 같은 파일을 읽고 쓴다.
SCHEDULE_CONFIG_FILE = PROJECT_ROOT / "config" / "schedule_config.json"

logger = logging.getLogger(__name__)

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
# /dashboard/*, /models*, /settings, /retraining/* 는 전부 고정 예시값을
# 돌려주고 있었다 — logs/retrain_history.jsonl 을 실제로 읽는 monitor
# (retraining_monitor.RetrainingMonitor)와 실제 모델 파일을 로드하는
# model_manager 는 이미 만들어져 있었지만(웹소켓 브로드캐스트 루프만
# 이걸 썼다), REST 엔드포인트는 아무도 이 둘을 호출한 적이 없었다.
# 아래는 그 둘을 그대로 연결한다 — 학습 이력이 없으면(이 환경의 현재
# 상태) 가짜 숫자 대신 status="no_data" 를 정직하게 돌려준다.
@app.get("/dashboard/summary", tags=["Dashboard"])
async def get_dashboard_summary(token: str = Depends(verify_token)):
    """대시보드 요약 정보 (실측: logs/retrain_history.jsonl 최신 기록)"""
    latest = monitor.get_latest_result()
    if latest is None:
        return {
            "status": "no_data",
            "ensemble_r2": None, "ensemble_rmse": None, "ensemble_mae": None,
            "last_updated": None, "previous_r2": None, "change_rate": None,
        }

    previous = monitor.get_previous_result()
    ensemble = latest.get("ensemble", {})
    prev_r2 = previous.get("ensemble", {}).get("r2") if previous else None
    change_rate = (
        round((ensemble.get("r2", 0) - prev_r2) / prev_r2 * 100, 2)
        if prev_r2 else None
    )

    return {
        "ensemble_r2": ensemble.get("r2"),
        "ensemble_rmse": ensemble.get("rmse"),
        "ensemble_mae": ensemble.get("mae"),
        "status": latest.get("status", "unknown"),
        "last_updated": latest.get("timestamp"),
        "previous_r2": prev_r2,
        "change_rate": change_rate,
    }


@app.get("/dashboard/trend", tags=["Dashboard"])
async def get_trend_data(weeks: int = 10, token: str = Depends(verify_token)):
    """R² 추세 데이터 (실측)"""
    return {"data": monitor.get_trend_data(weeks=weeks)}


@app.get("/dashboard/recent-trainings", tags=["Dashboard"])
async def get_recent_trainings(limit: int = 10, token: str = Depends(verify_token)):
    """최근 재학습 기록 (실측)"""
    history = history_manager.get_history(limit=limit)
    trainings = [
        {
            "date": r.get("timestamp"),
            "status": r.get("status", "unknown"),
            "r2": r.get("ensemble", {}).get("r2"),
            "rmse": r.get("ensemble", {}).get("rmse"),
            "duration": (
                f"{r['duration_minutes']}분" if r.get("duration_minutes") is not None else None
            ),
        }
        for r in reversed(history)  # 최신순
    ]
    return {"data": trainings}


@app.get("/dashboard/statistics", tags=["Dashboard"])
async def get_statistics(token: str = Depends(verify_token)):
    """통계 정보 (실측)"""
    stats = monitor.get_statistics()
    if not stats:
        return {"highest_r2": None, "average_r2": None, "improvement": None, "training_count": 0}
    return {
        "highest_r2": stats.get("max_r2"),
        "average_r2": stats.get("average_r2"),
        "improvement": f"{stats.get('success_rate', 0)}%",
        "training_count": stats.get("total_trainings", 0),
    }


# ============================================
# 모델 API
# ============================================
@app.get("/models", tags=["Models"])
async def list_models(token: str = Depends(verify_token)):
    """모델 목록 (실측: models/*.joblib — model_manager가 로드한 것)"""
    return {"data": model_manager.get_available_models()}


@app.get("/models/{model_id}", tags=["Models"])
async def get_model_details(model_id: str, token: str = Depends(verify_token)):
    """모델 상세 정보 (실측)"""
    meta = model_manager.get_model_metadata(model_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"모델을 찾을 수 없음: {model_id}")

    perf = model_manager.get_model_performance(model_id) or {}
    return {
        "id": model_id,
        "name": meta.get("display_name"),
        "type": meta.get("type"),
        "file": meta.get("file"),
        "version": meta.get("version"),
        "loaded_at": meta.get("loaded_at"),
        "is_demo": meta.get("is_demo", False),
        "is_real_data": meta.get("is_real_data", False),
        "r2": perf.get("r2"),
        "mae": perf.get("mae"),
        "rmse": perf.get("rmse"),
        "mape": perf.get("mape"),
    }


def _feature_names(count: int) -> List[str]:
    """config/schedule_config.json의 feature_columns를 재사용한다 — 개수가
    맞지 않으면(설정이 실제 학습 특성과 어긋난 경우) 정직하게 feature_0 스타일로
    돌려준다. 없는 컬럼명을 지어내지 않는다."""
    try:
        with open(SCHEDULE_CONFIG_FILE, "r", encoding="utf-8") as f:
            columns = json.load(f).get("feature_columns", [])
    except (OSError, json.JSONDecodeError):
        columns = []
    if len(columns) == count:
        return columns
    return [f"feature_{i}" for i in range(count)]


@app.get("/models/{model_id}/feature-importance", tags=["Models"])
async def get_feature_importance(model_id: str, token: str = Depends(verify_token)):
    """특성 중요도 (실측 — 트리 기반 모델의 feature_importances_)"""
    model = model_manager.get_model(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"모델을 찾을 수 없음: {model_id}")

    if not hasattr(model, "feature_importances_"):
        return {"data": [], "message": f"{type(model).__name__}은 특성 중요도를 지원하지 않습니다."}

    importances = model.feature_importances_
    names = _feature_names(len(importances))
    total = float(sum(importances)) or 1.0
    features = sorted(
        (
            {"name": name, "importance": round(float(value) / total * 100, 2)}
            for name, value in zip(names, importances)
        ),
        key=lambda item: -item["importance"],
    )
    return {"data": features[:10]}


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
@app.get("/data/quality", tags=["Data"], deprecated=True)
async def get_data_quality(token: str = Depends(verify_token)):
    """데이터 품질 정보 — 고정 예시값. 실측은 /data/comparable-sales/quality."""
    return {
        "total_rows": 5000,
        "missing_values": 15,
        "missing_percentage": 0.3,
        "outliers": 125,
        "outlier_percentage": 2.5,
        "quality_score": 0.992,
        "status": "excellent"
    }


@app.get("/data/price-distribution", tags=["Data"], deprecated=True)
async def get_price_distribution(token: str = Depends(verify_token)):
    """거래금액 분포 — 고정 예시값. 실측은 /data/comparable-sales/price-distribution."""
    return {
        "data": [
            {"range": "1-5억", "count": 850},
            {"range": "5-10억", "count": 1200},
            {"range": "10-15억", "count": 1500},
            {"range": "15-20억", "count": 900},
            {"range": "20억+", "count": 550},
        ]
    }


@app.get("/data/region-distribution", tags=["Data"], deprecated=True)
async def get_region_distribution(token: str = Depends(verify_token)):
    """지역별 분포 — 고정 예시값. 실측은 /data/comparable-sales/region-distribution."""
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
# 실거래 수집 데이터 (app/db 연동)
#
# 위 /data/* 세 엔드포인트는 고정 예시값을 돌려준다(데모용으로 보인다).
# 아래는 scripts/fetch_transactions_parallel.py 등 수집 파이프라인이
# app/db 에 적재한 실제 데이터를 그 자리에서 조회한다 — 관리자 화면이
# "수집된 데이터가 실제로 몇 건 들어왔는지"를 보려면 이 경로를 쓴다.
# ============================================
sys.path.insert(0, str(PROJECT_ROOT))


def _comparable_sales_session():
    from app.db.database import SessionLocal, init_db
    init_db()
    return SessionLocal()


@app.get("/data/comparable-sales/summary", tags=["Data"])
async def get_comparable_sales_summary(token: str = Depends(verify_token)):
    """수집 파이프라인이 적재한 실거래 데이터 현황(실측)."""
    from sqlalchemy import func
    from app.db.models import ComparableSale

    db = _comparable_sales_session()
    try:
        total = db.query(func.count(ComparableSale.id)).scalar() or 0
        by_type = (
            db.query(ComparableSale.property_type, func.count(ComparableSale.id))
            .group_by(ComparableSale.property_type).all()
        )
        by_sido = (
            db.query(ComparableSale.address_sido, func.count(ComparableSale.id))
            .group_by(ComparableSale.address_sido).all()
        )
        return {
            "total_rows": total,
            "by_property_type": [{"name": t or "미상", "count": c} for t, c in by_type],
            "by_region": [{"name": s or "미상", "count": c} for s, c in by_sido],
        }
    finally:
        db.close()


@app.get("/data/comparable-sales/price-distribution", tags=["Data"])
async def get_comparable_sales_price_distribution(token: str = Depends(verify_token)):
    """실거래 수집 데이터의 가격 분포(실측). /data/price-distribution 과 같은
    응답 모양을 쓰지만 값은 고정값이 아니라 DB 조회 결과다."""
    from app.db.models import ComparableSale

    buckets = [
        ("1-5억", 100_000_000, 500_000_000),
        ("5-10억", 500_000_000, 1_000_000_000),
        ("10-15억", 1_000_000_000, 1_500_000_000),
        ("15-20억", 1_500_000_000, 2_000_000_000),
        ("20억+", 2_000_000_000, None),
    ]
    db = _comparable_sales_session()
    try:
        data = []
        for label, lo, hi in buckets:
            q = db.query(ComparableSale).filter(ComparableSale.trade_amount >= lo)
            if hi is not None:
                q = q.filter(ComparableSale.trade_amount < hi)
            data.append({"range": label, "count": q.count()})
        return {"data": data}
    finally:
        db.close()


@app.get("/data/comparable-sales/region-distribution", tags=["Data"])
async def get_comparable_sales_region_distribution(token: str = Depends(verify_token)):
    """시군구별 실거래 건수(실측). /data/region-distribution 과 같은 응답 모양."""
    from sqlalchemy import func
    from app.db.models import ComparableSale

    db = _comparable_sales_session()
    try:
        rows = (
            db.query(ComparableSale.address_sigungu, func.count(ComparableSale.id))
            .group_by(ComparableSale.address_sigungu)
            .order_by(func.count(ComparableSale.id).desc()).all()
        )
        return {"data": [{"name": sgg or "미상", "value": count} for sgg, count in rows]}
    finally:
        db.close()


@app.get("/data/comparable-sales/quality", tags=["Data"])
async def get_comparable_sales_quality(token: str = Depends(verify_token)):
    """수집 데이터 품질(실측). /data/quality 와 같은 키를 쓰되 DB에서 계산한다.

    missing_values: 면적(건물·대지 모두)이나 거래금액이 비어 있는 행.
    outliers: 거래금액이 0 이하이거나 ㎡당 단가가 상식 범위(1만~5억 원)를 벗어난 행.
    """
    from sqlalchemy import or_
    from app.db.models import ComparableSale

    db = _comparable_sales_session()
    try:
        total = db.query(ComparableSale).count()
        missing = db.query(ComparableSale).filter(or_(
            ComparableSale.trade_amount.is_(None),
            (ComparableSale.building_area.is_(None)) & (ComparableSale.land_area.is_(None)),
        )).count()
        outliers = sum(
            1 for s in db.query(ComparableSale).filter(ComparableSale.trade_amount.isnot(None))
            if _is_price_outlier(s)
        )
        problems = missing + outliers
        score = round(1 - problems / total, 4) if total else 0.0
        status = "no_data" if not total else "excellent" if score >= 0.99 else "good" if score >= 0.95 else "needs_review"
        return {
            "total_rows": total,
            "missing_values": missing,
            "missing_percentage": round(missing / total * 100, 2) if total else 0.0,
            "outliers": outliers,
            "outlier_percentage": round(outliers / total * 100, 2) if total else 0.0,
            "quality_score": score,
            "status": status,
        }
    finally:
        db.close()


def _is_price_outlier(sale) -> bool:
    amount = float(sale.trade_amount)
    if amount <= 0:
        return True
    area = sale.building_area or sale.land_area
    if not area:
        return False
    return not (10_000 <= amount / float(area) <= 500_000_000)


# ============================================
# 설정 API
#
# config/schedule_config.json 은 retraining_monitor.py(성능 임계값)와
# weekly_retrain_scheduler.py(스케줄)가 이미 실제로 참조하는 설정 파일이다
# — 별도 설정 저장소를 새로 만들지 않고 이 파일을 그대로 읽고 쓴다. 그래야
# 관리자 화면에서 바꾼 값이 실제 재학습 스케줄/임계값에 반영된다.
# ============================================
def _load_schedule_config() -> Dict[str, Any]:
    try:
        with open(SCHEDULE_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"schedule_config.json 로드 실패, 기본값 사용: {e}")
        return {}


def _settings_view(config: Dict[str, Any]) -> Dict[str, Any]:
    schedule = config.get("schedule", {})
    alert = config.get("alert_config", {})
    return {
        "retrain_schedule": {
            "day_of_week": schedule.get("day_of_week", "thursday"),
            "hour": schedule.get("hour", 10),
            "minute": schedule.get("minute", 0),
        },
        "performance_threshold": config.get("performance_threshold", 0.95),
        "email_alert": alert.get("enable_email", False),
        "email_address": alert.get("email_address") or "",
        "slack_alert": alert.get("enable_slack", False),
        "log_level": config.get("logging", {}).get("level", "INFO"),
    }


@app.get("/settings", tags=["Settings"])
async def get_settings(token: str = Depends(verify_token)):
    """설정 조회 (실측: config/schedule_config.json)"""
    return _settings_view(_load_schedule_config())


@app.put("/settings", tags=["Settings"])
async def update_settings(settings: Dict[str, Any], token: str = Depends(verify_token)):
    """설정 업데이트 (실측 — config/schedule_config.json에 반영)"""
    config = _load_schedule_config()

    if "performance_threshold" in settings:
        config["performance_threshold"] = settings["performance_threshold"]

    alert = config.setdefault("alert_config", {})
    if "email_alert" in settings:
        alert["enable_email"] = settings["email_alert"]
    if "email_address" in settings:
        alert["email_address"] = settings["email_address"]
    if "slack_alert" in settings:
        alert["enable_slack"] = settings["slack_alert"]

    if "log_level" in settings:
        config.setdefault("logging", {})["level"] = settings["log_level"]

    try:
        SCHEDULE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"설정 저장 실패: {e}")

    return {"status": "success", "message": "설정이 저장되었습니다", "settings": _settings_view(config)}


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
    """재학습 상태 (실측)"""
    latest = monitor.get_latest_result()
    next_training = monitor.estimate_next_training()
    return {
        "status": latest.get("status", "unknown") if latest else "no_data",
        "last_training": latest.get("timestamp") if latest else None,
        "next_training": next_training.get("scheduled_time") if next_training else None,
    }


@app.get("/retraining/history", tags=["Retraining"])
async def get_retraining_history(limit: int = 50, token: str = Depends(verify_token)):
    """재학습 이력 (실측)"""
    history = history_manager.get_history(limit=limit)
    return {
        "data": [
            {
                "date": r.get("timestamp"),
                "status": r.get("status", "unknown"),
                "r2": r.get("ensemble", {}).get("r2"),
                "duration_minutes": r.get("duration_minutes"),
            }
            for r in reversed(history)
        ]
    }


# ============================================
# WebSocket 엔드포인트
# ============================================
def _is_ping(data: str) -> bool:
    """클라이언트 메시지가 ping인지 확인 (평문 "ping" 또는 {"type": "ping"} JSON 모두 지원)"""
    if data == "ping":
        return True
    try:
        return json.loads(data).get("type") == "ping"
    except (json.JSONDecodeError, AttributeError):
        return False


@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """대시보드 실시간 업데이트 WebSocket"""
    await connection_manager.connect(websocket, "dashboard")
    await connection_manager.send_personal(
        websocket, {"type": "connection", "status": "connected"}
    )
    try:
        while True:
            # 클라이언트로부터 메시지 수신 대기
            data = await websocket.receive_text()
            if _is_ping(data):
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
    await connection_manager.send_personal(
        websocket, {"type": "connection", "status": "connected"}
    )
    try:
        while True:
            # 클라이언트로부터 메시지 수신 대기
            data = await websocket.receive_text()
            if _is_ping(data):
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
