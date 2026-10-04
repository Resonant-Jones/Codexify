import Foundation
import CryptoKit

struct ScoutAccountHandoffAttempt {
    private let verifier: String
    private let state: String
    private var consumed = false
    let qualificationID: UUID?

    init(qualificationID: UUID? = nil) throws {
        verifier = try ScoutAccessOAuth.randomValue(); state = try ScoutAccessOAuth.randomValue()
        self.qualificationID = qualificationID
    }
    init(verifier: String, state: String, qualificationID: UUID? = nil) {
        self.verifier = verifier; self.state = state; self.qualificationID = qualificationID
    }

    var browserURL: URL {
        var url = URLComponents(url: ScoutAccessOAuth.resource.appendingPathComponent("login"), resolvingAgainstBaseURL: false)!
        url.queryItems = [URLQueryItem(name: "scout_state", value: state), URLQueryItem(name: "scout_challenge",
            value: ScoutAccessOAuth.base64URL(Data(SHA256.hash(data: Data(verifier.utf8)))))]
        if let qualificationID { url.queryItems!.append(URLQueryItem(name: "scout_attempt", value: qualificationID.uuidString.lowercased())) }
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
        if let qualificationID { request.setValue(qualificationID.uuidString.lowercased(), forHTTPHeaderField: "X-Scout-Auth-Attempt") }
        request.timeoutInterval = 10
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
    @Published private(set) var qualification: ScoutAuthenticationQualification?
    private var receiptPoll: Task<Void, Never>?
    private var browser: ASWebAuthenticationSession?
    private var operation: UUID?
    private let store = ScoutAccountSessionStore()

    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.flatMap(\.windows).first(where: \.isKeyWindow) ?? ASPresentationAnchor()
    }

    func cancel() {
        operation = nil; receiptPoll?.cancel(); receiptPoll = nil
        browser?.cancel(); browser = nil; isWorking = false; message = nil
        qualification = nil
    }

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

