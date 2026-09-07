"""SQLAlchemy 엔진/세션 설정.

이 모듈도 models.py 와 마찬가지로 원래 존재하지 않았다 — main.py 와
routes.py 가 참조하지만 실체가 없어 앱이 부팅 자체를 못 했다.

`DATABASE_URL` 환경변수로 운영 DB(PostgreSQL 등)를 지정할 수 있다.
지정하지 않으면 프로젝트 폴더 아래 SQLite 파일을 기본값으로 써서, 별도
DB 서버 없이 로컬에서 바로 동작하게 한다.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base

_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # avm_project/
_DEFAULT_SQLITE_PATH = _PROJECT_ROOT / "data" / "avm.sqlite"

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{_DEFAULT_SQLITE_PATH}")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """테이블이 없으면 만든다. 이미 있으면 손대지 않는다(비파괴적)."""
    if DATABASE_URL.startswith("sqlite"):
        _DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI `Depends(get_db)` 용 세션 제너레이터."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
