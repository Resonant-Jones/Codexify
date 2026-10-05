import Foundation
import XCTest
@testable import Scout

final class ScoutAccountSessionTests: XCTestCase {
    private let now = Date(timeIntervalSince1970: 100)

    private func profile(_ url: String = "https://personal.example", id: UUID = UUID()) -> ScoutEndpointProfile {
        ScoutEndpointProfile(id: id, name: "Node", baseURL: url, transportType: .custom,
            authenticationState: .unconfigured, validationState: .unconfigured, lastConnectedAt: nil,
            authenticationMode: .remoteSession)
    }

    private func credential(_ profile: ScoutEndpointProfile, expiry: Date? = nil) throws -> ScoutAccountSession {
        ScoutAccountSession(token: "fixture-account", userID: "fixture-user", expiresAt: expiry ?? now.addingTimeInterval(60),
            profileID: profile.id, origin: try ScoutAccessOAuth.origin(for: profile))
    }

    private func hostedLogout() -> URLRequest {
        var request = URLRequest(url: ScoutAccessOAuth.resource.appendingPathComponent("api/auth/logout"))
        request.httpMethod = "POST"
        request.setValue("Bearer oauth:fixture-ingress", forHTTPHeaderField: "Authorization")
        request.setValue("fixture-account", forHTTPHeaderField: "X-Guardian-Account-Session")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = Data("{}".utf8)
        return request
    }

    func testHostedRevocationReplayStaysAtItsOriginWithoutRestoringOrChangingCredentials() throws {
        let logout = hostedLogout()
        let probe = try ScoutHostedLogoutProof.request(from: logout, profile: profile(ScoutAccessOAuth.resource.absoluteString))
        XCTAssertEqual(probe.url, ScoutAccessOAuth.resource.appendingPathComponent("api/chat/threads"))
        XCTAssertEqual(probe.httpMethod, "GET")
        XCTAssertNil(probe.httpBody)
        XCTAssertNil(probe.value(forHTTPHeaderField: "Content-Type"))
        XCTAssertEqual(probe.value(forHTTPHeaderField: "Authorization"), logout.value(forHTTPHeaderField: "Authorization"))
        XCTAssertEqual(probe.value(forHTTPHeaderField: "X-Guardian-Account-Session"), logout.value(forHTTPHeaderField: "X-Guardian-Account-Session"))
        XCTAssertEqual(logout.httpMethod, "POST")
        XCTAssertNil(probe.value(forHTTPHeaderField: "X-API-Key"))
    }

    func testHostedRevocationReplayRejectsPersonalOriginsMissingSessionsAndMixedSelectors() {
        let hosted = profile(ScoutAccessOAuth.resource.absoluteString)
        XCTAssertThrowsError(try ScoutHostedLogoutProof.request(from: hostedLogout(), profile: profile()))
        for header in ["X-API-Key", "X-Guardian-Key", "Cookie"] {
            var logout = hostedLogout()
            logout.setValue("fixture-conflict", forHTTPHeaderField: header)
            XCTAssertThrowsError(try ScoutHostedLogoutProof.request(from: logout, profile: hosted))
        }
        for header in ["Authorization", "X-Guardian-Account-Session"] {
            var logout = hostedLogout()
            logout.setValue(nil, forHTTPHeaderField: header)
            XCTAssertThrowsError(try ScoutHostedLogoutProof.request(from: logout, profile: hosted))
        }
        var wrongOrigin = hostedLogout()
        wrongOrigin.url = URL(string: "https://other.example/api/auth/logout")!
        XCTAssertThrowsError(try ScoutHostedLogoutProof.request(from: wrongOrigin, profile: hosted))
    }

