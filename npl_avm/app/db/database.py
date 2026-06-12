from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from app.db.models import Base
import os
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/npl_avm.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    create_missing_indexes()


def create_missing_indexes():
    """Create all missing indexes defined in models."""
    try:
        inspector = inspect(engine)

        with engine.begin() as conn:
            for table_name, table in Base.metadata.tables.items():
                existing_indexes = {idx_dict['name'] for idx_dict in inspector.get_indexes(table_name)}

                if not hasattr(table, 'indexes'):
                    continue

                for idx in table.indexes:
                    if idx.name not in existing_indexes:
                        try:
                            idx.create(conn)
                            logger.info(f"Created index: {idx.name} on {table_name}")
                        except Exception as e:
                            logger.warning(f"Index creation failed: {idx.name} - {e}")
    except Exception as e:
        logger.warning(f"Index creation skipped: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
