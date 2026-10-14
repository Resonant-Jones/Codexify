import Foundation

struct ScoutThreadDocumentsResult {
    let httpStatus: Int?
    let documents: [ScoutThreadDocumentSummary]?
    let message: String
}

struct ScoutThreadDocumentsProbe {

    static func probe(
        endpoint: ScoutEndpointProfile,
        threadId: Int,
        apiKey: String? = nil,
        session: URLSession = .scoutAuthenticated
    ) async -> ScoutThreadDocumentsResult {
        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !urlString.isEmpty else {
            return ScoutThreadDocumentsResult(
                httpStatus: nil, documents: nil, message: "Base URL is empty."
            )
        }

        if urlString.hasSuffix("/") {
            urlString = String(urlString.dropLast())
        }
        urlString += "/api/threads/\(threadId)/documents"

        guard let url = URL(string: urlString),
              let scheme = url.scheme, !scheme.isEmpty,
              url.host != nil else {
            return ScoutThreadDocumentsResult(
                httpStatus: nil, documents: nil, message: "Malformed documents URL."
            )
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 5

        do {
            try ScoutRequestAuthentication.apply(to: &request, endpoint: endpoint, apiKey: apiKey)
            let (data, response) = try await session.data(for: request)
            if let http = response as? HTTPURLResponse {
                try ScoutRequestAuthentication.validate(response: http, endpoint: endpoint, request: request)
            }

            guard let httpResponse = response as? HTTPURLResponse else {
                return ScoutThreadDocumentsResult(
                    httpStatus: nil, documents: nil, message: "Unexpected response type."
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                let decoded = try? JSONDecoder().decode(ScoutThreadDocumentsResponse.self, from: data)
                let count = decoded?.documents?.count ?? 0
                return ScoutThreadDocumentsResult(
                    httpStatus: statusCode,
                    documents: decoded?.documents,
                    message: count > 0 ? "Loaded \(count) documents." : "No documents linked to this thread."
                )
            case 401, 403:
                return ScoutThreadDocumentsResult(
                    httpStatus: statusCode, documents: nil,
                    message: "Authentication required (HTTP \(statusCode))."
                )
            default:
                return ScoutThreadDocumentsResult(
                    httpStatus: statusCode, documents: nil,
                    message: "Documents request returned HTTP \(statusCode)."
                )
            }
        } catch let error as URLError where error.code == .timedOut {
            return ScoutThreadDocumentsResult(
                httpStatus: nil, documents: nil, message: "Documents request timed out."
            )
        } catch {
            return ScoutThreadDocumentsResult(
                httpStatus: nil, documents: nil,
                message: "Documents request failed: \(error.localizedDescription)"
            )
        }
    }
}
