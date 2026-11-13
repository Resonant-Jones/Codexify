import SwiftUI

struct SpacesView: View {
    var body: some View {
        Group {
            ContentUnavailableView(
                "Spaces aren’t available yet",
                systemImage: "safari",
                description: Text("Scout’s Spaces view is a place for projects and shared contexts. It isn’t connected to Spaces data yet.")
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}

#Preview {
    SpacesView()
}
