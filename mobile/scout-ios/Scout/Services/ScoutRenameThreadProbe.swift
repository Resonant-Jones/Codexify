import Foundation

struct ScoutRenameThreadResult {
    let httpStatus: Int?
    let message: String
}

struct ScoutRenameThreadProbe {

    static func rename(
        endpoint: ScoutEndpointProfile,
        threadId: Int,
        title: String,
        apiKey: String? = nil,
        session: URLSession = .shared
    ) async -> ScoutRenameThreadResult {
        let trimmed = title.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return ScoutRenameThreadResult(
                httpStatus: nil, message: "Thread title is empty."
            )
        }

        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !urlString.isEmpty else {
            return ScoutRenameThreadResult(
                httpStatus: nil, message: "Base URL is empty."
            )
        }

        if urlString.hasSuffix("/") {
            urlString = String(urlString.dropLast())
        }
        urlString += "/api/chat/threads/\(threadId)"

        guard let url = URL(string: urlString),
              let scheme = url.scheme, !scheme.isEmpty,
              url.host != nil else {
            return ScoutRenameThreadResult(
                httpStatus: nil, message: "Malformed URL."
            )
        }

        var request = URLRequest(url: url)
        request.httpMethod = "PATCH"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 5

        let hasApiKey = apiKey.map { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty } ?? false
        if let key = apiKey, hasApiKey {
            request.setValue(key, forHTTPHeaderField: "X-API-Key")
        }

        let body: [String: String] = ["title": trimmed]
        request.httpBody = try? JSONEncoder().encode(body)

        do {
            let (_, response) = try await session.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                return ScoutRenameThreadResult(
                    httpStatus: nil, message: "Unexpected response type."
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                return ScoutRenameThreadResult(
                    httpStatus: statusCode, message: "Thread renamed."
                )
            case 401, 403:
                return ScoutRenameThreadResult(
                    httpStatus: statusCode,
                    message: "Authentication required (HTTP \(statusCode))."
                )
            default:
                return ScoutRenameThreadResult(
                    httpStatus: statusCode,
                    message: "Rename returned HTTP \(statusCode)."
                )
            }
        } catch let error as URLError where error.code == .timedOut {
            return ScoutRenameThreadResult(
                httpStatus: nil, message: "Rename timed out."
            )
        } catch {
            return ScoutRenameThreadResult(
                httpStatus: nil, message: "Rename failed: \(error.localizedDescription)"
            )
        }
    }
}
