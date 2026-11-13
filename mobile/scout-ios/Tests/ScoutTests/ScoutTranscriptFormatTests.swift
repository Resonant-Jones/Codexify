import Foundation
import XCTest
@testable import Scout

final class ScoutTranscriptFormatTests: XCTestCase {
    func testMarkdownPreservesUnicodeAndProjectsTablesAndDiagramSource() throws {
        let source = """
            # Résumé — 日本語 🧭

            > **Note** &rarr; $\\leftrightarrow$

            1. First
            2. `\\rightarrow`

            | Name | |
            | - | - |
            | | ~~Ready~~ |

            ---

            ```mermaid
            flowchart LR
                A["Café"] --> B["東京"]
            ```
            """
        let blocks = try XCTUnwrap(ScoutTranscriptFormat.markdown(source))
        XCTAssertEqual(blocks.count, 7)
        guard case let .prose(header, heading, false, nil, 0) = blocks[0],
              case let .prose(quote, nil, true, nil, 0) = blocks[1],
              case .prose(_, nil, false, "1.", 1) = blocks[2],
              case let .prose(inlineCode, nil, false, "2.", 1) = blocks[3],
              case let .table(rows) = blocks[4],
              case .divider = blocks[5],
              case let .code(diagram, "mermaid") = blocks[6] else {
            return XCTFail("Unexpected Markdown structure")
        }
        XCTAssertEqual(heading, 1)
        XCTAssertEqual(String(header.characters), "Résumé — 日本語 🧭")
        XCTAssertEqual(String(quote.characters), "Note → ↔")
        XCTAssertEqual(String(inlineCode.characters), "\\rightarrow")
        XCTAssertEqual(rows.map { $0.map { String($0.characters) } }, [["Name", ""], ["", "Ready"]])
        XCTAssertEqual(diagram, "flowchart LR\n    A[\"Café\"] --> B[\"東京\"]\n")
    }

    func testMarkupKeepsImageAltTextAndRejectsExecutableLinks() throws {
        let source = "[Allowed](https://example.test) [Blocked](javascript:alert%281%29) ![Alt](https://example.test/pixel) <b>literal</b>"
        let blocks = try XCTUnwrap(ScoutTranscriptFormat.markdown(source))
        guard case let .prose(text, _, _, _, _) = blocks.first else { return XCTFail("Expected prose") }
        XCTAssertEqual(String(text.characters), "Allowed Blocked Alt <b>literal</b>")
        XCTAssertEqual(text.runs.compactMap(\.link), [URL(string: "https://example.test")!])
        XCTAssertTrue(text.runs.allSatisfy { $0.imageURL == nil })
    }

    func testEncodingRepairIsASeparateCandidateAndPreservesCorrectUnicode() {
        let source = "FranÃ§ais â€” ðŸ§­ • 日本語 and Cafe\u{301}"
        XCTAssertEqual(ScoutTranscriptFormat.repairedEncodingPreview(source), "Français — 🧭 • 日本語 and Cafe\u{301}")
        XCTAssertNil(ScoutTranscriptFormat.repairedEncodingPreview("Français — 🧭 • 日本語 and Cafe\u{301}"))
        XCTAssertNil(ScoutTranscriptFormat.repairedEncodingPreview("Preserve undecodable � and standalone Ã"))
        XCTAssertEqual(ScoutTranscriptFormat.repairedEncodingPreview("emoji ð\u{9F}\u{A7}\u{AD}"), "emoji 🧭")
    }

    func testLargeTranscriptFallsBackWithoutParsing() {
        let source = String(repeating: "🧭", count: ScoutTranscriptFormat.maximumFormattedBytes / 4 + 1)
        XCTAssertNil(ScoutTranscriptFormat.markdown(source))
        XCTAssertNil(ScoutTranscriptFormat.repairedEncodingPreview(source))
    }
}
