import Foundation
import XCTest
@testable import Scout

private final class FirstMessageURLProtocol: URLProtocol {
    static var requests: [URLRequest] = []
    static var status = 200
    static var body = "{}"

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        Self.requests.append(request)
        let response = HTTPURLResponse(url: request.url!, statusCode: Self.status,
                                       httpVersion: nil, headerFields: nil)!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: Data(Self.body.utf8))
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}

@MainActor
final class ScoutFirstMessageTests: XCTestCase {
    private var session: URLSession!
    private let endpoint = ScoutEndpointProfile(id: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!,
        name: "Test", baseURL: "https://example.test/vault", transportType: .custom,
        authenticationState: .authenticated, validationState: .reachable, lastConnectedAt: nil)

    override func setUp() {
        super.setUp()
        FirstMessageURLProtocol.requests = []
        FirstMessageURLProtocol.status = 200
        FirstMessageURLProtocol.body = #"{"created_thread":true,"thread_id":8,"thread":{"id":8,"title":"First line","project_id":2},"message":{"id":42}}"#
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [FirstMessageURLProtocol.self]
        session = URLSession(configuration: configuration)
    }

    override func tearDown() {
        session.invalidateAndCancel()
        super.tearDown()
    }

    private func body(of request: URLRequest) throws -> [String: Any] {
        var data = request.httpBody
        if data == nil, let stream = request.httpBodyStream {
            stream.open()
            defer { stream.close() }
            var buffer = [UInt8](repeating: 0, count: 4096)
            let count = stream.read(&buffer, maxLength: buffer.count)
            if count > 0 { data = Data(buffer.prefix(count)) }
        }
        return try XCTUnwrap(JSONSerialization.jsonObject(with: XCTUnwrap(data)) as? [String: Any])
    }

