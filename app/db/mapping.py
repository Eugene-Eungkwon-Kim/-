from __future__ import annotations

from difflib import SequenceMatcher
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class PropertyMapper:
    """NPL 물건 ↔ rtech 단지 매핑"""

    def __init__(self, db: "Session"):
        self.db = db
        self._cache: dict[str, Optional[int]] = {}

    @staticmethod
    def normalize_address(address: str) -> str:
        """시도 + 시군구 + 동/읍/면 까지만 추출"""
        parts = address.strip().split()
        if len(parts) >= 3:
            return " ".join(parts[:3])
        return address.strip()

    def address_to_complex_id(self, npl_address: str) -> Optional[int]:
        """
        1. Exact match (LIKE 검색)
        2. Fuzzy match (SequenceMatcher ratio > 0.8)
        """
        from app.db.models import Complex
        from sqlalchemy import select

        if npl_address in self._cache:
            return self._cache[npl_address]

        normalized = self.normalize_address(npl_address)

        stmt = select(Complex).where(Complex.address_full.ilike(f"%{normalized}%"))
        exact = self.db.execute(stmt).scalars().first()
        if exact:
            self._cache[npl_address] = exact.id
            return exact.id

        sido = normalized.split()[0] if normalized else ""
        candidates_stmt = select(Complex).where(Complex.address_sido == sido)
        candidates = self.db.execute(candidates_stmt).scalars().all()

        best_id: Optional[int] = None
        best_ratio = 0.0

        for c in candidates:
            if not c.address_full:
                continue
            ratio = SequenceMatcher(None, normalized, c.address_full).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_id = c.id

        result = best_id if best_ratio > 0.8 else None
        self._cache[npl_address] = result
        return result

    @staticmethod
    def estimate_area_similarity(npl_area: float, unit_area: float) -> float:
        """면적 유사도 0~1 반환 (오차율 기반)"""
        if unit_area <= 0 or npl_area <= 0:
            return 0.0
        ratio = npl_area / unit_area
        if ratio > 1:
            ratio = 1 / ratio
        # 오차율 0%=1.0, 오차율 50%=0.0 선형 스케일
        return max(0.0, min(1.0, ratio * 2 - 1))
