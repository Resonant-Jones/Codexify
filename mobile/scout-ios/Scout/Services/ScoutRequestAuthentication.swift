import Foundation

enum ScoutRequestAuthenticationError: LocalizedError, Equatable {
    case unsupportedRemoteSession
    case sessionRequired, expiredSession, invalidSession, wrongConnection, ingressRequired

    var errorDescription: String? {
        switch self {
        case .unsupportedRemoteSession:
            return "Remote-session authentication is not implemented in Scout yet. No request was sent."
        case .sessionRequired: return "Sign in to Guardian for this connection. No account session is stored; no request was sent."
        case .expiredSession: return "Guardian account session has expired. Sign in again; no request was sent."
        case .invalidSession: return "Guardian account session is invalid. Sign in again."
        case .wrongConnection: return "This credential does not belong to this connection. No request was sent."
        case .ingressRequired: return "Authorize or renew hosted ingress before sending an account request."
        }
    }
}

struct ScoutRequestAuthentication {
    static func isInvalidAccountResponse(_ response: HTTPURLResponse) -> Bool {
        response.statusCode == 401 && response.value(forHTTPHeaderField: "X-Guardian-Auth-Failure") == "ACCOUNT_SESSION_INVALID"
    }

    static func validate(response: HTTPURLResponse, endpoint: ScoutEndpointProfile, request: URLRequest) throws {
        guard endpoint.authenticationMode == .remoteSession, isInvalidAccountResponse(response) else { return }
        let hosted = try ScoutAccessOAuth.origin(for: endpoint) == ScoutAccessOAuth.resource.absoluteString
        guard !hosted || request.value(forHTTPHeaderField: "X-Guardian-Account-Session") != nil else { return }
        try ScoutAccountSessionStore().delete(for: endpoint)
        throw ScoutRequestAuthenticationError.invalidSession
    }

    static func apply(
        to request: inout URLRequest,
        endpoint: ScoutEndpointProfile,
        apiKey: String?,
        accountSession: ScoutAccountSession? = nil,
        ingress: ScoutAccessOAuth.Credential? = nil,
        now: Date = Date()
    ) throws {
        request.setValue(nil, forHTTPHeaderField: "Authorization")
        request.setValue(nil, forHTTPHeaderField: "X-API-Key")
        request.setValue(nil, forHTTPHeaderField: "X-Guardian-Account-Session")

        let origin = try ScoutAccessOAuth.origin(for: endpoint)
        guard let url = request.url, url.scheme?.lowercased() == "https", url.user == nil, url.password == nil,
              let host = url.host,
              "https://" + host.lowercased() + ((url.port == nil || url.port == 443) ? "" : ":\(url.port!)") == origin else {
            throw ScoutRequestAuthenticationError.wrongConnection
        }

        switch endpoint.authenticationMode {
        case .localAPIKey:
            if let key = apiKey, !key.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                request.setValue(key, forHTTPHeaderField: "X-API-Key")
            }
        case .remoteSession:
            guard let session = try accountSession ?? ScoutAccountSessionStore().load(for: endpoint) else {
                throw ScoutRequestAuthenticationError.sessionRequired
            }
            try session.validate(for: endpoint, now: now)
            if origin == ScoutAccessOAuth.resource.absoluteString {
                guard let admission = try ingress ?? ScoutAccessCredentialStore().load(for: endpoint), admission.expiresAt > now else {
                    throw ScoutRequestAuthenticationError.ingressRequired
                }
                request.setValue("Bearer \(admission.accessToken)", forHTTPHeaderField: "Authorization")
                if url.path != "/health" {
                    request.setValue(session.token, forHTTPHeaderField: "X-Guardian-Account-Session")
                }
            } else {
                request.setValue("Bearer \(session.token)", forHTTPHeaderField: "Authorization")
            }
        }
    }
}
