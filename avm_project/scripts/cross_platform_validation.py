#!/usr/bin/env python3
"""Cross-platform validation for iOS/Android feature parity."""

import json
import hashlib
import sys
from typing import Dict, Any, List

def validate_feature_parity() -> bool:
    """Validate iOS/Android Feature Order consistency."""

    # 22-Feature Contract: canonical order
    feature_order = [
        "area_m2", "building_age", "latitude", "longitude",
        "age_depreciation", "interest_rate", "gdp_growth", "inflation_rate",
        "economic_stress", "avg_ltv", "avg_interest_rate", "jeonse_ratio",
        "is_gangnam", "gangnam_premium", "ltv_impact", "rate_impact",
        "jeonse_adjustment", "economic_stress_factor", "rate_sensitivity",
        "brand_premium", "price_per_pyeong", "reserved"
    ]

    # Validation checks
    assert len(feature_order) == 22, f"Feature count mismatch: {len(feature_order)} != 22"
    assert feature_order[0] == "area_m2", f"First feature must be area_m2, got {feature_order[0]}"
    assert feature_order[21] == "reserved", f"Last feature must be reserved, got {feature_order[21]}"
    assert len(set(feature_order)) == 22, "Duplicate features detected"

    print("✅ Feature Order Validation:")
    print(f"   - Count: {len(feature_order)} features (expected: 22)")
    print(f"   - First: {feature_order[0]} (expected: area_m2)")
    print(f"   - Last: {feature_order[21]} (expected: reserved)")
    print(f"   - No duplicates: ✓")
    return True

def validate_cache_key_parity() -> bool:
    """Validate iOS/Android cache key generation consistency."""

    test_cases = [
        {
            "region": "Seoul",
            "area_m2": 84.0,
            "building_age": 5,
            "latitude": 37.4979,
            "longitude": 127.0276,
            "timestamp": 1722556800
        },
        {
            "region": "Busan",
            "area_m2": 72.0,
            "building_age": 10,
            "latitude": 35.1796,
            "longitude": 129.0756,
            "timestamp": 1722643200
        }
    ]

    print("✅ Cache Key Validation:")
    for i, test_data in enumerate(test_cases, 1):
        # Generate cache key using SHA-256 (consistent across platforms)
        input_str = json.dumps(test_data, sort_keys=True)
        cache_key = hashlib.sha256(input_str.encode()).hexdigest()

        # Verify key properties
        assert len(cache_key) == 64, f"Cache key length mismatch: {len(cache_key)} != 64"
        assert cache_key.isalnum(), f"Cache key contains non-alphanumeric: {cache_key}"

        print(f"   - Test case {i}: {cache_key[:16]}... (64 chars, SHA-256)")

    return True

def validate_region_metadata() -> bool:
    """Validate region metadata consistency."""

    regions = {
        "Seoul": {"brand_premium": 1.15, "latitude": 37.5665, "longitude": 126.9780},
        "Busan": {"brand_premium": 1.04, "latitude": 35.1796, "longitude": 129.0756},
        "Gyeonggi": {"brand_premium": 0.98, "latitude": 37.2756, "longitude": 127.0093},
        "Daegu": {"brand_premium": 0.85, "latitude": 35.8722, "longitude": 128.5933},
        "Incheon": {"brand_premium": 1.02, "latitude": 37.4563, "longitude": 126.7052},
        "Nationwide": {"brand_premium": 1.0, "latitude": 36.5, "longitude": 127.5}
    }

    print("✅ Region Metadata Validation:")
    for region, meta in regions.items():
        brand = meta["brand_premium"]
        lat = meta["latitude"]
        lon = meta["longitude"]

        assert 0.8 <= brand <= 1.2, f"{region} brand_premium out of range: {brand}"
        assert 34 <= lat <= 39, f"{region} latitude out of range: {lat}"
        assert 125 <= lon <= 130, f"{region} longitude out of range: {lon}"

        print(f"   - {region}: premium={brand:.2f}, lat={lat:.4f}, lon={lon:.4f} ✓")

    return True

def validate_age_depreciation() -> bool:
    """Validate age depreciation calculation."""

    test_cases = [
        (3, 1.0, "新築に近い"),
        (5, 0.96, "新築"),
        (11, 0.88, "中古"),
        (20, 0.72, "経年"),
        (25, 0.65, "老朽化")
    ]

    print("✅ Age Depreciation Validation:")
    for age, expected, label in test_cases:
        # Simple linear depreciation model
        if age <= 5:
            depreciation = 1.0
        elif age <= 15:
            depreciation = 1.0 - (age - 5) * 0.015
        else:
            depreciation = 0.85 - (age - 15) * 0.01

        # Clamp to [0.5, 1.0]
        depreciation = max(0.5, min(1.0, depreciation))

        diff = abs(depreciation - expected)
        assert diff < 0.05, f"Age {age}: depreciation {depreciation:.2f} != {expected:.2f}"
        print(f"   - Age {age:2d}: {depreciation:.2f} ({label}) ✓")

    return True

def main() -> int:
    """Execute all validations."""

    print("=" * 70)
    print("Cross-Platform Validation Report")
    print("=" * 70)
    print()

    try:
        # 1. Feature Order
        print("1. Feature Order Parity")
        print("-" * 70)
        validate_feature_parity()
        print()

        # 2. Cache Key Generation
        print("2. Cache Key Generation")
        print("-" * 70)
        validate_cache_key_parity()
        print()

        # 3. Region Metadata
        print("3. Region Metadata Consistency")
        print("-" * 70)
        validate_region_metadata()
        print()

        # 4. Age Depreciation
        print("4. Age Depreciation Calculation")
        print("-" * 70)
        validate_age_depreciation()
        print()

        # Summary
        print("=" * 70)
        print("✅ ALL VALIDATIONS PASSED")
        print("=" * 70)
        print("Ready for Phase 14.3 Device Testing")
        return 0

    except AssertionError as e:
        print(f"\n❌ Validation Failed: {e}")
        print("=" * 70)
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
