"""국제 시장 대비 감정가 포지셔닝 (F.2 cross-market position).

engine.py 의 estimate() 가 이 모듈을 try/except 로 감싸 호출하므로,
여기서 실패하거나 부정확해도 핵심 추정 흐름(estimated_value 등)에는
영향이 없다. 이 모듈도 원래 존재하지 않아 engine.py 의 import 가 실패하고
있었다.

국가별 벤치마크 낙찰가율은 CLAUDE.md 에 정의된 TOLERANCE_MAP 대상 국가를
참고한 1차 초안이며, 실제 국가별 시장 데이터 연동은 별도 작업이다.
"""

from dataclasses import dataclass
from typing import Dict

_BENCHMARK_RATE: Dict[str, float] = {
    "KR": 0.65, "BR": 0.60, "UK": 0.70, "SG": 0.68, "JP": 0.72,
    "DE": 0.68, "AU": 0.66, "CA": 0.66, "TH": 0.58, "HK": 0.68,
}


@dataclass
class MarketComparison:
    position: str
    comparisons: Dict[str, float]


def compare(avg_value: int, property_type: str) -> MarketComparison:
    """평균 감정가를 국가별 벤치마크 낙찰가율과 대조해 상대 위치를 만든다."""
    comparisons = dict(_BENCHMARK_RATE)
    kr_rate = comparisons.get("KR", 0.65)
    others = [rate for code, rate in comparisons.items() if code != "KR"]
    avg_other = sum(others) / len(others) if others else kr_rate

    if kr_rate >= avg_other * 1.05:
        relative = "높음"
    elif kr_rate <= avg_other * 0.95:
        relative = "낮음"
    else:
        relative = "비슷함"

    tier = "고가" if avg_value >= 1_000_000_000 else ("중가" if avg_value >= 300_000_000 else "저가")
    position = f"{property_type} {tier} 구간 — 해외 대비 낙찰가율 {relative}"

    return MarketComparison(position=position, comparisons=comparisons)
