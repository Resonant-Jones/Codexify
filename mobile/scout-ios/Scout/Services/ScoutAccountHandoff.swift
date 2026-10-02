import Foundation
import CryptoKit

struct ScoutAccountHandoffAttempt {
    private let verifier: String
    private let state: String
    private var consumed = false

    init() throws { verifier = try ScoutAccessOAuth.randomValue(); state = try ScoutAccessOAuth.randomValue() }
    init(verifier: String, state: String) { self.verifier = verifier; self.state = state }

    var browserURL: URL {
        var url = URLComponents(url: ScoutAccessOAuth.resource.appendingPathComponent("login"), resolvingAgainstBaseURL: false)!
        url.queryItems = [URLQueryItem(name: "scout_state", value: state), URLQueryItem(name: "scout_challenge",
            value: ScoutAccessOAuth.base64URL(Data(SHA256.hash(data: Data(verifier.utf8)))))]
        return url.url!
    }

    mutating func exchangeRequest(callback: URL, ingress: ScoutAccessOAuth.Credential, now: Date = Date()) throws -> URLRequest {
        guard !consumed else { throw ScoutAccessOAuthError.invalidCallback }
        consumed = true
        guard ingress.expiresAt > now else { throw ScoutRequestAuthenticationError.ingressRequired }
        guard let url = URLComponents(url: callback, resolvingAgainstBaseURL: false),
              url.scheme == ScoutAccessOAuth.callback.scheme, url.host == ScoutAccessOAuth.callback.host,
              url.path.isEmpty, url.user == nil, url.password == nil, url.port == nil, url.fragment == nil else {
            throw ScoutAccessOAuthError.invalidCallback
        }
        let items = url.queryItems ?? []
        let codes = items.filter { $0.name == "code" }
        let states = items.filter { $0.name == "state" }
        guard items.count == 2, states.count == 1, states[0].value == state,
              codes.count == 1, let code = codes[0].value,
              code.count == 43, code.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "-" || $0 == "_") }) else {
            throw ScoutAccessOAuthError.invalidCallback
        }
        var request = URLRequest(url: ScoutAccessOAuth.resource.appendingPathComponent("api/auth/scout/exchange"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("Bearer \(ingress.accessToken)", forHTTPHeaderField: "Authorization")
        request.httpBody = try JSONEncoder().encode(["code": code, "verifier": verifier])
        return request
    }

    static func decode(_ data: Data, profile: ScoutEndpointProfile, now: Date = Date()) throws -> ScoutAccountSession {
        struct Reply: Decodable { let token: String; let user_id: String; let expires_at: Double }
        let reply = try JSONDecoder().decode(Reply.self, from: data)
        guard reply.expires_at.isFinite else { throw ScoutRequestAuthenticationError.invalidSession }
        let session = ScoutAccountSession(token: reply.token, userID: reply.user_id,
            expiresAt: Date(timeIntervalSince1970: reply.expires_at), profileID: profile.id,
            origin: try ScoutAccessOAuth.origin(for: profile))
        try session.validate(for: profile, now: now)
        return session
    }
}

#if canImport(UIKit)
import UIKit
import AuthenticationServices
import SwiftUI

