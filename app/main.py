from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import create_tables
from app.api.routes import router_v1, router_v2


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="AVM Agent API",
    description="rtech 기반 자동감정평가 Agent",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(router_v1)
app.include_router(router_v2)


@app.get("/health")
def health():
    return {"status": "ok"}
