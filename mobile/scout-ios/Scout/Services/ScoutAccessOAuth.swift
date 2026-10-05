import Foundation
import CryptoKit
import Security

// Access admits requests through ingress. This credential is never a Guardian account session.
enum ScoutAccessOAuthError: Error {
    case unsupportedConnection, invalidCallback, rejectedAuthorization, invalidResponse
    case expiredCredential, superseded, randomGenerationFailed
}

struct ScoutAccessOAuth {
    static let resource = URL(string: "https://preview.codexify.space")!
    static let issuer = URL(string: "https://resonant-constructs.cloudflareaccess.com")!
    static let callback = URL(string: "ai.resonantconstructs.codexify.scout://access-callback")!
    // Public registration metadata; no client secret exists.
    static let clientID = "53bc5fc5-aba1-4b4e-8541-30772ce12c20"
    static let authorizationEndpoint = issuer.appendingPathComponent("cdn-cgi/access/oauth/authorization")
    static let tokenEndpoint = issuer.appendingPathComponent("cdn-cgi/access/oauth/token")
    static let revocationEndpoint = issuer.appendingPathComponent("cdn-cgi/access/oauth/revoke")

    static func origin(for profile: ScoutEndpointProfile) throws -> String {
        let normalized = profile.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: normalized), url.scheme?.lowercased() == "https",
              let host = url.host, !host.isEmpty, url.user == nil, url.password == nil,
              url.query == nil, url.fragment == nil, url.path.isEmpty || url.path == "/" else {
            throw ScoutAccessOAuthError.unsupportedConnection
        }
        return "https://\(host.lowercased())" + ((url.port == nil || url.port == 443) ? "" : ":\(url.port!)")
    }

    static func requireHosted(_ profile: ScoutEndpointProfile) throws {
        guard profile.authenticationMode == .remoteSession,
              try origin(for: profile) == resource.absoluteString else {
            throw ScoutAccessOAuthError.unsupportedConnection
        }
    }

    static func supportsAccountSignIn(_ profile: ScoutEndpointProfile) -> Bool {
        (try? origin(for: profile)) == resource.absoluteString
    }

    static func hostedProfile(preserving profile: ScoutEndpointProfile?) -> ScoutEndpointProfile {
        ScoutEndpointProfile(id: profile?.id ?? UUID(), name: "Hosted Codexify",
            baseURL: resource.absoluteString, transportType: .custom,
            authenticationState: .unconfigured, validationState: .unconfigured,
            lastConnectedAt: nil, authenticationMode: .remoteSession)
    }

    static func credentialAccount(for profile: ScoutEndpointProfile) throws -> String {
        let scope = profile.id.uuidString + "|" + (try origin(for: profile))
        return "access-oauth." + base64URL(Data(SHA256.hash(data: Data(scope.utf8))))
    }

    static func randomValue() throws -> String {
        var bytes = [UInt8](repeating: 0, count: 32)
        guard SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes) == errSecSuccess else {
            throw ScoutAccessOAuthError.randomGenerationFailed
        }
        return base64URL(Data(bytes))
    }

    static func base64URL(_ data: Data) -> String {
        data.base64EncodedString().replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "=", with: "")
    }

    struct Attempt {
        private let verifier: String
        private let state: String
        private var consumed = false

        init() throws {
            verifier = try ScoutAccessOAuth.randomValue()
            state = try ScoutAccessOAuth.randomValue()
        }

        // Deterministic input is used only by protocol regression tests.
        init(verifier: String, state: String) {
            self.verifier = verifier
            self.state = state
        }

        var authorizationURL: URL {
            var url = URLComponents(url: authorizationEndpoint, resolvingAgainstBaseURL: false)!
            url.queryItems = [
                URLQueryItem(name: "response_type", value: "code"),
                URLQueryItem(name: "client_id", value: clientID),
                URLQueryItem(name: "redirect_uri", value: callback.absoluteString),
                URLQueryItem(name: "resource", value: resource.absoluteString),
                URLQueryItem(name: "state", value: state),
                URLQueryItem(name: "code_challenge_method", value: "S256"),
                URLQueryItem(name: "code_challenge", value: base64URL(Data(SHA256.hash(data: Data(verifier.utf8)))))
            ]
            return url.url!
        }

        mutating func exchangeRequest(callbackURL: URL) throws -> URLRequest {
            guard !consumed else { throw ScoutAccessOAuthError.invalidCallback }
            consumed = true
            guard let url = URLComponents(url: callbackURL, resolvingAgainstBaseURL: false),
                  url.scheme == callback.scheme, url.host == callback.host,
                  url.path.isEmpty, url.port == nil, url.user == nil, url.password == nil,
                  url.fragment == nil else { throw ScoutAccessOAuthError.invalidCallback }
            let items = url.queryItems ?? []
            func value(_ name: String) -> String? {
                let matches = items.filter { $0.name == name }
                return matches.count == 1 ? matches[0].value : nil
            }
            guard value("state") == state else { throw ScoutAccessOAuthError.invalidCallback }
            guard !items.contains(where: { $0.name == "error" }),
                  let code = value("code"), !code.isEmpty else { throw ScoutAccessOAuthError.rejectedAuthorization }
            return formRequest(url: tokenEndpoint, fields: [
                "grant_type": "authorization_code", "client_id": clientID,
                "redirect_uri": callback.absoluteString, "code": code,
                "code_verifier": verifier, "resource": resource.absoluteString
            ])
        }
    }

    static func formRequest(url: URL, fields: [String: String]) -> URLRequest {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        let allowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~")
        request.httpBody = Data(fields.keys.sorted().map {
            $0.addingPercentEncoding(withAllowedCharacters: allowed)! + "=" + fields[$0]!.addingPercentEncoding(withAllowedCharacters: allowed)!
        }.joined(separator: "&").utf8)
        return request
    }

    static func refreshRequest(credential: Credential, profile: ScoutEndpointProfile) throws -> URLRequest {
        try requireHosted(profile)
        guard let token = credential.refreshToken, !token.isEmpty else {
            throw ScoutAccessOAuthError.expiredCredential
        }
        return formRequest(url: tokenEndpoint, fields: [
            "grant_type": "refresh_token", "client_id": clientID,
            "refresh_token": token, "resource": resource.absoluteString
        ])
    }

    struct Credential: Codable {
        let accessToken: String
        let refreshToken: String?
        let expiresAt: Date

        static func decode(_ data: Data, now: Date = Date(), retainingRefreshToken: String? = nil) throws -> Self {
            struct Response: Decodable {
                let access_token: String
                let token_type: String
                let expires_in: Double
                let refresh_token: String?
            }
            let response = try JSONDecoder().decode(Response.self, from: data)
            guard response.token_type.lowercased() == "bearer", !response.access_token.isEmpty,
                  response.expires_in.isFinite, response.expires_in > 0 else {
                throw ScoutAccessOAuthError.invalidResponse
            }
            guard response.refresh_token == nil || response.refresh_token?.isEmpty == false else {
                throw ScoutAccessOAuthError.invalidResponse
            }
            return Self(accessToken: response.access_token, refreshToken: response.refresh_token ?? retainingRefreshToken,
                        expiresAt: now.addingTimeInterval(response.expires_in))
        }
    }
}

// No credential-bearing request may redirect to another URL, even on the same origin.
final class ScoutAuthNoRedirect: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest,
                    completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}
