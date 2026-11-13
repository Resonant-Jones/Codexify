import XCTest
@testable import Scout

final class ScoutGenerativeUITests: XCTestCase {
    private func marker(_ props: [String: Any] = ["columns": ["Name", "Ready"], "rows": [["Name": "Scout", "Ready": true]]], base64: Bool = false, overrides: [String: Any] = [:]) throws -> String {
        var envelope: [String: Any] = ["version": 1, "kind": "native", "component": "table.rows", "props": props]
        envelope.merge(overrides) { _, new in new }
        let data = try JSONSerialization.data(withJSONObject: envelope, options: [.sortedKeys])
        let payload = base64 ? data.base64EncodedString().replacingOccurrences(of: "+", with: "-").replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "=", with: "") : String(decoding: data, as: UTF8.self).addingPercentEncoding(withAllowedCharacters: .alphanumerics)!
        return "<!-- cfy-ui:\(payload) -->"
    }
    private func message(_ text: String, role: String = "assistant", id: Int = 7) -> ScoutChatMessageSummary {
        .init(id: id, role: role, content: text, created_at: nil, updated_at: nil)
    }
    private func parse(_ text: String, enabled: Bool = true) -> ScoutGenerativeUIPresentation {
        ScoutGenerativeUI.presentation(for: message(text), enabled: enabled)
    }
    func testBothEncodingsAndProse() throws {
        for base64 in [false, true] {
            let result = parse("Before\n\(try marker(base64: base64))\nAfter")
            XCTAssertEqual(result.text, "Before\n\nAfter")
            XCTAssertEqual(result.tables.first?.rows, [["Scout", "true"]])
        }
    }
    func testSharedCorpus() throws {
        var root = URL(fileURLWithPath: #filePath)
        for _ in 0..<5 { root.deleteLastPathComponent() }
        let data = try Data(contentsOf: root.appendingPathComponent("docs/architecture/generative-ui-marker-corpus.json"))
        let corpus = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let cases = try XCTUnwrap(corpus["cases"] as? [[String: Any]])
        XCTAssertGreaterThan(cases.count, 10)
        for item in cases {
            let result = parse("Before\n\(try XCTUnwrap(item["marker"] as? String))\nAfter")
            XCTAssertEqual(result.text, "Before\n\nAfter", item["label"] as? String ?? "")
            // 'parses' is Web codec validity, not renderability: these corpus
            // examples name chart.bar/evil.shell or sandbox, never table.rows.
            XCTAssertTrue(result.tables.isEmpty)
        }
    }
    func testUnknownEnvelopeAndLayouts() throws {
        for overrides: [String: Any] in [["version": 2], ["version": "1"], ["version": true], ["kind": "sandbox"], ["component": "openui.program"], ["component": "evil.shell"], ["layout": "fullscreen"], ["layout": NSNull()], ["props": "bad"]] {
            XCTAssertTrue(parse(try marker(overrides: overrides)).tables.isEmpty)
        }
        for layout in ["compact", "wide"] { XCTAssertEqual(parse(try marker(overrides: ["layout": layout])).tables.count, 1) }
    }
    func testMalformedAndStreamingMarkers() {
        for marker in ["<!-- cfy-ui:!!! -->", "<!-- cfy-ui:%E0%A4%A -->", "<!-- cfy-ui:{\"html\":\"<b>raw</b>\"} -->", "<!-- cfy-ui:not-finished"] {
            XCTAssertEqual(parse("Before\n\(marker)\nAfter").text, "Before\n\nAfter")
        }
        XCTAssertEqual(parse("start <!-- CFY-UI:bad --> end").text, "start  end")
    }
    func testBoundsAndScalarCells() throws {
        let columns = (0..<10).map { "c\($0)" }
        let row: [String: Any] = ["c0": String(repeating: "x", count: 220), "c1": 42, "c2": false, "c3": NSNull(), "c4": ["html": "no"]]
        let table = try XCTUnwrap(parse(try marker(["columns": columns, "rows": Array(repeating: row, count: 55)])).tables.first)
        XCTAssertEqual(table.columns.count, 8)
        XCTAssertEqual(table.rows.count, 50)
        XCTAssertEqual(table.rows[0], [String(repeating: "x", count: 200), "42", "false", "", "", "", "", ""])
    }
    func testColumnObjectsUnicodeAndTitleBounds() throws {
        let table = try XCTUnwrap(parse(try marker(["title": String(repeating: "t", count: 220), "columns": [["key": "文書"], String(repeating: "k", count: 70), "文書"], "rows": [["文書": "Café 🐦"]]])).tables.first)
        XCTAssertEqual(table.title.utf16.count, 200)
        XCTAssertEqual(table.columns[1].utf16.count, 60)
        XCTAssertEqual(table.rows.first, ["Café 🐦", "", "Café 🐦"])
    }
    func testOversizedInput() throws {
        XCTAssertTrue(parse(try marker(["title": String(repeating: "x", count: 20_001)])).tables.isEmpty)
        let huge = "<!-- cfy-ui:" + String(repeating: "A", count: 260_001) + " -->"
        XCTAssertEqual(parse("start\n\(huge)\nend").text, "start\n\nend")
    }
    func testEmptyTablesAndInvalidRows() throws {
        XCTAssertEqual(parse(try marker([:])).tables.first?.rows, [])
        XCTAssertEqual(parse(try marker(["columns": ["name"], "rows": ["bad", NSNull(), ["name": "value"]]])).tables.first?.rows, [["value"]])
    }
    func testGateAndRoles() throws {
        let content = "Text\n" + (try marker())
        XCTAssertEqual(parse(content, enabled: false), .init(text: "Text", tables: []))
        for role in ["user", "system", "tool", "Assistant"] {
            XCTAssertEqual(ScoutGenerativeUI.presentation(for: message(content, role: role), enabled: true), .init(text: "Text", tables: []))
        }
    }
    func testReloadAndIndependentMessageScopes() throws {
        let original = message("Saved prose\n" + (try marker()))
        let reloaded = try JSONDecoder().decode(ScoutChatMessageSummary.self, from: JSONEncoder().encode(original))
        XCTAssertEqual(ScoutGenerativeUI.presentation(for: original, enabled: true), ScoutGenerativeUI.presentation(for: reloaded, enabled: true))
        XCTAssertEqual(reloaded, original)
        for id in [7, 8] { XCTAssertTrue(ScoutGenerativeUI.presentation(for: message("Other scope", id: id), enabled: true).tables.isEmpty) }
        XCTAssertEqual(ScoutGenerativeUI.presentation(for: original, enabled: true).tables.count, 1)
    }
    func testMultipleArtifactsBounded() throws {
        let content = Array(repeating: try marker(), count: 20).joined(separator: "\n")
        XCTAssertEqual(parse(content + "\nTail").tables.count, 16)
        XCTAssertEqual(parse(content + "\nTail").text, "Tail")
    }
}
