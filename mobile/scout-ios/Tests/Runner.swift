import Foundation

// ── Mock URLProtocol ──────────────────────────────────────────────

var _mockHandler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

final class MockURLProtocol: URLProtocol {
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func stopLoading() {}

    override func startLoading() {
        guard let handler = _mockHandler else {
            fatalError("MockURLProtocol handler not set")
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
}

// ── Helpers ───────────────────────────────────────────────────────

func makeSession() -> URLSession {
    let config = URLSessionConfiguration.ephemeral
    config.protocolClasses = [MockURLProtocol.self]
    return URLSession(configuration: config)
}

func makeEndpoint(baseURL: String = "https://vault.example.com") -> ScoutEndpointProfile {
    ScoutEndpointProfile(
        id: UUID(),
        name: "Test Vault",
        baseURL: baseURL,
        transportType: .tailscale,
        authenticationState: .unconfigured,
        validationState: .unconfigured,
        lastConnectedAt: nil
    )
}

func healthBody(status: String = "ok", service: String = "core") -> Data {
    """
    {"status":"\(status)","service":"\(service)","timestamp":"2024-01-01T00:00:00Z"}
    """.data(using: .utf8)!
}

// ── Test runner ───────────────────────────────────────────────────

@main
struct ScoutTestRunner {
    static func main() async {
        var passed = 0
        var failed = 0

        func check(_ name: String, _ condition: Bool, _ detail: String = "") {
            if condition {
                passed += 1
                print("  PASS  \(name)")
            } else {
                failed += 1
                print("  FAIL  \(name)\(detail.isEmpty ? "" : " — \(detail)")")
            }
        }

        // ── Header attachment ──────────────────────────────────────

        do {
            let session = makeSession()
            let endpoint = makeEndpoint()
            let key = "test-api-key-abc"
            _mockHandler = { request in
                check("header set correctly", request.value(forHTTPHeaderField: "X-API-Key") == key)
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, healthBody())
            }
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: endpoint, apiKey: key, session: session
            )
            check("validationState == .reachable", result.validationState == .reachable)
            check("authenticationState == .authenticated", result.authenticationState == .authenticated)
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                check("no X-API-Key header (nil key)", request.value(forHTTPHeaderField: "X-API-Key") == nil)
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, healthBody())
            }
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("authenticationState == .unconfigured", result.authenticationState == .unconfigured)
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                check("no X-API-Key header (whitespace)", request.value(forHTTPHeaderField: "X-API-Key") == nil)
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, healthBody())
            }
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(), apiKey: "   ", session: session
            )
            check("whitespace key → .unconfigured", result.authenticationState == .unconfigured)
        }

        // ── Status code interpretation ─────────────────────────────

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, healthBody())
            }
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(), apiKey: "key", session: session
            )
            check("2xx+key → .reachable", result.validationState == .reachable)
            check("2xx+key → .authenticated", result.authenticationState == .authenticated)
            check("2xx+key → connectedAt set", result.connectedAt != nil)
            check("2xx+key → 'authenticated' in message", result.message.contains("authenticated"))
            check("2xx+key → latency non-nil", result.latencyMilliseconds != nil)
            check("2xx+key → latency >= 0", (result.latencyMilliseconds ?? -1) >= 0)
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, healthBody())
            }
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("2xx no key → .reachable", result.validationState == .reachable)
            check("2xx no key → .unconfigured", result.authenticationState == .unconfigured)
            check("2xx no key → 'no API key' in message", result.message.contains("no API key"))
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 401, httpVersion: nil, headerFields: nil)!
                return (r, Data())
            }
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(), apiKey: "wrong", session: session
            )
            check("401 → .reachable", result.validationState == .reachable)
            check("401 → .authRequired", result.authenticationState == .authRequired)
            check("401 → connectedAt set", result.connectedAt != nil)
            check("401 → 'authentication is required' in msg",
                  result.message.contains("authentication is required"))
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 403, httpVersion: nil, headerFields: nil)!
                return (r, Data())
            }
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("403 → .reachable", result.validationState == .reachable)
            check("403 → .authRequired", result.authenticationState == .authRequired)
        }

        // ── Error handling ─────────────────────────────────────────

        do {
            let session = makeSession()
            _mockHandler = { _ in throw URLError(.timedOut) }
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("timeout → .unreachable", result.validationState == .unreachable)
            check("timeout → 'timed out' in msg", result.message.contains("timed out"))
            check("timeout → connectedAt nil", result.connectedAt == nil)
            check("timeout → latency nil", result.latencyMilliseconds == nil)
        }

        do {
            let session = makeSession()
            _mockHandler = { _ in throw URLError(.cannotConnectToHost) }
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("transport error → .unreachable", result.validationState == .unreachable)
            check("transport error → 'Connection failed' in msg",
                  result.message.contains("Connection failed"))
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 500, httpVersion: nil, headerFields: nil)!
                return (r, Data())
            }
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("500 → .unreachable", result.validationState == .unreachable)
            check("500 → 'unexpected status' in msg", result.message.contains("unexpected status"))
        }

        // ── Snapshot parsing ───────────────────────────────────────

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, healthBody(status: "ok", service: "core"))
            }
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(), apiKey: "key", session: session
            )
            check("snapshot not nil on 2xx", result.snapshot != nil)
            check("snapshot.status == 'ok'", result.snapshot?.status == "ok")
            check("snapshot.service == 'core'", result.snapshot?.service == "core")
            check("snapshot.timestamp set", result.snapshot?.timestamp == "2024-01-01T00:00:00Z")
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 401, httpVersion: nil, headerFields: nil)!
                return (r, Data())
            }
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("snapshot nil on 401", result.snapshot == nil)
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, "not json".data(using: .utf8)!)
            }
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("malformed JSON → .reachable", result.validationState == .reachable)
            check("malformed JSON → snapshot nil", result.snapshot == nil)
        }

        // ── URL validation ─────────────────────────────────────────

        do {
            let session = makeSession()
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(baseURL: "://"), apiKey: nil, session: session
            )
            check("malformed URL → .invalidConfiguration",
                  result.validationState == .invalidConfiguration)
            check("malformed URL → 'Malformed' in msg", result.message.contains("Malformed"))
        }

        do {
            let session = makeSession()
            let result = await ScoutEndpointConnectivityProbe.probe(
                endpoint: makeEndpoint(baseURL: ""), apiKey: nil, session: session
            )
            check("empty URL → .invalidConfiguration",
                  result.validationState == .invalidConfiguration)
            check("empty URL → 'empty' in msg", result.message.contains("empty"))
            check("empty URL → latency nil", result.latencyMilliseconds == nil)
        }

        // ── Summary ────────────────────────────────────────────────

        print("\n\(passed) passed, \(failed) failed")
        exit(failed > 0 ? 1 : 0)
    }
}
