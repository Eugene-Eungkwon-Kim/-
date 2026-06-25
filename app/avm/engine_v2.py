from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

import numpy as np
from pydantic import BaseModel

from app.avm.comparable_extraction import ComparableExtractor

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.db.models import Property

logger = logging.getLogger(__name__)

# 시점수정계수 임시 고정값 (Phase 4에서 실제 DB 연동 예정)
_TIME_ADJ = 0.8 * 0.02 + 0.2 * 0.01  # 0.018


class AVMResult(BaseModel):
    property_id: int
    point_estimate: int
    lower_bound: int
    upper_bound: int
    confidence_level: float
    comparable_count: int
    comparable_details: list[dict[str, Any]]
    method: str
    estimated_at: datetime


class AVMEngineV2:
    def __init__(self, db: "Session"):
        self.db = db
        self.extractor = ComparableExtractor(db)

    def estimate(self, npl_property: "Property", confidence_level: float = 0.85) -> AVMResult:
        comparables = self.extractor.extract_comparables(npl_property)
        if not comparables:
            raise ValueError("비교사례 부족 (최소 1개 필요)")

        prices = [float(c.transaction.price) for c in comparables]
        filtered = self._remove_outliers(prices) or prices

        filtered_set = set(filtered)
        comparables = [c for c in comparables if float(c.transaction.price) in filtered_set]

        adjusted = [float(c.transaction.price) * (1 + _TIME_ADJ) for c in comparables]

        weights = np.array([c.weight for c in comparables], dtype=float)
        weights /= weights.sum()
        point = float(np.dot(adjusted, weights))

        std = float(np.std(adjusted)) if len(adjusted) > 1 else point * 0.1
        margin = 1.96 * std / (len(adjusted) ** 0.5)

        return AVMResult(
            property_id=npl_property.id,
            point_estimate=int(point),
            lower_bound=int(point - margin),
            upper_bound=int(point + margin),
            confidence_level=confidence_level,
            comparable_count=len(comparables),
            comparable_details=[
                {
                    "transaction_id": c.transaction_id,
                    "price": int(c.transaction.price),
                    "date": c.transaction.report_date.isoformat() if c.transaction.report_date else None,
                    "similarity": c.similarity_score,
                    "weight": float(c.weight),
                }
                for c in comparables[:5]
            ],
            method="weighted_avg+time_adj",
            estimated_at=datetime.utcnow(),
        )

    @staticmethod
    def _remove_outliers(prices: list[float], k: float = 1.5) -> list[float]:
        if len(prices) < 4:
            return prices
        arr = np.array(prices)
        q1, q3 = float(np.percentile(arr, 25)), float(np.percentile(arr, 75))
        iqr = q3 - q1
        return [p for p in prices if q1 - k * iqr <= p <= q3 + k * iqr]
