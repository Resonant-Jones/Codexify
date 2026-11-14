import Foundation

enum ScoutTranscriptFormat {
    static let maximumFormattedBytes = 64 * 1024

    enum Block {
        case prose(AttributedString, heading: Int?, quote: Bool, marker: String?, depth: Int)
        case code(String, language: String?)
        case table([[AttributedString]])
        case divider
    }

    static func markdown(_ source: String) -> [Block]? {
        guard source.utf8.count <= maximumFormattedBytes,
              let parsed = try? AttributedString(markdown: source, options: .init(interpretedSyntax: .full))
        else { return nil }

        typealias Component = PresentationIntent.IntentType
        var groups: [(intents: [Component], text: AttributedString)] = []
        for run in parsed.runs {
            let intents = run.presentationIntent?.components ?? []
            var text = AttributedString(parsed[run.range])
            let isCode = intents.contains { intent in
                if case .codeBlock = intent.kind { return true }
                return false
            }
            if !isCode, run.inlinePresentationIntent?.contains(.code) != true {
                let original = String(text.characters)
                let normalized = normalizeArrows(original)
                if normalized != original {
                    text = AttributedString(normalized, attributes: run.attributes)
                }
            }
            if let url = text.link, !["https", "http", "mailto"].contains(url.scheme?.lowercased() ?? "") {
                text.link = nil
            }
            text.imageURL = nil
            if groups.last?.intents == intents {
                groups[groups.count - 1].text += text
            } else {
                groups.append((intents, text))
            }
        }

        var blocks: [Block] = []
        var table: [[AttributedString]] = []
        var tableID: Int?
        var renderedListItems: Set<Int> = []
        for (intents, text) in groups {
            let tableIntent = intents.first { intent in
                if case .table = intent.kind { return true }
                return false
            }
            if let parent = tableIntent, case .table(let columns) = parent.kind,
               let cell = intents.first, case .tableCell(let column) = cell.kind,
               intents.count >= 3 {
                if tableID != parent.identity {
                    if !table.isEmpty { blocks.append(.table(table)) }
                    table = []
                    tableID = parent.identity
                }
                let row: Int
                switch intents[1].kind {
                case .tableHeaderRow: row = 0
                case .tableRow(let index): row = index
                default: continue
                }
                guard columns.count > 0, columns.count <= 16,
                      row >= 0, row < 200 / columns.count,
                      column >= 0, column < columns.count else { return nil }
                while table.count <= row {
                    table.append(Array(repeating: AttributedString(), count: columns.count))
                }
                table[row][column] = text
                continue
            }

            if !table.isEmpty {
                blocks.append(.table(table))
                table = []
                tableID = nil
            }

            switch intents.first?.kind {
            case .thematicBreak:
                blocks.append(.divider)
            case .codeBlock(let language):
                blocks.append(.code(String(text.characters), language: language))
            default:
                var heading: Int?
                var quote = false
                var depth = 0
                var marker: String?
                var item: Component?
                for intent in intents {
                    switch intent.kind {
                    case .header(let level): heading = level
                    case .blockQuote: quote = true
                    case .listItem: if item == nil { item = intent }
                    case .orderedList, .unorderedList:
                        depth += 1
                        if depth == 1, let item, case .listItem(let number) = item.kind,
                           renderedListItems.insert(item.identity).inserted {
                            if case .orderedList = intent.kind { marker = "\(number)." }
                            else { marker = "•" }
                        }
                    default: break
                    }
                }
                blocks.append(.prose(text, heading: heading, quote: quote, marker: marker, depth: depth))
            }
        }
        if !table.isEmpty { blocks.append(.table(table)) }
        return blocks
    }

    // Match the Web chat's simple arrow notation in prose and leave code alone.
    private static func normalizeArrows(_ text: String) -> String {
        guard text.contains("\\") else { return text }
        let arrows = [("leftrightarrow", "↔"), ("rightarrow", "→"), ("leftarrow", "←"), ("to", "→")]
        return arrows.reduce(text) { value, arrow in
            let command = #"\\"# + arrow.0
            return value.replacingOccurrences(of: #"\$\s*"# + command + #"\s*\$"#,
                with: arrow.1, options: .regularExpression)
                .replacingOccurrences(of: command + #"\b"#, with: arrow.1, options: .regularExpression)
        }
    }

    /// Preview UTF-8 sequences misdecoded as Latin-1 or Windows-1252. The
    /// user chooses whether to view the candidate; the stored source is untouched.
    static func repairedEncodingPreview(_ source: String) -> String? {
        guard source.utf8.count <= maximumFormattedBytes else { return nil }
        let scalars = Array(source.unicodeScalars)
        var output = String.UnicodeScalarView()
        var index = 0
        while index < scalars.count {
            let scalar = scalars[index]
            let width: Int
            switch scalar.value {
            case 0xC2...0xDF: width = 2
            case 0xE0...0xEF: width = 3
            case 0xF0...0xF4: width = 4
            default: width = 0
            }
            if width > 0, index + width <= scalars.count {
                let bytes = scalars[index..<(index + width)].compactMap(legacyByte)
                if bytes.count == width, let decoded = String(bytes: bytes, encoding: .utf8),
                   let recovered = decoded.unicodeScalars.first, !CharacterSet.controlCharacters.contains(recovered) {
                    output.append(recovered)
                    index += width
                    continue
                }
            }
            output.append(scalar)
            index += 1
        }
        let repaired = String(output)
        return repaired == source ? nil : repaired
    }

    private static func legacyByte(_ scalar: Unicode.Scalar) -> UInt8? {
        if let byte = UInt8(exactly: scalar.value) { return byte }
        return windows1252[scalar]
    }

    private static let windows1252: [Unicode.Scalar: UInt8] = [
        "€": 0x80, "‚": 0x82, "ƒ": 0x83, "„": 0x84, "…": 0x85, "†": 0x86, "‡": 0x87,
        "ˆ": 0x88, "‰": 0x89, "Š": 0x8A, "‹": 0x8B, "Œ": 0x8C, "Ž": 0x8E,
        "‘": 0x91, "’": 0x92, "“": 0x93, "”": 0x94, "•": 0x95, "–": 0x96, "—": 0x97,
        "˜": 0x98, "™": 0x99, "š": 0x9A, "›": 0x9B, "œ": 0x9C, "ž": 0x9E, "Ÿ": 0x9F
    ]
}
