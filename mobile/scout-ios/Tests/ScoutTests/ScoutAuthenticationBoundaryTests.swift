import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import XCTest
@testable import Scout

private final class AuthenticationBoundaryURLProtocol: URLProtocol {
    static var requestCount = 0

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        Self.requestCount += 1
        let response = HTTPURLResponse(url: request.url!, statusCode: 500, httpVersion: nil, headerFields: nil)!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}
}

final class ScoutAuthenticationBoundaryTests: XCTestCase {
    func testLegacyProfilePreservesMetadataAndEncodesExplicitLocalMode() throws {
        let original = endpoint()
        var json = try object(for: original)
        json.removeValue(forKey: "authenticationMode")

        let decoded = try JSONDecoder().decode(ScoutEndpointProfile.self, from: data(for: json))
        XCTAssertEqual(decoded.authenticationMode, .localAPIKey)
        XCTAssertEqual(decoded.id, original.id)
        XCTAssertEqual(decoded.name, original.name)
        XCTAssertEqual(decoded.baseURL, original.baseURL)
        XCTAssertEqual(decoded.transportType, original.transportType)
        XCTAssertEqual(decoded.validationState, original.validationState)
        XCTAssertEqual(decoded.lastConnectedAt, original.lastConnectedAt)
        XCTAssertEqual(try object(for: decoded)["authenticationMode"] as? String, "localAPIKey")
    }

    func testKnownModesRoundTripIndependentlyOfTransport() throws {
        for transport in ScoutEndpointTransportType.allCases {
            for mode in ScoutEndpointAuthenticationMode.allCases {
                let original = endpoint(mode: mode, transport: transport)
                let restored = try JSONDecoder().decode(
                    ScoutEndpointProfile.self, from: JSONEncoder().encode(original)
                )
                XCTAssertEqual(restored.authenticationMode, mode)
                XCTAssertEqual(restored.transportType, transport)
                XCTAssertEqual(restored.id, original.id)
            }
        }
    }

    func testExplicitNullUnknownAndMalformedModesNeverBecomeLocal() throws {
        let original = endpoint()
        for badValue: Any in [NSNull(), "futureMode", 42, ["remoteSession": true]] {
            var json = try object(for: original)
            json["authenticationMode"] = badValue
            XCTAssertThrowsError(try JSONDecoder().decode(ScoutEndpointProfile.self, from: data(for: json)))
        }
    }

    func testRemoteStoredMetadataCannotRestoreAuthenticatedState() throws {
        var original = endpoint()
        original.authenticationState = .authenticated
        var json = try object(for: original)
        json["authenticationMode"] = "remoteSession"
        let restored = try JSONDecoder().decode(ScoutEndpointProfile.self, from: data(for: json))
        XCTAssertEqual(restored.authenticationMode, .remoteSession)
        XCTAssertEqual(restored.authenticationState, .unconfigured)
        XCTAssertEqual(try object(for: restored)["authenticationMode"] as? String, "remoteSession")
    }