@MainActor
final class ScoutAccountSignIn: NSObject, ObservableObject, ASWebAuthenticationPresentationContextProviding {
    @Published private(set) var isWorking = false
    @Published private(set) var message: String?
    private var browser: ASWebAuthenticationSession?
    private var operation: UUID?
    private let store = ScoutAccountSessionStore()

    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.flatMap(\.windows).first(where: \.isKeyWindow) ?? ASPresentationAnchor()
    }

    func cancel() { operation = nil; browser?.cancel(); browser = nil; isWorking = false; message = nil }

    func restoreStatus(profile: ScoutEndpointProfile) {
        guard !isWorking, message == nil else { return }
        do {
            guard let account = try store.load(for: profile) else {
                message = "No Guardian account session is stored for this connection."
                return
            }
            try account.validate(for: profile)
            message = "Guardian account session restored from this connection's Keychain. Check account session to qualify current authorization."
        } catch {
            message = (error as? ScoutRequestAuthenticationError)?.errorDescription ?? "Could not read the account session from Keychain."
        }
    }

    private func authorize(_ url: URL) async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(url: url, callbackURLScheme: ScoutAccessOAuth.callback.scheme) { callback, error in
                if let callback, error == nil { continuation.resume(returning: callback) }
                else { continuation.resume(throwing: ScoutAccessOAuthError.rejectedAuthorization) }
            }
            session.presentationContextProvider = self
            session.prefersEphemeralWebBrowserSession = false
            browser = session
            if !session.start() { browser = nil; continuation.resume(throwing: ScoutAccessOAuthError.rejectedAuthorization) }
        }
    }

    func signIn(profile: ScoutEndpointProfile) async {
        guard !isWorking else { return }
        let identity = UUID(); operation = identity; isWorking = true
        var stage = "Guardian browser sign-in"
        defer { if operation == identity { isWorking = false; browser = nil } }
        do {
            try ScoutAccessOAuth.requireHosted(profile)
            guard let ingress = try ScoutAccessCredentialStore().load(for: profile), ingress.expiresAt > Date() else {
                throw ScoutRequestAuthenticationError.ingressRequired
            }
            message = "Continue in the system browser using your existing Guardian account, then choose Continue to Scout."
            var attempt = try ScoutAccountHandoffAttempt()
            let callback = try await authorize(attempt.browserURL)
            guard operation == identity else { throw ScoutAccessOAuthError.superseded }
            stage = "Guardian handoff exchange"
            let request = try attempt.exchangeRequest(callback: callback, ingress: ingress)
            let (data, response) = try await URLSession.scoutAuthenticated.data(for: request)
            guard operation == identity else { throw ScoutAccessOAuthError.superseded }
            guard let http = response as? HTTPURLResponse else { throw ScoutAccessOAuthError.invalidResponse }
            guard http.statusCode == 200 else {
                message = "Guardian handoff returned HTTP \(http.statusCode). No new account session was stored."
                return
            }
            let account = try ScoutAccountHandoffAttempt.decode(data, profile: profile)
            try store.save(account, for: profile)
            message = "Guardian account session stored in this connection's Keychain. Check account session to qualify a protected read."
        } catch {
            guard operation == identity else { return }
            message = (error as? ScoutRequestAuthenticationError)?.errorDescription ?? stage + " did not finish. No new account session was stored."
        }
    }

    func check(profile: ScoutEndpointProfile) async {
        guard !isWorking else { return }
        let identity = UUID(); operation = identity; isWorking = true
        defer { if operation == identity { isWorking = false } }
        let result = await ScoutGuardianThreadsProbe.probe(endpoint: profile)
        guard operation == identity else { return }
        if result.httpStatus == 200, result.threads != nil {
            message = "Guardian account-session protected read qualified. " + result.message
        } else { message = "Account-session protected read remains unqualified. " + result.message }
    }

    func logout(profile: ScoutEndpointProfile) async {
        guard !isWorking else { return }
        let identity = UUID(); operation = identity; isWorking = true
        defer { if operation == identity { isWorking = false } }
        do {
            var request = URLRequest(url: URL(string: try ScoutAccessOAuth.origin(for: profile))!.appendingPathComponent("api/auth/logout"))
            request.httpMethod = "POST"
            // Remove local authority even if ingress/session expiry prevents revocation.
            let preparation = Result { try ScoutRequestAuthentication.apply(to: &request, endpoint: profile, apiKey: nil) }
            try store.delete(for: profile)
            try preparation.get()
            let (_, response) = try await URLSession.scoutAuthenticated.data(for: request)
            guard operation == identity else { return }
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                message = "Account session removed locally. Guardian revocation was not confirmed; remote revocation remains unproven."
                return
            }
            message = "Guardian revocation accepted and account session removed from this connection's Keychain. Ingress authorization remains separate."
        } catch {
            guard operation == identity else { return }
            message = "Guardian logout did not finish. Remote revocation is unconfirmed; check local account status."
        }
    }
}
#endif
