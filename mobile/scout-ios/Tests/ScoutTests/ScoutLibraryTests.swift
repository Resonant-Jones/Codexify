import Foundation
import XCTest
@testable import Scout

final class ScoutLibraryTests: XCTestCase {
    private var endpoint: ScoutEndpointProfile {
        .init(id: UUID(), name: "Test", baseURL: "https://library.example", transportType: .custom,
              authenticationState: .unconfigured, validationState: .reachable, lastConnectedAt: nil)
    }
    private func payload(_ records: [[String: Any]], source: ScoutLibrarySource, count: Any? = nil) throws -> Data {
        try JSONSerialization.data(withJSONObject: [source.listKey: records, "count": count ?? records.count])
    }

    func testFiltersReadOnlyContributingSourcesAndWidgetsInventNothing() {
        XCTAssertEqual(ScoutLibraryFilter.all.sources, [.uploadedImages, .generatedImages, .documents])
        XCTAssertEqual(ScoutLibraryFilter.images.sources, [.uploadedImages, .generatedImages])
        XCTAssertEqual(ScoutLibraryFilter.documents.sources, [.documents])
        XCTAssertTrue(ScoutLibraryFilter.widgets.sources.isEmpty)
    }

    func testSourceFamiliesPreserveCollidingCanonicalIDsAndUnknownOrigins() throws {
        let raw: [[String: Any]] = [["id": "shared", "filename": "image.png"]]
        let uploaded = ScoutLibraryService.project(try payload(raw, source: .uploadedImages), source: .uploadedImages)
        let generated = ScoutLibraryService.project(try payload(raw, source: .generatedImages), source: .generatedImages)
        let snapshot = ScoutLibrarySnapshot(sources: [uploaded, generated, uploaded])
        XCTAssertEqual(snapshot.resources.count, 2)
        XCTAssertEqual(Set(snapshot.resources.map(\.sourceID)), ["shared"])
        XCTAssertEqual(Set(snapshot.resources.map(\.id)), ["uploaded_image:shared", "generated_image:shared"])
        XCTAssertTrue(snapshot.resources.allSatisfy { $0.origin == "unknown" })
    }

    func testDocumentFamilyAndProvenanceAreIndependent() throws {
        let raw: [[String: Any]] = [
            ["id": 7, "artifact_type": "uploaded", "source_tag": "imported", "title": "A"],
            ["id": "7", "artifact_type": "generated", "source_tag": "generated", "title": "B"]
        ]
        let result = ScoutLibraryService.project(try payload(raw, source: .documents), source: .documents)
        XCTAssertEqual(result.coverage, .complete)
        XCTAssertEqual(result.resources.map(\.id), ["uploaded_document:7", "generated_document:7"])
        XCTAssertEqual(result.resources.map(\.origin), ["imported", "generated"])
        XCTAssertFalse(result.resources.contains(where: \.isImage))
    }

    func testMissingTypesAndMockRowsAreRejectedWithoutLosingValidResources() throws {
        let raw: [[String: Any]] = [
            ["id": "1", "artifact_type": "uploaded"],
            ["id": "2", "filename": "cannot-infer.pdf"],
            ["id": "3", "artifact_type": "generated", "mock": true],
            ["artifact_type": "uploaded"]
        ]
        let result = ScoutLibraryService.project(try payload(raw, source: .documents), source: .documents)
        XCTAssertEqual(result.coverage, .uncertain)
        XCTAssertEqual(result.resources.map(\.sourceID), ["1"])
        XCTAssertTrue(result.issue?.contains("3 resource") == true)
    }

