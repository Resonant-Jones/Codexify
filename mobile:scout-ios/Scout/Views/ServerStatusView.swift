import SwiftUI

struct ServerStatusView: View {
    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                Text("Server Status")
                    .font(.largeTitle)
                    .fontWeight(.semibold)

                Text("Future work will check Vault reachability and model/runtime health without collapsing warmup or degraded states into a generic offline result.")
                    .font(.body)
                    .foregroundStyle(.secondary)

                Spacer()
            }
            .padding()
            .navigationTitle("Server")
        }
    }
}

#Preview {
    ServerStatusView()
}
