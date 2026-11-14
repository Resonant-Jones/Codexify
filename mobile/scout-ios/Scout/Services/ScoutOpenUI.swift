import Foundation

struct ScoutOpenUIProgram: Equatable {
    enum Direction: String {
        case vertical, horizontal
    }

    let direction: Direction
    let items: [Item]

    enum Item: Equatable {
        case card(heading: String?, children: [Leaf])
        case leaf(Leaf)
    }

    enum TextSize: String {
        case sm, md, lg
    }

    enum Emphasis: String {
        case normal, strong, muted
    }

    enum HeadingLevel: String {
        case h2 = "2", h3 = "3", h4 = "4"
    }

    enum Tone: String {
        case neutral, info, success, warning, danger
    }

    enum Leaf: Equatable {
        case text(String, size: TextSize, emphasis: Emphasis)
        case heading(String, level: HeadingLevel)
        case badge(String, tone: Tone)
        case metric(label: String, value: String, detail: String?)
        case progress(label: String, value: Double, max: Double, status: String?)
        case list([String], ordered: Bool)
    }

    static func decode(program: String, libraryVersion: Int) -> Self? {
        guard libraryVersion == 1 || libraryVersion == 2,
              program.utf16.count <= (libraryVersion == 1 ? 2_048 : 4_096) else { return nil }
        do {
            var parser = try OpenUIParser(program)
            let statements = try parser.parse()
            var admission = OpenUIAdmission(statements: statements)
            return try admission.build(libraryVersion: libraryVersion)
        } catch {
            return nil
        }
    }
}

private enum InvalidOpenUI: Error {
    case program
}

private indirect enum OpenUIValue {
    case call(String, [OpenUIValue])
    case reference(String)
    case string(String)
    case number(Double)
    case boolean(Bool)
    case array([OpenUIValue])
}

private struct OpenUIParser {
    // Tokenize only the literals, names and punctuation used by the approved
    // library. An unrecognized character anywhere invalidates the whole program.
    private static let pattern = try! NSRegularExpression(
        pattern: #"\s+|"(?:[^"\\\x00-\x1F]|\\.)*"|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|[A-Za-z_][A-Za-z0-9_]*|[=(),\[\]]"#
    )
    private struct Token {
        let text: String
        let afterNewline: Bool
    }

    private let tokens: [Token]
    private var index = 0

    init(_ program: String) throws {
        let range = NSRange(program.startIndex..., in: program)
        var tokens: [Token] = []
        var end = 0
        var newline = false
        for match in Self.pattern.matches(in: program, range: range) {
            guard match.range.location == end, let bounds = Range(match.range, in: program) else {
                throw InvalidOpenUI.program
            }
            end = NSMaxRange(match.range)
            let text = program[bounds]
            if text.allSatisfy(\.isWhitespace) {
                newline = newline || text.contains(where: \.isNewline)
            } else {
                tokens.append(.init(text: String(text), afterNewline: newline))
                newline = false
            }
        }
        guard end == range.length else { throw InvalidOpenUI.program }
        self.tokens = tokens
    }

    mutating func parse() throws -> [String: OpenUIValue] {
        var statements: [String: OpenUIValue] = [:]
        while index < tokens.count {
            guard statements.count < 16, index == 0 || tokens[index].afterNewline,
                  let name = take(), Self.isIdentifier(name), name != "true", name != "false",
                  statements[name] == nil, consume("=") else { throw InvalidOpenUI.program }
            let value = try expression(depth: 0)
            guard case .call = value else { throw InvalidOpenUI.program }
            statements[name] = value
        }
        return statements
    }

    private mutating func expression(depth: Int) throws -> OpenUIValue {
        // Bound syntax depth before descending. Admission separately limits the
        // resolved component tree to Stack -> Card -> leaf.
        guard depth <= 8, let token = take() else { throw InvalidOpenUI.program }
        switch token {
        case "[":
            return .array(try values(until: "]", depth: depth + 1))
        case "true":
            return .boolean(true)
        case "false":
            return .boolean(false)
        default:
            if token.hasPrefix("\"") {
                guard let literal = try? JSONDecoder().decode(String.self, from: Data(token.utf8)) else {
                    throw InvalidOpenUI.program
                }
                return .string(literal)
            }
            if Self.isIdentifier(token) {
                if consume("(") {
                    return .call(token, try values(until: ")", depth: depth + 1))
                }
                return .reference(token)
            }
            guard let number = Double(token), number.isFinite else { throw InvalidOpenUI.program }
            return .number(number)
        }
    }

    private mutating func values(until close: String, depth: Int) throws -> [OpenUIValue] {
        var result: [OpenUIValue] = []
        if consume(close) { return result }
        repeat {
            guard result.count < 12 else { throw InvalidOpenUI.program }
            result.append(try expression(depth: depth))
            if consume(close) { return result }
        } while consume(",")
        throw InvalidOpenUI.program
    }

    private static func isIdentifier(_ token: String) -> Bool {
        // The lexer has already matched the complete identifier.
        token.first.map { $0.isASCII && ($0.isLetter || $0 == "_") } == true
    }

    private mutating func take() -> String? {
        guard index < tokens.count else { return nil }
        defer { index += 1 }
        return tokens[index].text
    }

    private mutating func consume(_ text: String) -> Bool {
        guard index < tokens.count, tokens[index].text == text else { return false }
        index += 1
        return true
    }
}

