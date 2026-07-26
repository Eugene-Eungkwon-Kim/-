import SwiftUI

struct PropertyInputView: View {
    @Binding var showInput: Bool
    @StateObject var viewModel: PropertyInputViewModel
    @EnvironmentObject var modelService: MLModelService
    @EnvironmentObject var cacheService: CacheService

    var body: some View {
        NavigationStack {
            Form {
                Section("Property Details") {
                    Stepper("Area (㎡): \(viewModel.property.areaSqm)", value: $viewModel.property.areaSqm, in: 20...500)
                    Stepper("Year Built: \(viewModel.property.yearBuilt)", value: $viewModel.property.yearBuilt, in: 1980...2024)
                    Stepper("Floor Level: \(viewModel.property.floorLevel)", value: $viewModel.property.floorLevel, in: 1...30)
                    Stepper("Total Floors: \(viewModel.property.floorsTotal)", value: $viewModel.property.floorsTotal, in: 1...50)
                }

                Section("Rooms") {
                    Stepper("Bedrooms: \(viewModel.property.bedrooms)", value: $viewModel.property.bedrooms, in: 1...8)
                    Stepper("Bathrooms: \(viewModel.property.bathrooms)", value: $viewModel.property.bathrooms, in: 1...5)
                }

                Section("Location Features") {
                    Stepper("Distance to Subway (m): \(viewModel.property.distanceSubwayM)", value: $viewModel.property.distanceSubwayM, in: 0...5000, step: 100)
                    Stepper("Distance to School (m): \(viewModel.property.distanceSchoolM)", value: $viewModel.property.distanceSchoolM, in: 0...5000, step: 100)
                    Stepper("Distance to Hospital (m): \(viewModel.property.distanceHospitalM)", value: $viewModel.property.distanceHospitalM, in: 0...5000, step: 100)
                    Stepper("Distance to Park (m): \(viewModel.property.distanceParkM)", value: $viewModel.property.distanceParkM, in: 0...5000, step: 100)
                }

                Section("Neighborhood") {
                    Slider(value: $viewModel.property.crimeRate, in: 0...1, step: 0.05)
                    Text("Crime Rate: \(String(format: "%.2f", viewModel.property.crimeRate))")

                    Slider(value: $viewModel.property.nightlightIntensity, in: 0...1, step: 0.05)
                    Text("Nightlight: \(String(format: "%.2f", viewModel.property.nightlightIntensity))")

                    Slider(value: $viewModel.property.populationDensity, in: 5000...30000, step: 500)
                    Text("Population Density: \(Int(viewModel.property.populationDensity))")
                }

                Section("Amenities") {
                    Toggle("Elevator", isOn: $viewModel.property.hasElevator)
                    Toggle("Parking", isOn: $viewModel.property.hasParking)
                    Toggle("Garden", isOn: $viewModel.property.hasGarden)
                }

                Section("Property Type") {
                    Picker("House Type", selection: $viewModel.property.houseType) {
                        ForEach(PropertyInput.HouseType.allCases, id: \.self) { type in
                            Text(type.rawValue).tag(type)
                        }
                    }
                }

                Section("Region (Optional)") {
                    Picker("Select Region", selection: $viewModel.selectedRegion) {
                        Text("Nationwide").tag(Optional<String>(nil))
                        ForEach(["Seoul", "Busan", "Gyeonggi", "Daegu", "Incheon"], id: \.self) { region in
                            Text(region).tag(Optional<String>(region))
                        }
                    }
                }

                Section {
                    Button(action: {
                        viewModel.predict()
                        if viewModel.predictionResult != nil {
                            showInput = false
                        }
                    }) {
                        HStack {
                            if viewModel.isLoading {
                                ProgressView()
                            }
                            Text("Predict Price")
                        }
                        .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(!modelService.isLoaded || viewModel.isLoading)
                }
            }
            .navigationTitle("Property Valuation")
            .onAppear {
                viewModel.modelService = modelService
                viewModel.cacheService = cacheService
            }
        }
    }
}
