import SwiftUI

struct ContentView: View {
    var body: some View {
        TabView {
            ForEach(ScoutAppRoute.allCases) { route in
                rootView(for: route)
                    .tabItem {
                        Label(route.title, systemImage: route.systemImage)
                    }
            }
        }
    }

    @ViewBuilder
    private func rootView(for route: ScoutAppRoute) -> some View {
        switch route {
        case .server:
            ServerStatusView()
        case .guardian:
            GuardianChatView()
        case .activity:
            ActivityStreamView()
        case .artifacts:
            ArtifactsView()
        case .settings:
            SettingsAuthView()
        }
    }
}

#Preview {
    ContentView()
}
