import Foundation
import XCTest
@testable import Scout

private final class SidebarURLProtocol: URLProtocol {
    static var requests: [URLRequest] = []
    static var body = "[]"
    static var status = 200
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        Self.requests.append(request)
        client?.urlProtocol(self, didReceive: HTTPURLResponse(url: request.url!, statusCode: Self.status,
            httpVersion: nil, headerFields: nil)!, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: Data(Self.body.utf8))
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}

final class ScoutSidebarServiceTests: XCTestCase {
    private var session: URLSession!
    private var profile: ScoutEndpointProfile {
        ScoutEndpointProfile(id: UUID(), name: "Vault", baseURL: "https://example.com/vault",
            transportType: .tailscale, authenticationState: .unconfigured, validationState: .unconfigured,
            lastConnectedAt: nil, authenticationMode: .localAPIKey)
    }
    override func setUp() {
        super.setUp()
        SidebarURLProtocol.requests = []
        SidebarURLProtocol.status = 200
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [SidebarURLProtocol.self]
        session = URLSession(configuration: config)
    }
    override func tearDown() { session.invalidateAndCancel(); super.tearDown() }

    func testThreadsRemainSearchableWhenProjectsCannotLoad() throws {
        let data = Data(#"{"threads":[{"id":1,"title":"Alpha","project_id":12,"origin_system":"openai"},{"id":2,"title":"Beta","origin_system":"codexify"},{"id":3,"title":"Archived Alpha","origin_system":"openai","archived_at":"2026-01-01"}]}"#.utf8)
        let threads = try XCTUnwrap(JSONDecoder().decode(ScoutChatThreadsResponse.self, from: data).threads)
        XCTAssertEqual(ScoutSidebarThreadFilter.withoutProjects(threads, source: "all", searchText: "").compactMap(\.id), [1, 2])
        XCTAssertEqual(ScoutSidebarThreadFilter.withoutProjects(threads, source: "openai", searchText: "alpha").compactMap(\.id), [1])
    }

    func testProjectsReadAndCreateUseAuthenticatedProjectRoute() async throws {
        SidebarURLProtocol.body = #"[{"id":1,"name":"General","system_role":"general"},{"id":2,"name":"Work"}]"#
        let list = await ScoutProjectsService.request(endpoint: profile, apiKey: "key", session: session)
        XCTAssertEqual(list.projects?.map(\.id), [1, 2])
        XCTAssertEqual(list.projects?.first?.isGeneral, true)
        XCTAssertEqual(SidebarURLProtocol.requests.first?.url?.path, "/vault/api/projects")
        XCTAssertEqual(SidebarURLProtocol.requests.first?.value(forHTTPHeaderField: "X-API-Key"), "key")

        SidebarURLProtocol.body = #"{"id":3,"name":"New"}"#
        let created = await ScoutProjectsService.request(endpoint: profile, apiKey: "key", name: "New", session: session)
        XCTAssertEqual(created.projects?.first?.id, 3)
        XCTAssertEqual(SidebarURLProtocol.requests.last?.httpMethod, "POST")
    }

    func testThreadPageRetainsProjectAndOriginAndSendsOffset() async throws {
        SidebarURLProtocol.body = #"{"threads":[{"id":7,"title":"Hello","project_id":2,"origin_system":"openai"}],"has_more":false}"#
        let result = await ScoutGuardianThreadsProbe.probe(endpoint: profile, apiKey: "key", offset: 200, session: session)
        XCTAssertEqual(result.threads?.first?.project_id, 2)
        XCTAssertEqual(result.threads?.first?.origin_system, "openai")
        XCTAssertEqual(SidebarURLProtocol.requests.first?.url?.query, "limit=200&offset=200")
    }

    func testNewThreadIncludesSelectedProject() async throws {
        SidebarURLProtocol.body = #"{"id":8,"thread":{"id":8,"title":"Work","project_id":2}}"#
        let result = await ScoutCreateThreadProbe.create(endpoint: profile, title: "Work", projectID: 2, apiKey: "key", session: session)
        XCTAssertEqual(result.thread?.project_id, 2)
        let request = try XCTUnwrap(SidebarURLProtocol.requests.first)
        var data = request.httpBody
        if data == nil, let stream = request.httpBodyStream {
            stream.open(); defer { stream.close() }
            var buffer = [UInt8](repeating: 0, count: 1024)
            let count = stream.read(&buffer, maxLength: buffer.count)
            if count > 0 { data = Data(buffer.prefix(count)) }
        }
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: try XCTUnwrap(data)) as? [String: Any])
        XCTAssertEqual(body["project_id"] as? Int, 2)
        XCTAssertEqual(body["title"] as? String, "Work")
    }

    func testMalformedSuccessfulResponsesAreErrors() async {
        SidebarURLProtocol.body = "{}"
        let projects = await ScoutProjectsService.request(endpoint: profile, apiKey: "key", session: session)
        let threads = await ScoutGuardianThreadsProbe.probe(endpoint: profile, apiKey: "key", session: session)
        XCTAssertNil(projects.projects)
        XCTAssertNotNil(projects.message)
        XCTAssertNil(threads.threads)
        XCTAssertNotNil(threads.message)
    }
}
