import Foundation
import XCTest
@testable import Scout

final class ScoutIngressRenewalTests: XCTestCase {
    private func profile() -> ScoutEndpointProfile {
        ScoutEndpointProfile(id: UUID(), name: "Hosted", baseURL: "https://preview.codexify.space",
            transportType: .custom, authenticationState: .unconfigured, validationState: .unconfigured,
            lastConnectedAt: nil, authenticationMode: .remoteSession)
    }

    func testConcurrentExpiredRequestsShareOneRefreshAndStoreRotation() async throws {
        let old = ScoutAccessOAuth.Credential(accessToken: "old", refreshToken: "old-refresh", expiresAt: .distantPast)
        var current: ScoutAccessOAuth.Credential? = old
        var calls = 0
        let renewal = ScoutIngressRenewal(load: { _ in current }, replace: { next, previous, _ in
            guard current?.accessToken == previous.accessToken else { return false }
            current = next
            return true
        }, exchange: { request in
            calls += 1
            XCTAssertEqual(request.url, ScoutAccessOAuth.tokenEndpoint)
            try await Task.sleep(nanoseconds: 20_000_000)
            let data = Data(#"{"access_token":"new","token_type":"Bearer","expires_in":900,"refresh_token":"rotated"}"#.utf8)
            return (data, HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
        })
        let endpoint = profile()
        async let first = renewal.credential(for: endpoint)
        async let second = renewal.credential(for: endpoint)
        let results = try await [first, second]
        XCTAssertEqual(results.map(\.accessToken), ["new", "new"])
        XCTAssertEqual(current?.refreshToken, "rotated")
        XCTAssertEqual(calls, 1)
    }

    func testRevokedCredentialIsNotRestoredByDelayedRefresh() async throws {
        let old = ScoutAccessOAuth.Credential(accessToken: "old", refreshToken: "refresh", expiresAt: .distantPast)
        var current: ScoutAccessOAuth.Credential? = old
        let renewal = ScoutIngressRenewal(load: { _ in current }, replace: { next, previous, _ in
            guard current?.accessToken == previous.accessToken else { return false }
            current = next
            return true
        }, exchange: { request in
            current = nil
            return (Data(#"{"access_token":"new","token_type":"Bearer","expires_in":900}"#.utf8),
                HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
        })
        do {
            _ = try await renewal.credential(for: profile())
            XCTFail("A revoked credential must not be restored")
        } catch {
            XCTAssertEqual(error as? ScoutRequestAuthenticationError, .ingressRequired)
        }
        XCTAssertNil(current)
    }

    func testValidCredentialDoesNotMakeRefreshRequest() async throws {
        let valid = ScoutAccessOAuth.Credential(accessToken: "valid", refreshToken: "refresh", expiresAt: .distantFuture)
        let renewal = ScoutIngressRenewal(load: { _ in valid }, replace: { _, _, _ in XCTFail(); return false },
            exchange: { _ in XCTFail(); throw URLError(.badServerResponse) })
        let result = try await renewal.credential(for: profile())
        XCTAssertEqual(result.accessToken, "valid")
    }

    func testRefreshFailureDoesNotOverwriteSavedGrant() async throws {
        let old = ScoutAccessOAuth.Credential(accessToken: "old", refreshToken: "refresh", expiresAt: .distantPast)
        let renewal = ScoutIngressRenewal(load: { _ in old }, replace: { _, _, _ in XCTFail(); return false },
            exchange: { request in
                (Data(), HTTPURLResponse(url: request.url!, statusCode: 401, httpVersion: nil, headerFields: nil)!)
            })
        do {
            _ = try await renewal.credential(for: profile())
            XCTFail("Rejected refresh must not succeed")
        } catch {
            XCTAssertEqual(error as? ScoutRequestAuthenticationError, .ingressRequired)
        }
    }

    func testWrongOriginRemovesStaleHeadersBeforeDispatch() async throws {
        var request = URLRequest(url: URL(string: "https://other.example/api/chat/threads")!)
        request.setValue("old", forHTTPHeaderField: "Authorization")
        request.setValue("old", forHTTPHeaderField: "X-Guardian-Account-Session")
        do {
            try await ScoutRequestAuthentication.prepare(to: &request, endpoint: profile(), apiKey: nil)
            XCTFail("A wrong-origin request must fail")
        } catch {
            XCTAssertEqual(error as? ScoutRequestAuthenticationError, .wrongConnection)
        }
        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        XCTAssertNil(request.value(forHTTPHeaderField: "X-Guardian-Account-Session"))
    }
}
