#!/usr/bin/env python3
"""모든 NPL 물건의 비교사례 추출 스크립트"""

import logging

from sqlalchemy import select

from app.db.database import SessionLocal, init_db as create_tables
from app.db.models import ComparableSale, Property
from app.avm.comparable_extraction import ComparableExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RESIDENTIAL_TYPES = ("아파트", "다세대", "연립", "오피스텔")


def run():
    create_tables()
    db = SessionLocal()

    try:
        extractor = ComparableExtractor(db)
        stmt = select(Property).where(
            Property.property_type.in_(RESIDENTIAL_TYPES)
        )
        props = db.execute(stmt).scalars().all()

        total_comps = 0

        for prop in props:
            comps = extractor.extract_comparables(prop)
            for comp in comps:
                db_comp = ComparableSale(
                    npl_property_id=comp.npl_property_id,
                    transaction_id=comp.transaction_id,
                    similarity_score=comp.similarity_score,
                    area_similarity=comp.area_similarity,
                    location_similarity=comp.location_similarity,
                    vintage_similarity=comp.vintage_similarity,
                    type_similarity=comp.type_similarity,
                    weight=comp.weight,
                )
                db.add(db_comp)
            total_comps += len(comps)

        db.commit()
        n = len(props)
        logger.info(
            "비교사례 추출 완료: %d개 (물건당 평균 %.1f개)",
            total_comps,
            total_comps / n if n else 0,
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
