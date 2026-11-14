import SwiftUI

enum ScoutAuxiliaryDestination: String, Identifiable {
    case settings
    case server
    var id: String { rawValue }
}

private struct ScoutOpenAuxiliaryKey: EnvironmentKey {
    static let defaultValue: (ScoutAuxiliaryDestination) -> Void = { _ in }
}

extension EnvironmentValues {
    var scoutOpenAuxiliary: (ScoutAuxiliaryDestination) -> Void {
        get { self[ScoutOpenAuxiliaryKey.self] }
        set { self[ScoutOpenAuxiliaryKey.self] = newValue }
    }
}

struct ScoutAuxiliaryMenu: ToolbarContent {
    @Environment(\.scoutOpenAuxiliary) private var openAuxiliary

    var body: some ToolbarContent {
        ToolbarItem(placement: .topBarTrailing) {
            Menu {
                Button("Settings", systemImage: "gearshape") {
                    openAuxiliary(.settings)
                }
                Button("Server Status", systemImage: "server.rack") {
                    openAuxiliary(.server)
                }
            } label: {
                Image(systemName: "ellipsis.circle")
                    .accessibilityLabel("More options")
            }
        }
    }
}
