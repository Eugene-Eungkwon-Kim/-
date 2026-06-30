"""WP 12: 좌표 기반 행정구역 등급 산정 — 위치를 보정 레이어에 연결.

기존엔 district_grade가 항상 '3'으로 고정되어 위·경도가 보정에 전혀
반영되지 않았다. 이 모듈은 좌표를 한국 주요 권역의 등급(1=프리미엄 ~ 6=외곽)으로
매핑하여 CorrectionLayer가 위치에 따라 다르게 동작하도록 한다.

ASSUMPTION: 앵커 좌표와 등급은 2024년 시세 권역을 근사한 가정값이다.
실거래 확보 시 권역별 평균 단가로 재캘리브레이션해야 한다.
"""

from typing import List, Tuple

# (위도, 경도, 등급) — 등급 1 = 최프리미엄, 6 = 외곽
GRADE_ANCHORS: List[Tuple[float, float, int]] = [
    (37.497, 127.024, 1),   # 강남3구 (강남/서초/송파)
    (37.540, 126.975, 2),   # 서울 prime (마포/용산/성동)
    (37.420, 127.130, 2),   # 성남/분당/과천
    (35.163, 129.163, 2),   # 해운대/수영
    (37.572, 127.005, 3),   # 서울 중심 (종로/중구)
    (37.548, 126.880, 3),   # 서울 서부 (강서/양천)
    (37.612, 127.025, 4),   # 서울 북부 (노원/도봉)
    (37.280, 127.010, 4),   # 수원/용인/경기 중부
    (37.456, 126.705, 5),   # 인천
    (35.175, 129.050, 5),   # 부산 일반
    (37.100, 127.200, 6),   # 경기 외곽 (평택/안성)
]

DEFAULT_GRADE = '3'


def _distance_sq(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """위·경도 유클리드 거리 제곱 (한국 범위 내 근사로 충분)."""
    return (lat1 - lat2) ** 2 + (lng1 - lng2) ** 2


def grade_from_coords(latitude: float, longitude: float) -> str:
    """좌표 → 가장 가까운 앵커의 등급 문자열('1'~'6').

    한국 영역(위도 33~38.5, 경도 124~132) 밖이면 기본 등급을 반환한다.
    """
    if not (33.0 <= latitude <= 38.5 and 124.0 <= longitude <= 132.0):
        return DEFAULT_GRADE

    nearest_grade = DEFAULT_GRADE
    best = float('inf')
    for a_lat, a_lng, grade in GRADE_ANCHORS:
        d = _distance_sq(latitude, longitude, a_lat, a_lng)
        if d < best:
            best = d
            nearest_grade = str(grade)
    return nearest_grade