    func testLocalRequestPreservesShapeAndUsesOnlyNonBlankAPIKey() throws {
        let originalBody = Data(#"{"example":true}"#.utf8)
        for key: String? in ["dummy-local-key", nil, "  \n "] {
            var request = URLRequest(url: URL(string: "https://vault.example.test/api/example")!)
            request.httpMethod = "PATCH"
            request.httpBody = originalBody
            request.timeoutInterval = 17
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.setValue("Bearer stale", forHTTPHeaderField: "Authorization")
            request.setValue("stale-key", forHTTPHeaderField: "X-API-Key")

            try ScoutRequestAuthentication.apply(to: &request, endpoint: endpoint(), apiKey: key)

            XCTAssertEqual(request.url?.absoluteString, "https://vault.example.test/api/example")
            XCTAssertEqual(request.httpMethod, "PATCH")
            XCTAssertEqual(request.httpBody, originalBody)
            XCTAssertEqual(request.timeoutInterval, 17)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-API-Key"), key == "dummy-local-key" ? key : nil)
        }
    }

    func testRemoteRequestRejectsWithOrWithoutLocalKeyAndClearsOldCredentials() {
        for key: String? in ["dummy-local-key", nil] {
            var request = URLRequest(url: URL(string: "https://vault.example.test/api/example")!)
            request.setValue("Bearer stale", forHTTPHeaderField: "Authorization")
            request.setValue("stale-key", forHTTPHeaderField: "X-API-Key")

            XCTAssertThrowsError(try ScoutRequestAuthentication.apply(
                to: &request, endpoint: endpoint(mode: .remoteSession), apiKey: key
            )) { error in
                XCTAssertEqual(error as? ScoutRequestAuthenticationError, .sessionRequired)
            }
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            XCTAssertNil(request.value(forHTTPHeaderField: "X-API-Key"))
        }
    }

    func testRemoteModeBlocksEveryDataConsumerBeforeURLLoading() async {
        let session = makeSession()
        defer { session.invalidateAndCancel() }
        AuthenticationBoundaryURLProtocol.requestCount = 0
        let remote = endpoint(mode: .remoteSession)
        let key = "dummy-local-key"

        let health = await ScoutEndpointConnectivityProbe.probe(endpoint: remote, apiKey: key, session: session)
        XCTAssertEqual(health.validationState, .invalidConfiguration)
        XCTAssertEqual(health.authenticationState, .unconfigured)
        XCTAssertNil(health.connectedAt)
        XCTAssertNil(health.snapshot)
        XCTAssertNil(health.latencyMilliseconds)
        assertBlocked(health.message, status: nil)

        let llmHealth = await ScoutLLMHealthProbe.probe(endpoint: remote, apiKey: key, session: session)
        XCTAssertNil(llmHealth.snapshot)
        XCTAssertNil(llmHealth.latencyMilliseconds)
        assertBlocked(llmHealth.message, status: llmHealth.httpStatus)

        let catalog = await ScoutLLMCatalogProbe.probe(endpoint: remote, apiKey: key, session: session)
        XCTAssertNil(catalog.snapshot)
        assertBlocked(catalog.message, status: catalog.httpStatus)

        let threads = await ScoutGuardianThreadsProbe.probe(endpoint: remote, apiKey: key, session: session)
        XCTAssertNil(threads.threads)
        assertBlocked(threads.message, status: threads.httpStatus)

        let messages = await ScoutGuardianThreadMessagesProbe.probe(endpoint: remote, threadId: 1, apiKey: key, session: session)
        XCTAssertNil(messages.messages)
        assertBlocked(messages.message, status: messages.httpStatus)

        let sent = await ScoutGuardianSendMessageService.send(endpoint: remote, threadId: 1, content: "hello", apiKey: key, session: session)
        XCTAssertNil(sent.messageId)
        assertBlocked(sent.message, status: sent.httpStatus)

        let completed = await ScoutGuardianCompleteThreadService.complete(endpoint: remote, threadId: 1, apiKey: key, session: session)
        XCTAssertNil(completed.taskId)
        XCTAssertNil(completed.turnId)
        assertBlocked(completed.message, status: completed.httpStatus)

        let documents = await ScoutThreadDocumentsProbe.probe(endpoint: remote, threadId: 1, apiKey: key, session: session)
        XCTAssertNil(documents.documents)
        assertBlocked(documents.message, status: documents.httpStatus)

        let detail = await ScoutDocumentDetailProbe.probe(endpoint: remote, documentId: "doc-1", apiKey: key, session: session)
        XCTAssertNil(detail.detail)
        assertBlocked(detail.message, status: detail.httpStatus)

        let trace = await ScoutRAGTraceProbe.probe(endpoint: remote, threadId: 1, apiKey: key, session: session)
        XCTAssertNil(trace.snapshot)
        assertBlocked(trace.message, status: trace.httpStatus)

        let tasks = await ScoutThreadTasksProbe.probe(endpoint: remote, threadId: 1, apiKey: key, session: session)
        XCTAssertNil(tasks.tasks)
        assertBlocked(tasks.message, status: tasks.httpStatus)

        let media = await ScoutMediaDocumentsProbe.probe(endpoint: remote, apiKey: key, session: session)
        XCTAssertNil(media.documents)
        assertBlocked(media.message, status: media.httpStatus)

        let created = await ScoutCreateThreadProbe.create(endpoint: remote, title: "Test", apiKey: key, session: session)
        XCTAssertNil(created.threadId)
        XCTAssertNil(created.thread)
        assertBlocked(created.message, status: created.httpStatus)

        let renamed = await ScoutRenameThreadProbe.rename(endpoint: remote, threadId: 1, title: "Test", apiKey: key, session: session)
        assertBlocked(renamed.message, status: renamed.httpStatus)
        XCTAssertEqual(AuthenticationBoundaryURLProtocol.requestCount, 0)
    }

    func testRemoteEventStreamThrowsTypedErrorAndYieldsNoEvent() async {
        let session = makeSession()
        defer { session.invalidateAndCancel() }
        AuthenticationBoundaryURLProtocol.requestCount = 0
        var received: [ScoutTaskEvent] = []

        do {
            for try await event in ScoutTaskEventStreamService.streamEvents(
                endpoint: endpoint(mode: .remoteSession), taskId: "task-1",
                apiKey: "dummy-local-key", session: session
            ) {
                received.append(event)
            }
            XCTFail("Remote stream ended without a policy error")
        } catch {
            XCTAssertEqual(error as? ScoutRequestAuthenticationError, .sessionRequired)
        }

        XCTAssertTrue(received.isEmpty)
        XCTAssertEqual(AuthenticationBoundaryURLProtocol.requestCount, 0)
    }

    private func assertBlocked(_ message: String, status: Int?, file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertNil(status, file: file, line: line)
        XCTAssertTrue(message.contains("No account session is stored"), message, file: file, line: line)
        XCTAssertEqual(AuthenticationBoundaryURLProtocol.requestCount, 0, file: file, line: line)
    }

    private func endpoint(
        mode: ScoutEndpointAuthenticationMode = .localAPIKey,
        transport: ScoutEndpointTransportType = .tailscale
    ) -> ScoutEndpointProfile {
        ScoutEndpointProfile(
            id: UUID(), name: "Test Vault", baseURL: "https://vault.example.test",
            transportType: transport, authenticationState: .unconfigured,
            validationState: .unconfigured, lastConnectedAt: Date(timeIntervalSince1970: 1_700_000_000),
            authenticationMode: mode
        )
    }

    private func makeSession() -> URLSession {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [AuthenticationBoundaryURLProtocol.self]
        return URLSession(configuration: configuration)
    }

    private func object(for profile: ScoutEndpointProfile) throws -> [String: Any] {
        try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(profile)) as? [String: Any])
    }

    private func data(for object: [String: Any]) throws -> Data {
        try JSONSerialization.data(withJSONObject: object)
    }
}
