from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.routes_rag import router as rag_router
from app.db.database import init_db


class RootResponse(BaseModel):
    status: str
    docs: str


app = FastAPI(
    title="NPL AVM API",
    description="NPL 담보자산 자동평가모델(AVM) — 전례/근거 데이터 기반 감정가 추정 및 낙찰가율 분석",
    version="0.2.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우트 등록
app.include_router(router, prefix="/api/v1")
app.include_router(rag_router)  # v4는 라우터에 포함


@app.on_event("startup")
def startup():
    init_db()


@app.get("/", response_model=RootResponse)
def root() -> RootResponse:
    return RootResponse(status="ok", docs="/docs")
