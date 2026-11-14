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
        GuardianChatView()
        .id(ViewIdentity(connection: connectionIdentity, sessionGeneration: sessionGeneration))
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

}

#Preview {
    ContentView()
}
