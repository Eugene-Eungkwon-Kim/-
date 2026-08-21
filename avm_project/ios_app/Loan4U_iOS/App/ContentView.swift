import SwiftUI

struct ContentView: View {
    @EnvironmentObject var modelService: MLModelService
    @EnvironmentObject var cacheService: CacheService
    @StateObject private var viewModel: PropertyInputViewModel
    @State private var showResult = false

    init() {
        _viewModel = StateObject(wrappedValue: PropertyInputViewModel(
            modelService: MLModelService.shared,
            cacheService: CacheService.shared
        ))
    }

    var body: some View {
        NavigationStack {
            PropertyInputView(viewModel: viewModel, showResult: $showResult)
                .navigationDestination(isPresented: $showResult) {
                    PredictionResultView(result: viewModel.predictionResult) {
                        viewModel.reset()
                        showResult = false
                    }
                }
        }
    }
}
