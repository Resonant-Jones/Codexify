import SwiftUI

struct ContentView: View {
    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @AppStorage("scout.accountSessionGeneration") private var sessionGeneration = 0
    private struct ViewIdentity: Hashable {
        let connection: ScoutConnectionIdentity?
        let sessionGeneration: Int
    }
    private var connectionIdentity: ScoutConnectionIdentity? {
        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else { return nil }
        return ScoutConnectionIdentity(endpoint: profile)
    }

    var body: some View {
        TabView {
            ForEach(ScoutAppRoute.allCases) { route in
                rootView(for: route)
                    .id(ViewIdentity(connection: connectionIdentity, sessionGeneration: route == .settings ? 0 : sessionGeneration))
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
