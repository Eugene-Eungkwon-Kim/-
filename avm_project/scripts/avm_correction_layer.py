"""WP 2.3: Correction Layer - 지역별·시간별 보정값 적용 (Loan4U 방식)."""

import logging
from typing import Dict

log = logging.getLogger(__name__)

# 지역×유형별 보정계수 — 모델 base_price에 곱하는 권역 프리미엄.
# ASSUMPTION: Loan4U MASS 분석에서 가져온 가정값이며 실거래로 캘리브레이션되지 않았다.
#   프리미엄 권역(등급1)일수록 모델 과소평가를 더 크게 보정한다는 가정.
# TODO(calibration): 실거래 확보 후 (모델예측 vs 실거래) 잔차로 권역별 계수 재추정.
REGION_CORRECTION_MAP: Dict[str, Dict[str, float]] = {
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
        '1': 1.15, '2': 1.12, '3': 1.10,
        '4': 1.08, '5': 1.06, '6': 1.05,
    },
}

# 연도별 시간 조정 (기준: 2024 = 1.0)
# ASSUMPTION: 한국 부동산 명목 시세 수준의 근사. TODO: 실제 지수(KB/한국부동산원)로 교체.
TEMPORAL_ADJUSTMENT: Dict[int, float] = {
    2024: 1.00, 2023: 0.95, 2022: 0.88,
    2021: 0.82, 2020: 0.75,
}


class CorrectionLayer:
    """지역별·시간별 보정값 적용."""

    def get_region_correction(self, property_type: str, district_grade: str) -> float:
        """지역 보정값 조회."""
        grade_map = REGION_CORRECTION_MAP.get(property_type.lower(), {})
        return grade_map.get(str(district_grade), 1.20)

    def get_temporal_adjustment(self, reference_year: int) -> float:
        """연도별 시간 조정값 조회."""
        return TEMPORAL_ADJUSTMENT.get(reference_year, 1.00)

    def apply_corrections(
        self,
        base_price: float,
        property_type: str,
        district_grade: str,
        reference_year: int = 2024,
    ) -> float:
        """보정 공식: base_price × region_factor × temporal_factor."""
        region = self.get_region_correction(property_type, district_grade)
        temporal = self.get_temporal_adjustment(reference_year)
        corrected = base_price * region * temporal
        log.debug(f"Correction: {base_price:,.0f} × {region} × {temporal} = {corrected:,.0f}")
        return corrected

    def get_correction_breakdown(
        self,
        base_price: float,
        property_type: str,
        district_grade: str,
        reference_year: int = 2024,
    ) -> Dict:
        """보정값 상세 분해 (디버깅용)."""
        region = self.get_region_correction(property_type, district_grade)
        temporal = self.get_temporal_adjustment(reference_year)
        return {
            'base_price': base_price,
            'region_factor': region,
            'temporal_factor': temporal,
            'corrected_price': base_price * region * temporal,
            'region_adjustment_pct': (region - 1.0) * 100,
            'temporal_adjustment_pct': (temporal - 1.0) * 100,
        }
