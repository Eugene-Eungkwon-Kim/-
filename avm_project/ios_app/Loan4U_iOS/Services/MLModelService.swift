import Foundation
import onnxruntime_objc

struct PredictionResult: Equatable {
    let predictedPrice: Int
    let confidenceScore: Double
    let region: String
    let timestamp: Date
}

/// Loads the shipped ONNX models and runs inference via ONNX Runtime.
/// Both platforms load the identical `.onnx` files — no CoreML/TFLite
/// conversion step, so what the Python contract test verifies is what runs.
@MainActor
final class MLModelService: ObservableObject {
    static let shared = MLModelService()

    @Published private(set) var isLoaded = false
    @Published private(set) var loadingError: String?

    private var env: ORTEnv?
    private var sessions: [String: ORTSession] = [:]
    private let modelKeys = ["nationwide", "seoul", "busan", "gyeonggi", "daegu", "incheon"]

    func load() async {
        do {
            let env = try ORTEnv(loggingLevel: .warning)
            self.env = env
            var loaded: [String: ORTSession] = [:]
            for key in modelKeys {
                guard let url = Bundle.main.url(forResource: "KR_\(key)_lite", withExtension: "onnx") else {
                    continue
                }
                loaded[key] = try ORTSession(env: env, modelPath: url.path, sessionOptions: nil)
            }
            guard loaded["nationwide"] != nil else {
                throw NSError(domain: "Loan4U", code: 1,
                              userInfo: [NSLocalizedDescriptionKey: "nationwide model missing"])
            }
            sessions = loaded
            isLoaded = true
        } catch {
            loadingError = "Model load failed: \(error.localizedDescription)"
        }
    }

    /// Region-specific model when available, else the nationwide fallback.
    func predict(_ input: PropertyInput, region: String?) -> PredictionResult? {
        let key = region?.lowercased() ?? "nationwide"
        guard let session = sessions[key] ?? sessions["nationwide"] else { return nil }

        let vector = FeatureEngineering.buildVector(input)
        do {
            let price = try runInference(session: session, vector: vector)
            guard price > 0 else { return nil }
            return PredictionResult(
                predictedPrice: Int(price.rounded()),
                confidenceScore: confidence(forRegion: key),
                region: region ?? "Nationwide",
                timestamp: Date()
            )
        } catch {
            loadingError = "Inference failed: \(error.localizedDescription)"
            return nil
        }
    }

    private func runInference(session: ORTSession, vector: [Float]) throws -> Float {
        let data = NSMutableData(bytes: vector, length: vector.count * MemoryLayout<Float>.stride)
        let input = try ORTValue(
            tensorData: data,
            elementType: .float,
            shape: [1, NSNumber(value: vector.count)]
        )
        let outputs = try session.run(
            withInputs: ["float_input": input],
            outputNames: ["variable"],
            runOptions: nil
        )
        guard let value = outputs["variable"],
              let tensorData = try value.tensorData() as Data? else {
            throw NSError(domain: "Loan4U", code: 2)
        }
        return tensorData.withUnsafeBytes { $0.load(as: Float.self) }
    }

    /// Confidence reflects each region model's validated MAPE, not a
    /// per-prediction uncertainty (the tree models don't expose one).
    private func confidence(forRegion key: String) -> Double {
        let mape: [String: Double] = [
            "seoul": 0.0947, "busan": 0.0948, "gyeonggi": 0.0994,
            "daegu": 0.1094, "incheon": 0.0950, "nationwide": 0.8148,
        ]
        return max(0.0, min(1.0, 1.0 - (mape[key] ?? 0.5)))
    }
}
