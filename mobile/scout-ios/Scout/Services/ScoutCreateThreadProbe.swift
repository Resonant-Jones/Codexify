import Foundation

struct ScoutCreateThreadResult {
    let httpStatus: Int?
    let thread: ScoutChatThreadSummary?
    let threadId: Int?
    let message: String
}

struct ScoutCreateThreadProbe {

    static func create(
        endpoint: ScoutEndpointProfile,
        title: String,
        apiKey: String? = nil,
        session: URLSession = .shared
    ) async -> ScoutCreateThreadResult {
        let trimmed = title.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return ScoutCreateThreadResult(
                httpStatus: nil, thread: nil, threadId: nil,
                message: "Thread title is empty."
            )
        }

        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !urlString.isEmpty else {
            return ScoutCreateThreadResult(
                httpStatus: nil, thread: nil, threadId: nil,
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
            return ScoutCreateThreadResult(
                httpStatus: nil, thread: nil, threadId: nil,
                message: "Malformed URL."
            )
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 5

        let hasApiKey = apiKey.map { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty } ?? false
        if let key = apiKey, hasApiKey {
            request.setValue(key, forHTTPHeaderField: "X-API-Key")
        }

        let body: [String: String] = ["title": trimmed]
        request.httpBody = try? JSONEncoder().encode(body)

        do {
            let (data, response) = try await session.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                return ScoutCreateThreadResult(
                    httpStatus: nil, thread: nil, threadId: nil,
                    message: "Unexpected response type."
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
                let threadId = json?["id"] as? Int
                let threadDict = json?["thread"] as? [String: Any]
                let thread: ScoutChatThreadSummary? = threadDict.flatMap { dict in
                    guard let data = try? JSONSerialization.data(withJSONObject: dict) else { return nil }
                    return try? JSONDecoder().decode(ScoutChatThreadSummary.self, from: data)
                }
                return ScoutCreateThreadResult(
                    httpStatus: statusCode, thread: thread, threadId: threadId,
                    message: "Thread created."
                )
            case 401, 403:
                return ScoutCreateThreadResult(
                    httpStatus: statusCode, thread: nil, threadId: nil,
                    message: "Authentication required (HTTP \(statusCode))."
                )
            default:
                return ScoutCreateThreadResult(
                    httpStatus: statusCode, thread: nil, threadId: nil,
                    message: "Create thread returned HTTP \(statusCode)."
                )
            }
        } catch let error as URLError where error.code == .timedOut {
            return ScoutCreateThreadResult(
                httpStatus: nil, thread: nil, threadId: nil,
                message: "Create thread timed out."
            )
        } catch {
            return ScoutCreateThreadResult(
                httpStatus: nil, thread: nil, threadId: nil,
                message: "Create thread failed: \(error.localizedDescription)"
            )
        }
    }
}
