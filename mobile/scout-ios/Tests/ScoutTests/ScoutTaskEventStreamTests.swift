import XCTest
@testable import Scout

@MainActor
final class ScoutTaskEventStreamTests: XCTestCase {
    private let endpoint = ScoutEndpointProfile(
        id: UUID(), name: "Test", baseURL: "https://task-events.example.test",
        transportType: .custom, authenticationState: .authenticated,
        validationState: .reachable, lastConnectedAt: nil
    )

    func testResumesFromLastCompleteEventThroughPrematureEOFAndTransientFailure() async throws {
        let network = session(responses: [
            .body(200, "id: 1-0\nevent: task.running\ndata: {}\n\nid: 2-0\nevent: task.completed\ndata: \n"),
            .transport(.networkConnectionLost),
            .body(503, ""),
            .body(200, "id: 1-0\nevent: task.running\ndata: {}\n\nid: 2-0\nevent: task.completed\ndata: {}\n\n"),
        ])
        defer { network.invalidateAndCancel() }

        var events: [ScoutTaskEvent] = []
        for try await event in ScoutTaskEventStreamService.streamEvents(
            endpoint: endpoint, taskId: "task-1", apiKey: "fixture-key", session: network,
            retryDelays: [.zero, .zero, .zero, .zero]
        ) {
            events.append(event)
        }

        XCTAssertEqual(events.map(\.eventId), ["1-0", "2-0"])
        XCTAssertEqual(events.map(\.eventType), ["task.running", "task.completed"])
        XCTAssertEqual(TaskEventRecoveryURLProtocol.cursors, ["0-0", "1-0", "1-0", "1-0"])
    }

    func testStopsAfterRetryBudgetAndFailsClosedOnDenial() async {
        for (status, expectedCount) in [(403, 1), (503, 3)] {
            let network = session(responses: Array(repeating: .body(status, ""), count: expectedCount))
            defer { network.invalidateAndCancel() }

            do {
                for try await _ in ScoutTaskEventStreamService.streamEvents(
                    endpoint: endpoint, taskId: "task-1", apiKey: "fixture-key", session: network,
                    retryDelays: [.zero, .zero]
                ) {
                    XCTFail("An error response must not yield a task event")
                }
                XCTFail("Expected an error for HTTP \(status)")
            } catch {
                XCTAssertEqual(TaskEventRecoveryURLProtocol.cursors.count, expectedCount)
            }
        }
    }

    func testScopeChangeDuringBackoffBlocksTheNextRequest() async throws {
        let network = session(responses: [.body(200, "id: 1-0\nevent: task.running\ndata: {}\n\n")])
        defer { network.invalidateAndCancel() }
        var isCurrent = true

        for try await _ in ScoutTaskEventStreamService.streamEvents(
            endpoint: endpoint, taskId: "task-1", apiKey: "fixture-key", session: network,
            retryDelays: [.milliseconds(100)], isCurrent: { isCurrent }
        ) {
            isCurrent = false
        }

        XCTAssertEqual(TaskEventRecoveryURLProtocol.cursors, ["0-0"])
    }

    func testCancellingTheObserverStopsReconnect() async {
        let network = session(responses: [.body(200, "id: 1-0\nevent: task.running\ndata: {}\n\n")])
        defer { network.invalidateAndCancel() }
        let initialEvent = expectation(description: "First task event received")
        let observer = Task {
            let stream = ScoutTaskEventStreamService.streamEvents(
                endpoint: endpoint, taskId: "task-1", apiKey: "fixture-key", session: network,
                retryDelays: [.milliseconds(100)]
            )
            for try await _ in stream { initialEvent.fulfill() }
        }
        await fulfillment(of: [initialEvent], timeout: 2)
        observer.cancel()
        _ = await observer.result
        try? await Task.sleep(for: .milliseconds(150))

        XCTAssertEqual(TaskEventRecoveryURLProtocol.cursors, ["0-0"])
    }

    private func session(responses: [TaskEventRecoveryURLProtocol.Response]) -> URLSession {
        TaskEventRecoveryURLProtocol.configure(responses)
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [TaskEventRecoveryURLProtocol.self]
        return URLSession(configuration: configuration)
    }
}

private final class TaskEventRecoveryURLProtocol: URLProtocol {
    enum Response {
        case body(Int, String)
        case transport(URLError.Code)
    }

    private static let lock = NSLock()
    private static var state: (responses: [Response], cursors: [String]) = ([], [])

    static func configure(_ responses: [Response]) {
        lock.withLock { state = (responses, []) }
    }

    static var cursors: [String] { lock.withLock { state.cursors } }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        let url = request.url!
        let cursor = URLComponents(url: url, resolvingAgainstBaseURL: false)?
            .queryItems?.first(where: { $0.name == "last_id" })?.value
        XCTAssertEqual(request.httpMethod, "GET")
        XCTAssertEqual(url.path, "/api/tasks/task-1/events")
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-API-Key"), "fixture-key")

        let next = Self.lock.withLock {
            let index = Self.state.cursors.count
            Self.state.cursors.append(cursor ?? "missing")
            return Self.state.responses.indices.contains(index) ? Self.state.responses[index] : nil
        }
        switch next {
        case let .body(status, body):
            let response = HTTPURLResponse(url: url, statusCode: status, httpVersion: nil,
                                           headerFields: ["Content-Type": "text/event-stream"])!
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: Data(body.utf8))
            client?.urlProtocolDidFinishLoading(self)
        case let .transport(code):
            client?.urlProtocol(self, didFailWithError: URLError(code))
        case nil:
            XCTFail("Unexpected additional event connection")
            client?.urlProtocol(self, didFailWithError: URLError(.badURL))
        }
    }

    override func stopLoading() {}
}
