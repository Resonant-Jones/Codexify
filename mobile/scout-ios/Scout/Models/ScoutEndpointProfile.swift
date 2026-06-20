import Foundation

enum ScoutEndpointTransportType: CaseIterable, Identifiable, Codable {
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

enum ScoutEndpointAuthenticationState: CaseIterable, Identifiable, Codable {
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

enum ScoutEndpointValidationState: CaseIterable, Identifiable, Codable {
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

enum ScoutEndpointDraftValidationError: CaseIterable, Identifiable {
    case emptyName
    case missingBaseURL
    case invalidURLFormat
    case unsupportedScheme

    var id: Self { self }

    var title: String {
        switch self {
        case .emptyName: return "Name is empty"
        case .missingBaseURL: return "Base URL is missing"
        case .invalidURLFormat: return "URL format is invalid"
        case .unsupportedScheme: return "Unsupported URL scheme"
        }
    }
}

struct ScoutEndpointProfile: Identifiable, Equatable, Codable {
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

    var draftValidationErrors: [ScoutEndpointDraftValidationError] {
        var errors: [ScoutEndpointDraftValidationError] = []

        if name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            errors.append(.emptyName)
        }

        let trimmedURL = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmedURL.isEmpty {
            errors.append(.missingBaseURL)
        } else if let url = URL(string: trimmedURL) {
            guard let scheme = url.scheme?.lowercased(), scheme == "https" else {
                errors.append(.unsupportedScheme)
            }
        } else {
            errors.append(.invalidURLFormat)
        }

        return errors
    }

    var isValidDraft: Bool {
        draftValidationErrors.isEmpty
    }

    mutating func validateDraft() {
        if isValidDraft {
            validationState = .reachable
        } else {
            validationState = .invalidConfiguration
        }
    }
}
