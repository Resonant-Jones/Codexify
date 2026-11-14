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
            // The corpus includes valid sandbox artifacts and unsupported
            // native component IDs. Neither should produce a native table.
            XCTAssertTrue(result.tables.isEmpty)
            if item["parses"] as? Bool == false {
                XCTAssertTrue(result.artifacts.isEmpty, item["label"] as? String ?? "")
            }
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
        let huge = "<!-- cfy-ui:" + String(repeating: "A", count: 2_400_001) + " -->"
        XCTAssertEqual(parse("start\n\(huge)\nend").text, "start\n\nend")
    }
    func testEmptyTablesAndInvalidRows() throws {
        XCTAssertEqual(parse(try marker([:])).tables.first?.rows, [])
        XCTAssertEqual(parse(try marker(["columns": ["name"], "rows": ["bad", NSNull(), ["name": "value"]]])).tables.first?.rows, [["value"]])
    }
    func testGateAndRoles() throws {
        let content = "Text\n" + (try marker())
        XCTAssertEqual(parse(content, enabled: false), .init(text: "Text", artifacts: []))
        for role in ["user", "system", "tool", "Assistant"] {
            XCTAssertEqual(ScoutGenerativeUI.presentation(for: message(content, role: role), enabled: true), .init(text: "Text", artifacts: []))
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
    func testRenderingReadsTablesAndBothOpenUIVersionsInOrder() throws {
        let metric = try openUI(1, #"root = CodexifyMetric("Tasks", "12", "Saved")"#)
        let foundation = try openUI(2, #"""
        status = CodexifyBadge("Ready", "success")
        root = CodexifyStack("horizontal", [
            status,
            CodexifyCard([CodexifyHeading("Queue", "3"), CodexifyText("Working", "md", "muted"),
                CodexifyProgress("Indexing", 3, 4, "Almost done"), CodexifyList(["First", "Second"], true)], "Local")
        ], true)
        """#, base64: true)
        let content = try ["Summary", metric, marker(), foundation].joined(separator: "\n")
        let saved = try JSONEncoder().encode(message(content))
        let reloaded = try JSONDecoder().decode(ScoutChatMessageSummary.self, from: saved)
        let result = ScoutGenerativeUI.presentation(for: reloaded, enabled: true)
        XCTAssertEqual(result.text, "Summary")
        XCTAssertEqual(result.artifacts, [
            .openUI(.init(direction: .vertical, items: [.leaf(.metric(label: "Tasks", value: "12", detail: "Saved"))])),
            .table(.init(title: "", columns: ["Name", "Ready"], rows: [["Scout", "true"]])),
            .openUI(.init(direction: .horizontal, items: [
                .leaf(.badge("Ready", tone: .success)),
                .card(heading: "Local", children: [.heading("Queue", level: .h3),
                    .text("Working", size: .md, emphasis: .muted),
                    .progress(label: "Indexing", value: 3, max: 4, status: "Almost done"),
                    .list(["First", "Second"], ordered: true)])
            ]))
        ])
        XCTAssertTrue(ScoutGenerativeUI.presentation(for: reloaded, enabled: false).artifacts.isEmpty)
        XCTAssertTrue(ScoutGenerativeUI.presentation(for: message(metric, role: "user"), enabled: true).artifacts.isEmpty)
    }

    func testOpenUIRejectsUnknownVersionsInvalidProgramsAndNonLiteralArguments() throws {
        let root = #"root = CodexifyStack("vertical", [])"#
        let rejected = [
            try openUI(true, root),
            try openUI(3, root),
            try openUI(1, root),
            try openUI(2, root, extra: ["unexpected": true]),
            try openUI(2, root + "\n" + root),
            try openUI(2, root + "\n" + #"unused = CodexifyText("spare")"#),
            try openUI(2, #"root = CodexifyStack("vertical", [missing])"#),
            try openUI(2, #"card = CodexifyCard([card])"# + "\n" + #"root = CodexifyStack("vertical", [card])"#),
            try openUI(2, #"root = CodexifyStack("vertical", [CodexifyCard([CodexifyCard([])])])"#),
            try openUI(2, #"root = CodexifyStack("vertical", [CodexifyText("x", "md", @Run("send"))])"#),
            try openUI(2, #"root = CodexifyStack("vertical", [CodexifyWidget("x")])"#),
            try openUI(2, #"root = CodexifyStack($direction, [])"#),
            try openUI(2, #"root = CodexifyStack("vertical", [CodexifyProgress("x", 5, 4)])"#),
            try openUI(2, #"root = CodexifyStack("vertical", [CodexifyProgress("x", 1, 1e999)])"#),
            try openUI(2, #"root = CodexifyStack("vertical", [CodexifyBadge("x", "unknown")])"#),
            try openUI(2, String(repeating: " ", count: 4_096) + root),
        ]
        for (index, artifact) in rejected.enumerated() {
            XCTAssertEqual(parse("Keep this\n" + artifact), .init(text: "Keep this", artifacts: []), "Case \(index)")
        }
    }

    func testOpenUIBoundsResolvedNodesAndKeepsMarkupInert() throws {
        let badge = #"CodexifyBadge("Ready")"#
        let accepted = Array(repeating: badge, count: 11).joined(separator: ",")
        XCTAssertEqual(parse(try openUI(2, "root = CodexifyStack(\"vertical\", [\(accepted)])")).artifacts.count, 1)
        XCTAssertTrue(parse(try openUI(2, "root = CodexifyStack(\"vertical\", [\(accepted), \(badge)])")).artifacts.isEmpty)
        let markup = #"<img src=x onerror="run()">"#
        let literal = String(decoding: try JSONEncoder().encode(markup), as: UTF8.self)
        let marker = try openUI(2, "root = CodexifyStack(\"vertical\", [CodexifyText(\(literal))])")
        XCTAssertEqual(parse(marker).artifacts, [.openUI(.init(direction: .vertical, items: [
            .leaf(.text(markup, size: .md, emphasis: .normal))
        ]))])
    }

    func testSandboxArtifactsRoundTripWithProseAndRemainAssistantOnly() throws {
        for base64 in [false, true] {
            let source = try sandbox(["title": " Calculator ", "layout": "wide", "html": "<button>Add</button>",
                                      "css": "button{color:blue}", "js": "document.querySelector('button').onclick=()=>{}"],
                                     base64: base64)
            let original = message("Before\n" + source + "\nAfter")
            let reloaded = try JSONDecoder().decode(ScoutChatMessageSummary.self, from: JSONEncoder().encode(original))
            let result = ScoutGenerativeUI.presentation(for: reloaded, enabled: true)
            XCTAssertEqual(result.text, "Before\n\nAfter")
            guard case let .sandbox(widget)? = result.artifacts.first else {
                return XCTFail("The saved marker should contain a widget")
            }
            XCTAssertEqual(widget.title, "Calculator")
            XCTAssertEqual(widget.html, "<button>Add</button>")
            XCTAssertEqual(widget.css, "button{color:blue}")
            XCTAssertTrue(ScoutGenerativeUI.presentation(for: message(source, role: "user"), enabled: true).artifacts.isEmpty)
            XCTAssertTrue(ScoutGenerativeUI.presentation(for: reloaded, enabled: false).artifacts.isEmpty)
        }
    }

    func testSandboxBoundsApplyToDecodedContent() throws {
        // One BMP character takes nine bytes in the model's percent encoding.
        let html = String(repeating: "界", count: 120_000)
        XCTAssertEqual(parse(try sandbox(["html": html])).artifacts.count, 1)
        for fields: [String: Any] in [
            ["html": html + "x"], ["html": "  "], ["html": "<p>x</p>", "layout": "fullscreen"],
            ["html": "<p>x</p>", "js": String(repeating: "x", count: 80_001)],
            ["html": "<p>x</p>", "css": String(repeating: "x", count: 60_001)]
        ] {
            XCTAssertEqual(parse("Fallback\n" + (try sandbox(fields))), .init(text: "Fallback", artifacts: []))
        }
    }

    func testWidgetCannotBreakOutOfTrustedDocument() throws {
        let widget = try XCTUnwrap(ScoutSandboxWidget(envelope: [
            "title": #"" onload="escape()"#,
            "html": #"</iframe><script src="https://example.invalid/escape"></script>"#,
            "js": #"const text = "</ScRiPt><b>data</b>";"#
        ]))
        let document = widget.document()
        XCTAssertTrue(document.contains(#"sandbox="allow-scripts""#))
        XCTAssertTrue(document.contains("frame-src 'none'"))
        XCTAssertTrue(document.contains("connect-src 'none'"))
        XCTAssertTrue(document.contains(#"title="&quot; onload=&quot;escape()""#))
        XCTAssertTrue(document.lowercased().contains(#"&lt;\/script&gt;&lt;b&gt;data&lt;/b&gt;"#))
        XCTAssertFalse(document.contains(#"<script src="https://example.invalid/escape">"#))
        XCTAssertEqual(document.components(separatedBy: "</iframe>").count, 2)
    }

    func testInlineWidgetHeightHonorsBoundedNumericHints() throws {
        let cases: [(Any?, Double)] = [
            (nil, 220), (false, 220), ("240", 220), (Double.infinity, 220),
            (100, 144), (240.5, 240.5), (1_000, 400),
        ]
        for (hint, expected) in cases {
            var envelope: [String: Any] = ["html": "<button>Play</button>"]
            envelope["initialHeight"] = hint
            let widget = try XCTUnwrap(ScoutSandboxWidget(envelope: envelope))
            XCTAssertEqual(widget.inlineHeight, expected)
        }
    }

    func testWidgetAudioBootstrapPrecedesGeneratedCode() throws {
        let widget = try XCTUnwrap(ScoutSandboxWidget(envelope: [
            "html": #"<button onclick="play()">Play</button>"#,
            "js": "interactive_only()",
        ]))
        let interactive = widget.document(audioScript: "installScoutWidgetAudio()")
        let bootstrap = try XCTUnwrap(interactive.range(of: "installScoutWidgetAudio()"))
        let payload = try XCTUnwrap(interactive.range(of: "&lt;button"))
        XCTAssertLessThan(bootstrap.lowerBound, payload.lowerBound)
        XCTAssertTrue(interactive.contains("interactive_only()"))
    }

    private func sandbox(_ fields: [String: Any], base64: Bool = false) throws -> String {
        try marker(base64: base64, overrides: fields.merging(["kind": "sandbox"]) { _, kind in kind })
    }

    private func openUI(_ version: Any, _ program: String, base64: Bool = false, extra: [String: Any] = [:]) throws -> String {
        try marker(["libraryVersion": version, "program": program].merging(extra) { _, new in new },
                   base64: base64, overrides: ["component": "openui.program"])
    }

}

private extension ScoutGenerativeUIPresentation {
    var tables: [ScoutGenUITable] {
        artifacts.compactMap {
            if case let .table(table) = $0 { return table }
            return nil
        }
    }
}
