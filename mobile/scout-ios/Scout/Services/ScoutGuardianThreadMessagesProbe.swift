import Foundation

struct ScoutGuardianThreadMessagesResult {
    let httpStatus: Int?
    let messages: [ScoutChatMessageSummary]?
    let total: Int?
    let message: String
}

struct ScoutGuardianThreadMessagesProbe {

    static func probe(
        endpoint: ScoutEndpointProfile,
        threadId: Int,
        apiKey: String? = nil,
        session: URLSession = .shared
    ) async -> ScoutGuardianThreadMessagesResult {
        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !urlString.isEmpty else {
            return ScoutGuardianThreadMessagesResult(
                httpStatus: nil,
                messages: nil,
                total: nil,
                message: "Base URL is empty."
            )
        }

        if urlString.hasSuffix("/") {
            urlString = String(urlString.dropLast())
        }
        urlString += "/api/chat/\(threadId)/messages"

        guard let url = URL(string: urlString),
              let scheme = url.scheme, !scheme.isEmpty,
              url.host != nil else {
            return ScoutGuardianThreadMessagesResult(
                httpStatus: nil,
                messages: nil,
                total: nil,
                message: "Malformed messages URL."
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
                return ScoutGuardianThreadMessagesResult(
                    httpStatus: nil,
                    messages: nil,
                    total: nil,
                    message: "Unexpected response type from server."
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                let decoded = try? JSONDecoder().decode(ScoutChatMessagesResponse.self, from: data)
                let count = decoded?.messages?.count ?? 0
                return ScoutGuardianThreadMessagesResult(
                    httpStatus: statusCode,
                    messages: decoded?.messages,
                    total: decoded?.total,
                    message: count > 0 ? "Loaded \(count) messages." : "No messages in thread."
                )
            case 401, 403:
                return ScoutGuardianThreadMessagesResult(
                    httpStatus: statusCode,
                    messages: nil,
                    total: nil,
                    message: "Authentication required (HTTP \(statusCode)). Set an API key in Settings."
                )
            default:
                return ScoutGuardianThreadMessagesResult(
                    httpStatus: statusCode,
                    messages: nil,
                    total: nil,
                    message: "Messages request returned HTTP \(statusCode)."
                )
            }
        } catch let error as URLError where error.code == .timedOut {
            return ScoutGuardianThreadMessagesResult(
                httpStatus: nil,
                messages: nil,
                total: nil,
                message: "Messages request timed out after 5 seconds."
            )
        } catch {
            return ScoutGuardianThreadMessagesResult(
                httpStatus: nil,
                messages: nil,
                total: nil,
                message: "Messages request failed: \(error.localizedDescription)"
            )
        }
    }
}
