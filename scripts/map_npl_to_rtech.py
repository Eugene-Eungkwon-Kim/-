#!/usr/bin/env python3
"""NPL 물건 2,645개 → rtech 단지 매핑 스크립트"""

import logging

from sqlalchemy import select

from app.db.database import SessionLocal, create_tables
from app.db.mapping import PropertyMapper
from app.db.models import Property

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run():
    create_tables()
    db = SessionLocal()

    try:
        mapper = PropertyMapper(db)
        props = db.execute(select(Property)).scalars().all()

        mapped = 0
        unmapped = 0

        for prop in props:
            if not prop.address_full:
                unmapped += 1
                continue

            complex_id = mapper.address_to_complex_id(prop.address_full)
            if complex_id:
                prop.complex_id = complex_id
                mapped += 1
            else:
                unmapped += 1

        db.commit()
        total = len(props)
        pct = mapped / total * 100 if total else 0
        logger.info(
            "매핑 완료: %d/%d (%.1f%%) | 실패: %d",
            mapped, total, pct, unmapped,
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
