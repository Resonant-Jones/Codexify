import Foundation

struct ScoutCompleteThreadResult {
    let httpStatus: Int?
    let taskId: String?
    let turnId: String?
    let messagesUrl: String?
    let traceUrl: String?
    let acceptanceStatus: String?
    let message: String
}

struct ScoutGuardianCompleteThreadService {

    static func complete(
        endpoint: ScoutEndpointProfile,
        threadId: Int,
        apiKey: String? = nil,
        session: URLSession = .shared
    ) async -> ScoutCompleteThreadResult {
        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !urlString.isEmpty else {
            return ScoutCompleteThreadResult(
                httpStatus: nil,
                taskId: nil,
                turnId: nil,
                messagesUrl: nil,
                traceUrl: nil,
                acceptanceStatus: nil,
                message: "Base URL is empty."
            )
        }

        if urlString.hasSuffix("/") {
            urlString = String(urlString.dropLast())
        }
        urlString += "/api/chat/\(threadId)/complete"

        guard let url = URL(string: urlString),
              let scheme = url.scheme, !scheme.isEmpty,
              url.host != nil else {
            return ScoutCompleteThreadResult(
                httpStatus: nil,
                taskId: nil,
                turnId: nil,
                messagesUrl: nil,
                traceUrl: nil,
                acceptanceStatus: nil,
                message: "Malformed completion URL."
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

        let body: [String: String] = [:]
        request.httpBody = try? JSONEncoder().encode(body)

        do {
            let (data, response) = try await session.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                return ScoutCompleteThreadResult(
                    httpStatus: nil,
                    taskId: nil,
                    turnId: nil,
                    messagesUrl: nil,
                    traceUrl: nil,
                    acceptanceStatus: nil,
                    message: "Unexpected response type from server."
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
                let taskId = json?["task_id"] as? String
                let turnId = json?["turn_id"] as? String
                let messagesUrl = json?["messages_url"] as? String
                let traceUrl = json?["trace_url"] as? String
                let acceptance = json?["acceptance_status"] as? String
                return ScoutCompleteThreadResult(
                    httpStatus: statusCode,
                    taskId: taskId,
                    turnId: turnId,
                    messagesUrl: messagesUrl,
                    traceUrl: traceUrl,
                    acceptanceStatus: acceptance,
                    message: "Completion accepted by Vault."
                )
            case 401, 403:
                return ScoutCompleteThreadResult(
                    httpStatus: statusCode,
                    taskId: nil,
                    turnId: nil,
                    messagesUrl: nil,
                    traceUrl: nil,
                    acceptanceStatus: nil,
                    message: "Authentication required (HTTP \(statusCode))."
                )
            case 404:
                return ScoutCompleteThreadResult(
                    httpStatus: statusCode,
                    taskId: nil,
                    turnId: nil,
                    messagesUrl: nil,
                    traceUrl: nil,
                    acceptanceStatus: nil,
                    message: "Thread not found (HTTP 404)."
                )
            case 429:
                return ScoutCompleteThreadResult(
                    httpStatus: statusCode,
                    taskId: nil,
                    turnId: nil,
                    messagesUrl: nil,
                    traceUrl: nil,
                    acceptanceStatus: nil,
                    message: "A completion is already in progress (HTTP 429)."
                )
            default:
                return ScoutCompleteThreadResult(
                    httpStatus: statusCode,
                    taskId: nil,
                    turnId: nil,
                    messagesUrl: nil,
                    traceUrl: nil,
                    acceptanceStatus: nil,
                    message: "Completion request returned HTTP \(statusCode)."
                )
            }
        } catch let error as URLError where error.code == .timedOut {
            return ScoutCompleteThreadResult(
                httpStatus: nil,
                taskId: nil,
                turnId: nil,
                messagesUrl: nil,
                traceUrl: nil,
                acceptanceStatus: nil,
                message: "Completion request timed out after 5 seconds."
            )
        } catch {
            return ScoutCompleteThreadResult(
                httpStatus: nil,
                taskId: nil,
                turnId: nil,
                messagesUrl: nil,
                traceUrl: nil,
                acceptanceStatus: nil,
                message: "Completion request failed: \(error.localizedDescription)"
            )
        }
    }
}