    func testPostLogoutDenialRequiresVerifiedHostedAdmissionAtTheExactRead() {
        let url = ScoutAccessOAuth.resource.appendingPathComponent("api/chat/threads")
        let failure = "ACCOUNT_SESSION_INVALID"
        for admission in ["edge-consumed", "opaque-forwarded"] {
            let headers = ["X-Guardian-Auth-Failure": failure, "X-Scout-Access-Admission": admission]
            XCTAssertTrue(ScoutHostedLogoutProof.verifiedDenial(HTTPURLResponse(url: url, statusCode: 401, httpVersion: nil, headerFields: headers)!))
            for status in [200, 400, 403] {
                XCTAssertFalse(ScoutHostedLogoutProof.verifiedDenial(HTTPURLResponse(url: url, statusCode: status, httpVersion: nil, headerFields: headers)!))
            }
            XCTAssertFalse(ScoutHostedLogoutProof.verifiedDenial(HTTPURLResponse(url: URL(string: "https://other.example/api/chat/threads")!, statusCode: 401, httpVersion: nil, headerFields: headers)!))
            // Preview eligibility can deny a revoked session without the general
            // invalidation marker. This bounded check does not change that policy.
            XCTAssertTrue(ScoutHostedLogoutProof.verifiedDenial(HTTPURLResponse(url: url, statusCode: 401, httpVersion: nil,
                headerFields: ["X-Scout-Access-Admission": admission])!))
        }
        for headers in [[:], ["X-Guardian-Auth-Failure": failure],
                        ["X-Guardian-Auth-Failure": failure, "X-Scout-Access-Admission": "unqualified"]] {
            XCTAssertFalse(ScoutHostedLogoutProof.verifiedDenial(HTTPURLResponse(url: url, statusCode: 401, httpVersion: nil, headerFields: headers)!))
        }
    }

    func testPersonalSessionUsesOnlyCanonicalBearer() throws {
        let p = profile()
        var request = URLRequest(url: URL(string: p.baseURL + "/api/chat/threads")!)
        request.setValue("fixture-stale", forHTTPHeaderField: "X-Guardian-Account-Session")
        try ScoutRequestAuthentication.apply(to: &request, endpoint: p, apiKey: "fixture-key",
            accountSession: credential(p), now: now)
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer fixture-account")
        XCTAssertNil(request.value(forHTTPHeaderField: "X-API-Key"))
        XCTAssertNil(request.value(forHTTPHeaderField: "X-Guardian-Account-Session"))
    }

    func testHostedCompositionKeepsCredentialsSeparate() throws {
        let p = profile("https://preview.codexify.space")
        var request = URLRequest(url: URL(string: p.baseURL + "/api/chat/threads")!)
        try ScoutRequestAuthentication.apply(to: &request, endpoint: p, apiKey: "fixture-key",
            accountSession: credential(p), ingress: .init(accessToken: "oauth:fixture-ingress", refreshToken: nil,
                expiresAt: now.addingTimeInterval(60)), now: now)
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer oauth:fixture-ingress")
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-Guardian-Account-Session"), "fixture-account")
        XCTAssertNil(request.value(forHTTPHeaderField: "X-API-Key"))
    }

    func testExpiredSessionAndProfileSwitchFailBeforeCredentialAttachment() throws {
        let p = profile()
        for (target, session, expected) in [
            (p, try credential(p, expiry: now), ScoutRequestAuthenticationError.expiredSession),
            (profile(id: UUID()), try credential(p), .wrongConnection),
            (profile("https://other.example", id: p.id), try credential(p), .wrongConnection)
        ] {
            var request = URLRequest(url: URL(string: target.baseURL + "/api/chat/threads")!)
            XCTAssertThrowsError(try ScoutRequestAuthentication.apply(to: &request, endpoint: target, apiKey: "fixture-key",
                accountSession: session, now: now)) { XCTAssertEqual($0 as? ScoutRequestAuthenticationError, expected) }
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            XCTAssertNil(request.value(forHTTPHeaderField: "X-API-Key"))
            XCTAssertNil(request.value(forHTTPHeaderField: "X-Guardian-Account-Session"))
        }
    }

    func testWrongOriginRequestsNeverReceiveAccountCredentials() throws {
        let p = profile()
        for url in ["https://other.example/api", "http://personal.example/api", "https://personal.example:444/api", "https://user:password@personal.example/api"] {
            var request = URLRequest(url: URL(string: url)!)
            XCTAssertThrowsError(try ScoutRequestAuthentication.apply(to: &request, endpoint: p, apiKey: nil,
                accountSession: credential(p), now: now)) { XCTAssertEqual($0 as? ScoutRequestAuthenticationError, .wrongConnection) }
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        }
    }

