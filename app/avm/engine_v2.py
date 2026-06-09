from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel

from app.avm.comparable_extraction import ComparableExtractor

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.db.models import Property

logger = logging.getLogger(__name__)


class AVMResult(BaseModel):
    property_id: int
    point_estimate: int
    lower_bound: int
    upper_bound: int
    confidence_level: float
    comparable_count: int
    comparable_details: List[Dict[str, Any]]
    method: str
    estimated_at: datetime


class AVMEngineV2:
    """
    확장된 감정평가 엔진 — 비교사례 기반 + 시점수정계수

    v1 대비:
    - 다중 거래사례 활용
    - IQR 이상치 제거
    - 시점수정계수 (KB시세 + 지가변동률)
    - 신뢰도 범위 추정
    """

    def __init__(self, db: "Session"):
        self.db = db
        self.extractor = ComparableExtractor(db)

    def estimate(
        self,
        npl_property: "Property",
        confidence_level: float = 0.85,
    ) -> AVMResult:
        """
        [Step 1] 비교사례 추출
        [Step 2] 이상치 제거
        [Step 3] 시점수정계수 적용
        [Step 4] 가중평균
        [Step 5] 신뢰도 범위 계산
        """
        comparables = self.extractor.extract_comparables(npl_property)

        if not comparables:
            raise ValueError("비교사례 부족 (최소 1개 필요)")

        prices = [float(c.transaction.price) for c in comparables]
        filtered_prices = self._remove_outliers(prices)
        if not filtered_prices:
            filtered_prices = prices

        # 이상치 제거 후 comparables 동기화
        filtered_set = set(filtered_prices)
        comparables = [
            c for c in comparables if float(c.transaction.price) in filtered_set
        ]

        adjusted_prices = []
        for comp in comparables:
            tx = comp.transaction
            adj = self._calc_time_adjustment(
                tx.report_date,
                getattr(npl_property, "address_sido", ""),
            )
            adjusted_prices.append(float(tx.price) * (1 + adj))

        weights = np.array([c.weight for c in comparables], dtype=float)
        weights /= weights.sum()

        point_estimate = float(np.dot(adjusted_prices, weights))

        std_dev = float(np.std(adjusted_prices)) if len(adjusted_prices) > 1 else point_estimate * 0.1
        # 95% 신뢰구간
        z = 1.96
        n = len(adjusted_prices)
        margin = z * std_dev / (n ** 0.5)

        lower_bound = int(point_estimate - margin)
        upper_bound = int(point_estimate + margin)

        details = [
            {
                "transaction_id": c.transaction_id,
                "price": int(c.transaction.price),
                "date": c.transaction.report_date.isoformat() if c.transaction.report_date else None,
                "similarity": c.similarity_score,
                "weight": float(c.weight),
            }
            for c in comparables[:5]
        ]

        return AVMResult(
            property_id=npl_property.id,
            point_estimate=int(point_estimate),
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=confidence_level,
            comparable_count=len(comparables),
            comparable_details=details,
            method="weighted_avg + time_adjustment",
            estimated_at=datetime.utcnow(),
        )

    def _remove_outliers(
        self, prices: List[float], iqr_multiplier: float = 1.5
    ) -> List[float]:
        """IQR 기반 이상치 제거"""
        if len(prices) < 4:
            return prices
        arr = np.array(prices)
        q1 = float(np.percentile(arr, 25))
        q3 = float(np.percentile(arr, 75))
        iqr = q3 - q1
        lo = q1 - iqr_multiplier * iqr
        hi = q3 + iqr_multiplier * iqr
        return [p for p in prices if lo <= p <= hi]

    def _calc_time_adjustment(self, transaction_date: Optional[date], sido: str) -> float:
        """시점수정계수 = 0.8 × KB시세변화율 + 0.2 × 지가변동률"""
        kb_rate = self._get_kb_price_change(sido, transaction_date)
        land_rate = self._get_land_price_change(sido, transaction_date)
        return 0.8 * kb_rate + 0.2 * land_rate

    def _get_kb_price_change(self, sido: str, from_date: Optional[date]) -> float:
        """KB 시세변화율 (미구축 단계 — 임시 고정값)"""
        return 0.02

    def _get_land_price_change(self, sido: str, from_date: Optional[date]) -> float:
        """지가변동률 (미구축 단계 — 임시 고정값)"""
        return 0.01
