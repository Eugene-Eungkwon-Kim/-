import SwiftUI

struct PredictionResultView: View {
    let result: PredictionResult?
    let onNewValuation: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            if let result {
                VStack(spacing: 16) {
                    Text("Estimated Price")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    Text("₩\(result.predictedPrice.formatted())")
                        .font(.system(size: 40, weight: .bold, design: .rounded))

                    VStack(spacing: 8) {
                        HStack {
                            Text("Confidence").font(.subheadline)
                            Spacer()
                            Text(String(format: "%.0f%%", result.confidenceScore * 100))
                                .font(.subheadline).fontWeight(.semibold)
                        }
                        ProgressView(value: result.confidenceScore)
                            .tint(confidenceColor(result.confidenceScore))
                    }

                    Divider()

                    row("Region", result.region)
                    row("Predicted", result.timestamp.formatted(date: .abbreviated, time: .shortened))
                }
                .padding(20)
                .background(Color(.secondarySystemBackground))
                .cornerRadius(12)

                Spacer()

                Button(action: onNewValuation) {
                    Text("New Valuation").frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
            } else {
                Text("No prediction available").foregroundStyle(.secondary)
                Spacer()
                Button("Go Back", action: onNewValuation).buttonStyle(.bordered)
            }
        }
        .padding()
        .navigationTitle("Valuation Result")
    }

    private func row(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label).foregroundStyle(.secondary)
            Spacer()
            Text(value).fontWeight(.semibold)
        }
        .font(.callout)
    }

    private func confidenceColor(_ score: Double) -> Color {
        score >= 0.8 ? .green : (score >= 0.5 ? .yellow : .orange)
    }
}
