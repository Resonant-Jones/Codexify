import Foundation
import CoreFoundation

/// Presentation derived solely from a canonical message. No cache, identity,
/// storage, transport, or execution bridge is introduced by this adapter.
struct ScoutGenUITable: Equatable {
    let title: String
    let columns: [String]
    let rows: [[String]]
}

struct ScoutGenerativeUIPresentation: Equatable {
    let text: String
    let tables: [ScoutGenUITable]
}

enum ScoutGenerativeUI {
    // Native opt-in is independent of Web's VITE_GENERATIVE_UI rendering gate
    // and Guardian's GUARDIAN_GENERATIVE_UI emission gate. Default remains off.
    static var renderingEnabled: Bool {
        ProcessInfo.processInfo.environment["SCOUT_GENERATIVE_UI"] == "true"
    }
    private static let complete = try! NSRegularExpression(pattern: "<!--\\s*cfy-ui:(.*?)-->", options: [.caseInsensitive, .dotMatchesLineSeparators])
    private static let incomplete = try! NSRegularExpression(pattern: "<!--\\s*cfy-ui:[^\\n]*$", options: [.anchorsMatchLines])
    private static let blankLines = try! NSRegularExpression(pattern: "\\n{3,}")

    static func presentation(for message: ScoutChatMessageSummary, enabled: Bool = renderingEnabled) -> ScoutGenerativeUIPresentation {
        let content = message.content ?? ""
        let range = NSRange(content.startIndex..., in: content)
        var tables: [ScoutGenUITable] = []
        for match in complete.matches(in: content, range: range) {
            // Decode only authorized assistant-message presentation, and cap the
            // number of native tables per message to bound mobile layout work.
            guard enabled, message.role == "assistant", tables.count < 16,
                  let payloadRange = Range(match.range(at: 1), in: content),
                  let table = decode(String(content[payloadRange])) else { continue }
            tables.append(table)
        }
        var text = complete.stringByReplacingMatches(in: content, range: range, withTemplate: "")
        text = incomplete.stringByReplacingMatches(in: text, range: NSRange(text.startIndex..., in: text), withTemplate: "")
        text = blankLines.stringByReplacingMatches(in: text, range: NSRange(text.startIndex..., in: text), withTemplate: "\n\n")
        return .init(text: text.trimmingCharacters(in: .whitespacesAndNewlines), tables: tables)
    }

    private static func clipped(_ string: String, _ count: Int) -> String {
        String(decoding: string.utf16.prefix(count), as: UTF16.self)
    }

    private static func decode(_ payload: String) -> ScoutGenUITable? {
        // Reject before allocating decoded JSON; percent-encoded UTF-8 can be
        // larger than base64url. This bound accommodates the native props limit.
        guard payload.utf16.count <= 260_000 else { return nil }
        let input = payload.trimmingCharacters(in: .whitespacesAndNewlines)
        let data: Data?
        if input.contains("%") {
            data = input.removingPercentEncoding?.data(using: .utf8)
        } else {
            guard !input.isEmpty, input.range(of: "^[A-Za-z0-9_-]+={0,2}$", options: .regularExpression) != nil else { return nil }
            var base64 = input.replacingOccurrences(of: "-", with: "+").replacingOccurrences(of: "_", with: "/")
            base64 += String(repeating: "=", count: (4 - base64.utf8.count % 4) % 4)
            data = Data(base64Encoded: base64)
        }
        guard let data, data.count <= 260_000,
              let object = try? JSONSerialization.jsonObject(with: data),
              let raw = object as? [String: Any],
              let version = raw["version"] as? NSNumber,
              CFGetTypeID(version) != CFBooleanGetTypeID(), version.doubleValue == 1,
              raw["kind"] as? String == "native",
              (raw["component"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines) == "table.rows",
              raw["layout"] == nil || ["compact", "wide"].contains(raw["layout"] as? String ?? ""),
              let props = raw["props"] as? [String: Any],
              let propsData = try? JSONSerialization.data(withJSONObject: props, options: [.fragmentsAllowed, .withoutEscapingSlashes]),
              let propsText = String(data: propsData, encoding: .utf8), propsText.utf16.count <= 20_000 else { return nil }
        let columns = ((props["columns"] as? [Any]) ?? []).prefix(8).compactMap { entry -> String? in
            let key = (entry as? String) ?? ((entry as? [String: Any])?["key"] as? String) ?? ""
            let value = clipped(key, 60)
            return value.isEmpty ? nil : value
        }
        let rows = ((props["rows"] as? [Any]) ?? []).prefix(50).compactMap { entry -> [String]? in
            guard let row = entry as? [String: Any] else { return nil }
            return columns.map { column in
                if let text = row[column] as? String { return clipped(text, 200) }
                if let number = row[column] as? NSNumber {
                    if CFGetTypeID(number) == CFBooleanGetTypeID() { return number.boolValue ? "true" : "false" }
                    return clipped(number.stringValue, 200)
                }
                return ""
            }
        }
        return .init(title: clipped(props["title"] as? String ?? "", 200), columns: columns, rows: rows)
    }
}
