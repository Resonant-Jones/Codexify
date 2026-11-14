import Foundation
import XCTest
@testable import Scout

final class ScoutDocumentReaderTests: XCTestCase {
    func testPageBoundariesPreserveMultibyteText() {
        let source = String(repeating: "a", count: ScoutDocumentPage.byteLimit - 1)
            + String(repeating: "🧭e\u{0301}\n", count: 2_000)
        var page = ScoutDocumentPage(source)
        var recovered = page.text
        XCTAssertEqual(page.text.utf8.count, ScoutDocumentPage.byteLimit - 1)
        while let next = page.nextStart {
            page = ScoutDocumentPage(source, from: next)
            XCTAssertLessThanOrEqual(page.text.utf8.count, ScoutDocumentPage.byteLimit)
            recovered += page.text
        }
        XCTAssertEqual(Array(recovered.utf8), Array(source.utf8))
    }

    func testCacheEvictsOldestEntriesAndSkipsOversizeDocuments() async {
        let cache = ScoutDocumentCache(maxBytes: 12)
        let connection = ScoutConnectionIdentity(endpoint: endpoint())
        func key(_ name: String) -> ScoutDocumentCache.Key {
            .init(connection: connection, accountGeneration: 0, authorization: Data([1]),
                  url: URL(string: "https://scout.example/\(name)")!)
        }
        let detail = ScoutDocumentDetail(id: nil, document_id: nil, filename: nil, title: nil,
            mime_type: nil, filesize: nil, src_url: nil, parsed_text: "123456", created_at: nil)
        await cache.insert(detail, for: key("a"))
        await cache.insert(detail, for: key("b"))
        _ = await cache.detail(for: key("a"))
        await cache.insert(detail, for: key("c"))
        let newest = await cache.detail(for: key("c"))
        let retained = await cache.detail(for: key("a"))
        let evicted = await cache.detail(for: key("b"))
        XCTAssertEqual(newest, detail)
        XCTAssertEqual(retained, detail)
        XCTAssertNil(evicted)

        let tinyCache = ScoutDocumentCache(maxBytes: 5)
        await tinyCache.insert(detail, for: key("a"))
        let oversized = await tinyCache.detail(for: key("a"))
        XCTAssertNil(oversized)
    }

    func testExpiredDocumentCannotBeReused() async {
        let cache = ScoutDocumentCache(lifetime: .seconds(2))
        let key = ScoutDocumentCache.Key(connection: .init(endpoint: endpoint()), accountGeneration: 0,
            authorization: Data([1]), url: URL(string: "https://scout.example/document")!)
        let detail = ScoutDocumentDetail(id: "doc", document_id: nil, filename: nil, title: nil,
            mime_type: nil, filesize: nil, src_url: nil, parsed_text: "Example", created_at: nil)
        let now = ContinuousClock.now
        await cache.insert(detail, for: key, now: now)
        let fresh = await cache.detail(for: key, now: now.advanced(by: .seconds(1)))
        let expired = await cache.detail(for: key, now: now.advanced(by: .seconds(2)))
        XCTAssertEqual(fresh, detail)
        XCTAssertNil(expired)
    }

