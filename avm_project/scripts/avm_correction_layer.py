"""WP 2.3: Correction Layer - 지역별·시간별 보정값 적용 (Loan4U 방식)."""

import logging
from typing import Dict

log = logging.getLogger(__name__)

# 지역×유형별 *잔차 보정계수* — 1.0 중심.
#
# 중요(이중계상 방지): 모델 타깃이 new_price(실제 시세)이므로 base_price는 이미
# "현재 시세 예측치"다. 따라서 보정은 시세에 프리미엄을 *추가*하는 것이 아니라,
# 모델의 권역별 *잔차 편향*만 ±소폭 조정해야 한다. (이전 1.20~1.30 계수는
# base_price를 체계적으로 +30% 부풀리는 이중계상 결함이었음 → 1.0 중심으로 교정)
#
# ASSUMPTION: 실거래 미확보 상태이므로 잔차 편향은 사실상 미지(=1.0)이다.
#   아래 ±3% 스프레드는 권역 신호를 유지하기 위한 최소 가정값일 뿐 근거가 아니다.
# TODO(calibration): 실거래 확보 후 (모델예측 vs 실거래) 권역별 평균잔차로 재추정.
#   캘리브레이션 전까지 corrected_price ≈ base_price 여야 한다.
REGION_CORRECTION_MAP: Dict[str, Dict[str, float]] = {
    'apartment': {
        '1': 1.03, '2': 1.02, '3': 1.00,
        '4': 0.99, '5': 0.98, '6': 0.97,
    },
    'multi_family': {
        '1': 1.00, '2': 0.99, '3': 0.98,
        '4': 0.97, '5': 0.96, '6': 0.95,
    },
    'townhouse': {
        '1': 1.00, '2': 0.99, '3': 0.98,
        '4': 0.97, '5': 0.96, '6': 0.95,
    },
    'officetel': {
        '1': 0.99, '2': 0.98, '3': 0.97,
        '4': 0.96, '5': 0.95, '6': 0.94,
    },
    'land': {
        '1': 0.98, '2': 0.97, '3': 0.96,
        '4': 0.95, '5': 0.94, '6': 0.93,
    },
}

DEFAULT_REGION_CORRECTION = 1.00   # 미지정 유형/등급 → 무보정(모델 예측 그대로)

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
        return grade_map.get(str(district_grade), DEFAULT_REGION_CORRECTION)

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
