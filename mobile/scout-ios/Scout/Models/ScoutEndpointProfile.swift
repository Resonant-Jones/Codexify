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

enum ScoutEndpointAuthenticationMode: String, CaseIterable, Identifiable, Codable {
    case localAPIKey
    case remoteSession

    var id: Self { self }

    var title: String {
        switch self {
        case .localAPIKey: return "Local API key"
        case .remoteSession: return "Remote session — not available yet"
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
    var authenticationMode: ScoutEndpointAuthenticationMode
    var authenticationState: ScoutEndpointAuthenticationState
    var validationState: ScoutEndpointValidationState
    var lastConnectedAt: Date?

    init(
        id: UUID,
        name: String,
        baseURL: String,
        transportType: ScoutEndpointTransportType,
        authenticationState: ScoutEndpointAuthenticationState,
        validationState: ScoutEndpointValidationState,
        lastConnectedAt: Date?,
        authenticationMode: ScoutEndpointAuthenticationMode = .localAPIKey
    ) {
        self.id = id
        self.name = name
        self.baseURL = baseURL
        self.transportType = transportType
        self.authenticationMode = authenticationMode
        self.authenticationState = authenticationMode == .remoteSession ? .unconfigured : authenticationState
        self.validationState = validationState
        self.lastConnectedAt = lastConnectedAt
    }

    private enum CodingKeys: String, CodingKey {
        case id, name, baseURL, transportType, authenticationMode
        case authenticationState, validationState, lastConnectedAt
    }

    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        id = try values.decode(UUID.self, forKey: .id)
        name = try values.decode(String.self, forKey: .name)
        baseURL = try values.decode(String.self, forKey: .baseURL)
        transportType = try values.decode(ScoutEndpointTransportType.self, forKey: .transportType)
        // Only a missing field is a legacy local profile. Explicit null and unknown values fail.
        authenticationMode = values.contains(.authenticationMode)
            ? try values.decode(ScoutEndpointAuthenticationMode.self, forKey: .authenticationMode)
            : .localAPIKey
        let storedState = try values.decode(ScoutEndpointAuthenticationState.self, forKey: .authenticationState)
        authenticationState = authenticationMode == .remoteSession ? .unconfigured : storedState
        validationState = try values.decode(ScoutEndpointValidationState.self, forKey: .validationState)
        lastConnectedAt = try values.decodeIfPresent(Date.self, forKey: .lastConnectedAt)
    }

    func encode(to encoder: Encoder) throws {
        var values = encoder.container(keyedBy: CodingKeys.self)
        try values.encode(id, forKey: .id)
        try values.encode(name, forKey: .name)
        try values.encode(baseURL, forKey: .baseURL)
        try values.encode(transportType, forKey: .transportType)
        try values.encode(authenticationMode, forKey: .authenticationMode)
        try values.encode(authenticationMode == .remoteSession ? .unconfigured : authenticationState,
                          forKey: .authenticationState)
        try values.encode(validationState, forKey: .validationState)
        try values.encodeIfPresent(lastConnectedAt, forKey: .lastConnectedAt)
    }

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
            if let scheme = url.scheme?.lowercased(), scheme != "https" {
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
