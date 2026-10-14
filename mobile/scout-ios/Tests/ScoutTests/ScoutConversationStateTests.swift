import Foundation
import XCTest
@testable import Scout

private final class ConversationURLProtocol: URLProtocol {
    static var handler: ((ConversationURLProtocol) -> Void)?
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() { Self.handler?(self) }
    override func stopLoading() {}
    func respond(status: Int = 200, content: String = "persisted assistant") {
        let response = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        let data = try! JSONSerialization.data(withJSONObject: ["messages": [["id": 1, "role": "assistant", "content": content]]])
        client?.urlProtocol(self, didLoad: data)
        client?.urlProtocolDidFinishLoading(self)
    }
}

final class ScoutConversationStateTests: XCTestCase {
    private func endpoint(_ url: String = "https://node-a.example.test") -> ScoutEndpointProfile {
        ScoutEndpointProfile(id: UUID(), name: "Node", baseURL: url, transportType: .custom,
                             authenticationState: .unconfigured, validationState: .unconfigured, lastConnectedAt: nil)
    }
    private func session() -> URLSession {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [ConversationURLProtocol.self]
        return URLSession(configuration: config)
    }

    @MainActor
    func testTerminalCompletionPublishesPersistedMessages() async {
        let state = ScoutConversationState(), node = endpoint(), network = session()
        defer { network.invalidateAndCancel(); ConversationURLProtocol.handler = nil }
        state.select(.init(endpoint: node, threadID: 4))
        ConversationURLProtocol.handler = { $0.respond() }
        let result = await state.handleTerminalEvent("task.completed", endpoint: node, threadID: 4, apiKey: nil, session: network)
        XCTAssertEqual(result, "Task completed. Messages refreshed.")
        XCTAssertEqual(state.messages?.first?.content, "persisted assistant")
    }

    @MainActor
    func testFailedCancelledAndNonTerminalEventsNeverFetchOrSynthesize() async {
        let state = ScoutConversationState(), node = endpoint(), network = session()
        defer { network.invalidateAndCancel(); ConversationURLProtocol.handler = nil }
        state.select(.init(endpoint: node, threadID: 4))
        ConversationURLProtocol.handler = { _ in XCTFail("Terminal failure must not fetch output") }
        for event in ["task.failed", "task.cancelled", "task.started"] {
            _ = await state.handleTerminalEvent(event, endpoint: node, threadID: 4, apiKey: nil, session: network)
            XCTAssertNil(state.messages)
        }
    }

    @MainActor
    func testFailedRefreshDoesNotClaimSuccessOrDiscardPersistedView() async {
        let state = ScoutConversationState(), node = endpoint(), network = session()
        defer { network.invalidateAndCancel(); ConversationURLProtocol.handler = nil }
        state.select(.init(endpoint: node, threadID: 4))
        ConversationURLProtocol.handler = { $0.respond() }
        _ = await state.refresh(endpoint: node, threadID: 4, apiKey: nil, session: network)
        ConversationURLProtocol.handler = { $0.respond(status: 503) }
        let result = await state.handleTerminalEvent("task.completed", endpoint: node, threadID: 4, apiKey: nil, session: network)
        XCTAssertEqual(result, "Task completed. Messages request returned HTTP 503.")
        XCTAssertEqual(state.messages?.first?.content, "persisted assistant")
    }

    @MainActor
    func testNodeSwitchRejectsLateReadWithSameThreadID() async {
        let state = ScoutConversationState(), nodeA = endpoint(), nodeB = endpoint("https://node-b.example.test"), network = session()
        defer { network.invalidateAndCancel(); ConversationURLProtocol.handler = nil }
        state.select(.init(endpoint: nodeA, threadID: 4))
        let started = expectation(description: "Read started")
        var pending: ConversationURLProtocol?
        ConversationURLProtocol.handler = { pending = $0; started.fulfill() }
        let read = Task { await state.refresh(endpoint: nodeA, threadID: 4, apiKey: nil, session: network) }
        await fulfillment(of: [started], timeout: 2)
        state.select(.init(endpoint: nodeB, threadID: 4))
        pending?.respond()
        let result = await read.value
        XCTAssertNil(result)
        XCTAssertNil(state.messages)
        XCTAssertEqual(state.selection, .init(endpoint: nodeB, threadID: 4))
    }

    @MainActor
    func testResumeReadPreservesSelectionAndRejectsOtherThread() async {
        let state = ScoutConversationState(), node = endpoint(), network = session()
        defer { network.invalidateAndCancel(); ConversationURLProtocol.handler = nil }
        let selected = ScoutConversationState.Selection(endpoint: node, threadID: 4)
        state.select(selected)
        var reads = 0
        ConversationURLProtocol.handler = { reads += 1; $0.respond(content: "persisted \(reads)") }
        _ = await state.refresh(endpoint: node, threadID: 4, apiKey: nil, session: network)
        state.select(selected)
        _ = await state.refresh(endpoint: node, threadID: 4, apiKey: nil, session: network)
        _ = await state.refresh(endpoint: node, threadID: 9, apiKey: nil, session: network)
        XCTAssertEqual(reads, 2)
        XCTAssertEqual(state.selection, selected)
        XCTAssertEqual(state.messages?.first?.content, "persisted 2")
    }
    @MainActor
    func testOlderOverlappingReadCannotReplaceNewerMessages() async {
        let state = ScoutConversationState(), node = endpoint(), network = session()
        defer { network.invalidateAndCancel(); ConversationURLProtocol.handler = nil }
        state.select(.init(endpoint: node, threadID: 4))
        let started = expectation(description: "Older read started")
        var pending: ConversationURLProtocol?
        var reads = 0
        ConversationURLProtocol.handler = {
            reads += 1
            if reads == 1 { pending = $0; started.fulfill() }
            else { $0.respond(content: "new persisted output") }
        }
        let older = Task { await state.refresh(endpoint: node, threadID: 4, apiKey: nil, session: network) }
        await fulfillment(of: [started], timeout: 2)
        _ = await state.refresh(endpoint: node, threadID: 4, apiKey: nil, session: network)
        pending?.respond(content: "old output")
        let result = await older.value
        XCTAssertNil(result)
        XCTAssertEqual(state.messages?.first?.content, "new persisted output")
    }

    @MainActor
    func testDisplayMetadataChangesPreserveConnectionAndConversation() async {
        let state = ScoutConversationState(), network = session()
        var node = endpoint()
        defer { network.invalidateAndCancel(); ConversationURLProtocol.handler = nil }
        let connection = ScoutConnectionIdentity(endpoint: node)
        state.select(.init(endpoint: node, threadID: 4))
        ConversationURLProtocol.handler = { $0.respond() }
        _ = await state.refresh(endpoint: node, threadID: 4, apiKey: nil, session: network)
        node.name = "Renamed node"
        node.validationState = .reachable
        node.lastConnectedAt = Date()
        XCTAssertEqual(ScoutConnectionIdentity(endpoint: node), connection)
        state.select(.init(endpoint: node, threadID: 4))
        XCTAssertEqual(state.messages?.first?.content, "persisted assistant")
        node.baseURL = "https://other-origin.example.test"
        state.select(.init(endpoint: node, threadID: 4))
        XCTAssertNil(state.messages)
    }

}
