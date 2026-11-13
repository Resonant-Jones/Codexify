import SwiftUI

struct ContentView: View {
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.colorSchemeContrast) private var colorContrast
    @AppStorage("scout.appearance.systemAccentRGB") private var systemAccent = ScoutAccentTheme.defaultRGB
    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @AppStorage("scout.accountSessionGeneration") private var sessionGeneration = 0
    @State private var presentedAuxiliary: ScoutAuxiliaryDestination?
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
                    .id(ViewIdentity(connection: connectionIdentity, sessionGeneration: sessionGeneration))
                    .tabItem {
                        Label {
                            Text(route.title)
                        } icon: {
                            Image(systemName: route.systemImage)
                        }
                    }
                    .tag(route)
            }
        }
        .toolbarBackground(colorScheme == .dark ? ScoutVisualStyle.color(CodexifyDesignTokens.Semantic.panelBg) : Color(uiColor: .systemBackground), for: .tabBar)
        .environment(\.scoutOpenAuxiliary, { presentedAuxiliary = $0 })
        .sheet(item: $presentedAuxiliary) { destination in
            switch destination {
            case .settings: SettingsAuthView(systemAccent: $systemAccent)
            case .server: ServerStatusView()
            }
        }
        .tint(ScoutAccentTheme(rgb: systemAccent, scheme: colorScheme, contrast: colorContrast).tint)
        .environment(\.scoutSystemAccent, systemAccent)
    }

    @ViewBuilder
    private func rootView(for route: ScoutAppRoute) -> some View {
        switch route {
        case .guardian:
            GuardianChatView()
        case .feed:
            ActivityStreamView()
        case .library:
            ArtifactsView()
        case .spaces:
            SpacesView()
        }
    }
}

#Preview {
    ContentView()
}
