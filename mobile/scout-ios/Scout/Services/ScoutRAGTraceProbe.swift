import Foundation

struct ScoutRAGTraceResult {
    let httpStatus: Int?
    let latencyMilliseconds: Int?
    let snapshot: ScoutRAGTraceSnapshot?
    let message: String
}

struct ScoutRAGTraceProbe {

    static func probe(
        endpoint: ScoutEndpointProfile,
        threadId: Int,
        apiKey: String? = nil,
        session: URLSession = .shared
    ) async -> ScoutRAGTraceResult {
        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !urlString.isEmpty else {
            return ScoutRAGTraceResult(
                httpStatus: nil, latencyMilliseconds: nil, snapshot: nil,
                message: "Base URL is empty."
            )
        }

        if urlString.hasSuffix("/") {
            urlString = String(urlString.dropLast())
        }
        urlString += "/api/chat/debug/rag-trace/\(threadId)/latest"

        guard let url = URL(string: urlString),
              let scheme = url.scheme, !scheme.isEmpty,
              url.host != nil else {
            return ScoutRAGTraceResult(
                httpStatus: nil, latencyMilliseconds: nil, snapshot: nil,
                message: "Malformed RAG trace URL."
            )
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 5

        let hasApiKey = apiKey.map { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty } ?? false
        if let key = apiKey, hasApiKey {
            request.setValue(key, forHTTPHeaderField: "X-API-Key")
        }

        let requestStart = Date()

        do {
            let (data, response) = try await session.data(for: request)
            let latencyMs = Int(requestStart.distance(to: Date()) * 1000)

            guard let httpResponse = response as? HTTPURLResponse else {
                return ScoutRAGTraceResult(
                    httpStatus: nil, latencyMilliseconds: latencyMs, snapshot: nil,
                    message: "Unexpected response type."
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                    return ScoutRAGTraceResult(
                        httpStatus: statusCode, latencyMilliseconds: latencyMs, snapshot: nil,
                        message: "RAG trace response could not be parsed."
                    )
                }
                let snapshot = ScoutRAGTraceSnapshot(from: json)
                return ScoutRAGTraceResult(
                    httpStatus: statusCode, latencyMilliseconds: latencyMs, snapshot: snapshot,
                    message: snapshot?.traceAvailable == true
                        ? "Retrieval trace available."
                        : "Retrieval trace unavailable."
                )
            case 401, 403:
                return ScoutRAGTraceResult(
                    httpStatus: statusCode, latencyMilliseconds: latencyMs, snapshot: nil,
                    message: "Authentication required (HTTP \(statusCode))."
                )
            case 404:
                return ScoutRAGTraceResult(
                    httpStatus: statusCode, latencyMilliseconds: latencyMs, snapshot: nil,
                    message: "Thread not found or no trace available (HTTP 404)."
                )
            default:
                return ScoutRAGTraceResult(
                    httpStatus: statusCode, latencyMilliseconds: latencyMs, snapshot: nil,
                    message: "RAG trace request returned HTTP \(statusCode)."
                )
            }
        } catch let error as URLError where error.code == .timedOut {
            return ScoutRAGTraceResult(
                httpStatus: nil, latencyMilliseconds: nil, snapshot: nil,
                message: "RAG trace request timed out."
            )
        } catch {
            return ScoutRAGTraceResult(
                httpStatus: nil, latencyMilliseconds: nil, snapshot: nil,
                message: "RAG trace request failed: \(error.localizedDescription)"
            )
        }
    }
}
