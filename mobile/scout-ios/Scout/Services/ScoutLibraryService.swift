import Foundation
import CoreFoundation

enum ScoutLibraryFilter: String, CaseIterable, Identifiable {
    case all, images, documents, widgets
    var id: Self { self }
    var title: String {
        switch self {
        case .all: return "All"
        case .images: return "Gallery"
        case .documents: return "Documents"
        case .widgets: return "Widgets"
        }
    }
    var sources: [ScoutLibrarySource] {
        switch self {
        case .all: return [.uploadedImages, .generatedImages, .documents]
        case .images: return [.uploadedImages, .generatedImages]
        case .documents: return [.documents]
        case .widgets: return []
        }
    }
}

enum ScoutLibrarySource: String, CaseIterable {
    case uploadedImages, generatedImages, documents
    var title: String {
        switch self {
        case .uploadedImages: return "Uploaded images"
        case .generatedImages: return "Generated images"
        case .documents: return "Documents"
        }
    }
    var path: String { self == .documents ? "/api/media/document-artifacts" : "/api/media/images" }
    var listKey: String { self == .documents ? "documents" : "images" }
}

struct ScoutLibraryResource: Identifiable, Hashable {
    let sourceID: String
    let family: String
    let title: String
    let origin: String
    let sourceURL: String?
    let mimeType: String?
    let createdAt: String?
    var id: String { family + ":" + sourceID }
    var isImage: Bool { family == "uploaded_image" || family == "generated_image" }
    var artifactType: String { family == "generated_document" ? "generated" : "uploaded" }
}

struct ScoutLibrarySourceResult {
    enum Coverage { case complete, empty, bounded, uncertain, failed }
    let source: ScoutLibrarySource
    let resources: [ScoutLibraryResource]
    let coverage: Coverage
    let issue: String?
    var nextOffset: Int? = nil

    func appending(_ page: Self) -> Self {
        guard page.source == source else { return self }
        if page.coverage == .failed || (page.coverage == .uncertain && page.resources.isEmpty) {
            return .init(source: source, resources: resources, coverage: coverage,
                         issue: [coverage == .uncertain ? issue : nil, page.issue].compactMap { $0 }.joined(separator: " "),
                         nextOffset: nextOffset)
        }
        var seen = Set<String>()
        let combined = (resources + page.resources).filter { seen.insert($0.id).inserted }
        return .init(source: source, resources: combined,
                     coverage: page.coverage == .empty && !combined.isEmpty ? .complete : page.coverage,
                     issue: page.issue ?? (coverage == .uncertain ? issue : nil), nextOffset: page.nextOffset)
    }
}

struct ScoutLibrarySnapshot {
    let sources: [ScoutLibrarySourceResult]
    var commonFailure: String? {
        guard let first = sources.first, first.coverage == .failed,
              sources.allSatisfy({ $0.coverage == .failed && $0.issue == first.issue }) else { return nil }
        return first.issue
    }
    var resources: [ScoutLibraryResource] {
        var seen = Set<String>()
        return sources.flatMap(\.resources).filter { seen.insert($0.id).inserted }.sorted {
            if $0.createdAt == $1.createdAt { return $0.id < $1.id }
            return ($0.createdAt ?? "") > ($1.createdAt ?? "")
        }
    }
    var issues: [String] { sources.compactMap { result in result.issue.map { result.source.title + ": " + $0 } } }
}

enum ScoutLibraryError: LocalizedError {
    case invalidResponse, http(Int), tooLarge, unavailablePreview
    var errorDescription: String? {
        switch self {
        case .invalidResponse: return "The server returned an unreadable Library response."
        case .http(let status):
            return [401, 403].contains(status) ? "Sign in again in Settings (HTTP \(status))." : "The server returned HTTP \(status)."
        case .tooLarge: return "This resource is too large for the mobile preview."
        case .unavailablePreview: return "A preview is not available for this resource."
        }
    }
}

/// Account identity is supplied exclusively by Scout's existing transport.
/// All sources are unscoped (the whole authorized Library), never inferred from
/// the currently selected conversation or from a client-supplied account ID.
struct ScoutLibraryService {
    static let limit = 100
    static let widgetsMessage = "Saved widgets are not available in the hosted Library yet. Interactive widgets in conversations remain available from Guardian."
    let endpoint: ScoutEndpointProfile
    let apiKey: String?
    var session: URLSession = .scoutAuthenticated

