import Foundation

struct ScoutSendMessageResult {
    let httpStatus: Int?
    let messageId: Int?
    let message: String
}

struct ScoutGuardianSendMessageService {

    static func send(
        endpoint: ScoutEndpointProfile,
        threadId: Int,
        content: String,
        apiKey: String? = nil,
        session: URLSession = .shared
    ) async -> ScoutSendMessageResult {
        let trimmed = content.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return ScoutSendMessageResult(
                httpStatus: nil,
                messageId: nil,
                message: "Message content is empty."
            )
        }

        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !urlString.isEmpty else {
            return ScoutSendMessageResult(
                httpStatus: nil,
                messageId: nil,
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
            return ScoutSendMessageResult(
                httpStatus: nil,
                messageId: nil,
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

        let body: [String: String] = ["role": "user", "content": trimmed]
        request.httpBody = try? JSONEncoder().encode(body)

        do {
            let (data, response) = try await session.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                return ScoutSendMessageResult(
                    httpStatus: nil,
                    messageId: nil,
                    message: "Unexpected response type from server."
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
                let msgObj = json?["message"] as? [String: Any]
                let msgId = msgObj?["id"] as? Int
                return ScoutSendMessageResult(
                    httpStatus: statusCode,
                    messageId: msgId,
                    message: "Message sent."
                )
            case 400:
                let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
                let error = json?["error"] as? String ?? "Bad request."
                return ScoutSendMessageResult(
                    httpStatus: statusCode,
                    messageId: nil,
                    message: error
                )
            case 401, 403:
                return ScoutSendMessageResult(
                    httpStatus: statusCode,
                    messageId: nil,
                    message: "Authentication required (HTTP \(statusCode))."
                )
            default:
                return ScoutSendMessageResult(
                    httpStatus: statusCode,
                    messageId: nil,
                    message: "Send returned HTTP \(statusCode)."
                )
            }
        } catch let error as URLError where error.code == .timedOut {
            return ScoutSendMessageResult(
                httpStatus: nil,
                messageId: nil,
                message: "Send timed out after 5 seconds."
            )
        } catch {
            return ScoutSendMessageResult(
                httpStatus: nil,
                messageId: nil,
                message: "Send failed: \(error.localizedDescription)"
            )
        }
    }
}
