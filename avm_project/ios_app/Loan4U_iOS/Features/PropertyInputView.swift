import SwiftUI

struct PropertyInputView: View {
    @ObservedObject var viewModel: PropertyInputViewModel
    @Binding var showResult: Bool
    @EnvironmentObject var modelService: MLModelService

    var body: some View {
        Form {
            Section("Region") {
                Picker("Region", selection: Binding(
                    get: { viewModel.selectedRegion ?? "Nationwide" },
                    set: { viewModel.selectedRegion = ($0 == "Nationwide") ? nil : $0 }
                )) {
                    Text("Nationwide").tag("Nationwide")
                    ForEach(FeatureEngineering.regions, id: \.self) { Text($0).tag($0) }
                }
            }

            Section("Property") {
                Stepper("Area: \(Int(viewModel.property.areaM2)) ㎡",
                        value: $viewModel.property.areaM2, in: 20...500, step: 1)
                Stepper("Year built: \(viewModel.property.yearBuilt)",
                        value: $viewModel.property.yearBuilt, in: 1980...FeatureEngineering.currentYear)
            }

            if let error = modelService.loadingError {
                Section { Text(error).foregroundStyle(.red).font(.footnote) }
            }

            Section {
                Button(action: predict) {
                    HStack {
                        if viewModel.isLoading { ProgressView() }
                        Text(viewModel.isLoading ? "Predicting…" : "Predict Price")
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(!modelService.isLoaded || viewModel.isLoading)
            }
        }
        .navigationTitle("Property Valuation")
        .onChange(of: viewModel.predictionResult) { _, result in
            if result != nil { showResult = true }
        }
    }

    private func predict() { viewModel.predict() }
}
