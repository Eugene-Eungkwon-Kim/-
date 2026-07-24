package com.loan4u.features

import kotlin.math.log

object FeatureEngineering {
    fun buildFeatures(property: PropertyInput): Map<String, Float> {
        val calendar = java.util.Calendar.getInstance()
        val currentMonth = calendar.get(java.util.Calendar.MONTH) + 1
        val currentYear = calendar.get(java.util.Calendar.YEAR)

        return mapOf(
            "area_sqm" to property.areaSqm.toFloat(),
            "year_built" to property.yearBuilt.toFloat(),
            "floor_level" to property.floorLevel.toFloat(),
            "floors_total" to property.floorsTotal.toFloat(),
            "bedrooms" to property.bedrooms.toFloat(),
            "bathrooms" to property.bathrooms.toFloat(),
            "distance_subway_m" to property.distanceSubwayM.toFloat(),
            "distance_school_m" to property.distanceSchoolM.toFloat(),
            "distance_hospital_m" to property.distanceHospitalM.toFloat(),
            "distance_park_m" to property.distanceParkM.toFloat(),
            "crime_rate" to property.crimeRate.toFloat(),
            "nightlight_intensity" to property.nightlightIntensity.toFloat(),
            "population_density" to property.populationDensity.toFloat(),
            "has_elevator" to (if (property.hasElevator) 1f else 0f),
            "has_parking" to (if (property.hasParking) 1f else 0f),
            "has_garden" to (if (property.hasGarden) 1f else 0f),
            "house_type_apt" to (if (property.houseType == HouseType.APARTMENT) 1f else 0f),
            "house_type_townhouse" to (if (property.houseType == HouseType.TOWNHOUSE) 1f else 0f),
            "house_type_villa" to (if (property.houseType == HouseType.VILLA) 1f else 0f),
            "transaction_month_log" to log(currentMonth.toDouble()).toFloat(),
            "transaction_year" to currentYear.toFloat(),
        )
    }
}

data class PropertyInput(
    val areaSqm: Int = 85,
    val yearBuilt: Int = 2010,
    val floorLevel: Int = 5,
    val floorsTotal: Int = 15,
    val bedrooms: Int = 3,
    val bathrooms: Int = 2,
    val distanceSubwayM: Int = 500,
    val distanceSchoolM: Int = 800,
    val distanceHospitalM: Int = 1200,
    val distanceParkM: Int = 300,
    val crimeRate: Double = 0.5,
    val nightlightIntensity: Double = 0.65,
    val populationDensity: Double = 18500.0,
    val hasElevator: Boolean = true,
    val hasParking: Boolean = true,
    val hasGarden: Boolean = false,
    val houseType: HouseType = HouseType.APARTMENT,
)

enum class HouseType {
    APARTMENT,
    TOWNHOUSE,
    VILLA,
}
