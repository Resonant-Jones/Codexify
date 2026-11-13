import Foundation
import CryptoKit

struct ScoutDocumentDetailResult {
    let httpStatus: Int?
    let detail: ScoutDocumentDetail?
    let message: String
}

struct ScoutDocumentDetailProbe {
    static let recentDocuments = ScoutDocumentCache()

    static func probe(
        endpoint: ScoutEndpointProfile,
        documentId: String,
        apiKey: String? = nil,
        session: URLSession = .scoutAuthenticated,
        cache: ScoutDocumentCache? = nil,
        accountGeneration: Int = 0,
        reload: Bool = false,
        preview: Bool = false
    ) async -> ScoutDocumentDetailResult {
        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !urlString.isEmpty else {
            return ScoutDocumentDetailResult(
                httpStatus: nil, detail: nil, message: "Base URL is empty."
            )
        }

        if urlString.hasSuffix("/") {
            urlString = String(urlString.dropLast())
        }
        urlString += "/api/documents/\(documentId)"

        guard let url = URL(string: urlString),
              let scheme = url.scheme, !scheme.isEmpty,
              url.host != nil else {
            return ScoutDocumentDetailResult(
                httpStatus: nil, detail: nil, message: "Malformed document URL."
            )
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 5

        do {
            try await ScoutRequestAuthentication.prepare(to: &request, endpoint: endpoint, apiKey: apiKey)
            let key = cache == nil ? nil : cacheKey(for: request, endpoint: endpoint, accountGeneration: accountGeneration)
            if let cache, let key {
                if reload {
                    await cache.remove(key)
                } else if let detail = await cache.detail(for: key) {
                    return ScoutDocumentDetailResult(httpStatus: nil, detail: detail, message: "Recent document loaded.")
                }
            }
            if preview, var components = URLComponents(url: url, resolvingAgainstBaseURL: false) {
                components.queryItems = (components.queryItems ?? []) + [URLQueryItem(name: "preview", value: "true")]
                request.url = components.url ?? url
            }
            let (data, response) = try await session.data(for: request)
            if let http = response as? HTTPURLResponse {
                try ScoutRequestAuthentication.validate(response: http, endpoint: endpoint, request: request)
            }

            guard let httpResponse = response as? HTTPURLResponse else {
                return ScoutDocumentDetailResult(
                    httpStatus: nil, detail: nil, message: "Unexpected response type."
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                let detail = try? JSONDecoder().decode(ScoutDocumentDetail.self, from: data)
                if let cache, let key, let detail, detail.text_preview_truncated != true, !Task.isCancelled {
                    await cache.insert(detail, for: key)
                }
                return ScoutDocumentDetailResult(
                    httpStatus: statusCode, detail: detail,
                    message: detail != nil ? "Document loaded." : "Document loaded but details unavailable."
                )
            case 401, 403:
                return ScoutDocumentDetailResult(
                    httpStatus: statusCode, detail: nil,
                    message: "Authentication required (HTTP \(statusCode))."
                )
            default:
                return ScoutDocumentDetailResult(
                    httpStatus: statusCode, detail: nil,
                    message: "Document request returned HTTP \(statusCode)."
                )
            }
        } catch let error as URLError where error.code == .timedOut {
            return ScoutDocumentDetailResult(
                httpStatus: nil, detail: nil, message: "Document request timed out."
            )
        } catch {
            return ScoutDocumentDetailResult(
                httpStatus: nil, detail: nil,
                message: "Document request failed: \(error.localizedDescription)"
            )
        }
    }
    // Bind a cached result to the exact credential selection without storing
    // credential headers or logging their fingerprint. Anonymous reads skip it.
    private static func cacheKey(for request: URLRequest, endpoint: ScoutEndpointProfile,
                                 accountGeneration: Int) -> ScoutDocumentCache.Key? {
        guard let url = request.url else { return nil }
        let credentials = ["X-API-Key", "X-Guardian-Account-Session", "Authorization"].map {
            request.value(forHTTPHeaderField: $0)
        }
        guard credentials.contains(where: { $0 != nil }), let encoded = try? JSONEncoder().encode(credentials) else { return nil }
        return .init(connection: .init(endpoint: endpoint), accountGeneration: accountGeneration,
                     authorization: Data(SHA256.hash(data: encoded)), url: url)
    }
}
