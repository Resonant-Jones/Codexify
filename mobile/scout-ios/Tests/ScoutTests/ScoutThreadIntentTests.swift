import Foundation
import AppIntents
import XCTest
@testable import Scout

private final class ThreadIntentURLProtocol: URLProtocol {
    static var requests: [URLRequest] = []
    static var status = 200
    static var body = #"{"threads":[{"id":7,"title":"Existing"}],"has_more":false}"#
    static var onRequest: (() -> Void)?
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        Self.requests.append(request)
        Self.onRequest?()
        client?.urlProtocol(self, didReceive: HTTPURLResponse(url: request.url!, statusCode: Self.status,
            httpVersion: nil, headerFields: nil)!, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: Data(Self.body.utf8))
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}

final class ScoutThreadIntentTests: XCTestCase {
    private var session: URLSession!
    override func setUp() {
        super.setUp()
        ThreadIntentURLProtocol.requests = []
        ThreadIntentURLProtocol.status = 200
        ThreadIntentURLProtocol.body = #"{"threads":[{"id":7,"title":"Existing"}],"has_more":false}"#
        ThreadIntentURLProtocol.onRequest = nil
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [ThreadIntentURLProtocol.self]
        session = URLSession(configuration: config)
    }
    override func tearDown() {
        session.invalidateAndCancel()
        ThreadIntentURLProtocol.onRequest = nil
        super.tearDown()
    }

    private func profile(_ url: String = "https://personal.example/vault", id: UUID = UUID(),
                         mode: ScoutEndpointAuthenticationMode = .localAPIKey) -> ScoutEndpointProfile {
        ScoutEndpointProfile(id: id, name: "Personal Vault", baseURL: url, transportType: .tailscale,
            authenticationState: .unconfigured, validationState: .unconfigured, lastConnectedAt: nil, authenticationMode: mode)
    }
    private func context(_ p: ScoutEndpointProfile? = nil, key: String = "fixture-operator") throws -> ScoutThreadActionContext {
        try ScoutThreadActionContext(endpoint: p ?? profile(), apiKey: key)
    }
    private func remote(_ p: ScoutEndpointProfile, user: String, token: String = "fixture-account") throws -> ScoutThreadActionContext {
        try ScoutThreadActionContext(endpoint: p, accountSession: ScoutAccountSession(token: token, userID: user,
            expiresAt: Date().addingTimeInterval(3600), profileID: p.id, origin: ScoutAccessOAuth.origin(for: p)))
    }
    private func actions(_ context: ScoutThreadActionContext) -> ScoutThreadActions {
        ScoutThreadActions(current: { context }, session: session)
    }

    func testActualReadIntentAndQueryUseProtectedExistingService() async throws {
        let selected = try context()
        let result = try await ListScoutThreadsIntent().perform(using: actions(selected))
        let entities = try XCTUnwrap(result.value)
        XCTAssertEqual(entities.map(\.id), [selected.reference(id: 7, title: nil).id])
        XCTAssertEqual(entities.first?.title, "Existing")
        let resolved = try await ScoutThreadEntityQuery().entities(for: entities.map(\.id), using: actions(selected))
        XCTAssertEqual(resolved.first?.title, "Existing")
        XCTAssertEqual(ThreadIntentURLProtocol.requests.count, 2)
        for request in ThreadIntentURLProtocol.requests {
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(request.url?.absoluteString, "https://personal.example/vault/api/chat/threads")
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-API-Key"), "fixture-operator")
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        }
        let suggestions = try await ScoutThreadEntityQuery().suggestedEntities()
        XCTAssertTrue(suggestions.isEmpty)
        XCTAssertEqual(ThreadIntentURLProtocol.requests.count, 2)
    }

