from fastapi import FastAPI
from app.api.routes import router
from app.db.database import init_db

app = FastAPI(
    title="NPL AVM API",
    description="NPL 담보자산 자동평가모델(AVM) — 전례/근거 데이터 기반 감정가 추정 및 낙찰가율 분석",
    version="0.1.0",
)

app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
