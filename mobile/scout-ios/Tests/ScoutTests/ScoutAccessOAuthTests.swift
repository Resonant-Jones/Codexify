import Foundation
import XCTest
@testable import Scout

final class ScoutAccessOAuthTests: XCTestCase {
    private func profile(_ url: String = "https://preview.codexify.space", id: UUID = UUID(),
                         mode: ScoutEndpointAuthenticationMode = .remoteSession) -> ScoutEndpointProfile {
        ScoutEndpointProfile(id: id, name: "Test", baseURL: url, transportType: .custom,
            authenticationState: .unconfigured, validationState: .unconfigured,
            lastConnectedAt: nil, authenticationMode: mode)
    }

    func testAuthorizationUsesS256AndExactResourceWithoutSecret() throws {
        let attempt = ScoutAccessOAuth.Attempt(verifier: "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk", state: "test-state")
        let items = URLComponents(url: attempt.authorizationURL, resolvingAgainstBaseURL: false)!.queryItems!
        let values = Dictionary(uniqueKeysWithValues: items.map { ($0.name, $0.value!) })
        XCTAssertEqual(values["code_challenge_method"], "S256")
        XCTAssertEqual(values["code_challenge"], "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
        XCTAssertEqual(values["redirect_uri"], ScoutAccessOAuth.callback.absoluteString)
        XCTAssertEqual(values["resource"], "https://preview.codexify.space")
        XCTAssertNil(values["code_verifier"])
        XCTAssertNil(values["client_secret"])
    }

    func testCallbackIsExactStateBoundAndSingleUse() throws {
        var attempt = ScoutAccessOAuth.Attempt(verifier: String(repeating: "a", count: 43), state: "test-state")
        let callback = URL(string: "ai.resonantconstructs.codexify.scout://access-callback?code=fixture&state=test-state")!
        let request = try attempt.exchangeRequest(callbackURL: callback)
        XCTAssertEqual(request.url, ScoutAccessOAuth.tokenEndpoint)
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertNil(request.value(forHTTPHeaderField: "X-API-Key"))
        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        XCTAssertTrue(String(data: request.httpBody!, encoding: .utf8)!.contains("code_verifier="))
        XCTAssertThrowsError(try attempt.exchangeRequest(callbackURL: callback))
    }

    func testWrongCallbackStateDuplicateAndErrorFailClosed() {
        let urls = [
            "other://access-callback?code=fixture&state=test-state",
            "ai.resonantconstructs.codexify.scout://wrong?code=fixture&state=test-state",
            "ai.resonantconstructs.codexify.scout://access-callback/path?code=fixture&state=test-state",
            "ai.resonantconstructs.codexify.scout://access-callback?code=fixture&state=wrong",
            "ai.resonantconstructs.codexify.scout://access-callback?code=fixture&state=test-state&state=test-state",
            "ai.resonantconstructs.codexify.scout://access-callback?code=one&code=two&state=test-state",
            "ai.resonantconstructs.codexify.scout://access-callback?code=fixture&state=test-state#error",
            "ai.resonantconstructs.codexify.scout://access-callback?code=fixture&state=test-state&error=denied"
        ]
        for url in urls {
            var attempt = ScoutAccessOAuth.Attempt(verifier: "fixture-verifier", state: "test-state")
            XCTAssertThrowsError(try attempt.exchangeRequest(callbackURL: URL(string: url)!))
        }
    }

    func testCredentialScopeSeparatesProfilesAndOrigins() throws {
        let id = UUID()
        let scope = try ScoutAccessOAuth.credentialAccount(for: profile(id: id))
        XCTAssertEqual(scope, try ScoutAccessOAuth.credentialAccount(for: profile("https://preview.codexify.space:443/", id: id)))
        XCTAssertNotEqual(scope, try ScoutAccessOAuth.credentialAccount(for: profile(id: UUID())))
        XCTAssertNotEqual(scope, try ScoutAccessOAuth.credentialAccount(for: profile("https://personal.example", id: id)))
        XCTAssertNotEqual(scope, try ScoutAccessOAuth.credentialAccount(for: profile("https://preview.codexify.space:444", id: id)))
    }

    func testHostedFlowRejectsLocalModeWrongOriginAndCredentialURLs() {
        for p in [profile(mode: .localAPIKey), profile("https://personal.example"),
                  profile("https://preview.codexify.space.attacker.example"),
                  profile("http://preview.codexify.space"), profile("https://user:password@preview.codexify.space"),
                  profile("https://preview.codexify.space/path"), profile("https://preview.codexify.space?next=other")] {
            XCTAssertThrowsError(try ScoutAccessOAuth.requireHosted(p))
        }
    }

    func testTokenValidationAndExpiryAreDistinctFromGuardianSession() throws {
        let data = Data(#"{"access_token":"fixture-ingress-token","token_type":"Bearer","expires_in":900,"refresh_token":"fixture-refresh"}"#.utf8)
        let now = Date(timeIntervalSince1970: 10)
        let credential = try ScoutAccessOAuth.Credential.decode(data, now: now)
        XCTAssertEqual(credential.expiresAt, now.addingTimeInterval(900))
        for body in [#"{"access_token":"","token_type":"Bearer","expires_in":900}"#,
                     #"{"access_token":"fixture","token_type":"Basic","expires_in":900}"#,
                     #"{"access_token":"fixture","token_type":"Bearer","expires_in":0}"#] {
            XCTAssertThrowsError(try ScoutAccessOAuth.Credential.decode(Data(body.utf8)))
        }
        var request = URLRequest(url: ScoutAccessOAuth.resource)
        XCTAssertThrowsError(try ScoutRequestAuthentication.apply(to: &request, endpoint: profile(), apiKey: credential.accessToken))
        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        XCTAssertNil(request.value(forHTTPHeaderField: "X-API-Key"))
    }

    func testNoCredentialRequestFollowsRedirect() {
        let delegate = ScoutAuthNoRedirect()
        let session = URLSession(configuration: .ephemeral)
        defer { session.invalidateAndCancel() }
        let task = session.dataTask(with: ScoutAccessOAuth.tokenEndpoint)
        let response = HTTPURLResponse(url: ScoutAccessOAuth.tokenEndpoint, statusCode: 302, httpVersion: nil,
            headerFields: ["Location": "https://other.example"])!
        var called = false
        delegate.urlSession(session, task: task, willPerformHTTPRedirection: response,
            newRequest: URLRequest(url: URL(string: "https://other.example")!)) { redirected in
            called = true
            XCTAssertNil(redirected)
        }
        XCTAssertTrue(called)
    }

    func testRefreshUsesExistingPublicClientAndRejectsOtherConnections() throws {
        let credential = ScoutAccessOAuth.Credential(accessToken: "fixture", refreshToken: "fixture-refresh", expiresAt: .distantPast)
        let request = try ScoutAccessOAuth.refreshRequest(credential: credential, profile: profile())
        XCTAssertEqual(request.url, ScoutAccessOAuth.tokenEndpoint)
        XCTAssertEqual(request.httpMethod, "POST")
        let body = String(data: request.httpBody!, encoding: .utf8)!
        XCTAssertTrue(body.contains("grant_type=refresh_token"))
        XCTAssertTrue(body.contains("resource=https%3A%2F%2Fpreview.codexify.space"))
        XCTAssertFalse(body.contains("client_secret"))
        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        XCTAssertNil(request.value(forHTTPHeaderField: "X-API-Key"))
        XCTAssertThrowsError(try ScoutAccessOAuth.refreshRequest(credential: credential, profile: profile("https://personal.example")))
        XCTAssertThrowsError(try ScoutAccessOAuth.refreshRequest(credential: credential, profile: profile(mode: .localAPIKey)))
        for token in [nil, ""] as [String?] {
            XCTAssertThrowsError(try ScoutAccessOAuth.refreshRequest(credential: .init(accessToken: "fixture", refreshToken: token, expiresAt: .distantPast), profile: profile()))
        }
    }

    func testRefreshRotationAndOmittedRefreshToken() throws {
        let body = Data(#"{"access_token":"fixture-new","token_type":"Bearer","expires_in":900}"#.utf8)
        XCTAssertEqual(try ScoutAccessOAuth.Credential.decode(body, retainingRefreshToken: "fixture-old").refreshToken, "fixture-old")
        let rotated = Data(#"{"access_token":"fixture-new","token_type":"Bearer","expires_in":900,"refresh_token":"fixture-rotated"}"#.utf8)
        XCTAssertEqual(try ScoutAccessOAuth.Credential.decode(rotated, retainingRefreshToken: "fixture-old").refreshToken, "fixture-rotated")
        let empty = Data(#"{"access_token":"fixture-new","token_type":"Bearer","expires_in":900,"refresh_token":""}"#.utf8)
        XCTAssertThrowsError(try ScoutAccessOAuth.Credential.decode(empty, retainingRefreshToken: "fixture-old"))
    }

    func testRandomVerifierLengthAndEncoding() throws {
        let first = try ScoutAccessOAuth.randomValue()
        let second = try ScoutAccessOAuth.randomValue()
        XCTAssertEqual(first.count, 43)
        XCTAssertNotEqual(first, second)
        XCTAssertNil(first.rangeOfCharacter(from: CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_").inverted))
    }
}
