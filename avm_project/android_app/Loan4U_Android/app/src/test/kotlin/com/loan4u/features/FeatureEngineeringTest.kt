package com.loan4u.features

import org.junit.Assert.*
import org.junit.Test

class FeatureEngineeringTest {
    @Test
    fun buildFeaturesReturnsCorrectCount() {
        val property = PropertyInput()
        val features = FeatureEngineering.buildFeatures(property)
        assertEquals("Should have exactly 22 features", 22, features.size)
    }

    @Test
    fun buildFeaturesContainsExpectedKeys() {
        val property = PropertyInput()
        val features = FeatureEngineering.buildFeatures(property)

        val expectedKeys = setOf(
            "area_sqm", "year_built", "floor_level", "floors_total",
            "bedrooms", "bathrooms", "distance_subway_m", "distance_school_m",
            "distance_hospital_m", "distance_park_m", "crime_rate",
            "nightlight_intensity", "population_density", "has_elevator",
            "has_parking", "has_garden", "house_type_apt",
            "house_type_townhouse", "house_type_villa",
            "transaction_month_log", "transaction_year",
        )

        expectedKeys.forEach { key ->
            assertTrue("Missing key: $key", features.containsKey(key))
        }
    }

    @Test
    fun buildFeaturesWithCustomProperty() {
        val property = PropertyInput(
            areaSqm = 150,
            yearBuilt = 2020,
            bedrooms = 4,
        )

        val features = FeatureEngineering.buildFeatures(property)

        assertEquals(150f, features["area_sqm"])
        assertEquals(2020f, features["year_built"])
        assertEquals(4f, features["bedrooms"])
    }

    @Test
    fun amenityFeaturesCorrectlyEncoded() {
        val property = PropertyInput(
            hasElevator = true,
            hasParking = false,
            hasGarden = true,
        )

        val features = FeatureEngineering.buildFeatures(property)

        assertEquals(1f, features["has_elevator"])
        assertEquals(0f, features["has_parking"])
        assertEquals(1f, features["has_garden"])
    }

    @Test
    fun houseTypeEncodingApartment() {
        val property = PropertyInput(houseType = HouseType.APARTMENT)

        val features = FeatureEngineering.buildFeatures(property)

        assertEquals(1f, features["house_type_apt"])
        assertEquals(0f, features["house_type_townhouse"])
        assertEquals(0f, features["house_type_villa"])
    }

    @Test
    fun houseTypeEncodingTownhouse() {
        val property = PropertyInput(houseType = HouseType.TOWNHOUSE)

        val features = FeatureEngineering.buildFeatures(property)

        assertEquals(0f, features["house_type_apt"])
        assertEquals(1f, features["house_type_townhouse"])
        assertEquals(0f, features["house_type_villa"])
    }

    @Test
    fun distanceValuesEncoded() {
        val property = PropertyInput(
            distanceSubwayM = 500,
            distanceSchoolM = 800,
            distanceHospitalM = 1200,
            distanceParkM = 300,
        )

        val features = FeatureEngineering.buildFeatures(property)

        assertEquals(500f, features["distance_subway_m"])
        assertEquals(800f, features["distance_school_m"])
        assertEquals(1200f, features["distance_hospital_m"])
        assertEquals(300f, features["distance_park_m"])
    }
}
