#!/usr/bin/env python3
"""헤도닉 가격모형 학습 스크립트

Usage:
    python scripts/train_hedonic_model.py
"""

import logging
from pathlib import Path

from sqlalchemy import select

from app.db.database import SessionLocal, init_db as create_tables
from app.db.models import Transaction
from app.ml.hedonic import HedhonicPriceModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MODEL_PATH = "data/hedonic_model.pkl"
MIN_SAMPLES = 10_000


def run():
    create_tables()
    db = SessionLocal()

    try:
        stmt = (
            select(Transaction)
            .where(
                Transaction.is_abnormal.is_(False),
                Transaction.verified.is_(True),
            )
            .limit(100_000)
        )
        txs = db.execute(stmt).scalars().all()
        logger.info("학습 데이터: %d건", len(txs))

        if len(txs) < MIN_SAMPLES:
            logger.warning("학습 데이터 부족 (%d건 < %d건)", len(txs), MIN_SAMPLES)

        model = HedhonicPriceModel()
        model.fit(txs)

        Path("data").mkdir(exist_ok=True)
        model.save(MODEL_PATH)

        fi = model.feature_importance()
        logger.info("특성 중요도: %s", fi)

    finally:
        db.close()


if __name__ == "__main__":
    run()
