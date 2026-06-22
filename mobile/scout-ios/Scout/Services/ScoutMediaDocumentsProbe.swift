import Foundation

struct ScoutMediaDocumentsResult {
    let httpStatus: Int?
    let documents: [ScoutDocumentDetail]?
    let message: String
}

struct ScoutMediaDocumentsProbe {

    static func probe(
        endpoint: ScoutEndpointProfile,
        apiKey: String? = nil,
        session: URLSession = .shared
    ) async -> ScoutMediaDocumentsResult {
        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !urlString.isEmpty else {
            return ScoutMediaDocumentsResult(
                httpStatus: nil, documents: nil, message: "Base URL is empty."
            )
        }

        if urlString.hasSuffix("/") {
            urlString = String(urlString.dropLast())
        }
        urlString += "/api/media/documents"

        guard let url = URL(string: urlString),
              let scheme = url.scheme, !scheme.isEmpty,
              url.host != nil else {
            return ScoutMediaDocumentsResult(
                httpStatus: nil, documents: nil, message: "Malformed URL."
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
                return ScoutMediaDocumentsResult(
                    httpStatus: nil, documents: nil, message: "Unexpected response type."
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let docs = json["documents"] as? [[String: Any]] else {
                    return ScoutMediaDocumentsResult(
                        httpStatus: statusCode, documents: nil,
                        message: "Could not parse document list."
                    )
                }
                let decoded = docs.compactMap { try? JSONDecoder().decode(
                    ScoutDocumentDetail.self,
                    from: JSONSerialization.data(withJSONObject: $0)
                )}
                return ScoutMediaDocumentsResult(
                    httpStatus: statusCode, documents: decoded,
                    message: decoded.isEmpty ? "No documents found." : "Loaded \(decoded.count) documents."
                )
            case 401, 403:
                return ScoutMediaDocumentsResult(
                    httpStatus: statusCode, documents: nil,
                    message: "Authentication required (HTTP \(statusCode))."
                )
            default:
                return ScoutMediaDocumentsResult(
                    httpStatus: statusCode, documents: nil,
                    message: "Documents request returned HTTP \(statusCode)."
                )
            }
        } catch let error as URLError where error.code == .timedOut {
            return ScoutMediaDocumentsResult(
                httpStatus: nil, documents: nil, message: "Documents request timed out."
            )
        } catch {
            return ScoutMediaDocumentsResult(
                httpStatus: nil, documents: nil,
                message: "Documents request failed: \(error.localizedDescription)"
            )
        }
    }
}
