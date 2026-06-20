import Foundation

enum ScoutAppRoute: String, CaseIterable, Identifiable {
    case server
    case guardian
    case activity
    case artifacts
    case settings

    var id: String {
        rawValue
    }

    var title: String {
        switch self {
        case .server:
            return "Server"
        case .guardian:
            return "Guardian"
        case .activity:
            return "Activity"
        case .artifacts:
            return "Artifacts"
        case .settings:
            return "Settings"
        }
    }

    var systemImage: String {
        switch self {
        case .server:
            return "server.rack"
        case .guardian:
            return "message"
        case .activity:
            return "list.bullet.rectangle"
        case .artifacts:
            return "doc.on.doc"
        case .settings:
            return "gearshape"
        }
    }
}
