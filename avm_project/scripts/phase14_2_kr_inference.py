#!/usr/bin/env python3
"""
Phase 14.2.KR - Shared Inference Contract (Single Source of Truth)

Builds the exact 22-feature vector the KR models were trained on, in the
trained column order, from a minimal property input plus a macro snapshot.

This module is the canonical reference; iOS (Swift) and Android (Kotlin)
feature engineering MUST reproduce build_feature_vector() identically.

Feature order is loaded from config/feature_contract.json (derived from the
training data's numeric columns minus leak patterns).
"""

import json
from pathlib import Path
from typing import Dict, List

import numpy as np

CONFIG_DIR = Path(__file__).resolve().parent.parent / 'config'


def load_contract() -> List[str]:
    data = json.loads((CONFIG_DIR / 'feature_contract.json').read_text())
    return data['feature_order']


def load_macro() -> Dict[str, float]:
    return json.loads((CONFIG_DIR / 'kr_macro_snapshot.json').read_text())


def load_region_meta() -> Dict[str, Dict[str, float]]:
    return json.loads((CONFIG_DIR / 'kr_region_meta.json').read_text())


def age_depreciation(building_age: float) -> float:
    """Training age_factor: piecewise depreciation by building age."""
    if building_age <= 5:
        return 1.0
    if building_age <= 10:
        return 0.95
    if building_age <= 15:
        return 0.88
    if building_age <= 20:
        return 0.78
    return 0.65


def build_features(
    region: str,
    area_m2: float,
    year_built: int,
    current_year: int = 2026,
) -> Dict[str, float]:
    """Compute all 22 named features deterministically."""
    macro = load_macro()
    meta = load_region_meta().get(region, {})

    building_age = float(current_year - year_built)
    feats: Dict[str, float] = {
        'area_m2': float(area_m2),
        'year_built': float(year_built),
        'latitude': float(meta.get('latitude', 37.5)),
        'longitude': float(meta.get('longitude', 127.0)),
        'building_age': building_age,
        'interest_rate': macro['interest_rate'],
        'gdp_growth': macro['gdp_growth'],
        'inflation_rate': macro['inflation_rate'],
        'economic_stress': macro['economic_stress'],
        'avg_ltv': macro['avg_ltv'],
        'avg_interest_rate': macro['avg_interest_rate'],
        'jeonse_ratio': macro['jeonse_ratio'],
        'is_gangnam': float(meta.get('is_gangnam', 0)),
        'gangnam_premium': float(meta.get('gangnam_premium', 0.0)),
        'age_depreciation': age_depreciation(building_age),
        'ltv_impact': macro['ltv_impact'],
        'rate_impact': macro['rate_impact'],
        'jeonse_adjustment': macro['jeonse_adjustment'],
        'economic_stress_factor': macro['economic_stress_factor'],
        'rate_sensitivity': macro['rate_sensitivity'],
        'brand_premium': float(meta.get('brand_premium', 1.0)),
        'price_per_pyeong': float(area_m2) / 3.3,
    }
    return feats


def build_feature_vector(
    region: str,
    area_m2: float,
    year_built: int,
    current_year: int = 2026,
) -> np.ndarray:
    """Ordered [1, 22] float32 vector matching the trained column order."""
    order = load_contract()
    feats = build_features(region, area_m2, year_built, current_year)
    vec = np.array([[feats[name] for name in order]], dtype=np.float32)
    return vec