    func load(_ filter: ScoutLibraryFilter) async -> ScoutLibrarySnapshot {
        await withTaskGroup(of: ScoutLibrarySourceResult.self) { group in
            for source in filter.sources { group.addTask { await fetch(source) } }
            var results: [ScoutLibrarySourceResult] = []
            for await result in group { results.append(result) }
            return ScoutLibrarySnapshot(sources: results.sorted { $0.source.rawValue < $1.source.rawValue })
        }
    }

    func fetch(_ source: ScoutLibrarySource, offset: Int = 0) async -> ScoutLibrarySourceResult {
        do {
            var query = [URLQueryItem(name: "limit", value: String(Self.limit)),
                         URLQueryItem(name: "offset", value: String(offset))]
            if source == .generatedImages { query.append(URLQueryItem(name: "tag", value: "generated")) }
            let url = try apiURL(path: source.path, query: query)
            let data = try await read(url, maxBytes: 4 * 1024 * 1024).data
            return Self.project(data, source: source, offset: offset)
        } catch is ScoutRequestAuthenticationError {
            return .init(source: source, resources: [], coverage: .failed,
                         issue: "Sign in to Guardian for this connection in Settings, then refresh Library.")
        } catch {
            return .init(source: source, resources: [], coverage: .failed, issue: error.localizedDescription)
        }
    }

    static func project(_ data: Data, source: ScoutLibrarySource, offset: Int = 0) -> ScoutLibrarySourceResult {
        guard let body = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let records = body[source.listKey] as? [Any],
              let number = body["count"] as? NSNumber,
              CFGetTypeID(number) != CFBooleanGetTypeID(),
              number.doubleValue == Double(records.count) else {
            return .init(source: source, resources: [], coverage: .uncertain,
                         issue: "The resource list or count is missing or inconsistent. Refresh to try again.")
        }
        var resources: [ScoutLibraryResource] = []
        var rejected = 0
        let paged = body.keys.contains("next_offset")
        var nextOffset: Int?
        if paged, !(body["next_offset"] is NSNull) {
            let (expected, overflow) = offset.addingReportingOverflow(records.count)
            guard let next = body["next_offset"] as? NSNumber,
                  CFGetTypeID(next) != CFBooleanGetTypeID(), !overflow,
                  records.count > 0, next.doubleValue == Double(expected), next.intValue == expected else {
                return .init(source: source, resources: [], coverage: .uncertain,
                             issue: "The next Library page could not be read. Refresh to try again.")
            }
            nextOffset = expected
        }
        for record in records {
            guard let raw = record as? [String: Any], raw["mock"] as? Bool != true,
                  let id = sourceID(raw["id"] ?? raw["document_id"]) else { rejected += 1; continue }
            let family: String
            switch source {
            case .uploadedImages: family = "uploaded_image"
            case .generatedImages: family = "generated_image"
            case .documents:
                guard let type = string(raw["artifact_type"])?.lowercased(), ["uploaded", "generated"].contains(type) else {
                    rejected += 1; continue
                }
                family = type + "_document"
            }
            let tag = string(raw["source_tag"])?.lowercased() ?? "unknown"
            resources.append(.init(sourceID: id, family: family,
                title: (source == .documents ? string(raw["title"]) : nil) ?? string(raw["filename"]) ?? string(raw["prompt"]) ?? "Untitled",
                origin: ["uploaded", "generated", "imported"].contains(tag) ? tag : "unknown",
                sourceURL: string(raw["src_url"]), mimeType: string(raw["mime_type"]), createdAt: string(raw["created_at"])))
        }
        if rejected > 0 {
            return .init(source: source, resources: resources, coverage: .uncertain,
                         issue: "\(rejected) resource(s) have incomplete metadata and could not be displayed.", nextOffset: nextOffset)
        }
        if let nextOffset {
            return .init(source: source, resources: resources, coverage: .bounded, issue: nil, nextOffset: nextOffset)
        }
        if !paged && records.count >= limit {
            return .init(source: source, resources: resources, coverage: .bounded,
                         issue: "Showing the latest \(limit). The server does not provide pagination; older resources may be omitted.")
        }
        return .init(source: source, resources: resources, coverage: records.isEmpty ? .empty : .complete, issue: nil)
    }

