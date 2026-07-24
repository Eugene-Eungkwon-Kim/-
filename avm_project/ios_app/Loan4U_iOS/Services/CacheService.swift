import CryptoKit
import Foundation

@MainActor
final class CacheService: ObservableObject {
    static let shared = CacheService()

    private let fileManager = FileManager.default
    private let cacheDirURL: URL
    private let ttlSeconds: TimeInterval = 86400

    @Published var cachedPredictions: [String: CachedPrediction] = [:]

    init() {
        let paths = fileManager.urls(for: .cachesDirectory, in: .userDomainMask)
        cacheDirURL = paths[0].appendingPathComponent("loan4u_cache")
        try? fileManager.createDirectory(at: cacheDirURL, withIntermediateDirectories: true)
        loadCachedPredictions()
    }

    func cacheKey(for features: [String: Double]) -> String {
        let sorted = features.sorted { $0.key < $1.key }
        let data = try? JSONEncoder().encode(sorted.map { "\($0.key):\($0.value)" })
        return data.flatMap { data in
            Insecure.MD5.hash(data: data).map { String(format: "%02hhx", $0) }.joined()
        } ?? UUID().uuidString
    }

    func getCachedPrediction(for features: [String: Double]) -> CachedPrediction? {
        let key = cacheKey(for: features)
        guard let cached = cachedPredictions[key] else { return nil }
        guard Date().timeIntervalSince(cached.timestamp) < ttlSeconds else {
            cachedPredictions.removeValue(forKey: key)
            return nil
        }
        return cached
    }

    func cachePrediction(_ result: PredictionResult, for features: [String: Double]) {
        let key = cacheKey(for: features)
        let cached = CachedPrediction(result: result, timestamp: Date())
        cachedPredictions[key] = cached
        saveCachedPredictions()
    }

    private func loadCachedPredictions() {
        let fileURL = cacheDirURL.appendingPathComponent("predictions.json")
        guard let data = try? Data(contentsOf: fileURL) else { return }
        if let decoded = try? JSONDecoder().decode([String: CachedPrediction].self, from: data) {
            cachedPredictions = decoded
        }
    }

    private func saveCachedPredictions() {
        let fileURL = cacheDirURL.appendingPathComponent("predictions.json")
        if let encoded = try? JSONEncoder().encode(cachedPredictions) {
            try? encoded.write(to: fileURL)
        }
    }
}

struct CachedPrediction: Codable {
    let result: PredictionResult
    let timestamp: Date
}

extension PredictionResult: Codable {
    enum CodingKeys: String, CodingKey {
        case predictedPrice, confidenceScore, region, timestamp
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(predictedPrice, forKey: .predictedPrice)
        try container.encode(confidenceScore, forKey: .confidenceScore)
        try container.encode(region, forKey: .region)
        try container.encode(timestamp, forKey: .timestamp)
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        predictedPrice = try container.decode(Int.self, forKey: .predictedPrice)
        confidenceScore = try container.decode(Double.self, forKey: .confidenceScore)
        region = try container.decode(String.self, forKey: .region)
        timestamp = try container.decode(Date.self, forKey: .timestamp)
    }
}
