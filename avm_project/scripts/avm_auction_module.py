"""WP 2.5: Auction Module - 낙찰가 추정 (Loan4U 공식)."""

import logging
from typing import Dict

log = logging.getLogger(__name__)

# 지역별 경매 낙찰가율 (낙찰가 / 감정가). 시세보다 낮으므로 1.0 미만.
# ASSUMPTION: 대법원 경매정보 낙찰가율 통계 범위를 근사한 가정값이다.
#   - 아파트: 유동성 높아 80~93%대, 프리미엄 권역일수록 회수율 높음
#   - 다세대/연립/오피스텔: 유동성 낮아 70~85%대
#   - 토지: 가장 비유동적 65~78%대
# TODO(calibration): 실거래/경매 데이터 확보 후 권역·유형별 실측 낙찰가율로 교체.
REGION_RATES: Dict[str, Dict[str, float]] = {
    'apartment': {
        '1': 0.93, '2': 0.91, '3': 0.89,
        '4': 0.87, '5': 0.85, '6': 0.82,
    },
    'multi_family': {
        '1': 0.85, '2': 0.82, '3': 0.79,
        '4': 0.76, '5': 0.74, '6': 0.72,
    },
    'townhouse': {
        '1': 0.85, '2': 0.82, '3': 0.79,
        '4': 0.76, '5': 0.74, '6': 0.72,
    },
    'officetel': {
        '1': 0.84, '2': 0.82, '3': 0.80,
        '4': 0.78, '5': 0.77, '6': 0.75,
    },
    'land': {
        '1': 0.78, '2': 0.75, '3': 0.72,
        '4': 0.70, '5': 0.68, '6': 0.65,
    },
}

# 시장 국면 보정 — ASSUMPTION: 상승장 낙찰가율 +5%p, 하락장 -5%p 가정.
MARKET_CONDITIONS: Dict[str, float] = {
    'rising': 1.05,
    'normal': 1.00,
    'declining': 0.95,
}

DEFAULT_REGION_RATE = 0.85   # 미지정 유형/등급 폴백 (아파트 평균 근사)


class AuctionModule:
    """낙찰 예상가 계산: Base × Region Rate × Market Factor."""

    def get_region_rate(self, property_type: str, district_grade: str) -> float:
        """지역별 낙찰가율 조회."""
        rate_map = REGION_RATES.get(property_type.lower(), {})
        return rate_map.get(str(district_grade), DEFAULT_REGION_RATE)

    @staticmethod
    def _auction_confidence(region_rate: float, market_condition: str) -> float:
        """낙찰가 추정 신뢰도 — 유동성(낙찰가율↑)과 시장 안정성에 비례.

        하드코딩 0.88 대체: 회수율이 높은(유동적) 권역일수록, 안정 시장일수록
        낙찰가 예측이 신뢰할 만하다는 가정.
        """
        liquidity = (region_rate - 0.65) / (0.93 - 0.65)        # 0~1 정규화
        market_penalty = {'normal': 0.0, 'rising': 0.05, 'declining': 0.10}.get(market_condition, 0.10)
        confidence = 0.75 + 0.15 * max(0.0, min(1.0, liquidity)) - market_penalty
        return round(max(0.60, min(0.92, confidence)), 3)

    def estimate_auction_price(
        self,
        base_price: float,
        property_type: str,
        district_grade: str,
        market_condition: str = 'normal',
    ) -> Dict:
        """낙찰 예상가 계산."""
        region_rate = self.get_region_rate(property_type, district_grade)
        market_factor = MARKET_CONDITIONS.get(market_condition, 1.00)
        auction_price = base_price * region_rate * market_factor

        log.debug(f"Auction: {base_price:,.0f} × {region_rate} × {market_factor} = {auction_price:,.0f}")

        return {
            'base_price': base_price,
            'region_rate': region_rate,
            'market_factor': market_factor,
            'estimated_auction_price': auction_price,
            'market_condition': market_condition,
            'confidence': self._auction_confidence(region_rate, market_condition),
        }
