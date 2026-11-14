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
        session: URLSession = .scoutAuthenticated
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

        let body: [String: String] = ["role": "user", "content": trimmed]
        request.httpBody = try? JSONEncoder().encode(body)

        do {
            try await ScoutRequestAuthentication.prepare(to: &request, endpoint: endpoint, apiKey: apiKey)
            let (data, response) = try await session.data(for: request)
            if let http = response as? HTTPURLResponse {
                try ScoutRequestAuthentication.validate(response: http, endpoint: endpoint, request: request)
            }

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

struct ScoutFirstMessageResult {
    let httpStatus: Int?
    let threadID: Int?
    let threadTitle: String?
    let messageID: Int?
    let message: String
}

/// Creates a thread only when its first message is sent. Guardian is the
/// authority for both returned IDs; an ambiguous response must not be replayed.
struct ScoutGuardianFirstMessageService {
    private struct Body: Encodable {
        let role: String
        let content: String
        let title: String
        let project_id: Int?

        private enum CodingKeys: String, CodingKey { case role, content, title, project_id, user_id }

        func encode(to encoder: Encoder) throws {
            var container = encoder.container(keyedBy: CodingKeys.self)
            try container.encode(role, forKey: .role)
            try container.encode(content, forKey: .content)
            try container.encode(title, forKey: .title)
            try container.encodeIfPresent(project_id, forKey: .project_id)
            // Omitting this field invokes Guardian's legacy "default" user.
            // Null lets Guardian derive ownership from the authenticated scope.
            try container.encodeNil(forKey: .user_id)
        }
    }

    private struct Receipt: Decodable {
        struct Thread: Decodable {
            let id: Int
            let title: String?
            let project_id: Int?
        }
        struct Message: Decodable { let id: Int }
        let created_thread: Bool
        let thread_id: Int
        let thread: Thread?
        let message: Message
    }

    static func title(for content: String) -> String {
        let firstLine = content.trimmingCharacters(in: .whitespacesAndNewlines)
            .components(separatedBy: .newlines).first?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return firstLine.isEmpty ? "New Thread" : String(firstLine.prefix(60))
    }

    static func send(
        endpoint: ScoutEndpointProfile,
        content: String,
        projectID: Int?,
        apiKey: String? = nil,
        session: URLSession = .scoutAuthenticated
    ) async -> ScoutFirstMessageResult {
        let trimmed = content.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return .init(httpStatus: 400, threadID: nil, threadTitle: nil, messageID: nil, message: "Message content is empty.")
        }
        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if urlString.hasSuffix("/") { urlString.removeLast() }
        urlString += "/api/chat/messages"
        guard let url = URL(string: urlString), let scheme = url.scheme, !scheme.isEmpty, url.host != nil else {
            return .init(httpStatus: 400, threadID: nil, threadTitle: nil, messageID: nil, message: "Malformed URL.")
        }

        let initialTitle = title(for: trimmed)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 5
        request.httpBody = try? JSONEncoder().encode(Body(role: "user", content: trimmed, title: initialTitle, project_id: projectID))

        do {
            try await ScoutRequestAuthentication.prepare(to: &request, endpoint: endpoint, apiKey: apiKey)
            let (data, response) = try await session.data(for: request)
            if let http = response as? HTTPURLResponse {
                try ScoutRequestAuthentication.validate(response: http, endpoint: endpoint, request: request)
            }
            guard let http = response as? HTTPURLResponse else {
                return .init(httpStatus: nil, threadID: nil, threadTitle: nil, messageID: nil, message: "Unexpected response from server.")
            }
            guard [200, 201].contains(http.statusCode) else {
                return .init(httpStatus: http.statusCode, threadID: nil, threadTitle: nil, messageID: nil,
                             message: "First message returned HTTP \(http.statusCode).")
            }
            guard let receipt = try? JSONDecoder().decode(Receipt.self, from: data),
                  receipt.created_thread, receipt.thread_id > 0, receipt.message.id > 0,
                  receipt.thread == nil || receipt.thread?.id == receipt.thread_id,
                  projectID == nil || receipt.thread?.project_id == projectID else {
                return .init(httpStatus: http.statusCode, threadID: nil, threadTitle: nil, messageID: nil,
                             message: "Guardian did not confirm the new thread and message. Check the sidebar before retrying.")
            }
            let returnedTitle = receipt.thread?.title?.trimmingCharacters(in: .whitespacesAndNewlines)
            return .init(httpStatus: http.statusCode, threadID: receipt.thread_id,
                         threadTitle: returnedTitle?.isEmpty == false ? returnedTitle : initialTitle,
                         messageID: receipt.message.id, message: "Message sent.")
        } catch let error as URLError where error.code == .timedOut {
            return .init(httpStatus: nil, threadID: nil, threadTitle: nil, messageID: nil, message: "First message timed out after 5 seconds.")
        } catch {
            return .init(httpStatus: nil, threadID: nil, threadTitle: nil, messageID: nil, message: "First message failed: \(error.localizedDescription)")
        }
    }
}
