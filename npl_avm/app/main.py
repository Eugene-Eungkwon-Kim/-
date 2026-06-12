import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.routes_batch import router as batch_router
from app.api.routes_export import router as export_router
from app.api.routes_filter import router as filter_router
from app.api.routes_report import router as report_router
from app.api.routes_monitoring import router as monitoring_router
from app.db.database import init_db
from app.monitoring.metrics import metrics_collector

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("NPL AVM API 시작")
    yield
    logger.info("NPL AVM API 종료")


app = FastAPI(
    title="NPL AVM API",
    description="NPL 담보자산 자동평가모델(AVM) — 전례/근거 데이터 기반 감정가 추정 및 낙찰가율 분석",
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(router, prefix="/api/v1")
app.include_router(batch_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(filter_router, prefix="/api/v1")
app.include_router(report_router, prefix="/api/v1")
app.include_router(monitoring_router, prefix="/api/v1")


@app.middleware("http")
async def record_request_metrics(request: Request, call_next):
    start = time.monotonic()
    error_msg = None
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        status_code = 500
        error_msg = str(exc)
        raise
    finally:
        latency_ms = (time.monotonic() - start) * 1000
        metrics_collector.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=status_code,
            latency_ms=latency_ms,
            error=error_msg,
        )
    return response


@app.get("/", tags=["root"])
def root():
    return {"status": "ok", "version": "1.2.0", "docs": "/docs"}
