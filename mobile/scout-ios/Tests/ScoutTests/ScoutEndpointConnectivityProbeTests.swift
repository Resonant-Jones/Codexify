import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import XCTest
@testable import Scout

final class ScoutEndpointConnectivityURLProtocol: URLProtocol {
    static var handler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    override class func canInit(with request: URLRequest) -> Bool {
        true
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
        guard let handler = Self.handler else {
            XCTFail("ScoutEndpointConnectivityURLProtocol handler was not configured")
            return
        }

        do {
            let (response, data) = try handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}

final class ScoutEndpointConnectivityProbeTests: XCTestCase {
    override func tearDown() {
        ScoutEndpointConnectivityURLProtocol.handler = nil
        super.tearDown()
    }

    func testValidGuardianHealthResponseIsVerifiedReachable() async {
        let result = await probe(body: guardianHealthBody())

        XCTAssertEqual(result.validationState, .reachable)
        XCTAssertEqual(result.authenticationState, .unconfigured)
        XCTAssertEqual(result.snapshot?.status, "ok")
        XCTAssertEqual(result.snapshot?.service, "core")
        XCTAssertEqual(result.snapshot?.timestamp, "2026-09-21T12:00:00+00:00")
        XCTAssertNotNil(result.connectedAt)
    }

    func testValidGuardianHealthWithoutAPIKeyDoesNotClaimAuthentication() async {
        let result = await probe(body: guardianHealthBody(), apiKey: nil)

        XCTAssertEqual(result.validationState, .reachable)
        XCTAssertEqual(result.authenticationState, .unconfigured)
    }

    func testValidGuardianHealthWithAPIKeyDoesNotClaimAuthenticationFromCredentialPresence() async {
        let apiKey = "local-operator-key"
        let result = await probe(body: guardianHealthBody(), apiKey: apiKey) { request in
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-API-Key"), apiKey)
        }

        XCTAssertEqual(result.validationState, .reachable)
        XCTAssertEqual(result.authenticationState, .unconfigured)
        XCTAssertNotEqual(result.authenticationState, .authenticated)
    }

    func testArbitraryHTMLSuccessIsNotVerified() async {
        let result = await probe(body: Data("<html><body>generic proxy</body></html>".utf8))

        assertUnverified(result)
    }

    func testLoginInterstitialHTMLSuccessIsNotVerified() async {
        let result = await probe(
            body: Data("<html><title>Sign in</title><body>Continue to login</body></html>".utf8)
        )

        assertUnverified(result)
    }

    func testMalformedJSONSuccessIsNotVerified() async {
        let result = await probe(body: Data(#"{"status":"ok""#.utf8))

        assertUnverified(result)
    }

    func testUnrelatedJSONSuccessIsNotVerified() async {
        let result = await probe(body: Data(#"{"status":"ok","service":"proxy"}"#.utf8))

        assertUnverified(result)
    }

    func testPartialGuardianHealthSuccessMissingDetailsIsNotVerified() async {
        let result = await probe(
            body: Data(
                #"{"status":"ok","service":"core","timestamp":"2026-09-21T12:00:00+00:00"}"#.utf8
            )
        )

        assertUnverified(result)
    }

    func testEmptySuccessBodyIsNotVerified() async {
        let result = await probe(body: Data())

        assertUnverified(result)
    }

    func testGuardianHealthBodyWithNonSuccessStatusIsNotVerified() async {
        let result = await probe(statusCode: 503, body: guardianHealthBody())

        XCTAssertEqual(result.validationState, .unreachable)
        XCTAssertNil(result.snapshot)
        XCTAssertNil(result.connectedAt)
    }

    func testTransportErrorPreservesFailClosedBehavior() async {
        let result = await probe(error: URLError(.cannotConnectToHost))

        XCTAssertEqual(result.validationState, .unreachable)
        XCTAssertNil(result.snapshot)
        XCTAssertNil(result.connectedAt)
        XCTAssertTrue(result.message.contains("Connection failed"))
    }

    private func probe(
        statusCode: Int = 200,
        body: Data,
        apiKey: String? = nil,
        inspectRequest: ((URLRequest) -> Void)? = nil
    ) async -> ScoutEndpointConnectivityResult {
        let session = makeSession()
        defer { session.invalidateAndCancel() }

        ScoutEndpointConnectivityURLProtocol.handler = { request in
            inspectRequest?(request)
            let response = HTTPURLResponse(
                url: try XCTUnwrap(request.url),
                statusCode: statusCode,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (response, body)
        }

        return await ScoutEndpointConnectivityProbe.probe(
            endpoint: makeEndpoint(),
            apiKey: apiKey,
            session: session
        )
    }

    private func probe(error: Error) async -> ScoutEndpointConnectivityResult {
        let session = makeSession()
        defer { session.invalidateAndCancel() }

        ScoutEndpointConnectivityURLProtocol.handler = { _ in
            throw error
        }

        return await ScoutEndpointConnectivityProbe.probe(
            endpoint: makeEndpoint(),
            session: session
        )
    }

    private func assertUnverified(
        _ result: ScoutEndpointConnectivityResult,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertEqual(result.validationState, .unreachable, file: file, line: line)
        XCTAssertEqual(result.authenticationState, .unconfigured, file: file, line: line)
        XCTAssertEqual(
            result.message,
            "Endpoint responded, but did not return a valid Guardian health response.",
            file: file,
            line: line
        )
        XCTAssertNil(result.snapshot, file: file, line: line)
        XCTAssertNil(result.connectedAt, file: file, line: line)
    }

    private func makeSession() -> URLSession {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [ScoutEndpointConnectivityURLProtocol.self]
        return URLSession(configuration: configuration)
    }

    private func makeEndpoint() -> ScoutEndpointProfile {
        ScoutEndpointProfile(
            id: UUID(),
            name: "Test Vault",
            baseURL: "https://vault.example.com",
            transportType: .tailscale,
            authenticationState: .unconfigured,
            validationState: .unconfigured,
            lastConnectedAt: nil
        )
    }

    private func guardianHealthBody() -> Data {
        Data(
            #"{"status":"ok","service":"core","timestamp":"2026-09-21T12:00:00+00:00","details":{}}"#.utf8
        )
    }
}
