"""WP 4: KR 특화 AVM 통합 테스트 — 지역별 가격 검증."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# (이름, area_sqm, old_price, lat, lng, ptype, min_price_억, max_price_억)
# 허용범위는 보정 이중계상 수정 후 실측 corrected_price 기준 ±~20% 밴드.
# 의도적으로 좁게 설정 — 과거 30% 인플레(예: 강남 33억)가 재발하면 테스트가 잡아낸다.
KR_TEST_CASES = [
    ('강남_84sqm',      84,  2_400_000_000, 37.497, 127.024, 'apartment', 22.5, 32.5),
    ('서울prime_59sqm', 59,    800_000_000, 37.540, 126.975, 'apartment',  7.5, 11.5),
    ('서울중심_33sqm',  33,    450_000_000, 37.572, 127.005, 'apartment',  3.9,  6.0),
    ('서울북부_84sqm',  84,    600_000_000, 37.612, 127.025, 'apartment',  5.6,  8.6),
    ('성남_84sqm',      84,    900_000_000, 37.420, 127.130, 'apartment',  8.3, 12.5),
    ('수원_85sqm',      85,    550_000_000, 37.280, 127.010, 'apartment',  4.9,  7.5),
    ('인천_84sqm',      84,    420_000_000, 37.456, 126.705, 'apartment',  3.6,  5.5),
    ('해운대_84sqm',    84,  1_000_000_000, 35.163, 129.163, 'apartment',  8.2, 12.5),
    ('부산일반_59sqm',  59,    350_000_000, 35.175, 129.050, 'apartment',  3.0,  4.7),
    ('경기외곽_24sqm',  24,    180_000_000, 37.100, 127.200, 'apartment',  1.4,  2.2),
]


@pytest.fixture(scope='module')
def engine():
    from scripts.avm_core_engine import AVMCoreEngine
    return AVMCoreEngine()


class TestKRValuation:

    @pytest.mark.parametrize('name,area,old_price,lat,lng,ptype,lo,hi', KR_TEST_CASES)
    def test_price_positive(self, engine, name, area, old_price, lat, lng, ptype, lo, hi):
        """모든 KR 케이스에서 corrected_price > 0."""
        result = engine.valuate(
            area_sqm=area, old_price=old_price,
            latitude=lat, longitude=lng, property_type=ptype,
        )
        assert result['corrected_price'] > 0, f"{name}: 가격 ≤ 0"

    @pytest.mark.parametrize('name,area,old_price,lat,lng,ptype,lo_억,hi_억', KR_TEST_CASES)
    def test_price_in_market_range(self, engine, name, area, old_price, lat, lng, ptype, lo_억, hi_억):
        """corrected_price 가 한국 시장 허용 범위 내 (억원 단위)."""
        result = engine.valuate(
            area_sqm=area, old_price=old_price,
            latitude=lat, longitude=lng, property_type=ptype,
        )
        price_억 = result['corrected_price'] / 1e8
        assert lo_억 <= price_억 <= hi_억, (
            f"{name}: {price_억:.1f}억, 허용 [{lo_억}, {hi_억}]억"
        )

    def test_price_monotone_by_area(self, engine):
        """동일 지역·조건에서 면적이 클수록 총 가격이 높아야 함."""
        areas = [24, 50, 84, 120]
        prices = [
            engine.valuate(
                area_sqm=a, old_price=1_000_000_000,
                latitude=37.497, longitude=127.024,
                property_type='apartment',
            )['corrected_price']
            for a in areas
        ]
        assert prices == sorted(prices), \
            f"면적 단조증가 위반: {[round(p/1e8,1) for p in prices]}억"

    def test_confidence_above_floor(self, engine):
        """정상 KR 입력 시 신뢰도 ≥ 0.60."""
        result = engine.valuate(
            area_sqm=84, old_price=1_000_000_000,
            latitude=37.497, longitude=127.024,
            property_type='apartment',
        )
        assert result['confidence'] >= 0.60, \
            f"신뢰도 {result['confidence']:.3f} < 0.60"

    def test_auction_price_positive(self, engine):
        """낙찰가 추정값이 양수."""
        result = engine.valuate(
            area_sqm=84, old_price=1_000_000_000,
            latitude=37.497, longitude=127.024,
            property_type='apartment',
        )
        assert result['auction_forecast']['estimated_auction_price'] > 0

    def test_gangnam_higher_than_gyeonggi_outer(self, engine):
        """강남 3구 84㎡ 가격 > 경기 외곽 84㎡ 가격 (동일 old_price)."""
        base_price = 800_000_000
        gangnam = engine.valuate(
            area_sqm=84, old_price=base_price,
            latitude=37.497, longitude=127.024, property_type='apartment',
        )['corrected_price']
        gyeonggi = engine.valuate(
            area_sqm=84, old_price=base_price,
            latitude=37.100, longitude=127.200, property_type='apartment',
        )['corrected_price']
        assert gangnam > gyeonggi, \
            f"강남({gangnam/1e8:.1f}억) ≤ 경기외곽({gyeonggi/1e8:.1f}억)"

    def test_response_keys_complete(self, engine):
        """응답 필드 완전성 검증."""
        result = engine.valuate(
            area_sqm=84, old_price=1_000_000_000,
            latitude=37.497, longitude=127.024,
            property_type='apartment',
        )
        required = {'base_price', 'corrected_price', 'confidence',
                    'validation_status', 'validation', 'auction_forecast',
                    'latency_ms', 'model_version', 'timestamp'}
        assert required <= result.keys(), f"누락 필드: {required - result.keys()}"

    def test_latency_under_500ms(self, engine):
        """콜드 캐시 레이턴시 < 500ms."""
        import time
        start = time.perf_counter()
        engine.valuate(
            area_sqm=84, old_price=1_000_000_000,
            latitude=37.497, longitude=127.024,
            property_type='apartment',
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"레이턴시 {elapsed_ms:.0f}ms > 500ms"

    def test_batch_valuate_kr(self, engine):
        """KR 5건 배치 평가 — 모두 양수 가격."""
        props = [
            {'area_sqm': a, 'old_price': p, 'latitude': lat, 'longitude': lng,
             'property_type': 'apartment'}
            for a, p, lat, lng in [
                (84, 2_000_000_000, 37.497, 127.024),
                (59,   800_000_000, 37.540, 126.975),
                (85,   550_000_000, 37.280, 127.010),
                (84,   420_000_000, 37.456, 126.705),
                (84,   900_000_000, 35.163, 129.163),
            ]
        ]
        results = engine.batch_valuate(props)
        assert len(results) == 5
        assert all(r['corrected_price'] > 0 for r in results), "배치 내 음수 가격 존재"

    # ── 입력 가드레일 (OOD 방어) ──────────────────────────────────────────

    def test_reject_zero_price(self, engine):
        """old_price=0 은 ValueError로 거부."""
        with pytest.raises(ValueError, match="old_price"):
            engine.valuate(area_sqm=84, old_price=0,
                           latitude=37.5, longitude=127.0, property_type='apartment')

    def test_reject_negative_area(self, engine):
        """음수 면적은 ValueError로 거부."""
        with pytest.raises(ValueError, match="area_sqm"):
            engine.valuate(area_sqm=-5, old_price=500_000_000,
                           latitude=37.5, longitude=127.0, property_type='apartment')

    def test_overseas_coords_flagged_low_confidence(self, engine):
        """한국 밖 좌표는 경고 + 신뢰도 페널티."""
        r = engine.valuate(area_sqm=84, old_price=500_000_000,
                           latitude=45.0, longitude=140.0, property_type='apartment')
        assert len(r['input_warnings']) >= 1
        assert r['confidence'] <= 0.50, "OOD 입력인데 신뢰도 페널티 미적용"

    def test_normal_input_no_warnings(self, engine):
        """정상 한국 입력은 경고 없음."""
        r = engine.valuate(area_sqm=84, old_price=800_000_000,
                           latitude=37.497, longitude=127.024, property_type='apartment')
        assert r['input_warnings'] == []

    # ── 강화된 정량 단언 ──────────────────────────────────────────────────

    def test_grade_descends_with_distance_from_gangnam(self, engine):
        """강남에서 멀어질수록 등급 숫자가 커진다(=프리미엄 낮아짐)."""
        gangnam = engine.valuate(area_sqm=84, old_price=8e8,
                                 latitude=37.497, longitude=127.024, property_type='apartment')
        outer = engine.valuate(area_sqm=84, old_price=8e8,
                               latitude=37.100, longitude=127.200, property_type='apartment')
        assert int(gangnam['district_grade']) < int(outer['district_grade'])

    def test_auction_below_valuation(self, engine):
        """낙찰 예상가는 항상 보정 평가가보다 낮다(경매 할인)."""
        r = engine.valuate(area_sqm=84, old_price=8e8,
                           latitude=37.497, longitude=127.024, property_type='apartment')
        assert r['auction_forecast']['estimated_auction_price'] < r['corrected_price']

    def test_regression_engine_suite(self):
        """엔진 테스트 스위트 회귀 없음 — 실패 0건 (subprocess 실행)."""
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', 'tests/test_avm_engine.py', '-q', '--tb=short'],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert ' failed' not in result.stdout and 'passed' in result.stdout, \
            f"엔진 테스트 회귀:\n{result.stdout}\n{result.stderr}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

