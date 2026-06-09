from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING, List

from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.db.models import ComparableSale, Property

logger = logging.getLogger(__name__)


class ComparableExtractor:
    """NPL 물건의 비교사례 추출"""

    def __init__(self, db: "Session"):
        self.db = db

    def extract_comparables(
        self,
        npl_property: "Property",
        radius_km: float = 2.0,
        lookback_months: int = 12,
    ) -> List["ComparableSale"]:
        """
        Matching 우선순위:
        1. 같은 단지 거래 (similarity 0.95)
        2. 면적 유사한 인접 거래 (area_sim > 0.7)
        """
        from app.db.models import ComparableSale, Transaction, Unit

        cutoff = date.today() - timedelta(days=30 * lookback_months)
        comparables: List[ComparableSale] = []

        if npl_property.complex_id:
            stmt = (
                select(Transaction)
                .where(
                    Transaction.complex_id == npl_property.complex_id,
                    Transaction.report_date >= cutoff,
                    Transaction.is_abnormal.is_(False),
                )
                .limit(20)
            )
            same_complex_txs = self.db.execute(stmt).scalars().all()

            for tx in same_complex_txs:
                comp = ComparableSale(
                    npl_property_id=npl_property.id,
                    transaction_id=tx.id,
                    similarity_score=0.95,
                    area_similarity=1.0,
                    location_similarity=1.0,
                    vintage_similarity=1.0,
                    type_similarity=1.0,
                    weight=0.95,
                )
                comp.transaction = tx
                comparables.append(comp)

        if len(comparables) < 5:
            npl_area = npl_property.building_area or 0
            if npl_area > 0:
                area_lo = npl_area * 0.7
                area_hi = npl_area * 1.3

                stmt2 = (
                    select(Transaction)
                    .join(Unit, Transaction.unit_id == Unit.id)
                    .where(
                        Unit.exclusive_area >= area_lo,
                        Unit.exclusive_area <= area_hi,
                        Transaction.report_date >= cutoff,
                        Transaction.is_abnormal.is_(False),
                        Transaction.complex_id != npl_property.complex_id
                        if npl_property.complex_id
                        else True,
                    )
                    .limit(10)
                )
                nearby_txs = self.db.execute(stmt2).scalars().all()

                for tx in nearby_txs:
                    unit_area = tx.unit.exclusive_area if tx.unit else 0
                    area_sim = self._calc_area_similarity(npl_area, unit_area)
                    if area_sim < 0.7:
                        continue
                    score = area_sim * 0.8
                    comp = ComparableSale(
                        npl_property_id=npl_property.id,
                        transaction_id=tx.id,
                        similarity_score=score,
                        area_similarity=area_sim,
                        location_similarity=0.8,
                        vintage_similarity=0.8,
                        type_similarity=0.8,
                        weight=score,
                    )
                    comp.transaction = tx
                    comparables.append(comp)

        return comparables

    def _calc_area_similarity(self, area1: float, area2: float) -> float:
        if area2 <= 0 or area1 <= 0:
            return 0.0
        ratio = area1 / area2
        if ratio > 1:
            ratio = 1 / ratio
        return max(0.0, ratio * 2 - 1)
