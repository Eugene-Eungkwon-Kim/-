package com.loan4u.features

import org.junit.Assert.assertEquals
import org.junit.Test

class FeatureEngineeringTest {
    @Test fun contractHas22Features() {
        assertEquals(22, FeatureEngineering.featureOrder.size)
    }

    @Test fun vectorMatchesContractLength() {
        assertEquals(22, FeatureEngineering.buildVector(PropertyInput()).size)
    }

    @Test fun featureOrderMatchesTrainedColumns() {
        assertEquals("area_m2", FeatureEngineering.featureOrder.first())
        assertEquals("price_per_pyeong", FeatureEngineering.featureOrder.last())
        assertEquals("building_age", FeatureEngineering.featureOrder[4])
    }

    @Test fun pricePerPyeongDerivation() {
        val feats = FeatureEngineering.buildFeatures(PropertyInput("Seoul", 84.0, 2015))
        assertEquals(84.0 / 3.3, feats["price_per_pyeong"]!!, 1e-6)
    }

    @Test fun ageDepreciationBuckets() {
        assertEquals(1.0, FeatureEngineering.ageDepreciation(3.0), 1e-9)
        assertEquals(0.88, FeatureEngineering.ageDepreciation(11.0), 1e-9) // 2026-2015
        assertEquals(0.65, FeatureEngineering.ageDepreciation(25.0), 1e-9)
    }

    @Test fun regionMetaApplied() {
        val feats = FeatureEngineering.buildFeatures(PropertyInput("Busan", 84.0, 2015))
        assertEquals(1.04, feats["brand_premium"]!!, 1e-6)
        assertEquals(37.301888, feats["latitude"]!!, 1e-6)
    }

    @Test fun vectorOrderPlacesAreaFirst() {
        val v = FeatureEngineering.buildVector(PropertyInput("Seoul", 84.0, 2015))
        assertEquals(84.0f, v[0], 1e-4f)          // area_m2
        assertEquals((84.0 / 3.3).toFloat(), v[21], 1e-4f) // price_per_pyeong
    }
}
