import Combine
import Foundation

@MainActor
final class PropertyInputViewModel: ObservableObject {
    @Published var property = PropertyInput()
    @Published var selectedRegion: String?
    @Published var isLoading = false
    @Published var predictionResult: PredictionResult?

    @ObservedObject var modelService: MLModelService
    @ObservedObject var cacheService: CacheService

    init(modelService: MLModelService, cacheService: CacheService) {
        self.modelService = modelService
        self.cacheService = cacheService
    }

    func predict() {
        guard modelService.isLoaded else { return }
        isLoading = true

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }

            let features = FeatureEngineering.buildFeatures(property: self.property)

            if let cached = self.cacheService.getCachedPrediction(for: features) {
                await MainActor.run {
                    self.predictionResult = cached.result
                    self.isLoading = false
                }
                return
            }

            let result = self.modelService.predict(
                features: features,
                region: self.selectedRegion
            )

            await MainActor.run {
                if let result = result {
                    self.cacheService.cachePrediction(result, for: features)
                    self.predictionResult = result
                }
                self.isLoading = false
            }
        }
    }

    func resetForm() {
        property = PropertyInput()
        selectedRegion = nil
        predictionResult = nil
    }
}