    func documentText(_ resource: ScoutLibraryResource) async throws -> String? {
        guard !resource.isImage else { throw ScoutLibraryError.unavailablePreview }
        let data = try await read(documentURL(resource), maxBytes: 16 * 1024 * 1024).data
        guard let body = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              Self.sourceID(body["id"] ?? body["document_id"]) == resource.sourceID,
              Self.string(body["artifact_type"]) == resource.artifactType else { throw ScoutLibraryError.invalidResponse }
        return Self.string(body["content"]) ?? Self.string(body["parsed_text"])
    }

    func documentURL(_ resource: ScoutLibraryResource) throws -> URL {
        let base = try apiURL(path: "/api/media/document-artifacts")
        let unreserved = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~")
        guard ![".", ".."].contains(resource.sourceID),
              let id = resource.sourceID.addingPercentEncoding(withAllowedCharacters: unreserved),
              var components = URLComponents(url: base, resolvingAgainstBaseURL: false) else { throw ScoutLibraryError.invalidResponse }
        components.percentEncodedPath += "/" + id
        components.queryItems = [URLQueryItem(name: "artifact_type", value: resource.artifactType)]
        guard let url = components.url else { throw ScoutLibraryError.invalidResponse }
        return url
    }

    func media(_ resource: ScoutLibraryResource) async throws -> (data: Data, mimeType: String?) {
        guard let raw = resource.sourceURL else { throw ScoutLibraryError.unavailablePreview }
        let url = try Self.mediaURL(raw, endpoint: endpoint)
        return try await read(url, maxBytes: 24 * 1024 * 1024)
    }

    // Signed resource URLs are data, not authority to disclose credentials to
    // another host. Authentication also revalidates this origin before dispatch.
    static func mediaURL(_ value: String, endpoint: ScoutEndpointProfile) throws -> URL {
        let origin = try ScoutAccessOAuth.origin(for: endpoint)
        guard let base = URL(string: origin + "/"),
              let url = URL(string: value, relativeTo: base)?.absoluteURL,
              url.scheme?.lowercased() == "https", url.user == nil, url.password == nil,
              url.host?.lowercased() == base.host?.lowercased(), (url.port ?? 443) == (base.port ?? 443) else {
            throw ScoutRequestAuthenticationError.wrongConnection
        }
        return url
    }

    func apiURL(path: String, query: [URLQueryItem] = []) throws -> URL {
        let base = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard var components = URLComponents(string: base + path) else { throw ScoutLibraryError.invalidResponse }
        components.queryItems = query.isEmpty ? nil : query
        guard let url = components.url else { throw ScoutLibraryError.invalidResponse }
        return url
    }

    func read(_ url: URL, maxBytes: Int) async throws -> (data: Data, mimeType: String?) {
        let generation = UserDefaults.standard.integer(forKey: "scout.accountSessionGeneration")
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 20)
        request.httpMethod = "GET"
        try await ScoutRequestAuthentication.prepare(to: &request, endpoint: endpoint, apiKey: apiKey)
        let (bytes, response) = try await session.bytes(for: request)
        guard let http = response as? HTTPURLResponse else { throw ScoutLibraryError.invalidResponse }
        try ScoutRequestAuthentication.validate(response: http, endpoint: endpoint, request: request)
        guard (200..<300).contains(http.statusCode) else { throw ScoutLibraryError.http(http.statusCode) }
        guard response.expectedContentLength <= maxBytes else { throw ScoutLibraryError.tooLarge }
        var data = Data()
        for try await byte in bytes {
            guard data.count < maxBytes else { throw ScoutLibraryError.tooLarge }
            data.append(byte)
        }
        try Task.checkCancellation()
        guard generation == UserDefaults.standard.integer(forKey: "scout.accountSessionGeneration") else {
            throw ScoutRequestAuthenticationError.sessionRequired
        }
        return (data, response.mimeType)
    }

    private static func string(_ value: Any?) -> String? {
        guard let value = value as? String, !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return nil }
        return value
    }
    private static func sourceID(_ value: Any?) -> String? {
        if let value = string(value) { return value }
        if let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(), number.doubleValue.isFinite { return number.stringValue }
        return nil
    }
}
