import Foundation

struct ScoutGuardianThreadsResult {
    let httpStatus: Int?
    let threads: [ScoutChatThreadSummary]?
    let hasMore: Bool?
    let message: String
}

struct ScoutGuardianThreadsProbe {

    static func probe(
        endpoint: ScoutEndpointProfile,
        apiKey: String? = nil,
        session: URLSession = .shared
    ) async -> ScoutGuardianThreadsResult {
        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !urlString.isEmpty else {
            return ScoutGuardianThreadsResult(
                httpStatus: nil,
                threads: nil,
                hasMore: nil,
                message: "Base URL is empty."
            )
        }

        if urlString.hasSuffix("/") {
            urlString = String(urlString.dropLast())
        }
        urlString += "/api/chat/threads"

        guard let url = URL(string: urlString),
              let scheme = url.scheme, !scheme.isEmpty,
              url.host != nil else {
            return ScoutGuardianThreadsResult(
                httpStatus: nil,
                threads: nil,
                hasMore: nil,
                message: "Malformed threads URL."
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
                return ScoutGuardianThreadsResult(
                    httpStatus: nil,
                    threads: nil,
                    hasMore: nil,
                    message: "Unexpected response type from server."
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                let decoded = try? JSONDecoder().decode(ScoutChatThreadsResponse.self, from: data)
                return ScoutGuardianThreadsResult(
                    httpStatus: statusCode,
                    threads: decoded?.threads,
                    hasMore: decoded?.has_more,
                    message: decoded?.threads?.isEmpty == false
                        ? "Loaded \(decoded?.threads?.count ?? 0) threads."
                        : "No threads found."
                )
            case 401, 403:
                return ScoutGuardianThreadsResult(
                    httpStatus: statusCode,
                    threads: nil,
                    hasMore: nil,
                    message: "Authentication required (HTTP \(statusCode)). Set an API key in Settings."
                )
            default:
                return ScoutGuardianThreadsResult(
                    httpStatus: statusCode,
                    threads: nil,
                    hasMore: nil,
                    message: "Threads request returned HTTP \(statusCode)."
                )
            }
        } catch let error as URLError where error.code == .timedOut {
            return ScoutGuardianThreadsResult(
                httpStatus: nil,
                threads: nil,
                hasMore: nil,
                message: "Threads request timed out after 5 seconds."
            )
        } catch {
            return ScoutGuardianThreadsResult(
                httpStatus: nil,
                threads: nil,
                hasMore: nil,
                message: "Threads request failed: \(error.localizedDescription)"
            )
        }
    }
}
