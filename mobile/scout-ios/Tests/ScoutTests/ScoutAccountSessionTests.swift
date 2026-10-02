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

}
