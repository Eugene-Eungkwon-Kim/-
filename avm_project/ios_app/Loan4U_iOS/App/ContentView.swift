import SwiftUI

struct ContentView: View {
    @State private var showInput = true
    @EnvironmentObject var modelService: MLModelService

    var body: some View {
        NavigationStack {
            if showInput {
                PropertyInputView(showInput: $showInput)
            } else {
                PredictionResultView(showInput: $showInput)
            }
        }
    }
}
