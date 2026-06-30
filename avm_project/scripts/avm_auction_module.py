"""WP 2.5: Auction Module - 낙찰가 추정 (Loan4U 공식)."""

import logging
from typing import Dict

log = logging.getLogger(__name__)

# Loan4U 지역별 낙찰가율
REGION_RATES: Dict[str, Dict[str, float]] = {
    'apartment': {
        '1': 1.30, '2': 1.28, '3': 1.26,
        '4': 1.24, '5': 1.22, '6': 1.20,
    },
    'multi_family': {
        '1': 1.30, '2': 1.26, '3': 1.22,
        '4': 1.20, '5': 1.20, '6': 1.20,
    },
    'townhouse': {
        '1': 1.30, '2': 1.26, '3': 1.22,
        '4': 1.20, '5': 1.20, '6': 1.20,
    },
    'officetel': {
        '1': 1.20, '2': 1.18, '3': 1.16,
        '4': 1.15, '5': 1.17, '6': 1.20,
    },
    'land': {
        '1': 1.10, '2': 1.08, '3': 1.06,
        '4': 1.05, '5': 1.05, '6': 1.05,
    },
}

MARKET_CONDITIONS: Dict[str, float] = {
    'rising': 1.05,
    'normal': 1.00,
    'declining': 0.95,
}


class AuctionModule:
    """낙찰 예상가 계산: Base × Region Rate × Market Factor."""

    def get_region_rate(self, property_type: str, district_grade: str) -> float:
        """지역별 낙찰가율 조회."""
        rate_map = REGION_RATES.get(property_type.lower(), {})
        return rate_map.get(str(district_grade), 1.20)

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
            'confidence': 0.88,
        }
