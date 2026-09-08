import XCTest
@testable import Loan4U_iOS

final class FeatureEngineeringTests: XCTestCase {
    func testContractHas22Features() {
        XCTAssertEqual(FeatureEngineering.featureOrder.count, 22)
    }

    func testVectorMatchesContractLength() {
        let vector = FeatureEngineering.buildVector(PropertyInput())
        XCTAssertEqual(vector.count, 22)
    }

    func testFeatureOrderMatchesTrainedColumns() {
        // Must match config/feature_contract.json exactly.
        XCTAssertEqual(FeatureEngineering.featureOrder.first, "area_m2")
        XCTAssertEqual(FeatureEngineering.featureOrder.last, "price_per_pyeong")
        XCTAssertEqual(FeatureEngineering.featureOrder[4], "building_age")
    }

    func testPricePerPyeongDerivation() {
        let feats = FeatureEngineering.buildFeatures(PropertyInput(region: "Seoul", areaM2: 84, yearBuilt: 2015))
        XCTAssertEqual(feats["price_per_pyeong"]!, 84.0 / 3.3, accuracy: 1e-6)
    }

    func testAgeDepreciationBuckets() {
        XCTAssertEqual(FeatureEngineering.ageDepreciation(3), 1.0)
        XCTAssertEqual(FeatureEngineering.ageDepreciation(11), 0.88)   // 2026-2015
        XCTAssertEqual(FeatureEngineering.ageDepreciation(25), 0.65)
    }

    func testRegionMetaApplied() {
        let feats = FeatureEngineering.buildFeatures(PropertyInput(region: "Busan", areaM2: 84, yearBuilt: 2015))
        XCTAssertEqual(feats["brand_premium"]!, 1.04, accuracy: 1e-6)
        XCTAssertEqual(feats["latitude"]!, 37.301888, accuracy: 1e-6)
    }
}
