import CryptoKit
import Foundation

struct CachedPrediction: Codable {
    let result: PredictionResult
    let timestamp: Date
}

/// SHA256-keyed local cache with a 24h TTL, persisted to Caches/.
@MainActor
final class CacheService: ObservableObject {
    static let shared = CacheService()

    private let fileManager = FileManager.default
    private let cacheDirURL: URL
    private let ttlSeconds: TimeInterval = 86_400
    private var entries: [String: CachedPrediction] = [:]

    init() {
        let caches = fileManager.urls(for: .cachesDirectory, in: .userDomainMask)[0]
        cacheDirURL = caches.appendingPathComponent("loan4u_cache")
        try? fileManager.createDirectory(at: cacheDirURL, withIntermediateDirectories: true)
        load()
    }

    func cacheKey(_ input: PropertyInput, region: String?) -> String {
        let raw = "\(region ?? "nationwide")|\(input.region)|\(input.areaM2)|\(input.yearBuilt)"
        let digest = SHA256.hash(data: Data(raw.utf8))
        return digest.map { String(format: "%02x", $0) }.joined()
    }

    func cached(_ input: PropertyInput, region: String?) -> PredictionResult? {
        let key = cacheKey(input, region: region)
        guard let entry = entries[key] else { return nil }
        guard Date().timeIntervalSince(entry.timestamp) < ttlSeconds else {
            entries.removeValue(forKey: key)
            return nil
        }
        return entry.result
    }

    func store(_ result: PredictionResult, for input: PropertyInput, region: String?) {
        entries[cacheKey(input, region: region)] = CachedPrediction(result: result, timestamp: Date())
        persist()
    }

    private var fileURL: URL { cacheDirURL.appendingPathComponent("predictions.json") }

    private func load() {
        guard let data = try? Data(contentsOf: fileURL),
              let decoded = try? JSONDecoder().decode([String: CachedPrediction].self, from: data)
        else { return }
        entries = decoded
    }

    private func persist() {
        if let data = try? JSONEncoder().encode(entries) {
            try? data.write(to: fileURL)
        }
    }
}

extension PredictionResult: Codable {}
