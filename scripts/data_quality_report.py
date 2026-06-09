#!/usr/bin/env python3
"""데이터 품질 리포트 생성 스크립트"""

import logging

from sqlalchemy import func, select

from app.db.database import SessionLocal, create_tables
from app.db.models import Complex, Transaction

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run():
    create_tables()
    db = SessionLocal()

    try:
        total_complexes = db.execute(select(func.count(Complex.id))).scalar()
        total_transactions = db.execute(select(func.count(Transaction.id))).scalar()
        abnormal_txs = db.execute(
            select(func.count(Transaction.id)).where(Transaction.is_abnormal.is_(True))
        ).scalar()
        verified_txs = db.execute(
            select(func.count(Transaction.id)).where(Transaction.verified.is_(True))
        ).scalar()

        earliest = db.execute(select(func.min(Transaction.report_date))).scalar()
        latest = db.execute(select(func.max(Transaction.report_date))).scalar()

        report = {
            "complexes": {
                "total": total_complexes,
            },
            "transactions": {
                "total": total_transactions,
                "abnormal": abnormal_txs,
                "verified": verified_txs,
                "abnormal_pct": round(abnormal_txs / total_transactions * 100, 2)
                if total_transactions
                else 0,
            },
            "temporal_coverage": {
                "earliest": str(earliest),
                "latest": str(latest),
            },
        }

        for section, vals in report.items():
            logger.info("[%s] %s", section, vals)

        return report
    finally:
        db.close()


if __name__ == "__main__":
    run()
