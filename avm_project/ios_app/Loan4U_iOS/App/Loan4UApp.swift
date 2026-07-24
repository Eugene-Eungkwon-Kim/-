import SwiftUI

@main
struct Loan4UApp: App {
    let modelService = MLModelService.shared
    let cacheService = CacheService.shared

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(modelService)
                .environmentObject(cacheService)
        }
    }
}
