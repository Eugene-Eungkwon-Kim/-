import Foundation

@MainActor
final class PropertyInputViewModel: ObservableObject {
    @Published var property = PropertyInput()
    @Published var selectedRegion: String? = "Seoul"
    @Published var isLoading = false
    @Published var predictionResult: PredictionResult?

    private let modelService: MLModelService
    private let cacheService: CacheService

    init(modelService: MLModelService, cacheService: CacheService) {
        self.modelService = modelService
        self.cacheService = cacheService
    }

    func predict() {
        guard modelService.isLoaded, !isLoading else { return }
        isLoading = true

        let input = property
        let region = selectedRegion

        if let hit = cacheService.cached(input, region: region) {
            predictionResult = hit
            isLoading = false
            return
        }

        Task { [weak self] in
            guard let self else { return }
            let result = self.modelService.predict(input, region: region)
            if let result { self.cacheService.store(result, for: input, region: region) }
            self.predictionResult = result
            self.isLoading = false
        }
    }

    func reset() {
        property = PropertyInput()
        selectedRegion = "Seoul"
        predictionResult = nil
    }
}
