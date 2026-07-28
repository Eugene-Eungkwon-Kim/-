package com.loan4u.features

/** User-provided property inputs; the rest of the 22-feature contract is derived. */
data class PropertyInput(
    val region: String = "Seoul",
    val areaM2: Double = 84.0,
    val yearBuilt: Int = 2015,
)

/**
 * Builds the model's 22-feature vector in the trained column order.
 * MUST stay identical to scripts/phase14_2_kr_inference.py and the iOS
 * FeatureEngineering.swift.
 */
object FeatureEngineering {
    const val CURRENT_YEAR = 2026

    val featureOrder = listOf(
        "area_m2", "year_built", "latitude", "longitude", "building_age",
        "interest_rate", "gdp_growth", "inflation_rate", "economic_stress",
        "avg_ltv", "avg_interest_rate", "jeonse_ratio", "is_gangnam",
        "gangnam_premium", "age_depreciation", "ltv_impact", "rate_impact",
        "jeonse_adjustment", "economic_stress_factor", "rate_sensitivity",
        "brand_premium", "price_per_pyeong",
    )

    private val macro = mapOf(
        "interest_rate" to 0.035, "gdp_growth" to 0.022, "inflation_rate" to 0.028,
        "economic_stress" to 0.07, "avg_ltv" to 0.737646, "avg_interest_rate" to 0.042403,
        "jeonse_ratio" to 0.363643, "ltv_impact" to 0.368823, "rate_impact" to -0.084806,
        "jeonse_adjustment" to 0.400007, "economic_stress_factor" to -0.105,
        "rate_sensitivity" to -0.0,
    )

    private data class Meta(val lat: Double, val lon: Double, val brand: Double)

    private val regionMeta = mapOf(
        "Seoul" to Meta(37.22849, 127.534287, 1.0),
        "Busan" to Meta(37.301888, 127.646675, 1.04),
        "Gyeonggi" to Meta(37.260923, 127.602947, 1.04),
        "Daegu" to Meta(37.231418, 127.409407, 1.04),
        "Incheon" to Meta(37.280423, 127.209532, 1.04),
    )

    val regions = listOf("Seoul", "Busan", "Gyeonggi", "Daegu", "Incheon")

    fun ageDepreciation(age: Double): Double = when {
        age <= 5 -> 1.0
        age <= 10 -> 0.95
        age <= 15 -> 0.88
        age <= 20 -> 0.78
        else -> 0.65
    }

    fun buildFeatures(input: PropertyInput): Map<String, Double> {
        val meta = regionMeta[input.region] ?: Meta(37.5, 127.0, 1.0)
        val buildingAge = (CURRENT_YEAR - input.yearBuilt).toDouble()
        return mapOf(
            "area_m2" to input.areaM2,
            "year_built" to input.yearBuilt.toDouble(),
            "latitude" to meta.lat,
            "longitude" to meta.lon,
            "building_age" to buildingAge,
            "interest_rate" to macro.getValue("interest_rate"),
            "gdp_growth" to macro.getValue("gdp_growth"),
            "inflation_rate" to macro.getValue("inflation_rate"),
            "economic_stress" to macro.getValue("economic_stress"),
            "avg_ltv" to macro.getValue("avg_ltv"),
            "avg_interest_rate" to macro.getValue("avg_interest_rate"),
            "jeonse_ratio" to macro.getValue("jeonse_ratio"),
            "is_gangnam" to 0.0,
            "gangnam_premium" to 0.0,
            "age_depreciation" to ageDepreciation(buildingAge),
            "ltv_impact" to macro.getValue("ltv_impact"),
            "rate_impact" to macro.getValue("rate_impact"),
            "jeonse_adjustment" to macro.getValue("jeonse_adjustment"),
            "economic_stress_factor" to macro.getValue("economic_stress_factor"),
            "rate_sensitivity" to macro.getValue("rate_sensitivity"),
            "brand_premium" to meta.brand,
            "price_per_pyeong" to input.areaM2 / 3.3,
        )
    }

    /** Ordered FloatArray[22] matching the trained column order. */
    fun buildVector(input: PropertyInput): FloatArray {
        val feats = buildFeatures(input)
        return FloatArray(featureOrder.size) { i -> (feats[featureOrder[i]] ?: 0.0).toFloat() }
    }
}
