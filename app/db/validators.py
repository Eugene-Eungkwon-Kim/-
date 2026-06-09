from datetime import date
import statistics


class ComplexValidator:

    @staticmethod
    def validate_address(address: str, code: str = "") -> bool:
        """시도 + 시군구 최소 포함 여부 확인"""
        if not address or len(address.strip()) < 5:
            return False
        parts = address.strip().split()
        return len(parts) >= 2

    @staticmethod
    def validate_area(total_area: float, unit_count: int) -> bool:
        """호당 평균면적 합리성 (최소 30㎡, 최대 500㎡)"""
        if unit_count <= 0 or total_area <= 0:
            return False
        avg_area = total_area / unit_count
        return 30 <= avg_area <= 500


class TransactionValidator:

    @staticmethod
    def detect_abnormal_price(
        unit_price: float,
        complex_avg: float,
        z_score_threshold: float = 3.0,
    ) -> bool:
        """Z-score 기반 이상거래 탐지 — complex_avg=0이면 검사 생략"""
        if complex_avg <= 0:
            return False
        z = abs(unit_price - complex_avg) / (complex_avg * 0.3)
        return z > z_score_threshold

    @staticmethod
    def validate_date_sequence(contract_date: date, report_date: date) -> bool:
        """계약일 ≤ 신고일 검증"""
        return contract_date <= report_date
