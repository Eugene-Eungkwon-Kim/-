import Foundation

/// Property inputs the user actually provides. Everything else in the model's
/// 22-feature contract is derived deterministically (see FeatureEngineering).
struct PropertyInput {
    var region: String = "Seoul"
    var areaM2: Double = 84.0
    var yearBuilt: Int = 2015
}

/// Builds the model's 22-feature vector in the trained column order.
/// This MUST stay identical to scripts/phase14_2_kr_inference.py.
enum FeatureEngineering {
    static let currentYear = 2026

    /// Canonical trained column order (config/feature_contract.json).
    static let featureOrder: [String] = [
        "area_m2", "year_built", "latitude", "longitude", "building_age",
        "interest_rate", "gdp_growth", "inflation_rate", "economic_stress",
        "avg_ltv", "avg_interest_rate", "jeonse_ratio", "is_gangnam",
        "gangnam_premium", "age_depreciation", "ltv_impact", "rate_impact",
        "jeonse_adjustment", "economic_stress_factor", "rate_sensitivity",
        "brand_premium", "price_per_pyeong",
    ]

    /// National macro snapshot (config/kr_macro_snapshot.json).
    static let macro: [String: Double] = [
        "interest_rate": 0.035, "gdp_growth": 0.022, "inflation_rate": 0.028,
        "economic_stress": 0.07, "avg_ltv": 0.737646, "avg_interest_rate": 0.042403,
        "jeonse_ratio": 0.363643, "ltv_impact": 0.368823, "rate_impact": -0.084806,
        "jeonse_adjustment": 0.400007, "economic_stress_factor": -0.105,
        "rate_sensitivity": -0.0,
    ]

    /// Per-region metadata (config/kr_region_meta.json).
    static let regionMeta: [String: (lat: Double, lon: Double, brand: Double)] = [
        "Seoul": (37.22849, 127.534287, 1.0),
        "Busan": (37.301888, 127.646675, 1.04),
        "Gyeonggi": (37.260923, 127.602947, 1.04),
        "Daegu": (37.231418, 127.409407, 1.04),
        "Incheon": (37.280423, 127.209532, 1.04),
    ]

    static let regions = ["Seoul", "Busan", "Gyeonggi", "Daegu", "Incheon"]

    static func ageDepreciation(_ age: Double) -> Double {
        switch age {
        case ..<5.0001: return 1.0
        case ..<10.0001: return 0.95
        case ..<15.0001: return 0.88
        case ..<20.0001: return 0.78
        default: return 0.65
        }
    }

    static func buildFeatures(_ input: PropertyInput) -> [String: Double] {
        let meta = regionMeta[input.region] ?? (37.5, 127.0, 1.0)
        let buildingAge = Double(currentYear - input.yearBuilt)
        return [
            "area_m2": input.areaM2,
            "year_built": Double(input.yearBuilt),
            "latitude": meta.lat,
            "longitude": meta.lon,
            "building_age": buildingAge,
            "interest_rate": macro["interest_rate"]!,
            "gdp_growth": macro["gdp_growth"]!,
            "inflation_rate": macro["inflation_rate"]!,
            "economic_stress": macro["economic_stress"]!,
            "avg_ltv": macro["avg_ltv"]!,
            "avg_interest_rate": macro["avg_interest_rate"]!,
            "jeonse_ratio": macro["jeonse_ratio"]!,
            "is_gangnam": 0.0,
            "gangnam_premium": 0.0,
            "age_depreciation": ageDepreciation(buildingAge),
            "ltv_impact": macro["ltv_impact"]!,
            "rate_impact": macro["rate_impact"]!,
            "jeonse_adjustment": macro["jeonse_adjustment"]!,
            "economic_stress_factor": macro["economic_stress_factor"]!,
            "rate_sensitivity": macro["rate_sensitivity"]!,
            "brand_premium": meta.brand,
            "price_per_pyeong": input.areaM2 / 3.3,
        ]
    }

    /// Ordered [22] Float vector matching the trained column order.
    static func buildVector(_ input: PropertyInput) -> [Float] {
        let feats = buildFeatures(input)
        return featureOrder.map { Float(feats[$0] ?? 0.0) }
    }
}
