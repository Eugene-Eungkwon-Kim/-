import CoreML
import Foundation

@MainActor
final class MLModelService: ObservableObject {
    static let shared = MLModelService()

    @Published var isLoaded = false
    @Published var loadingError: String?

    private var nationalwideModel: MLModel?
    private var regionalModels: [String: MLModel] = [:]
    private let regionNames = ["Seoul", "Busan", "Gyeonggi", "Daegu", "Incheon"]

    init() {
        loadModels()
    }

    func loadModels() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            do {
                try self?.loadNationwideModel()
                try self?.loadRegionalModels()
                await MainActor.run {
                    self?.isLoaded = true
                }
            } catch {
                await MainActor.run {
                    self?.loadingError = "Failed to load models: \(error.localizedDescription)"
                }
            }
        }
    }

    private func loadNationwideModel() throws {
        let modelURL = Bundle.main.url(forResource: "KR_nationwide_lite_int8", withExtension: "mlmodel")
            ?? Bundle.main.url(forResource: "KR_nationwide_lite_int8", withExtension: "mlmodelc")!
        nationalwideModel = try MLModel(contentsOf: modelURL)
    }

    private func loadRegionalModels() throws {
        for region in regionNames {
            let modelName = "KR_\(region.lowercased())_lite_int8"
            if let modelURL = Bundle.main.url(forResource: modelName, withExtension: "mlmodel")
                ?? Bundle.main.url(forResource: modelName, withExtension: "mlmodelc") {
                regionalModels[region] = try MLModel(contentsOf: modelURL)
            }
        }
    }

    func predict(features: [String: Double], region: String?) -> PredictionResult? {
        guard isLoaded, let features = prepareFeatures(features) else { return nil }

        let model = region.flatMap { regionalModels[$0] } ?? nationalwideModel
        guard let model = model else { return nil }

        do {
            let input = try MLDictionaryFeatureProvider(dictionary: features)
            let output = try model.prediction(from: input)

            if let priceValue = output.featureValue(for: "price")?.doubleValue {
                let confidenceScore = min(1.0, max(0.0, 1.0 - abs(priceValue - 500_000_000) / 1_000_000_000))
                return PredictionResult(
                    predictedPrice: Int(priceValue),
                    confidenceScore: confidenceScore,
                    region: region ?? "Nationwide",
                    timestamp: Date()
                )
            }
        } catch {
            loadingError = "Prediction failed: \(error.localizedDescription)"
        }

        return nil
    }

    private func prepareFeatures(_ input: [String: Double]) -> [String: MLFeatureValue]? {
        var features: [String: MLFeatureValue] = [:]
        for (key, value) in input {
            features[key] = MLFeatureValue(double: value)
        }
        return features
    }
}

struct PredictionResult {
    let predictedPrice: Int
    let confidenceScore: Double
    let region: String
    let timestamp: Date
}
