import XCTest
@testable import Scout

@MainActor
final class ScoutComposerFlowTests: XCTestCase {
    private func scope(thread: Int = 4, account: Int = 0, node: String = "https://node.example.test") -> ScoutComposerFlow.Scope {
        let profile = ScoutEndpointProfile(id: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!, name: "Test", baseURL: node,
            transportType: .custom, authenticationState: .authenticated, validationState: .reachable, lastConnectedAt: nil)
        return .init(connection: .init(endpoint: profile), threadID: thread, accountGeneration: account)
    }
    private func accepted(_ id: Int = 42) -> ScoutSendMessageResult { .init(httpStatus: 201, messageId: id, message: "Message sent.") }
    private func completion(_ code: Int? = 202, task: String? = "task-1") -> ScoutCompleteThreadResult {
        .init(httpStatus: code, taskId: task, turnId: "turn-1", messagesUrl: nil, traceUrl: nil, acceptanceStatus: "accepted", message: "Fixture response")
    }
    private func prepared() -> ScoutComposerFlow {
        let flow = ScoutComposerFlow()
        flow.select(scope())
        flow.draft = "A real draft\nwith multiple lines"
        return flow
    }

    func testEmptyMessageNeverDispatches() async {
        let flow = prepared()
        flow.draft = " \n "
        await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in XCTFail("Empty write"); return self.accepted() },
                          complete: { XCTFail("Empty completion"); return self.completion() })
        XCTAssertEqual(flow.phase, .idle)
        XCTAssertFalse(flow.canSubmit)
    }

    func testAcceptancePrecedesCompletionAndPreservesCanonicalID() async {
        let flow = prepared(), original = flow.draft
        var order: [String] = []
        await flow.submit(scope: scope(), isCurrent: { true }, save: { text in
            XCTAssertEqual(text, original)
            order.append("save")
            return self.accepted()
        }, complete: {
            XCTAssertEqual(flow.acceptedMessageID, 42)
            order.append("complete")
            return self.completion()
        })
        XCTAssertEqual(order, ["save", "complete"])
        XCTAssertEqual(flow.acceptedMessageID, 42)
        XCTAssertEqual(flow.taskID, "task-1")
        XCTAssertEqual(flow.phase, .pending)
        XCTAssertEqual(flow.draft, "")
        XCTAssertFalse(flow.canSubmit)
    }

    func testRapidRepeatedTapsWriteAndRequestOnlyOnce() async {
        let flow = prepared(), started = expectation(description: "Write started")
        var resume: CheckedContinuation<ScoutSendMessageResult, Never>?
        var writes = 0, requests = 0
        let operation = Task {
            await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in
                writes += 1
                return await withCheckedContinuation { resume = $0; started.fulfill() }
            }, complete: { requests += 1; return self.completion() })
        }
        await fulfillment(of: [started], timeout: 2)
        await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in writes += 1; return self.accepted() }, complete: { requests += 1; return self.completion() })
        resume?.resume(returning: accepted())
        await operation.value
        await flow.requestResponse(scope: scope(), isCurrent: { true }, complete: { requests += 1; return self.completion() })
        XCTAssertEqual(writes, 1)
        XCTAssertEqual(requests, 1)
    }

    func testRejectedMessageRetainsDraftAndDoesNotRequestCompletion() async {
        let flow = prepared(), original = flow.draft
        await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in .init(httpStatus: 400, messageId: nil, message: "Rejected") }, complete: { XCTFail("Completion after rejection"); return self.completion() })
        XCTAssertEqual(flow.phase, .messageRejected)
        XCTAssertEqual(flow.draft, original)
        XCTAssertTrue(flow.canSubmit)
        XCTAssertNil(flow.acceptedMessageID)
    }

    func testUnknownMessageOutcomeBlocksReplayAndCompletion() async {
        for code: Int? in [nil, 500, 408] {
            let flow = prepared(), original = flow.draft
            var writes = 0
            for _ in 0..<2 {
                await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in writes += 1; return .init(httpStatus: code, messageId: nil, message: "Unknown") }, complete: { XCTFail("Completion after unknown write"); return self.completion() })
            }
            XCTAssertEqual(writes, 1)
            XCTAssertEqual(flow.draft, original)
            XCTAssertEqual(flow.phase, .unconfirmed)
        }
    }

    func testSuccessfulHTTPWithoutMessageIdentityCannotAdvance() async {
        let flow = prepared()
        await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in .init(httpStatus: 201, messageId: nil, message: "Malformed") }, complete: { XCTFail("Missing canonical ID"); return self.completion() })
        XCTAssertEqual(flow.phase, .unconfirmed)
        XCTAssertFalse(flow.draft.isEmpty)
    }

    func testCompletionRejectionRecoversWithoutAnotherMessageWrite() async {
        let flow = prepared()
        var writes = 0, requests = 0
        await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in writes += 1; return self.accepted() }, complete: { requests += 1; return self.completion(403, task: nil) })
        XCTAssertEqual(flow.phase, .responseRejected)
        XCTAssertEqual(flow.acceptedMessageID, 42)
        flow.draft = "Next unsent draft"
        XCTAssertFalse(flow.canSubmit)
        await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in writes += 1; return self.accepted() }, complete: { XCTFail("Write recovery"); return self.completion() })
        await flow.requestResponse(scope: scope(), isCurrent: { true }, complete: { requests += 1; return self.completion() })
        XCTAssertEqual(writes, 1)
        XCTAssertEqual(requests, 2)
        XCTAssertEqual(flow.acceptedMessageID, 42)
        XCTAssertEqual(flow.draft, "Next unsent draft")
    }

    func testUncertainOrAlreadyPendingCompletionCannotBeRepeated() async {
        for code: Int? in [nil, 429, 500, 202] {
            let flow = prepared()
            var requests = 0
            await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in self.accepted() }, complete: { requests += 1; return self.completion(code, task: nil) })
            await flow.requestResponse(scope: scope(), isCurrent: { true }, complete: { requests += 1; return self.completion() })
            XCTAssertEqual(flow.phase, .unconfirmed)
            XCTAssertEqual(flow.acceptedMessageID, 42)
            XCTAssertEqual(requests, 1)
            XCTAssertEqual(flow.draft, "")
        }
    }

    func testScopeChangesDuringMessageWriteNeverDispatchCompletionOrPublishOldState() async {
        for changed in [scope(thread: 5), scope(account: 1), scope(node: "https://other.example.test")] {
            let flow = prepared(), started = expectation(description: "Write started")
            var resume: CheckedContinuation<ScoutSendMessageResult, Never>?
            let operation = Task {
                await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in
                    await withCheckedContinuation { resume = $0; started.fulfill() }
                }, complete: { XCTFail("Cross-scope completion"); return self.completion() })
            }
            await fulfillment(of: [started], timeout: 2)
            flow.select(changed)
            flow.draft = "New scope draft"
            resume?.resume(returning: accepted())
            await operation.value
            XCTAssertEqual(flow.scope, changed)
            XCTAssertNil(flow.acceptedMessageID)
            XCTAssertNil(flow.taskID)
            XCTAssertEqual(flow.draft, "New scope draft")
        }
    }

    func testAccountChangeDuringCompletionDiscardsLateAcceptance() async {
        let flow = prepared(), started = expectation(description: "Completion started")
        var resume: CheckedContinuation<ScoutCompleteThreadResult, Never>?
        let operation = Task {
            await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in self.accepted() }, complete: {
                await withCheckedContinuation { resume = $0; started.fulfill() }
            })
        }
        await fulfillment(of: [started], timeout: 2)
        flow.select(scope(account: 1))
        resume?.resume(returning: completion())
        await operation.value
        XCTAssertNil(flow.taskID)
        XCTAssertEqual(flow.phase, .idle)
    }

    func testCredentialChangeWithoutViewUpdateStopsFollowingOperation() async {
        let flow = prepared()
        var current = true
        await flow.submit(scope: scope(), isCurrent: { current }, save: { _ in current = false; return self.accepted() }, complete: { XCTFail("Changed credential"); return self.completion() })
        XCTAssertNil(flow.scope)
        XCTAssertEqual(flow.draft, "")
    }

    func testCancellationAfterDispatchNeverRequestsCompletion() async {
        let flow = prepared(), started = expectation(description: "Write started")
        var resume: CheckedContinuation<ScoutSendMessageResult, Never>?
        let operation = Task {
            await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in
                await withCheckedContinuation { resume = $0; started.fulfill() }
            }, complete: { XCTFail("Cancelled continuation"); return self.completion() })
        }
        await fulfillment(of: [started], timeout: 2)
        operation.cancel()
        resume?.resume(returning: accepted())
        await operation.value
        XCTAssertEqual(flow.phase, .responseRejected)
        XCTAssertEqual(flow.acceptedMessageID, 42)
        XCTAssertEqual(flow.draft, "")
        XCTAssertFalse(flow.canSubmit)
        XCTAssertTrue(flow.canRequestResponse)
    }

    func testCancellationDoesNotDiscardKnownCompletionAcceptance() async {
        let flow = prepared(), started = expectation(description: "Completion started")
        var resume: CheckedContinuation<ScoutCompleteThreadResult, Never>?
        let operation = Task {
            await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in self.accepted() }, complete: {
                await withCheckedContinuation { resume = $0; started.fulfill() }
            })
        }
        await fulfillment(of: [started], timeout: 2)
        operation.cancel()
        resume?.resume(returning: completion())
        await operation.value
        XCTAssertEqual(flow.acceptedMessageID, 42)
        XCTAssertEqual(flow.taskID, "task-1")
        XCTAssertEqual(flow.phase, .pending)
        XCTAssertFalse(flow.canRequestResponse)
    }

    func testOptionsDismissalPreservesDraftAndDoesNotDispatch() {
        let flow = prepared(), original = flow.draft
        flow.optionsPresented = true
        flow.optionsPresented = false // Same binding used by Done and native sheet dismissal.
        XCTAssertEqual(flow.draft, original)
        XCTAssertEqual(flow.phase, .idle)
        XCTAssertNil(flow.acceptedMessageID)
    }

    func testMessageOnlyIsTheExistingAlternativeAndDoesNotComplete() async {
        let flow = prepared()
        await flow.submit(scope: scope(), messageOnly: true, isCurrent: { true }, save: { _ in self.accepted() }, complete: { XCTFail("Message-only completion"); return self.completion() })
        XCTAssertEqual(flow.phase, .idle)
        XCTAssertEqual(flow.acceptedMessageID, 42)
        XCTAssertEqual(flow.draft, "")
    }

    func testOnlyExactTaskTerminalEvidenceReleasesPendingSend() async {
        let flow = prepared()
        await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in self.accepted() }, complete: { self.completion() })
        flow.draft = "Next turn"
        flow.observationEnded(taskID: "task-1", scope: scope())
        XCTAssertFalse(flow.canSubmit)
        XCTAssertFalse(flow.terminal("task.completed", taskID: "other", scope: scope()))
        XCTAssertFalse(flow.terminal("task.completed", taskID: "task-1", scope: scope(account: 1)))
        XCTAssertFalse(flow.terminal("task.started", taskID: "task-1", scope: scope()))
        XCTAssertTrue(flow.terminal("task.completed", taskID: "task-1", scope: scope()))
        XCTAssertTrue(flow.canSubmit)
        XCTAssertFalse(flow.terminal("task.failed", taskID: "task-1", scope: scope()))
        XCTAssertEqual(flow.acceptedMessageID, 42)
    }

    func testSwitchAwayAndBackRejectsOldInFlightResult() async {
        let flow = prepared(), started = expectation(description: "Write started")
        var resume: CheckedContinuation<ScoutSendMessageResult, Never>?
        let operation = Task {
            await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in
                await withCheckedContinuation { resume = $0; started.fulfill() }
            }, complete: { XCTFail("Stale operation after returning to scope"); return self.completion() })
        }
        await fulfillment(of: [started], timeout: 2)
        flow.select(scope(thread: 9))
        flow.select(scope())
        flow.draft = "New visit"
        resume?.resume(returning: accepted())
        await operation.value
        XCTAssertNil(flow.acceptedMessageID)
        XCTAssertEqual(flow.draft, "New visit")
    }

    func testExistingHTTPServicesComposeWithoutChangingWireContracts() async {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [ComposerURLProtocol.self]
        let network = URLSession(configuration: config)
        defer { network.invalidateAndCancel(); ComposerURLProtocol.paths = [] }
        ComposerURLProtocol.paths = []
        let endpoint = ScoutEndpointProfile(id: UUID(), name: "Test", baseURL: "https://composer.example.test",
            transportType: .custom, authenticationState: .authenticated, validationState: .reachable, lastConnectedAt: nil)
        let flow = ScoutComposerFlow()
        let target = ScoutComposerFlow.Scope(connection: .init(endpoint: endpoint), threadID: 4, accountGeneration: 0)
        flow.select(target)
        flow.draft = "Preserve this message"
        await flow.submit(scope: target, isCurrent: { true }, save: { text in
            await ScoutGuardianSendMessageService.send(endpoint: endpoint, threadId: 4, content: text, apiKey: "fixture-key", session: network)
        }, complete: {
            await ScoutGuardianCompleteThreadService.complete(endpoint: endpoint, threadId: 4, apiKey: "fixture-key", session: network)
        })
        XCTAssertEqual(ComposerURLProtocol.paths, ["/api/chat/4/messages", "/api/chat/4/complete"])
        XCTAssertEqual(flow.acceptedMessageID, 42)
        XCTAssertEqual(flow.taskID, "wire-task")
        XCTAssertEqual(flow.phase, .pending)
    }

    func testFailureAndCancellationNeverReportCompletion() async {
        for event in ["task.failed", "task.cancelled"] {
            let flow = prepared()
            await flow.submit(scope: scope(), isCurrent: { true }, save: { _ in self.accepted() }, complete: { self.completion() })
            XCTAssertTrue(flow.terminal(event, taskID: "task-1", scope: scope()))
            XCTAssertTrue(flow.status?.contains("No assistant message was synthesized") == true)
        }
    }
}

private final class ComposerURLProtocol: URLProtocol {
    static var paths: [String] = []
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        let path = request.url!.path
        Self.paths.append(path)
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-API-Key"), "fixture-key")
        let body = path.hasSuffix("messages") ? #"{"message":{"id":42}}"# : #"{"task_id":"wire-task","acceptance_status":"accepted"}"#
        let response = HTTPURLResponse(url: request.url!, statusCode: path.hasSuffix("messages") ? 201 : 202, httpVersion: nil, headerFields: ["Content-Type": "application/json"])!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: Data(body.utf8))
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}
