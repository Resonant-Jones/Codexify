import Foundation

struct ScoutTaskEvent: Equatable {
    let eventId: String?
    let eventType: String?
    let data: String?
    let createdAt: String?

    var parsedData: [String: Any]? {
        guard let data = data,
              let jsonData = data.data(using: .utf8) else { return nil }
        return try? JSONSerialization.jsonObject(with: jsonData) as? [String: Any]
    }

    var isTerminal: Bool {
        guard let type = eventType else { return false }
        return ["task.completed", "task.failed", "task.cancelled"].contains(type)
    }
}

enum ScoutSSEParseError: Error {
    case malformedLine(String)
}

struct ScoutSSEParser {
    /// Parse raw SSE text into an array of ScoutTaskEvent.
    static func parse(_ text: String) -> [ScoutTaskEvent] {
        var events: [ScoutTaskEvent] = []
        var currentId: String? = nil
        var currentEvent: String? = nil
        var currentData: String = ""
        var currentCreatedAt: String? = nil

        for line in text.replacingOccurrences(of: "\r\n", with: "\n").components(separatedBy: "\n") {
            let trimmed = line.trimmingCharacters(in: .whitespaces)

            if trimmed.isEmpty {
                // Empty line = end of event
                if !currentData.isEmpty || currentEvent != nil {
                    events.append(ScoutTaskEvent(
                        eventId: currentId,
                        eventType: currentEvent,
                        data: currentData.isEmpty ? nil : currentData,
                        createdAt: currentCreatedAt
                    ))
                }
                currentId = nil
                currentEvent = nil
                currentData = ""
                currentCreatedAt = nil
                continue
            }

            if trimmed.hasPrefix(":") {
                // Comment line - skip
                continue
            }

            guard let colonIndex = trimmed.firstIndex(of: ":") else {
                continue
            }

            let field = String(trimmed[..<colonIndex]).trimmingCharacters(in: .whitespaces)
            var value = String(trimmed[trimmed.index(after: colonIndex)...])
            if value.hasPrefix(" ") {
                value = String(value.dropFirst())
            }

            switch field {
            case "id":
                currentId = value.isEmpty ? nil : value
            case "event":
                currentEvent = value.isEmpty ? nil : value
            case "data":
                if currentData.isEmpty {
                    currentData = value
                } else {
                    currentData += "\n" + value
                }
            case "retry":
                // retry hint - not stored as event field
                break
            default:
                break
            }
        }

        return events
    }
}

struct ScoutTaskEventStreamService {
    private struct HTTPFailure: LocalizedError {
        let status: Int

        var errorDescription: String? { "The task event stream returned HTTP \(status)." }
    }

    static func streamEvents(
        endpoint: ScoutEndpointProfile,
        taskId: String,
        apiKey: String? = nil,
        lastId: String = "0-0",
        session: URLSession = .scoutAuthenticated,
        retryDelays: [Duration] = [.seconds(1), .seconds(2), .seconds(4), .seconds(8)],
        isCurrent: @escaping @MainActor () -> Bool = { true }
    ) -> AsyncThrowingStream<ScoutTaskEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                var cursor = lastId
                var delays = retryDelays.makeIterator()

                do {
                    while !Task.isCancelled, await isCurrent() {
                        do {
                            try await readConnection(endpoint: endpoint, taskId: taskId, apiKey: apiKey,
                                                     cursor: cursor, session: session, isCurrent: isCurrent) { event in
                                if let id = event.eventId {
                                    guard id != cursor else { return }
                                    cursor = id
                                }
                                continuation.yield(event)
                            }
                            continuation.finish()
                            return
                        } catch {
                            guard isRetryable(error), let delay = delays.next() else { throw error }
                            try await Task.sleep(for: delay)
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }

            continuation.onTermination = { _ in
                task.cancel()
            }
        }
    }

    private static func readConnection(
        endpoint: ScoutEndpointProfile, taskId: String, apiKey: String?, cursor: String, session: URLSession,
        isCurrent: @MainActor () -> Bool, receive: (ScoutTaskEvent) -> Void
    ) async throws {
        var baseURL = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if baseURL.hasSuffix("/") { baseURL.removeLast() }
        guard var components = URLComponents(string: baseURL + "/api/tasks/\(taskId)/events"),
              let scheme = components.scheme, !scheme.isEmpty, components.host != nil else {
            throw URLError(.badURL)
        }
        components.queryItems = [URLQueryItem(name: "last_id", value: cursor)]
        guard let url = components.url else { throw URLError(.badURL) }

        var request = URLRequest(url: url)
        request.timeoutInterval = 30
        try await ScoutRequestAuthentication.prepare(to: &request, endpoint: endpoint, apiKey: apiKey)
        guard await isCurrent() else { return }
        try Task.checkCancellation()

        let (bytes, response) = try await session.bytes(for: request)
        guard let http = response as? HTTPURLResponse else { throw URLError(.badServerResponse) }
        try ScoutRequestAuthentication.validate(response: http, endpoint: endpoint, request: request)
        guard (200..<300).contains(http.statusCode) else { throw HTTPFailure(status: http.statusCode) }

        var line = Data()
        var frame = Data()
        for try await byte in bytes {
            try Task.checkCancellation()
            line.append(byte)
            guard byte == 0x0A else { continue }

            frame.append(line)
            let blankLine = line.count == 1 || (line.count == 2 && line.first == 0x0D)
            line.removeAll(keepingCapacity: true)
            guard blankLine else { continue }

            let events = ScoutSSEParser.parse(String(decoding: frame, as: UTF8.self))
            frame.removeAll(keepingCapacity: true)
            for event in events {
                receive(event)
                if event.isTerminal { return }
            }
        }

        // A partial final frame cannot advance the cursor or establish completion.
        throw URLError(.networkConnectionLost)
    }

    private static func isRetryable(_ error: Error) -> Bool {
        if let http = error as? HTTPFailure {
            return [408, 500, 502, 503, 504].contains(http.status)
        }
        guard let error = error as? URLError else { return false }
        switch error.code {
        case .networkConnectionLost, .timedOut, .notConnectedToInternet, .cannotConnectToHost,
             .cannotFindHost, .dnsLookupFailed, .resourceUnavailable:
            return true
        default:
            return false
        }
    }
}
