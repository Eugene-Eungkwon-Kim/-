"""AVMEngineV2 단위 테스트"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.avm.engine_v2 import AVMEngineV2, AVMResult
from app.db.models import ComparableSale, Complex, Property, Transaction, Unit


def _make_property(pid=1, building_area=84.0, complex_id=1, sido="경기도"):
    prop = MagicMock(spec=Property)
    prop.id = pid
    prop.building_area = building_area
    prop.complex_id = complex_id
    prop.address_sido = sido
    return prop


def _make_transaction(tid=1, price=300_000_000, report_date=None, complex_id=1):
    tx = MagicMock(spec=Transaction)
    tx.id = tid
    tx.price = price
    tx.report_date = report_date or date(2026, 1, 1)
    tx.complex_id = complex_id
    unit = MagicMock(spec=Unit)
    unit.exclusive_area = 84.0
    tx.unit = unit
    return tx


def _make_comparable(tx, score=0.9):
    comp = MagicMock(spec=ComparableSale)
    comp.transaction = tx
    comp.transaction_id = tx.id
    comp.similarity_score = score
    comp.weight = score
    return comp


@pytest.fixture
def db_session():
    return MagicMock()


@pytest.fixture
def engine(db_session):
    return AVMEngineV2(db_session)


def test_remove_outliers_basic(engine):
    """IQR 이상치 제거 — 극단값 제거 확인"""
    prices = [100, 110, 105, 108, 102, 1000, 99]
    filtered = engine._remove_outliers(prices)
    assert 1000 not in filtered
    assert len(filtered) < len(prices)


def test_remove_outliers_small_list(engine):
    """4개 미만 시 원본 반환"""
    prices = [100, 200, 300]
    assert engine._remove_outliers(prices) == prices


def test_calc_time_adjustment_returns_float(engine):
    """시점수정계수 반환 타입 확인"""
    adj = engine._calc_time_adjustment(date(2025, 1, 1), "경기도")
    assert isinstance(adj, float)
    assert -0.5 < adj < 0.5  # 합리적 범위


def test_estimate_raises_when_no_comparables(engine):
    """비교사례 없을 때 ValueError"""
    prop = _make_property()
    with patch.object(engine.extractor, "extract_comparables", return_value=[]):
        with pytest.raises(ValueError):
            engine.estimate(prop)


def test_estimate_success(engine):
    """정상 추정 — AVMResult 반환"""
    prop = _make_property()
    txs = [_make_transaction(i, 300_000_000 + i * 1_000_000) for i in range(5)]
    comps = [_make_comparable(tx) for tx in txs]

    with patch.object(engine.extractor, "extract_comparables", return_value=comps):
        result = engine.estimate(prop)

    assert isinstance(result, AVMResult)
    assert result.property_id == 1
    assert result.point_estimate > 0
    assert result.lower_bound <= result.point_estimate <= result.upper_bound
    assert result.comparable_count == 5


def test_estimate_confidence_level_passed(engine):
    """confidence_level 파라미터 전달 확인"""
    prop = _make_property()
    txs = [_make_transaction(i, 300_000_000) for i in range(3)]
    comps = [_make_comparable(tx) for tx in txs]

    with patch.object(engine.extractor, "extract_comparables", return_value=comps):
        result = engine.estimate(prop, confidence_level=0.9)

    assert result.confidence_level == 0.9
