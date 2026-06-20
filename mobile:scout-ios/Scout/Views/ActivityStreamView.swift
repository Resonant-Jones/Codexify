import SwiftUI

struct ActivityStreamView: View {
    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                Text("Activity")
                    .font(.largeTitle)
                    .fontWeight(.semibold)

                Text("Future work will display Guardian task and event updates while keeping request execution, provider readiness, and visibility state distinct.")
                    .font(.body)
                    .foregroundStyle(.secondary)

                Spacer()
            }
            .padding()
            .navigationTitle("Activity")
        }
    }
}

#Preview {
    ActivityStreamView()
}