private struct OpenUIAdmission {
    typealias Program = ScoutOpenUIProgram

    let statements: [String: OpenUIValue]
    private var used: Set<String> = ["root"]
    private var nodeCount = 0

    init(statements: [String: OpenUIValue]) {
        self.statements = statements
    }

    mutating func build(libraryVersion: Int) throws -> Program {
        guard let root = statements["root"] else { throw InvalidOpenUI.program }
        let call = try component(root, path: ["root"])
        if libraryVersion == 1 {
            guard call.name == "CodexifyMetric", statements.count == 1 else { throw InvalidOpenUI.program }
            return .init(direction: .vertical, items: [.leaf(try leaf(call))])
        }

        guard call.name == "CodexifyStack" else { throw InvalidOpenUI.program }
        var args = call.args
        let direction: Program.Direction = try args.readEnum()
        let children = try args.array()
        // The mobile layout stacks horizontally requested items when they can't
        // fit. The wire hint must still be a valid literal when present.
        if !args.isEmpty { _ = try args.boolean() }
        try args.requireEnd()

        var items: [Program.Item] = []
        for child in children {
            let call = try component(child, path: call.path)
            if call.name == "CodexifyCard" {
                var card = call.args
                let children = try card.array()
                guard children.count <= 8 else { throw InvalidOpenUI.program }
                let heading = try card.optionalString(max: 120)
                try card.requireEnd()
                var leaves: [Program.Leaf] = []
                for child in children {
                    leaves.append(try leaf(component(child, path: call.path)))
                }
                items.append(.card(heading: heading, children: leaves))
            } else {
                items.append(.leaf(try leaf(call)))
            }
        }
        guard used.count == statements.count else { throw InvalidOpenUI.program }
        return .init(direction: direction, items: items)
    }

    private struct Component {
        let name: String
        let args: OpenUIArguments
        let path: Set<String>
    }

    private mutating func component(_ value: OpenUIValue, path: Set<String>) throws -> Component {
        nodeCount += 1
        guard nodeCount <= 12 else { throw InvalidOpenUI.program }

        let resolved: OpenUIValue
        var path = path
        if case let .reference(name) = value {
            guard path.insert(name).inserted, let statement = statements[name] else {
                throw InvalidOpenUI.program
            }
            used.insert(name)
            resolved = statement
        } else {
            resolved = value
        }
        guard case let .call(name, values) = resolved else { throw InvalidOpenUI.program }
        return .init(name: name, args: .init(values), path: path)
    }

    private func leaf(_ call: Component) throws -> Program.Leaf {
        var args = call.args
        let result: Program.Leaf
        switch call.name {
        case "CodexifyText":
            result = try .text(args.string(max: 400), size: args.readEnum(default: .md),
                               emphasis: args.readEnum(default: .normal))
        case "CodexifyHeading":
            result = try .heading(args.string(max: 120), level: args.readEnum(default: .h2))
        case "CodexifyBadge":
            result = try .badge(args.string(max: 40), tone: args.readEnum(default: .neutral))
        case "CodexifyMetric":
            result = try .metric(label: args.string(max: 100), value: args.string(max: 40),
                                 detail: args.optionalString(max: 180))
        case "CodexifyProgress":
            let label = try args.string(max: 100)
            let value = try args.number()
            let max = try args.number()
            guard max > 0, value >= 0, value <= max else { throw InvalidOpenUI.program }
            result = try .progress(label: label, value: value, max: max, status: args.optionalString(max: 80))
        case "CodexifyList":
            let values = try args.array()
            let items = try values.map { value in
                guard case let .string(text) = value, text.utf16.count <= 160 else {
                    throw InvalidOpenUI.program
                }
                return text
            }
            result = .list(items, ordered: args.isEmpty ? false : try args.boolean())
        default:
            throw InvalidOpenUI.program
        }
        try args.requireEnd()
        return result
    }
}

private struct OpenUIArguments {
    private var values: ArraySlice<OpenUIValue>
    var isEmpty: Bool { values.isEmpty }

    init(_ values: [OpenUIValue]) {
        self.values = values[...]
    }

    func requireEnd() throws {
        guard isEmpty else { throw InvalidOpenUI.program }
    }

    mutating func string(max: Int) throws -> String {
        guard case let .string(value)? = values.popFirst(), value.utf16.count <= max else {
            throw InvalidOpenUI.program
        }
        return value
    }

    mutating func optionalString(max: Int) throws -> String? {
        isEmpty ? nil : try string(max: max)
    }

    mutating func readEnum<T: RawRepresentable>(default fallback: T? = nil) throws -> T where T.RawValue == String {
        if isEmpty, let fallback { return fallback }
        guard case let .string(value)? = values.popFirst(), let result = T(rawValue: value) else {
            throw InvalidOpenUI.program
        }
        return result
    }

    mutating func boolean() throws -> Bool {
        guard case let .boolean(value)? = values.popFirst() else { throw InvalidOpenUI.program }
        return value
    }

    mutating func number() throws -> Double {
        guard case let .number(value)? = values.popFirst() else { throw InvalidOpenUI.program }
        return value
    }

    mutating func array() throws -> [OpenUIValue] {
        guard case let .array(value)? = values.popFirst() else { throw InvalidOpenUI.program }
        return value
    }
}
