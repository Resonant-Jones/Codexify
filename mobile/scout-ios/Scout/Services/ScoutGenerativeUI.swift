import Foundation
import CoreFoundation

/// Presentation derived solely from a canonical message. No cache, identity,
/// storage, transport, or execution bridge is introduced by this adapter.
struct ScoutGenUITable: Equatable {
    let title: String
    let columns: [String]
    let rows: [[String]]
}

enum ScoutGenerativeUIArtifact: Equatable {
    case table(ScoutGenUITable)
    case openUI(ScoutOpenUIProgram)
    case sandbox(ScoutSandboxWidget)
}

struct ScoutGenerativeUIPresentation: Equatable {
    let text: String
    let artifacts: [ScoutGenerativeUIArtifact]
}

enum ScoutGenerativeUI {
    // Mobile rendering is enabled at a normal launch. Keep an
    // explicit opt-out for development diagnostics.
    static var renderingEnabled: Bool {
        ProcessInfo.processInfo.environment["SCOUT_GENERATIVE_UI"] != "false"
    }

    private static let complete = try! NSRegularExpression(pattern: "<!--\\s*cfy-ui:(.*?)-->", options: [.caseInsensitive, .dotMatchesLineSeparators])
    private static let incomplete = try! NSRegularExpression(pattern: "<!--\\s*cfy-ui:[^\\n]*$", options: [.anchorsMatchLines])
    private static let blankLines = try! NSRegularExpression(pattern: "\\n{3,}")

    static func presentation(for message: ScoutChatMessageSummary, enabled: Bool = renderingEnabled) -> ScoutGenerativeUIPresentation {
        let content = message.content ?? ""
        let range = NSRange(content.startIndex..., in: content)
        var artifacts: [ScoutGenerativeUIArtifact] = []
        if enabled, message.role == "assistant" {
            for match in complete.matches(in: content, range: range) {
                if artifacts.count == 16 { break }
                if let payloadRange = Range(match.range(at: 1), in: content),
                   let artifact = decode(String(content[payloadRange])) {
                    artifacts.append(artifact)
                }
            }
        }
        var text = complete.stringByReplacingMatches(in: content, range: range, withTemplate: "")
        text = incomplete.stringByReplacingMatches(in: text, range: NSRange(text.startIndex..., in: text), withTemplate: "")
        text = blankLines.stringByReplacingMatches(in: text, range: NSRange(text.startIndex..., in: text), withTemplate: "\n\n")
        return .init(text: text.trimmingCharacters(in: .whitespacesAndNewlines), artifacts: artifacts)
    }

    private static func clipped(_ string: String, _ count: Int) -> String {
        String(decoding: string.utf16.prefix(count), as: UTF16.self)
    }

    private static func decode(_ payload: String) -> ScoutGenerativeUIArtifact? {
        // The Web field limits are measured in UTF-16. Percent encoding can
        // use nine ASCII characters per UTF-16 unit, including non-ASCII text.
        guard payload.utf16.count <= 2_400_000 else { return nil }
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
        guard let data, data.count <= 1_600_000,
              let object = try? JSONSerialization.jsonObject(with: data),
              let raw = object as? [String: Any],
              version(raw["version"]) == 1,
              raw["layout"] == nil || ["compact", "wide"].contains(raw["layout"] as? String ?? "") else { return nil }
        if raw["kind"] as? String == "sandbox" {
            return ScoutSandboxWidget(envelope: raw).map(ScoutGenerativeUIArtifact.sandbox)
        }
        guard raw["kind"] as? String == "native",
              let component = (raw["component"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines),
              let props = raw["props"] as? [String: Any],
              let propsData = try? JSONSerialization.data(withJSONObject: props, options: [.fragmentsAllowed, .withoutEscapingSlashes]),
              let propsText = String(data: propsData, encoding: .utf8), propsText.utf16.count <= 20_000 else { return nil }
        switch component {
        case "table.rows":
            return .table(decodeTable(props))
        case "openui.program":
            guard props.count == 2, let libraryVersion = version(props["libraryVersion"]),
                  let source = props["program"] as? String,
                  let program = ScoutOpenUIProgram.decode(program: source, libraryVersion: libraryVersion) else { return nil }
            return .openUI(program)
        default:
            return nil
        }
    }

    private static func version(_ value: Any?) -> Int? {
        guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID() else { return nil }
        return Int(exactly: number.doubleValue)
    }

    private static func decodeTable(_ props: [String: Any]) -> ScoutGenUITable {
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
