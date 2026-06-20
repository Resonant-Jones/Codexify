import SwiftUI

struct ArtifactsView: View {
    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                Text("Artifacts")
                    .font(.largeTitle)
                    .fontWeight(.semibold)

                Text("Future work will show documents, media, and generated outputs returned by Vault without claiming local ownership of durable artifact state.")
                    .font(.body)
                    .foregroundStyle(.secondary)

                Spacer()
            }
            .padding()
            .navigationTitle("Artifacts")
        }
    }
}

#Preview {
    ArtifactsView()
}
