import Foundation

enum ScoutRequestAuthenticationError: LocalizedError, Equatable {
    case unsupportedRemoteSession

    var errorDescription: String? {
        switch self {
        case .unsupportedRemoteSession:
            return "Remote-session authentication is not implemented in Scout yet. No request was sent."
        }
    }
}

struct ScoutRequestAuthentication {
    static func apply(
        to request: inout URLRequest,
        endpoint: ScoutEndpointProfile,
        apiKey: String?
    ) throws {
        request.setValue(nil, forHTTPHeaderField: "Authorization")
        request.setValue(nil, forHTTPHeaderField: "X-API-Key")

        switch endpoint.authenticationMode {
        case .localAPIKey:
            if let key = apiKey, !key.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                request.setValue(key, forHTTPHeaderField: "X-API-Key")
            }
        case .remoteSession:
            throw ScoutRequestAuthenticationError.unsupportedRemoteSession
        }
    }
}