    func testCreateIntentConfirmsBeforeExistingServiceAndReturnsCanonicalID() async throws {
        let selected = try context()
        ThreadIntentURLProtocol.body = #"{"id":12,"thread":{"id":12,"title":"Canonical"}}"#
        let intent = CreateScoutThreadIntent()
        intent.threadTitle = "  New thread  "
        var confirmed = false
        let result = try await intent.perform(using: actions(selected)) { captured, title in
            XCTAssertTrue(ThreadIntentURLProtocol.requests.isEmpty)
            XCTAssertEqual(captured.scope, selected.scope)
            XCTAssertEqual(title, "New thread")
            confirmed = true
        }
        XCTAssertTrue(confirmed)
        XCTAssertEqual(result.value?.id, selected.reference(id: 12, title: nil).id)
        XCTAssertEqual(result.value?.title, "Canonical")
        let request = try XCTUnwrap(ThreadIntentURLProtocol.requests.first)
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.url?.path, "/vault/api/chat/threads")
        // URLProtocol supplies body streams on some Foundation versions; consume only fixture bytes.
        var data = request.httpBody
        if data == nil, let stream = request.httpBodyStream {
            stream.open(); defer { stream.close() }
            var buffer = [UInt8](repeating: 0, count: 1024)
            let count = stream.read(&buffer, maxLength: buffer.count)
            if count > 0 { data = Data(buffer.prefix(count)) }
        }
        let body = try XCTUnwrap(data)
        XCTAssertEqual(try JSONSerialization.jsonObject(with: body) as? [String: String], ["title": "New thread"])
        XCTAssertEqual(ThreadIntentURLProtocol.requests.count, 1) // No send/completion/retry.
    }

    func testScopeIncludesProfileNodeBasePathModeAndAccountButNeverCredentials() throws {
        let p = profile()
        let selected = try context(p)
        XCTAssertEqual(selected.scope, try context(p, key: "replacement-fixture-key").scope)
        XCTAssertFalse(selected.reference(id: 7, title: nil).id.contains("fixture-operator"))
        for different in [profile(p.baseURL), profile("https://other.example/vault", id: p.id),
                          profile("https://personal.example/other", id: p.id)] {
            XCTAssertNotEqual(selected.scope, try context(different).scope)
        }
        let pRemote = profile(p.baseURL, id: p.id, mode: .remoteSession)
        let a = try remote(pRemote, user: "account-a")
        XCTAssertNotEqual(a.scope, selected.scope)
        XCTAssertNotEqual(a.scope, try remote(pRemote, user: "account-b").scope)
        XCTAssertEqual(a.scope, try remote(pRemote, user: "account-a", token: "replacement-account").scope)
        XCTAssertFalse(a.isCurrent(try remote(pRemote, user: "account-a", token: "replacement-account")))
        XCTAssertEqual(selected.scope, try context(profile("https://PERSONAL.example:443/vault/", id: p.id)).scope)
    }

    func testWrongScopeAndMalformedReferenceFailBeforeDispatch() async throws {
        let selected = try context()
        for id in [try context().reference(id: 7, title: nil).id, selected.reference(id: 0, title: nil).id,
                   selected.reference(id: 7, title: nil).id + "garbage"] {
            do { _ = try await actions(selected).resolve([id]); XCTFail("Unexpected resolution") }
            catch { XCTAssertEqual(error as? ScoutThreadActionError, .unavailableReference) }
        }
        XCTAssertTrue(ThreadIntentURLProtocol.requests.isEmpty)
    }

    func testDeletedThreadIsNotResolvedFromCachedTitleAndPartialPageIsExplicit() async throws {
        let selected = try context()
        let id = selected.reference(id: 99, title: "Cached title").id
        let missing = try await actions(selected).resolve([id])
        XCTAssertTrue(missing.isEmpty)
        ThreadIntentURLProtocol.body = #"{"threads":[],"has_more":true}"#
        do { _ = try await actions(selected).resolve([id]); XCTFail("Partial catalog reported missing") }
        catch { XCTAssertEqual(error as? ScoutThreadActionError, .incompleteCatalog) }
    }

    func testCancelledConfirmationAndChangedProfileDoNotWrite() async throws {
        var selected = try context()
        let service = ScoutThreadActions(current: { selected }, session: session)
        do {
            _ = try await service.create(title: "New") { _, _ in throw CancellationError() }
            XCTFail("Cancelled confirmation wrote")
        } catch { XCTAssertTrue(error is CancellationError) }
        do {
            _ = try await service.create(title: "New") { _, _ in selected = try self.context() }
            XCTFail("Changed profile wrote")
        } catch { XCTAssertEqual(error as? ScoutThreadActionError, .changedConnection) }
        XCTAssertTrue(ThreadIntentURLProtocol.requests.isEmpty)
    }

    func testDelayedReadOrWriteCannotPublishUnderChangedProfile() async throws {
        for write in [false, true] {
            var selected = try context()
            let service = ScoutThreadActions(current: { selected }, session: session)
            ThreadIntentURLProtocol.body = write ? #"{"id":12}"# : #"{"threads":[],"has_more":false}"#
            ThreadIntentURLProtocol.onRequest = { selected = try! self.context() }
            do {
                if write { _ = try await service.create(title: "New") { _, _ in } }
                else { _ = try await service.list() }
                XCTFail("Stale result published")
            } catch { XCTAssertEqual(error as? ScoutThreadActionError, .changedConnection) }
        }
        XCTAssertEqual(ThreadIntentURLProtocol.requests.count, 2)
    }

    func testRemoteReadPinsCanonicalSessionAndNeverFallsBackToKey() async throws {
        let p = profile(mode: .remoteSession)
        let selected = try remote(p, user: "fixture-user")
        _ = try await actions(selected).list()
        let request = try XCTUnwrap(ThreadIntentURLProtocol.requests.first)
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer fixture-account")
        XCTAssertNil(request.value(forHTTPHeaderField: "X-API-Key"))
        XCTAssertThrowsError(try ScoutThreadActionContext(endpoint: p, apiKey: "fixture-key"))
    }

    func testInvalidReadAndUncertainWritesNeverProduceEntitiesOrRetry() async throws {
        let selected = try context()
        ThreadIntentURLProtocol.body = #"{"threads":[{"id":7},{"id":7}]}"#
        do { _ = try await actions(selected).list(); XCTFail("Duplicate identities accepted") }
        catch { XCTAssertEqual(error as? ScoutThreadActionError, .invalidResponse) }
        for body in ["{}", #"{"id":0}"#, #"{"id":7,"thread":{"id":8}}"#] {
            ThreadIntentURLProtocol.body = body
            do { _ = try await actions(selected).create(title: "New") { _, _ in }; XCTFail("Unconfirmed write claimed") }
            catch { XCTAssertEqual(error as? ScoutThreadActionError, .uncertainWrite) }
        }
        ThreadIntentURLProtocol.status = 503
        do { _ = try await actions(selected).create(title: "New") { _, _ in }; XCTFail("Failed write claimed") }
        catch { XCTAssertEqual(error as? ScoutThreadActionError, .uncertainWrite) }
        XCTAssertEqual(ThreadIntentURLProtocol.requests.count, 5)
    }

    func testAcceptedWriteAndLostAuthenticationCannotClaimCreation() async throws {
        let selected = try context()
        ThreadIntentURLProtocol.status = 202
        ThreadIntentURLProtocol.body = #"{"id":12}"#
        do { _ = try await actions(selected).create(title: "New") { _, _ in }; XCTFail("Acceptance labeled creation") }
        catch { XCTAssertEqual(error as? ScoutThreadActionError, .uncertainWrite) }
        var authorized = true
        let service = ScoutThreadActions(current: {
            guard authorized else { throw ScoutThreadActionError.authenticationRequired }
            return selected
        }, session: session)
        do {
            _ = try await service.create(title: "New") { _, _ in authorized = false }
            XCTFail("Credential loss wrote")
        } catch { XCTAssertEqual(error as? ScoutThreadActionError, .changedConnection) }
        XCTAssertEqual(ThreadIntentURLProtocol.requests.count, 1)
    }
}
