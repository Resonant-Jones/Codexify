import Foundation

enum ScoutEndpointTransportType: CaseIterable, Identifiable {
    case tailscale
    case localNetwork
    case custom

    var id: Self { self }

    var title: String {
        switch self {
        case .tailscale: return "Tailscale"
        case .localNetwork: return "Local Network"
        case .custom: return "Custom"
        }
    }
}

enum ScoutEndpointAuthenticationState: CaseIterable, Identifiable {
    case unconfigured
    case authRequired
    case authenticated

    var id: Self { self }

    var title: String {
        switch self {
        case .unconfigured: return "Unconfigured"
        case .authRequired: return "Auth Required"
        case .authenticated: return "Authenticated"
        }
    }
}

enum ScoutEndpointValidationState: CaseIterable, Identifiable {
    case unconfigured
    case validating
    case reachable
    case unreachable
    case invalidConfiguration

    var id: Self { self }

    var title: String {
        switch self {
        case .unconfigured: return "Unconfigured"
        case .validating: return "Validating"
        case .reachable: return "Reachable"
        case .unreachable: return "Unreachable"
        case .invalidConfiguration: return "Invalid Configuration"
        }
    }
}

struct ScoutEndpointProfile: Identifiable, Equatable {
    var id: UUID
    var name: String
    var baseURL: String
    var transportType: ScoutEndpointTransportType
    var authenticationState: ScoutEndpointAuthenticationState
    var validationState: ScoutEndpointValidationState
    var lastConnectedAt: Date?

    static var emptyDraft: ScoutEndpointProfile {
        ScoutEndpointProfile(
            id: UUID(),
            name: "",
            baseURL: "",
            transportType: .tailscale,
            authenticationState: .unconfigured,
            validationState: .unconfigured,
            lastConnectedAt: nil
        )
    }
}