    func testExpiredIngressCannotFallBackToAccountBearerOnHostedNode() throws {
        let p = profile("https://preview.codexify.space")
        var request = URLRequest(url: URL(string: p.baseURL + "/api/chat/threads")!)
        XCTAssertThrowsError(try ScoutRequestAuthentication.apply(to: &request, endpoint: p, apiKey: "fixture-key",
            accountSession: credential(p), ingress: .init(accessToken: "oauth:fixture", refreshToken: nil, expiresAt: now), now: now)) {
            XCTAssertEqual($0 as? ScoutRequestAuthenticationError, .ingressRequired)
        }
        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        XCTAssertNil(request.value(forHTTPHeaderField: "X-API-Key"))
        XCTAssertNil(request.value(forHTTPHeaderField: "X-Guardian-Account-Session"))
    }
    func testLocalKeySlotsAreIsolatedByProfileAndOrigin() throws {
        let a = profile()
        XCTAssertNotEqual(try ScoutKeychainStore.credentialAccount(for: a),
            try ScoutKeychainStore.credentialAccount(for: profile(id: UUID())))
        XCTAssertNotEqual(try ScoutKeychainStore.credentialAccount(for: a),
            try ScoutKeychainStore.credentialAccount(for: profile("https://other.example", id: a.id)))
        var local = a
        local.authenticationMode = .localAPIKey
        var request = URLRequest(url: URL(string: "https://other.example/api")!)
        XCTAssertThrowsError(try ScoutRequestAuthentication.apply(to: &request, endpoint: local, apiKey: "fixture-key"))
        XCTAssertNil(request.value(forHTTPHeaderField: "X-API-Key"))
    }

    func testPersonalBasePathKeepsCanonicalTransportAndHostedBasePathIsRejected() throws {
        let p = profile("https://personal.example/codexify")
        XCTAssertEqual(try ScoutAccessOAuth.origin(for: p), "https://personal.example")
        var request = URLRequest(url: URL(string: p.baseURL)!.appendingPathComponent("api/chat/threads"))
        try ScoutRequestAuthentication.apply(to: &request, endpoint: p, apiKey: nil, accountSession: credential(p), now: now)
        XCTAssertEqual(request.url?.path, "/codexify/api/chat/threads")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer fixture-account")
        var local = p
        local.authenticationMode = .localAPIKey
        try ScoutRequestAuthentication.apply(to: &request, endpoint: local, apiKey: "fixture-key")
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-API-Key"), "fixture-key")
        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        let hosted = profile("https://preview.codexify.space/codexify")
        XCTAssertFalse(ScoutAccessOAuth.supportsAccountSignIn(hosted))
        XCTAssertThrowsError(try ScoutAccessOAuth.requireHosted(hosted))
        var denied = URLRequest(url: URL(string: hosted.baseURL + "/api/chat/threads")!)
        XCTAssertThrowsError(try ScoutRequestAuthentication.apply(to: &denied, endpoint: hosted, apiKey: nil,
            accountSession: credential(hosted), ingress: .init(accessToken: "oauth:fixture", refreshToken: nil,
                expiresAt: now.addingTimeInterval(60)), now: now))
        XCTAssertNil(denied.value(forHTTPHeaderField: "Authorization"))
        XCTAssertNil(denied.value(forHTTPHeaderField: "X-Guardian-Account-Session"))
    }

    func testLateRejectionPreservesReplacementSessionAndOnlyDeletesMatchingSession() throws {
        let p = profile()
        var current: ScoutAccountSession? = try credential(p)
        var deletions = 0
        let remove = { current = nil; deletions += 1 }
        XCTAssertFalse(try ScoutAccountSessionStore.deleteIfMatching("fixture-old", load: { current }, remove: remove))
        XCTAssertEqual(current?.token, "fixture-account")
        XCTAssertEqual(deletions, 0)
        XCTAssertTrue(try ScoutAccountSessionStore.deleteIfMatching("fixture-account", load: { current }, remove: remove))
        XCTAssertNil(current)
        XCTAssertEqual(deletions, 1)
        XCTAssertFalse(try ScoutAccountSessionStore.deleteIfMatching("fixture-account", load: { current }, remove: remove))
        XCTAssertEqual(deletions, 1)
    }

    func testRejectedTokenSelectionNeverConfusesIngressWithAccount() {
        let hosted = hostedLogout()
        XCTAssertEqual(ScoutRequestAuthentication.selectedAccountToken(in: hosted, hosted: true), "fixture-account")
        var personal = hosted
        personal.setValue("Bearer fixture-personal-account", forHTTPHeaderField: "Authorization")
        personal.setValue(nil, forHTTPHeaderField: "X-Guardian-Account-Session")
        XCTAssertEqual(ScoutRequestAuthentication.selectedAccountToken(in: personal, hosted: false), "fixture-personal-account")
        XCTAssertNil(ScoutRequestAuthentication.selectedAccountToken(in: personal, hosted: true))
    }

}