    func testReopenUsesCacheButCredentialConnectionAndGenerationChangesFetchAgain() async {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [ScoutDocumentTestProtocol.self]
        let session = URLSession(configuration: configuration)
        defer { session.invalidateAndCancel() }
        let cache = ScoutDocumentCache()
        let profile = endpoint()
        func read(_ endpoint: ScoutEndpointProfile, key: String?, generation: Int = 0,
                  reload: Bool = false) async -> ScoutDocumentDetailResult {
            await ScoutDocumentDetailProbe.probe(endpoint: endpoint, documentId: "doc", apiKey: key,
                session: session, cache: cache, accountGeneration: generation, reload: reload)
        }
        let initial = await read(profile, key: "first")
        let reopened = await read(profile, key: "first")
        XCTAssertEqual(initial.httpStatus, 200)
        XCTAssertNil(reopened.httpStatus)
        XCTAssertEqual(initial.detail?.parsed_text, "fixture")
        XCTAssertEqual(reopened.detail, initial.detail)

        let changedKey = await read(profile, key: "replacement")
        let changedNode = await read(endpoint("https://other.example"), key: "first")
        let changedAccount = await read(profile, key: "first", generation: 1)
        let refreshed = await read(profile, key: "first", reload: true)
        let deniedRefresh = await ScoutDocumentDetailProbe.probe(endpoint: profile, documentId: "denied", apiKey: "first",
            session: session, cache: cache)
        let repeatedDenial = await ScoutDocumentDetailProbe.probe(endpoint: profile, documentId: "denied", apiKey: "first",
            session: session, cache: cache)
        let anonymous = await read(profile, key: nil)
        let anonymousAgain = await read(profile, key: nil)
        XCTAssertEqual([changedKey.httpStatus, changedNode.httpStatus, changedAccount.httpStatus,
            refreshed.httpStatus, deniedRefresh.httpStatus, repeatedDenial.httpStatus,
            anonymous.httpStatus, anonymousAgain.httpStatus], [200, 200, 200, 200, 403, 403, 200, 200])
    }

    func testTruncatedPreviewIsNotCachedAsTheFullDocument() async {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [ScoutDocumentTestProtocol.self]
        let session = URLSession(configuration: configuration)
        defer { session.invalidateAndCancel() }
        let cache = ScoutDocumentCache()
        let profile = endpoint()

        func read(id: String, preview: Bool) async -> ScoutDocumentDetailResult {
            await ScoutDocumentDetailProbe.probe(endpoint: profile, documentId: id, apiKey: "test",
                session: session, cache: cache, preview: preview)
        }

        let preview = await read(id: "large", preview: true)
        XCTAssertEqual(preview.detail?.parsed_text, "first page")
        XCTAssertEqual(preview.detail?.text_preview_truncated, true)
        let full = await read(id: "large", preview: false)
        XCTAssertEqual(full.httpStatus, 200)
        XCTAssertEqual(full.detail?.parsed_text, "first page and the remainder")
        let reopened = await read(id: "large", preview: true)
        XCTAssertNil(reopened.httpStatus)
        XCTAssertEqual(reopened.detail, full.detail)

        // An older server ignores the preview parameter and returns a full document.
        let older = await read(id: "older", preview: true)
        XCTAssertEqual(older.detail?.parsed_text, "fixture")
        XCTAssertNil(older.detail?.text_preview_truncated)
        let reopenedOlder = await read(id: "older", preview: true)
        XCTAssertNil(reopenedOlder.httpStatus)
        XCTAssertEqual(reopenedOlder.detail, older.detail)
    }

    private func endpoint(_ url: String = "https://scout.example") -> ScoutEndpointProfile {
        .init(id: UUID(), name: "Test", baseURL: url, transportType: .custom,
              authenticationState: .unconfigured, validationState: .unconfigured, lastConnectedAt: nil)
    }
}

private final class ScoutDocumentTestProtocol: URLProtocol {
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        guard let url = request.url, let client else { return }
        let status = url.lastPathComponent == "denied" ? 403 : 200
        let response = HTTPURLResponse(url: url, statusCode: status, httpVersion: nil, headerFields: nil)!
        client.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        let body: String
        if url.lastPathComponent == "large" {
            let preview = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?
                .contains(URLQueryItem(name: "preview", value: "true")) == true
            body = preview
                ? #"{"id":"large","parsed_text":"first page","text_preview_truncated":true}"#
                : #"{"id":"large","parsed_text":"first page and the remainder"}"#
        } else {
            body = #"{"id":"doc","parsed_text":"fixture"}"#
        }
        client.urlProtocol(self, didLoad: Data(body.utf8))
        client.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}
