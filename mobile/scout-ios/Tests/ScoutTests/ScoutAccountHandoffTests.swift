import Foundation
import XCTest
@testable import Scout

final class ScoutAccountHandoffTests: XCTestCase {
    private let verifier = String(repeating: "v", count: 43)
    private let state = String(repeating: "s", count: 43)
    private let code = String(repeating: "c", count: 43)
    private let admission = ScoutAccessOAuth.Credential(accessToken: "oauth:fixture-ingress", refreshToken: nil, expiresAt: .distantFuture)

    func testBrowserHandoffAndExchangeAreFixedOriginPkceBoundAndSingleUse() throws {
        var attempt = ScoutAccountHandoffAttempt(verifier: verifier, state: state)
        XCTAssertEqual(attempt.browserURL.host, "preview.codexify.space")
        let params = URLComponents(url: attempt.browserURL, resolvingAgainstBaseURL: false)!.queryItems!
        XCTAssertEqual(params.count, 2)
        XCTAssertFalse(attempt.browserURL.absoluteString.contains("scout_challenge=" + verifier))
        let callback = URL(string: ScoutAccessOAuth.callback.absoluteString + "?code=\(code)&state=\(state)")!
        let request = try attempt.exchangeRequest(callback: callback, ingress: admission)
        XCTAssertEqual(request.url?.absoluteString, "https://preview.codexify.space/api/auth/scout/exchange")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer oauth:fixture-ingress")
        XCTAssertNil(request.value(forHTTPHeaderField: "X-API-Key"))
        XCTAssertNil(request.value(forHTTPHeaderField: "X-Guardian-Account-Session"))
        XCTAssertEqual(try JSONDecoder().decode([String: String].self, from: request.httpBody!), ["code": code, "verifier": verifier])
        XCTAssertThrowsError(try attempt.exchangeRequest(callback: callback, ingress: admission))
    }

    func testWrongCallbackStateDuplicatesAndExtraMaterialFailClosed() {
        for raw in [
            "other://access-callback?code=\(code)&state=\(state)",
            ScoutAccessOAuth.callback.absoluteString + "?code=\(code)&state=wrong",
            ScoutAccessOAuth.callback.absoluteString + "?code=\(code)&state=\(state)&code=\(code)",
            ScoutAccessOAuth.callback.absoluteString + "?code=\(code)&state=\(state)&token=fixture",
            ScoutAccessOAuth.callback.absoluteString + "/path?code=\(code)&state=\(state)",
            ScoutAccessOAuth.callback.absoluteString + "?code=\(code)&state=\(state)#fragment"
        ] {
            var attempt = ScoutAccountHandoffAttempt(verifier: verifier, state: state)
            XCTAssertThrowsError(try attempt.exchangeRequest(callback: URL(string: raw)!, ingress: admission))
        }
    }

    func testCanonicalAccountFailureMarkerIsRequiredForInvalidation() {
        let url = URL(string: "https://preview.codexify.space/api/chat/threads")!
        for status in [200, 401, 403] {
            let ordinary = HTTPURLResponse(url: url, statusCode: status, httpVersion: nil, headerFields: nil)!
            XCTAssertFalse(ScoutRequestAuthentication.isInvalidAccountResponse(ordinary))
            let marked = HTTPURLResponse(url: url, statusCode: status, httpVersion: nil,
                headerFields: ["X-Guardian-Auth-Failure": "ACCOUNT_SESSION_INVALID"])!
            XCTAssertEqual(ScoutRequestAuthentication.isInvalidAccountResponse(marked), status == 401)
        }
    }
}
