import SwiftUI

struct PredictionResultView: View {
    @Binding var showInput: Bool
    @State var result: PredictionResult?
    @EnvironmentObject var cacheService: CacheService

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                if let result = result {
                    VStack(spacing: 16) {
                        Text("Estimated Price")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Text("₩\(result.predictedPrice.formatted())")
                            .font(.system(size: 48, weight: .bold, design: .rounded))
                            .foregroundStyle(.primary)

                        VStack(spacing: 8) {
                            HStack {
                                Text("Confidence")
                                    .font(.subheading)
                                Spacer()
                                Text(String(format: "%.1f%%", result.confidenceScore * 100))
                                    .font(.subheading)
                                    .fontWeight(.semibold)
                            }

                            ProgressView(value: result.confidenceScore)
                                .tint(confidenceColor(result.confidenceScore))
                        }

                        Divider()

                        HStack(spacing: 12) {
                            Label("Region", systemImage: "map.fill")
                            Spacer()
                            Text(result.region)
                                .fontWeight(.semibold)
                        }
                        .font(.callout)

                        HStack(spacing: 12) {
                            Label("Predicted", systemImage: "clock.fill")
                            Spacer()
                            Text(result.timestamp.formatted(date: .abbreviated, time: .shortened))
                                .font(.callout)
                        }
                    }
                    .padding(20)
                    .background(Color(.systemGray6))
                    .cornerRadius(12)

                    Spacer()

                    Button(action: { showInput = true }) {
                        Text("New Valuation")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                } else {
                    Text("No prediction available")
                        .foregroundStyle(.secondary)
                    Spacer()
                    Button(action: { showInput = true }) {
                        Text("Go Back")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                }
            }
            .padding()
            .navigationTitle("Valuation Result")
        }
    }

    private func confidenceColor(_ score: Double) -> Color {
        if score >= 0.8 {
            return .green
        } else if score >= 0.6 {
            return .yellow
        } else {
            return .orange
        }
    }
}
