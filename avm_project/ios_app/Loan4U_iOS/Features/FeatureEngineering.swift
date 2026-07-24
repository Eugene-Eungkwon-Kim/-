import Foundation

struct FeatureEngineering {
    static func buildFeatures(property: PropertyInput) -> [String: Double] {
        var features: [String: Double] = [:]

        features["area_sqm"] = Double(property.areaSqm)
        features["year_built"] = Double(property.yearBuilt)
        features["floor_level"] = Double(property.floorLevel)
        features["floors_total"] = Double(property.floorsTotal)
        features["bedrooms"] = Double(property.bedrooms)
        features["bathrooms"] = Double(property.bathrooms)

        features["distance_subway_m"] = Double(property.distanceSubwayM)
        features["distance_school_m"] = Double(property.distanceSchoolM)
        features["distance_hospital_m"] = Double(property.distanceHospitalM)
        features["distance_park_m"] = Double(property.distanceParkM)

        features["crime_rate"] = property.crimeRate
        features["nightlight_intensity"] = property.nightlightIntensity
        features["population_density"] = property.populationDensity

        features["has_elevator"] = property.hasElevator ? 1.0 : 0.0
        features["has_parking"] = property.hasParking ? 1.0 : 0.0
        features["has_garden"] = property.hasGarden ? 1.0 : 0.0

        features["house_type_apt"] = property.houseType == .apartment ? 1.0 : 0.0
        features["house_type_townhouse"] = property.houseType == .townhouse ? 1.0 : 0.0
        features["house_type_villa"] = property.houseType == .villa ? 1.0 : 0.0

        features["transaction_month_log"] = log(Double(Date().month))
        features["transaction_year"] = Double(Date().year)

        return features
    }
}

struct PropertyInput {
    var areaSqm: Int = 85
    var yearBuilt: Int = 2010
    var floorLevel: Int = 5
    var floorsTotal: Int = 15
    var bedrooms: Int = 3
    var bathrooms: Int = 2

    var distanceSubwayM: Int = 500
    var distanceSchoolM: Int = 800
    var distanceHospitalM: Int = 1200
    var distanceParkM: Int = 300

    var crimeRate: Double = 0.5
    var nightlightIntensity: Double = 0.65
    var populationDensity: Double = 18500.0

    var hasElevator: Bool = true
    var hasParking: Bool = true
    var hasGarden: Bool = false

    var houseType: HouseType = .apartment

    enum HouseType: String, CaseIterable {
        case apartment = "Apartment"
        case townhouse = "Townhouse"
        case villa = "Villa"
    }
}

extension Date {
    var month: Int {
        Calendar.current.component(.month, from: self)
    }

    var year: Int {
        Calendar.current.component(.year, from: self)
    }
}
