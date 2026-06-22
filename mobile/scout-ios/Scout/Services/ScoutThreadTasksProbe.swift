import Foundation

struct ScoutThreadTasksResult {
    let httpStatus: Int?
    let tasks: [ScoutTaskReceiptSummary]?
    let message: String
}

struct ScoutThreadTasksProbe {

    static func probe(
        endpoint: ScoutEndpointProfile,
        threadId: Int,
        apiKey: String? = nil,
        session: URLSession = .shared
    ) async -> ScoutThreadTasksResult {
        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !urlString.isEmpty else {
            return ScoutThreadTasksResult(
                httpStatus: nil, tasks: nil, message: "Base URL is empty."
            )
        }

        if urlString.hasSuffix("/") {
            urlString = String(urlString.dropLast())
        }
        urlString += "/api/chat/threads/\(threadId)/tasks"

        guard let url = URL(string: urlString),
              let scheme = url.scheme, !scheme.isEmpty,
              url.host != nil else {
            return ScoutThreadTasksResult(
                httpStatus: nil, tasks: nil, message: "Malformed tasks URL."
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
                return ScoutThreadTasksResult(
                    httpStatus: nil, tasks: nil, message: "Unexpected response type."
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                let decoded = try? JSONDecoder().decode(ScoutThreadTasksResponse.self, from: data)
                let count = decoded?.tasks?.count ?? 0
                return ScoutThreadTasksResult(
                    httpStatus: statusCode,
                    tasks: decoded?.tasks,
                    message: count > 0 ? "\(count) task receipt(s)." : "No task receipts for this thread."
                )
            case 401, 403:
                return ScoutThreadTasksResult(
                    httpStatus: statusCode, tasks: nil,
                    message: "Authentication required (HTTP \(statusCode))."
                )
            default:
                return ScoutThreadTasksResult(
                    httpStatus: statusCode, tasks: nil,
                    message: "Tasks request returned HTTP \(statusCode)."
                )
            }
        } catch let error as URLError where error.code == .timedOut {
            return ScoutThreadTasksResult(
                httpStatus: nil, tasks: nil, message: "Tasks request timed out."
            )
        } catch {
            return ScoutThreadTasksResult(
                httpStatus: nil, tasks: nil,
                message: "Tasks request failed: \(error.localizedDescription)"
            )
        }
    }
}