    func testFirstMessageCreatesNamedThreadInSelectedProject() async throws {
        let result = await ScoutGuardianFirstMessageService.send(endpoint: endpoint,
            content: "  First line\nMore context  ", projectID: 2, apiKey: "fixture-key", session: session)
        XCTAssertEqual(result.threadID, 8)
        XCTAssertEqual(result.messageID, 42)
        XCTAssertEqual(result.threadTitle, "First line")
        let request = try XCTUnwrap(FirstMessageURLProtocol.requests.first)
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.url?.path, "/vault/api/chat/messages")
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-API-Key"), "fixture-key")
        let payload = try body(of: request)
        XCTAssertEqual(payload["role"] as? String, "user")
        XCTAssertEqual(payload["content"] as? String, "First line\nMore context")
        XCTAssertEqual(payload["title"] as? String, "First line")
        XCTAssertEqual(payload["project_id"] as? Int, 2)
        XCTAssertNil(payload["thread_id"])
        // Omission makes Guardian's request model substitute the legacy
        // "default" user, which hosted account-scoped requests reject.
        XCTAssertTrue(payload.keys.contains("user_id"))
        XCTAssertTrue(payload["user_id"] is NSNull)
    }

    func testTitleUsesFirstLineAndIsBounded() {
        XCTAssertEqual(ScoutGuardianFirstMessageService.title(for: "  First line\nSecond line  "), "First line")
        XCTAssertEqual(ScoutGuardianFirstMessageService.title(for: String(repeating: "x", count: 90)), String(repeating: "x", count: 60))
        XCTAssertEqual(ScoutGuardianFirstMessageService.title(for: " \n "), "New Thread")
    }

    func testMalformedOrWrongProjectReceiptDoesNotConfirmMessage() async {
        for body in [
            #"{"created_thread":true,"thread_id":8,"message":{"id":42}}"#,
            #"{"created_thread":true,"thread_id":8,"thread":{"id":9,"project_id":2},"message":{"id":42}}"#,
            #"{"created_thread":false,"thread_id":8,"thread":{"id":8,"project_id":2},"message":{"id":42}}"#,
            #"{"created_thread":true,"thread_id":8,"thread":{"id":8,"project_id":3},"message":{"id":42}}"#
        ] {
            FirstMessageURLProtocol.body = body
            let result = await ScoutGuardianFirstMessageService.send(endpoint: endpoint, content: "First", projectID: 2,
                                                                       apiKey: "fixture-key", session: session)
            XCTAssertNil(result.threadID)
            XCTAssertNil(result.messageID)
        }
    }

    func testUnconfirmedFirstMessageIsNotAutomaticallyReplayed() async {
        FirstMessageURLProtocol.body = "{}"
        let flow = ScoutComposerFlow()
        let scope = ScoutComposerFlow.Scope(connection: .init(endpoint: endpoint), threadID: nil, accountGeneration: 0)
        flow.select(scope)
        flow.draft = "Keep my message"
        for _ in 0..<2 {
            await flow.submit(scope: scope, isCurrent: { true }, save: { text in
                let result = await ScoutGuardianFirstMessageService.send(endpoint: self.endpoint, content: text,
                    projectID: 2, apiKey: "fixture-key", session: self.session)
                return .init(httpStatus: result.httpStatus, messageId: result.messageID, message: result.message)
            }, complete: {
                XCTFail("An unconfirmed write must not request a response")
                return .init(httpStatus: nil, taskId: nil, turnId: nil, messagesUrl: nil, traceUrl: nil,
                             acceptanceStatus: nil, message: "Unexpected")
            })
        }
        XCTAssertEqual(FirstMessageURLProtocol.requests.count, 1)
        XCTAssertEqual(flow.draft, "Keep my message")
        XCTAssertEqual(flow.phase, .unconfirmed)
    }

    func testRejectedFirstMessageKeepsDraftAvailableForRetry() async {
        FirstMessageURLProtocol.status = 400
        let flow = ScoutComposerFlow()
        let scope = ScoutComposerFlow.Scope(connection: .init(endpoint: endpoint), threadID: nil, accountGeneration: 0)
        flow.select(scope)
        flow.draft = "Keep my message"
        await flow.submit(scope: scope, isCurrent: { true }, save: { text in
            let result = await ScoutGuardianFirstMessageService.send(endpoint: self.endpoint, content: text,
                projectID: 2, apiKey: "fixture-key", session: self.session)
            return .init(httpStatus: result.httpStatus, messageId: result.messageID, message: result.message)
        }, complete: {
            XCTFail("A rejected message must not request a response")
            return .init(httpStatus: nil, taskId: nil, turnId: nil, messagesUrl: nil, traceUrl: nil,
                         acceptanceStatus: nil, message: "Unexpected")
        })
        XCTAssertEqual(flow.phase, .messageRejected)
        XCTAssertEqual(flow.draft, "Keep my message")
        XCTAssertTrue(flow.canSubmit)
    }

    func testAcceptedDraftPromotionPreservesPendingResponse() async {
        let flow = ScoutComposerFlow()
        let draft = ScoutComposerFlow.Scope(connection: .init(endpoint: endpoint), threadID: nil, accountGeneration: 0)
        let thread = ScoutComposerFlow.Scope(connection: .init(endpoint: endpoint), threadID: 8, accountGeneration: 0)
        flow.select(draft)
        flow.draft = "First line"
        await flow.submit(scope: draft, isCurrent: { true }, save: { text in
            let result = await ScoutGuardianFirstMessageService.send(endpoint: self.endpoint, content: text,
                projectID: 2, apiKey: "fixture-key", session: self.session)
            return .init(httpStatus: result.httpStatus, messageId: result.messageID, message: result.message)
        }, complete: {
            .init(httpStatus: 202, taskId: "task-1", turnId: nil, messagesUrl: nil, traceUrl: nil,
                  acceptanceStatus: "accepted", message: "Accepted")
        })
        XCTAssertTrue(flow.promoteDraft(from: draft, to: thread))
        flow.select(thread) // The persisted thread view attaches to the same flow.
        XCTAssertEqual(flow.scope, thread)
        XCTAssertEqual(flow.acceptedMessageID, 42)
        XCTAssertEqual(flow.taskID, "task-1")
        XCTAssertEqual(flow.phase, .pending)
        XCTAssertEqual(flow.draft, "")
        XCTAssertFalse(flow.promoteDraft(from: draft, to: thread))
    }
}
