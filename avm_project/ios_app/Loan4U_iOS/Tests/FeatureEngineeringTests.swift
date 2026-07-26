import XCTest

final class FeatureEngineeringTests: XCTestCase {
    func testBuildFeaturesReturnsCorrectCount() {
        let property = PropertyInput()
        let features = FeatureEngineering.buildFeatures(property: property)
        XCTAssertEqual(features.count, 22, "Should have exactly 22 features")
    }

    func testBuildFeaturesContainsExpectedKeys() {
        let property = PropertyInput()
        let features = FeatureEngineering.buildFeatures(property: property)

        let expectedKeys = [
            "area_sqm", "year_built", "floor_level", "floors_total",
            "bedrooms", "bathrooms", "distance_subway_m", "distance_school_m",
            "distance_hospital_m", "distance_park_m", "crime_rate",
            "nightlight_intensity", "population_density", "has_elevator",
            "has_parking", "has_garden", "house_type_apt",
            "house_type_townhouse", "house_type_villa",
            "transaction_month_log", "transaction_year",
        ]

        for key in expectedKeys {
            XCTAssertNotNil(features[key], "Missing key: \(key)")
        }
    }

    func testBuildFeaturesWithCustomProperty() {
        var property = PropertyInput()
        property.areaSqm = 150
        property.yearBuilt = 2020
        property.bedrooms = 4

        let features = FeatureEngineering.buildFeatures(property: property)

        XCTAssertEqual(features["area_sqm"], 150.0)
        XCTAssertEqual(features["year_built"], 2020.0)
        XCTAssertEqual(features["bedrooms"], 4.0)
    }

    func testAmenityFeaturesCorrectlyEncoded() {
        var property = PropertyInput()
        property.hasElevator = true
        property.hasParking = false
        property.hasGarden = true

        let features = FeatureEngineering.buildFeatures(property: property)

        XCTAssertEqual(features["has_elevator"], 1.0)
        XCTAssertEqual(features["has_parking"], 0.0)
        XCTAssertEqual(features["has_garden"], 1.0)
    }

    func testHouseTypeEncodingApartment() {
        var property = PropertyInput()
        property.houseType = .apartment

        let features = FeatureEngineering.buildFeatures(property: property)

        XCTAssertEqual(features["house_type_apt"], 1.0)
        XCTAssertEqual(features["house_type_townhouse"], 0.0)
        XCTAssertEqual(features["house_type_villa"], 0.0)
    }
}
