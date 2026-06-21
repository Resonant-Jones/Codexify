import Foundation

struct ScoutDocumentDetailResult {
    let httpStatus: Int?
    let detail: ScoutDocumentDetail?
    let message: String
}

struct ScoutDocumentDetailProbe {

    static func probe(
        endpoint: ScoutEndpointProfile,
        documentId: String,
        apiKey: String? = nil,
        session: URLSession = .shared
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

        let hasApiKey = apiKey.map { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty } ?? false
        if let key = apiKey, hasApiKey {
            request.setValue(key, forHTTPHeaderField: "X-API-Key")
        }

        do {
            let (data, response) = try await session.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                return ScoutDocumentDetailResult(
                    httpStatus: nil, detail: nil, message: "Unexpected response type."
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                let detail = try? JSONDecoder().decode(ScoutDocumentDetail.self, from: data)
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
}
