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

        // ── LLM health probe ──────────────────────────────────────

        func llmBody() -> Data {
            """
            {"status":"ok","service":"llm","timestamp":"2024-01-01T00:00:00Z","provider":"local","model":"gemma2:2b"}
            """.data(using: .utf8)!
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                check("LLM probe has X-API-Key", request.value(forHTTPHeaderField: "X-API-Key") == "key")
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, llmBody())
            }
            let result = await ScoutLLMHealthProbe.probe(
                endpoint: makeEndpoint(), apiKey: "key", session: session
            )
            check("LLM 2xx → httpStatus 200", result.httpStatus == 200)
            check("LLM 2xx → latency non-nil", result.latencyMilliseconds != nil)
            check("LLM 2xx → latency >= 0", (result.latencyMilliseconds ?? -1) >= 0)
            check("LLM 2xx → snapshot not nil", result.snapshot != nil)
            check("LLM 2xx → provider == 'local'", result.snapshot?.provider == "local")
            check("LLM 2xx → model == 'gemma2:2b'", result.snapshot?.model == "gemma2:2b")
            check("LLM 2xx → status == 'ok'", result.snapshot?.status == "ok")
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, "not json".data(using: .utf8)!)
            }
            let result = await ScoutLLMHealthProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("LLM decode fail → snapshot nil", result.snapshot == nil)
            check("LLM decode fail → httpStatus preserved", result.httpStatus == 200)
            check("LLM decode fail → latency present", result.latencyMilliseconds != nil)
        }

        do {
            let session = makeSession()
            _mockHandler = { _ in throw URLError(.timedOut) }
            let result = await ScoutLLMHealthProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("LLM timeout → latency nil", result.latencyMilliseconds == nil)
            check("LLM timeout → snapshot nil", result.snapshot == nil)
            check("LLM timeout → httpStatus nil", result.httpStatus == nil)
            check("LLM timeout → 'timed out' in msg", result.message.contains("timed out"))
        }

        do {
            let session = makeSession()
            _mockHandler = { _ in throw URLError(.cannotConnectToHost) }
            let result = await ScoutLLMHealthProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("LLM transport error → latency nil", result.latencyMilliseconds == nil)
            check("LLM transport error → snapshot nil", result.snapshot == nil)
            check("LLM transport error → 'failed' in msg", result.message.contains("failed"))
        }

        // ── LLM catalog probe ────────────────────────────────────

        func catalogBody() -> Data {
            """
            {"providers":[{"id":"local","displayName":"Local","enabled":true,"available":true,"models":[{"id":"gemma2:2b","displayName":"Gemma 2B"},{"id":"llama3.2","displayName":"Llama 3.2"}]}]}
            """.data(using: .utf8)!
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                check("Catalog probe has X-API-Key", request.value(forHTTPHeaderField: "X-API-Key") == "key")
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, catalogBody())
            }
            let result = await ScoutLLMCatalogProbe.probe(
                endpoint: makeEndpoint(), apiKey: "key", session: session
            )
            check("Catalog 2xx → httpStatus 200", result.httpStatus == 200)
            check("Catalog 2xx → latency non-nil", result.latencyMilliseconds != nil)
            check("Catalog 2xx → latency >= 0", (result.latencyMilliseconds ?? -1) >= 0)
            check("Catalog 2xx → snapshot not nil", result.snapshot != nil)
            check("Catalog → 2 models", result.snapshot?.providers?.first?.models?.count == 2)
            check("Catalog → provider id 'local'", result.snapshot?.providers?.first?.id == "local")
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, "not json".data(using: .utf8)!)
            }
            let result = await ScoutLLMCatalogProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("Catalog decode fail → snapshot nil", result.snapshot == nil)
            check("Catalog decode fail → httpStatus preserved", result.httpStatus == 200)
            check("Catalog decode fail → latency present", result.latencyMilliseconds != nil)
        }

        do {
            let session = makeSession()
            _mockHandler = { _ in throw URLError(.timedOut) }
            let result = await ScoutLLMCatalogProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("Catalog timeout → latency nil", result.latencyMilliseconds == nil)
            check("Catalog timeout → snapshot nil", result.snapshot == nil)
            check("Catalog timeout → httpStatus nil", result.httpStatus == nil)
            check("Catalog timeout → 'timed out' in msg", result.message.contains("timed out"))
        }

        do {
            let session = makeSession()
            _mockHandler = { _ in throw URLError(.cannotConnectToHost) }
            let result = await ScoutLLMCatalogProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("Catalog transport error → latency nil", result.latencyMilliseconds == nil)
            check("Catalog transport error → snapshot nil", result.snapshot == nil)
            check("Catalog transport error → 'failed' in msg", result.message.contains("failed"))
        }

        // ── Guardian threads probe ───────────────────────────────

        func threadsBody(count: Int = 2) -> Data {
            let thread = """
            {"id":1,"title":"Hello","summary":"A test thread","created_at":"2024-01-01T00:00:00Z","updated_at":"2024-01-02T00:00:00Z"}
            """
            let threads = (0..<count).map { _ in thread }.joined(separator: ",")
            return """
            {"ok":true,"threads":[\(threads)],"limit":50,"offset":0,"next_offset":\(count),"has_more":false}
            """.data(using: .utf8)!
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                check("Threads probe has X-API-Key", request.value(forHTTPHeaderField: "X-API-Key") == "key")
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, threadsBody())
            }
            let result = await ScoutGuardianThreadsProbe.probe(
                endpoint: makeEndpoint(), apiKey: "key", session: session
            )
            check("Threads 2xx → httpStatus 200", result.httpStatus == 200)
            check("Threads 2xx → threads non-nil", result.threads != nil)
            check("Threads 2xx → 2 threads", result.threads?.count == 2)
            check("Threads 2xx → title 'Hello'", result.threads?.first?.title == "Hello")
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                check("Threads no header when key nil", request.value(forHTTPHeaderField: "X-API-Key") == nil)
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, threadsBody(count: 0))
            }
            let result = await ScoutGuardianThreadsProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("Threads empty → threads empty", result.threads?.isEmpty == true)
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, "not json".data(using: .utf8)!)
            }
            let result = await ScoutGuardianThreadsProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("Threads decode fail → threads nil", result.threads == nil)
            check("Threads decode fail → httpStatus preserved", result.httpStatus == 200)
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 401, httpVersion: nil, headerFields: nil)!
                return (r, Data())
            }
            let result = await ScoutGuardianThreadsProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("Threads 401 → threads nil", result.threads == nil)
            check("Threads 401 → auth message", result.message.contains("Authentication required"))
        }

        do {
            let session = makeSession()
            _mockHandler = { _ in throw URLError(.timedOut) }
            let result = await ScoutGuardianThreadsProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("Threads timeout → threads nil", result.threads == nil)
            check("Threads timeout → 'timed out' in msg", result.message.contains("timed out"))
        }

        do {
            let session = makeSession()
            _mockHandler = { _ in throw URLError(.cannotConnectToHost) }
            let result = await ScoutGuardianThreadsProbe.probe(
                endpoint: makeEndpoint(), apiKey: nil, session: session
            )
            check("Threads transport error → threads nil", result.threads == nil)
            check("Threads transport error → 'failed' in msg", result.message.contains("failed"))
        }

        // ── Guardian messages probe ──────────────────────────────

        func messagesBody() -> Data {
            """
            {"ok":true,"total":2,"messages":[{"id":1,"role":"user","content":"Hello","created_at":"2024-01-01T00:00:00Z"},{"id":2,"role":"assistant","content":"Hi there!","created_at":"2024-01-01T00:00:01Z"}]}
            """.data(using: .utf8)!
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                check("Messages probe has X-API-Key", request.value(forHTTPHeaderField: "X-API-Key") == "key")
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, messagesBody())
            }
            let result = await ScoutGuardianThreadMessagesProbe.probe(
                endpoint: makeEndpoint(), threadId: 1, apiKey: "key", session: session
            )
            check("Messages 2xx → httpStatus 200", result.httpStatus == 200)
            check("Messages 2xx → messages non-nil", result.messages != nil)
            check("Messages 2xx → 2 messages", result.messages?.count == 2)
            check("Messages 2xx → role 'user'", result.messages?.first?.role == "user")
            check("Messages 2xx → content 'Hello'", result.messages?.first?.content == "Hello")
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                check("Messages no header when key nil", request.value(forHTTPHeaderField: "X-API-Key") == nil)
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, """
                {"ok":true,"total":0,"messages":[]}
                """.data(using: .utf8)!)
            }
            let result = await ScoutGuardianThreadMessagesProbe.probe(
                endpoint: makeEndpoint(), threadId: 1, apiKey: nil, session: session
            )
            check("Messages empty → messages empty", result.messages?.isEmpty == true)
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (r, "not json".data(using: .utf8)!)
            }
            let result = await ScoutGuardianThreadMessagesProbe.probe(
                endpoint: makeEndpoint(), threadId: 1, apiKey: nil, session: session
            )
            check("Messages decode fail → messages nil", result.messages == nil)
            check("Messages decode fail → httpStatus preserved", result.httpStatus == 200)
        }

        do {
            let session = makeSession()
            _mockHandler = { request in
                let r = HTTPURLResponse(url: request.url!, statusCode: 401, httpVersion: nil, headerFields: nil)!
                return (r, Data())
            }
            let result = await ScoutGuardianThreadMessagesProbe.probe(
                endpoint: makeEndpoint(), threadId: 1, apiKey: nil, session: session
            )
            check("Messages 401 → messages nil", result.messages == nil)
            check("Messages 401 → auth message", result.message.contains("Authentication required"))
        }

        do {
            let session = makeSession()
            _mockHandler = { _ in throw URLError(.timedOut) }
            let result = await ScoutGuardianThreadMessagesProbe.probe(
                endpoint: makeEndpoint(), threadId: 1, apiKey: nil, session: session
            )
            check("Messages timeout → messages nil", result.messages == nil)
            check("Messages timeout → 'timed out' in msg", result.message.contains("timed out"))
        }

        do {
            let session = makeSession()
            _mockHandler = { _ in throw URLError(.cannotConnectToHost) }
            let result = await ScoutGuardianThreadMessagesProbe.probe(
                endpoint: makeEndpoint(), threadId: 1, apiKey: nil, session: session
            )
            check("Messages transport error → messages nil", result.messages == nil)
            check("Messages transport error → 'failed' in msg", result.message.contains("failed"))
        }

        // ── Summary ────────────────────────────────────────────────

        print("\n\(passed) passed, \(failed) failed")
        exit(failed > 0 ? 1 : 0)
    }
}
