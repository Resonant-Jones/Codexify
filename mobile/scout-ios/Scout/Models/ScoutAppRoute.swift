import Foundation

enum ScoutAppRoute: String, CaseIterable, Identifiable {
    case guardian
    case feed
    case library
    case spaces

    var id: String { rawValue }
    var title: String {
        switch self {
        case .guardian: return "Guardian"
        case .feed: return "Feed"
        case .library: return "Library"
        case .spaces: return "Spaces"
        }
    }
    var systemImage: String {
        switch self {
        case .guardian: return "bubble.left"
        case .feed: return "dot.radiowaves.left.and.right"
        case .library: return "cylinder"
        case .spaces: return "safari"
        }
    }
}