    private func authorize(_ url: URL, didLaunch: () -> Void) async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(url: url, callbackURLScheme: ScoutAccessOAuth.callback.scheme) { callback, error in
                if let callback, error == nil { continuation.resume(returning: callback) }
                else { continuation.resume(throwing: ScoutAccessOAuthError.rejectedAuthorization) }
            }
            session.presentationContextProvider = self
            session.prefersEphemeralWebBrowserSession = false
            browser = session
            if session.start() { didLaunch() }
            else { browser = nil; continuation.resume(throwing: ScoutAccessOAuthError.rejectedAuthorization) }
        }
    }

    private func observe(_ stage: ScoutAuthenticationQualification.Stage, _ status: ScoutAuthenticationQualification.Status,
                         _ classification: ScoutAuthenticationQualification.Classification, http: Int? = nil) {
        qualification?.record(stage, status, classification, httpStatus: http)
    }

    private func readReceipt(ingress: ScoutAccessOAuth.Credential, identity: UUID) async {
        guard let evidence = qualification else { return }
        do {
            let (data, response) = try await URLSession.scoutAuthenticated.data(for: evidence.receiptRequest(ingress: ingress))
            guard operation == identity, !Task.isCancelled,
                  (response as? HTTPURLResponse)?.statusCode == 200 else {
                if operation == identity, !Task.isCancelled { qualification?.correlationLost() }
                return
            }
            let receipt = try JSONDecoder().decode(ScoutAuthenticationQualification.BackendReceipt.self, from: data)
            qualification?.merge(receipt)
        } catch {
            if operation == identity, !Task.isCancelled { qualification?.correlationLost() }
            // Missing runtime evidence is unobserved, never authentication failure.
        }
    }

    func signIn(profile: ScoutEndpointProfile) async {
        guard !isWorking else { return }
        let identity = UUID(); operation = identity; isWorking = true
        var stage = ScoutAuthenticationQualification.Stage.ingress
        defer {
            if operation == identity {
                receiptPoll?.cancel(); receiptPoll = nil; isWorking = false; browser = nil
            }
        }
        do {
            try ScoutAccessOAuth.requireHosted(profile)
            qualification = try ScoutAuthenticationQualification(profile: profile)
            let storedIngress = try ScoutAccessCredentialStore().load(for: profile)
            let availability = ScoutAuthenticationQualification.ingressAvailability(expiresAt: storedIngress?.expiresAt)
            observe(.ingress, availability.status, availability.classification)
            guard let ingress = storedIngress, availability.status == .passed else {
                message = availability.classification == .credentialExpired
                    ? "Stored ingress authorization has expired. Check stored ingress to renew the existing grant before Guardian sign-in."
                    : "No ingress credential is stored for this connection. Authorize hosted ingress before Guardian sign-in."
                return
            }
            stage = .browser
            // Register only a public UUID before asking the operator to sign in.
            let (receiptData, receiptResponse) = try await URLSession.scoutAuthenticated.data(for: qualification!.receiptRequest(ingress: ingress, begin: true))
            guard operation == identity else { return }
            guard (receiptResponse as? HTTPURLResponse)?.statusCode == 200 else {
                let http = receiptResponse as? HTTPURLResponse
                let classification = ScoutAuthenticationQualification.correlationFailure(data: receiptData, httpStatus: http?.statusCode,
                    rejection: http?.value(forHTTPHeaderField: "X-Scout-Qualification-Rejection"))
                observe(.browser, .failed, classification, http: http?.statusCode)
                message = "Runtime correlation is unavailable. Guardian browser login was not launched."
                return
            }
            let initialReceipt = try JSONDecoder().decode(ScoutAuthenticationQualification.BackendReceipt.self, from: receiptData)
            guard initialReceipt.attempt_id == qualification?.publicID else { throw ScoutAccessOAuthError.invalidResponse }
            qualification?.merge(initialReceipt)
            var attempt = try ScoutAccountHandoffAttempt(qualificationID: qualification!.attemptID)
            stage = .browser
            message = "Sign in with your existing Guardian account, then choose Continue to Scout."
            receiptPoll = Task { [weak self] in
                for _ in 0..<300 {
                    guard !Task.isCancelled, let self, self.operation == identity else { return }
                    await self.readReceipt(ingress: ingress, identity: identity)
                    try? await Task.sleep(nanoseconds: 2_000_000_000)
                }
            }
            let callback = try await authorize(attempt.browserURL) { self.observe(.browser, .passed, .confirmed) }
            guard operation == identity else { return }
            observe(.callback, .passed, .confirmed)
            await readReceipt(ingress: ingress, identity: identity)
            guard operation == identity else { return }
            stage = .state
            let request = try attempt.exchangeRequest(callback: callback, ingress: ingress)
            observe(.state, .passed, .confirmed)
            stage = .exchange
            let (data, response) = try await URLSession.scoutAuthenticated.data(for: request)
            guard operation == identity else { return }
            guard let http = response as? HTTPURLResponse else { throw ScoutAccessOAuthError.invalidResponse }
            guard http.statusCode == 200 else {
                observe(.exchange, .failed, .rejected, http: http.statusCode)
                message = "Guardian handoff exchange failed. See authentication qualification."
                return
            }
            observe(.accountLogin, .passed, .confirmed, http: 200)
            observe(.exchange, .passed, .confirmed, http: 200)
            stage = .nativeSession
            guard http.value(forHTTPHeaderField: "X-Scout-Native-Session-Issued") == "true" else {
                observe(.nativeSession, .failed, .invalidReply)
                message = "Fresh native session issuance was not confirmed."
                return
            }
            let account = try ScoutAccountHandoffAttempt.decode(data, profile: profile)
            observe(.nativeSession, .passed, .confirmed)
            stage = .keychain
            try store.save(account, for: profile)
            guard let persisted = try store.load(for: profile) else { throw ScoutRequestAuthenticationError.sessionRequired }
            try persisted.validate(for: profile)
            guard persisted.token == account.token, persisted.userID == account.userID,
                  persisted.expiresAt == account.expiresAt else { throw ScoutRequestAuthenticationError.invalidSession }
            observe(.keychain, .passed, .confirmed)
            stage = .protectedRead
            await qualifyProtectedRead(profile: profile, identity: identity)
        } catch {
            guard operation == identity else { return }
            let classification: ScoutAuthenticationQualification.Classification
            if stage == .state { classification = .invalidCallback }
            else if stage == .ingress || stage == .keychain { classification = .storageFailure }
            else if error is DecodingError { classification = .invalidReply }
            else if error as? ScoutAccessOAuthError == .rejectedAuthorization { classification = .cancelled }
            else { classification = .transportFailure }
            observe(stage, .failed, classification)
            message = "Guardian sign-in did not finish. See authentication qualification for the first unqualified stage."
        }
    }

    private func qualifyProtectedRead(profile: ScoutEndpointProfile, identity: UUID) async {
        do {
            let request = try ScoutAuthenticationQualification.protectedRequest(profile: profile, identity: qualification?.attemptID ?? UUID())
            let (data, response) = try await URLSession.scoutAuthenticated.data(for: request)
            guard operation == identity else { return }
            guard let http = response as? HTTPURLResponse else { throw ScoutAccessOAuthError.invalidResponse }
            if ScoutRequestAuthentication.isInvalidAccountResponse(http) {
                try? ScoutRequestAuthentication.validate(response: http, endpoint: profile, request: request)
                observe(.protectedRead, .failed, .invalidSession, http: http.statusCode)
                message = "Guardian rejected the native account session. Sign in again."
                return
            }
            guard http.statusCode == 200 else {
                observe(.protectedRead, .failed, .rejected, http: http.statusCode)
                message = "Native account session stored; protected Guardian read failed."
                return
            }
            let threads = try JSONDecoder().decode(ScoutChatThreadsResponse.self, from: data)
            guard threads.threads != nil else { throw ScoutAccessOAuthError.invalidResponse }
            observe(.protectedRead, .passed, .confirmed, http: 200)
            message = qualification?.firstUnqualifiedStage == nil
                ? "All nine authentication stages qualified. Protected Guardian thread read succeeded."
                : "Stored account protected read succeeded; this sign-in attempt still has unqualified stages."
        } catch {
            guard operation == identity else { return }
            let classification: ScoutAuthenticationQualification.Classification = error is DecodingError ? .invalidReply
                : (error is ScoutRequestAuthenticationError ? .invalidSession : .transportFailure)
            observe(.protectedRead, .failed, classification)
            message = "Native protected read is unqualified. See authentication qualification."
        }
    }

    func check(profile: ScoutEndpointProfile) async {
        guard !isWorking else { return }
        let identity = UUID(); operation = identity; isWorking = true
        defer { if operation == identity { isWorking = false } }
        if qualification?.result(for: .keychain).status == .passed {
            await qualifyProtectedRead(profile: profile, identity: identity)
            return
        }
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