    func testMalformedAndMissingCountsNeverBecomeEmptySuccess() throws {
        let bodies = [#"{}"#, #"{"images":[]}"#, #"{"images":[],"count":1}"#,
                      #"{"images":[],"count":false}"#, #"{"images":{},"count":0}"#,
                      #"{"images":[],"count":"0"}"#, "<html>Sign in</html>"]
        for body in bodies {
            let result = ScoutLibraryService.project(Data(body.utf8), source: .uploadedImages)
            XCTAssertEqual(result.coverage, .uncertain, body)
            XCTAssertNotNil(result.issue)
        }
        let empty = ScoutLibraryService.project(try payload([], source: .documents), source: .documents)
        XCTAssertEqual(empty.coverage, .empty)
        XCTAssertNil(empty.issue)
    }

    func testAtLimitIsBoundedAndFailureDoesNotDiscardOtherSources() throws {
        let records = (0..<ScoutLibraryService.limit).map { ["id": String($0)] }
        let bounded = ScoutLibraryService.project(try payload(records, source: .uploadedImages), source: .uploadedImages)
        let failed = ScoutLibrarySourceResult(source: .documents, resources: [], coverage: .failed, issue: "Offline")
        let snapshot = ScoutLibrarySnapshot(sources: [bounded, failed])
        XCTAssertEqual(bounded.coverage, .bounded)
        XCTAssertEqual(snapshot.resources.count, 100)
        XCTAssertEqual(snapshot.issues.count, 2)
    }

    func testMediaURLsKeepCredentialsOnSelectedHTTPSOrigin() throws {
        let profile = endpoint
        XCTAssertEqual(try ScoutLibraryService.mediaURL("/uploads/a.png?token=opaque", endpoint: profile).host, "library.example")
        XCTAssertNoThrow(try ScoutLibraryService.mediaURL("https://library.example:443/a", endpoint: profile))
        for value in ["https://other.example/a", "//other.example/a", "http://library.example/a",
                      "https://library.example:444/a", "https://user:password@library.example/a", "data:image/svg+xml,abc"] {
            XCTAssertThrowsError(try ScoutLibraryService.mediaURL(value, endpoint: profile), value)
        }
    }

    func testPagingDistinguishesAFullFinalPageFromMoreResults() throws {
        let records = (0..<100).map { ["id": String($0)] }
        let finalData = try JSONSerialization.data(withJSONObject: ["images": records, "count": 100, "next_offset": NSNull()])
        let final = ScoutLibraryService.project(finalData, source: .uploadedImages)
        XCTAssertEqual(final.coverage, .complete)
        XCTAssertNil(final.issue)
        XCTAssertNil(final.nextOffset)
        let moreData = try JSONSerialization.data(withJSONObject: ["images": records, "count": 100, "next_offset": 100])
        let more = ScoutLibraryService.project(moreData, source: .uploadedImages)
        XCTAssertEqual(more.coverage, .bounded)
        XCTAssertEqual(more.nextOffset, 100)
        XCTAssertNil(more.issue)
    }

    func testMalformedPagingCannotLoopOrSkipResources() throws {
        for next: Any in [false, "101", 100, 102, -1, 101.5] {
            let data = try JSONSerialization.data(withJSONObject: ["images": [["id": "a"]], "count": 1, "next_offset": next])
            let result = ScoutLibraryService.project(data, source: .uploadedImages, offset: 100)
            XCTAssertEqual(result.coverage, .uncertain)
            XCTAssertNil(result.nextOffset)
        }
        let empty = Data(#"{"images":[],"count":0,"next_offset":100}"#.utf8)
        XCTAssertEqual(ScoutLibraryService.project(empty, source: .uploadedImages, offset: 100).coverage, .uncertain)
    }

    func testNextPageFailureRetainsResourcesAndRetryOffsetThenRecovers() throws {
        let firstData = Data(#"{"images":[{"id":"a"}],"count":1,"next_offset":1}"#.utf8)
        let first = ScoutLibraryService.project(firstData, source: .uploadedImages)
        let failure = ScoutLibrarySourceResult(source: .uploadedImages, resources: [], coverage: .failed, issue: "Offline")
        let retry = first.appending(failure)
        XCTAssertEqual(retry.resources.map(\.sourceID), ["a"])
        XCTAssertEqual(retry.nextOffset, 1)
        XCTAssertEqual(retry.issue, "Offline")
        let finalData = Data(#"{"images":[{"id":"a"},{"id":"b"}],"count":2,"next_offset":null}"#.utf8)
        let recovered = retry.appending(ScoutLibraryService.project(finalData, source: .uploadedImages, offset: 1))
        XCTAssertEqual(recovered.resources.map(\.sourceID), ["a", "b"])
        XCTAssertEqual(recovered.coverage, .complete)
        XCTAssertNil(recovered.nextOffset)
        XCTAssertNil(recovered.issue)
    }

    func testNextPageRequestRetainsSourceAndAccountAuthentication() async throws {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [ScoutLibraryURLProtocol.self]
        let session = URLSession(configuration: configuration)
        defer { session.invalidateAndCancel(); ScoutLibraryURLProtocol.handler = nil }
        ScoutLibraryURLProtocol.handler = { request in
            let items = URLComponents(url: request.url!, resolvingAgainstBaseURL: false)!.queryItems!
            XCTAssertEqual(Dictionary(uniqueKeysWithValues: items.map { ($0.name, $0.value!) }),
                           ["limit": "100", "offset": "100", "tag": "generated"])
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-API-Key"), "test-key")
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!,
                    Data(#"{"images":[{"id":"older"}],"count":1,"next_offset":null}"#.utf8))
        }
        let page = await ScoutLibraryService(endpoint: endpoint, apiKey: "test-key", session: session).fetch(.generatedImages, offset: 100)
        XCTAssertEqual(page.resources.map(\.id), ["generated_image:older"])
        XCTAssertNil(page.issue)
        XCTAssertNil(page.nextOffset)
    }

    func testGeneratedImageRequestHasNoClientIdentityOrConversationScope() throws {
        let service = ScoutLibraryService(endpoint: endpoint, apiKey: "test-key")
        let url = try service.apiURL(path: ScoutLibrarySource.generatedImages.path,
                                    query: [.init(name: "limit", value: "100"), .init(name: "tag", value: "generated")])
        XCTAssertEqual(url.path, "/api/media/images")
        XCTAssertEqual(URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.map(\.name), ["limit", "tag"])
    }

    func testServiceUsesExistingAuthenticationAndReportsPartialHTTPFailure() async throws {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [ScoutLibraryURLProtocol.self]
        let session = URLSession(configuration: configuration, delegate: ScoutAuthNoRedirect(), delegateQueue: nil)
        defer { session.invalidateAndCancel(); ScoutLibraryURLProtocol.handler = nil }
        ScoutLibraryURLProtocol.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-API-Key"), "test-key")
            XCTAssertNil(request.value(forHTTPHeaderField: "X-Guardian-Account-Session"))
            let document = request.url!.path.contains("document-artifacts")
            let response = HTTPURLResponse(url: request.url!, statusCode: document ? 503 : 200, httpVersion: nil,
                                           headerFields: ["Content-Type": "application/json"])!
            return (response, Data((document ? "{}" : #"{"images":[{"id":"1","source_tag":"uploaded"}],"count":1}"#).utf8))
        }
        let service = ScoutLibraryService(endpoint: endpoint, apiKey: "test-key", session: session)
        let result = await service.load(.all)
        XCTAssertEqual(result.resources.count, 2)
        XCTAssertEqual(result.sources.first { $0.source == .documents }?.coverage, .failed)
        XCTAssertEqual(result.issues.count, 1)
    }

    func testOversizedResponseIsRefusedBeforeReadingBody() async throws {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [ScoutLibraryURLProtocol.self]
        let session = URLSession(configuration: configuration)
        defer { session.invalidateAndCancel(); ScoutLibraryURLProtocol.handler = nil }
        ScoutLibraryURLProtocol.handler = { request in
            (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil,
                             headerFields: ["Content-Length": "100000000"])!, Data())
        }
        do {
            _ = try await ScoutLibraryService(endpoint: endpoint, apiKey: "test-key", session: session)
                .read(URL(string: "https://library.example/uploads/test")!, maxBytes: 1024)
            XCTFail("Oversized response was accepted")
        } catch { XCTAssertTrue(error is ScoutLibraryError) }
    }

    func testDocumentPreviewKeepsFamilyAndEscapesCanonicalID() throws {
        let service = ScoutLibraryService(endpoint: endpoint, apiKey: "test-key")
        let resource = ScoutLibraryResource(sourceID: "a/b?c#d", family: "generated_document", title: "A",
                                            origin: "generated", sourceURL: nil, mimeType: nil, createdAt: nil)
        let url = try service.documentURL(resource)
        XCTAssertTrue(url.absoluteString.contains("a%2Fb%3Fc%23d"))
        XCTAssertEqual(URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems,
                       [.init(name: "artifact_type", value: "generated")])
    }

    func testMissingRemoteAccountNeverFallsBackToAPIKey() async throws {
        var profile = endpoint
        profile.authenticationMode = .remoteSession
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [ScoutLibraryURLProtocol.self]
        let session = URLSession(configuration: configuration)
        defer { session.invalidateAndCancel(); ScoutLibraryURLProtocol.handler = nil }
        ScoutLibraryURLProtocol.handler = { request in
            XCTFail("Missing account session must not send a request")
            throw URLError(.cancelled)
        }
        let result = await ScoutLibraryService(endpoint: profile, apiKey: "must-not-use", session: session).load(.all)
        XCTAssertTrue(result.resources.isEmpty)
        XCTAssertTrue(result.sources.allSatisfy { $0.coverage == .failed })
        XCTAssertNotNil(result.commonFailure)
    }

    func testResponseAfterAccountGenerationChangeIsDiscarded() async throws {
        let key = "scout.accountSessionGeneration"
        let before = UserDefaults.standard.integer(forKey: key)
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [ScoutLibraryURLProtocol.self]
        let session = URLSession(configuration: configuration)
        defer {
            session.invalidateAndCancel(); ScoutLibraryURLProtocol.handler = nil
            UserDefaults.standard.set(before, forKey: key)
        }
        ScoutLibraryURLProtocol.handler = { request in
            UserDefaults.standard.set(before + 1, forKey: key)
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!,
                    Data(#"{"documents":[{"id":"private","artifact_type":"uploaded"}],"count":1}"#.utf8))
        }
        let result = await ScoutLibraryService(endpoint: endpoint, apiKey: "test-key", session: session).load(.documents)
        XCTAssertTrue(result.resources.isEmpty)
        XCTAssertEqual(result.sources.first?.coverage, .failed)
    }
}

private final class ScoutLibraryURLProtocol: URLProtocol {
    static var handler: ((URLRequest) throws -> (HTTPURLResponse, Data))?
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        do {
            let (response, data) = try Self.handler!(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch { client?.urlProtocol(self, didFailWithError: error) }
    }
    override func stopLoading() {}
}
