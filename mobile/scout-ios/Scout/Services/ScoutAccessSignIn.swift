#if canImport(UIKit)
import UIKit
import AuthenticationServices
import SwiftUI

@MainActor
final class ScoutAccessSignIn: NSObject, ObservableObject, ASWebAuthenticationPresentationContextProviding {
    @Published private(set) var isWorking = false
    @Published private(set) var message: String?
    private var browser: ASWebAuthenticationSession?
    private var operation: UUID?
    private let store = ScoutAccessCredentialStore()

    private func networkSession() -> URLSession {
        let config = URLSessionConfiguration.ephemeral
        config.httpShouldSetCookies = false
        config.httpCookieStorage = nil
        config.urlCredentialStorage = nil
        config.timeoutIntervalForRequest = 20
        return URLSession(configuration: config, delegate: ScoutAuthNoRedirect(), delegateQueue: nil)
    }

    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
            .flatMap(\.windows).first(where: \.isKeyWindow) ?? ASPresentationAnchor()
    }

    func cancel() {
        operation = nil
        browser?.cancel()
        browser = nil
        isWorking = false
        message = nil
    }

    func restoreStatus(profile: ScoutEndpointProfile) {
        guard !isWorking, message == nil else { return }
        do {
            guard let credential = try store.load(for: profile) else {
                message = "No ingress credential is stored for this connection. Authorize hosted ingress to continue."
                return
            }
            message = credential.expiresAt > Date()
                ? "Ingress credential is stored in Keychain. Check stored ingress to qualify admission. Guardian account-session handoff is still required."
                : "Stored ingress authorization has expired. Check stored ingress to renew the existing grant, or authorize again. Guardian account-session handoff is still required."
        } catch {
            message = "Could not read this connection's ingress credential from Keychain."
        }
    }

    private func qualify(credential: ScoutAccessOAuth.Credential, profile: ScoutEndpointProfile,
                         session: URLSession, identity: UUID) async throws {
        try ScoutAccessOAuth.requireHosted(profile)
        var probe = URLRequest(url: ScoutAccessOAuth.resource.appendingPathComponent("api/chat/threads"))
        probe.setValue("application/json", forHTTPHeaderField: "Accept")
        probe.setValue("Bearer \(credential.accessToken)", forHTTPHeaderField: "Authorization")
        let (_, response) = try await session.data(for: probe)
        guard operation == identity else { throw ScoutAccessOAuthError.superseded }
        guard let http = response as? HTTPURLResponse else { throw ScoutAccessOAuthError.invalidResponse }
        message = ScoutIngressQualification(response: http).message(response: http)
    }

    func checkStoredIngress(profile: ScoutEndpointProfile) async {
        guard !isWorking else { return }
        let identity = UUID()
        operation = identity
        isWorking = true
        message = "Checking this connection's stored ingress authorization…"
        defer { if operation == identity { isWorking = false } }
        do {
            guard var credential = try store.load(for: profile) else {
                message = "No ingress credential is stored for this connection. Authorize hosted ingress to continue."
                return
            }
            let session = networkSession()
            defer { session.invalidateAndCancel() }
            if credential.expiresAt <= Date() {
                let request = try ScoutAccessOAuth.refreshRequest(credential: credential, profile: profile)
                let (data, response) = try await session.data(for: request)
                guard operation == identity else { throw ScoutAccessOAuthError.superseded }
                guard let http = response as? HTTPURLResponse else { throw ScoutAccessOAuthError.invalidResponse }
                guard http.statusCode == 200 else {
                    message = "Ingress renewal returned HTTP \(http.statusCode)" + diagnosticRay(http)
                        + ". Authorize hosted ingress again; no Guardian account session was issued."
                    return
                }
                credential = try ScoutAccessOAuth.Credential.decode(data, retainingRefreshToken: credential.refreshToken)
                try store.save(credential, for: profile)
            }
            try await qualify(credential: credential, profile: profile, session: session, identity: identity)
        } catch {
            guard operation == identity else { return }
            message = "Stored ingress qualification did not finish. No Guardian account session was issued."
        }
    }

    private func authorize(_ url: URL) async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(url: url, callbackURLScheme: ScoutAccessOAuth.callback.scheme) { callback, error in
                if let callback, error == nil {
                    continuation.resume(returning: callback)
                } else {
                    continuation.resume(throwing: ScoutAccessOAuthError.rejectedAuthorization)
                }
            }
            session.presentationContextProvider = self
            session.prefersEphemeralWebBrowserSession = false
            browser = session
            if !session.start() {
                browser = nil
                continuation.resume(throwing: ScoutAccessOAuthError.rejectedAuthorization)
            }
        }
    }

    func signIn(profile: ScoutEndpointProfile) async {
        guard !isWorking else { return }
        let identity = UUID()
        operation = identity
        isWorking = true
        message = "Continue in the system browser to authorize hosted ingress."
        var failureStage = "System-browser authorization"
        defer {
            if operation == identity { isWorking = false; browser = nil }
        }
        do {
            try ScoutAccessOAuth.requireHosted(profile)
            var attempt = try ScoutAccessOAuth.Attempt()
            let callback = try await authorize(attempt.authorizationURL)
            guard operation == identity else { throw ScoutAccessOAuthError.superseded }
            failureStage = "Callback validation"
            let request = try attempt.exchangeRequest(callbackURL: callback)
            failureStage = "PKCE token exchange"
            let session = networkSession()
            defer { session.invalidateAndCancel() }
            let (data, response) = try await session.data(for: request)
            guard operation == identity else { throw ScoutAccessOAuthError.superseded }
            guard let http = response as? HTTPURLResponse else { throw ScoutAccessOAuthError.invalidResponse }
            guard http.statusCode == 200 else {
                failureStage = "PKCE token exchange returned HTTP \(http.statusCode)" + diagnosticRay(http)
                throw ScoutAccessOAuthError.invalidResponse
            }
            failureStage = "Token validation and Keychain storage"
            let credential = try ScoutAccessOAuth.Credential.decode(data)
            try store.save(credential, for: profile)
            message = "Ingress credential stored in Keychain. Checking the separate Guardian boundary…"
            failureStage = "Protected API qualification"
            try await qualify(credential: credential, profile: profile, session: session, identity: identity)
        } catch {
            guard operation == identity else { return }
            // Never display raw callback URLs, response bodies, or system errors containing credential material.
            message = failureStage + " did not finish. Retry sign-in; no Guardian account session was created."
        }
    }

    private func diagnosticRay(_ response: HTTPURLResponse) -> String {
        guard let ray = response.value(forHTTPHeaderField: "CF-Ray"),
              ray.count <= 64, ray.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "-") }) else { return "" }
        return " (Cloudflare Ray " + ray + ")"
    }

    func revoke(profile: ScoutEndpointProfile) async {
        guard !isWorking else { return }
        let identity = UUID()
        operation = identity
        isWorking = true
        defer { if operation == identity { isWorking = false } }
        do {
            guard let credential = try store.load(for: profile) else {
                message = "No ingress credential is stored for this connection."
                return
            }
            let session = networkSession()
            defer { session.invalidateAndCancel() }
            let token = credential.refreshToken ?? credential.accessToken
            let request = ScoutAccessOAuth.formRequest(url: ScoutAccessOAuth.revocationEndpoint,
                fields: ["client_id": ScoutAccessOAuth.clientID, "token": token,
                         "token_type_hint": credential.refreshToken == nil ? "access_token" : "refresh_token"])
            let (_, response) = try await session.data(for: request)
            guard operation == identity else { return }
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                message = "Ingress revocation was not confirmed. The credential remains in Keychain; retry."
                return
            }
            try store.delete(for: profile)
            message = "Ingress revocation accepted; connection credential removed from Keychain. Guardian logout is a separate operation."
        } catch {
            guard operation == identity else { return }
            message = "Ingress revocation did not finish. Retry; no remote revocation is claimed."
        }
    }
}
#endif
