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

        for line in text.components(separatedBy: "\n") {
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

    static func streamEvents(
        endpoint: ScoutEndpointProfile,
        taskId: String,
        apiKey: String? = nil,
        lastId: String = "0-0",
        session: URLSession = .shared
    ) -> AsyncThrowingStream<ScoutTaskEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
                    if urlString.hasSuffix("/") {
                        urlString = String(urlString.dropLast())
                    }
                    urlString += "/api/tasks/\(taskId)/events?last_id=\(lastId)"

                    guard let url = URL(string: urlString),
                          let scheme = url.scheme, !scheme.isEmpty,
                          url.host != nil else {
                        continuation.finish(throwing: URLError(.badURL))
                        return
                    }

                    var request = URLRequest(url: url)
                    request.timeoutInterval = 30

                    let hasApiKey = apiKey.map { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty } ?? false
                    if let key = apiKey, hasApiKey {
                        request.setValue(key, forHTTPHeaderField: "X-API-Key")
                    }

                    let (bytes, response) = try await session.bytes(for: request)

                    guard let httpResponse = response as? HTTPURLResponse,
                          (200..<300).contains(httpResponse.statusCode) else {
                        continuation.finish()
                        return
                    }

                    var buffer = ""
                    var eventBuffer = ""

                    for try await byte in bytes {
                        guard !Task.isCancelled else {
                            continuation.finish()
                            return
                        }

                        guard let char = String(bytes: [byte], encoding: .utf8) else { continue }
                        buffer.append(char)

                        if char == "\n" {
                            eventBuffer.append(buffer)
                            let trimmed = buffer.trimmingCharacters(in: .whitespaces)
                            buffer = ""

                            if trimmed.isEmpty {
                                let events = ScoutSSEParser.parse(eventBuffer)
                                eventBuffer = ""
                                for event in events {
                                    continuation.yield(event)
                                    if event.isTerminal {
                                        continuation.finish()
                                        return
                                    }
                                }
                            }
                        }
                    }

                    // Parse any remaining buffered text
                    if !eventBuffer.isEmpty || !buffer.isEmpty {
                        let events = ScoutSSEParser.parse(eventBuffer + buffer)
                        for event in events {
                            continuation.yield(event)
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
}
