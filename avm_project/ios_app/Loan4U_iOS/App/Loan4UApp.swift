import SwiftUI

@main
struct Loan4UApp: App {
    @StateObject private var modelService = MLModelService.shared
    @StateObject private var cacheService = CacheService.shared

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(modelService)
                .environmentObject(cacheService)
                .task { await modelService.load() }
        }
    }
}
