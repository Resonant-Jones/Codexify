import SwiftUI

struct ScoutTranscriptView: View {
    let source: String
    var markdown = false
    @State private var parsedSource: String?
    @State private var blocks: [ScoutTranscriptFormat.Block]?
    @State private var showSource = false
    @State private var diagram: Diagram?

    private struct Diagram: Identifiable {
        let id = UUID()
        let source: String
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if markdown, parsedSource == source, let blocks, !blocks.isEmpty {
                ForEach(blocks.indices, id: \.self) { index in
                    blockView(blocks[index])
                }
            } else if source.utf8.count > ScoutTranscriptFormat.maximumFormattedBytes {
                prose(AttributedString(ScoutDocumentPage(source).text))
                Button("Read full message") { showSource = true }
            } else {
                prose(AttributedString(source))
            }
        }
        .task(id: source) {
            guard markdown else { return }
            let text = source
            let parsed = await Task.detached(priority: .userInitiated) {
                ScoutTranscriptFormat.markdown(text)
            }.value
            guard !Task.isCancelled else { return }
            blocks = parsed
            parsedSource = text
        }
        .contextMenu {
            Button("View source", systemImage: "doc.plaintext") { showSource = true }
            Button("Copy source", systemImage: "doc.on.doc") { UIPasteboard.general.string = source }
        }
        .sheet(isPresented: $showSource) { ScoutTranscriptSourceView(source: source) }
        .sheet(item: $diagram) { ScoutMermaidSheet(source: $0.source) }
    }

    @ViewBuilder private func blockView(_ block: ScoutTranscriptFormat.Block) -> some View {
        switch block {
        case let .prose(text, heading, quote, marker, depth):
            HStack(alignment: .top, spacing: 6) {
                if quote {
                    Rectangle().fill(Color.secondary.opacity(0.45)).frame(width: 2)
                        .accessibilityHidden(true)
                }
                if let marker { Text(marker).accessibilityHidden(true) }
                if let heading {
                    prose(text).font(heading == 1 ? .title2.bold() : .headline)
                        .accessibilityAddTraits(.isHeader)
                } else {
                    prose(text)
                }
            }
            .padding(.leading, CGFloat(min(depth, 4)) * 8)
        case let .code(text, language):
            VStack(alignment: .leading, spacing: 8) {
                if language?.lowercased() == "mermaid", ScoutMermaidSheet.canPreview(text) {
                    Button("Open Mermaid diagram", systemImage: "point.3.connected.trianglepath.dotted") {
                        diagram = Diagram(source: text)
                    }
                    .frame(minHeight: ScoutVisualStyle.controlMinimum)
                }
                if let language, !language.isEmpty {
                    Text(language.uppercased()).font(.caption).foregroundStyle(.secondary)
                }
                ScrollView(.horizontal) {
                    Text(verbatim: text).font(.system(.body, design: .monospaced))
                        .textSelection(.enabled)
                }
            }
            .modifier(ScoutPanel(secondary: true))
        case .table(let rows):
            ScrollView(.horizontal) {
                Grid(alignment: .topLeading, horizontalSpacing: 12, verticalSpacing: 8) {
                    ForEach(rows.indices, id: \.self) { row in
                        GridRow {
                            ForEach(rows[row].indices, id: \.self) { column in
                                if row == 0 {
                                    prose(rows[row][column]).font(.headline)
                                        .accessibilityAddTraits(.isHeader)
                                } else {
                                    prose(rows[row][column])
                                }
                            }
                        }
                    }
                }
                .padding(ScoutVisualStyle.inset)
            }
            .modifier(ScoutPanel(secondary: true))
        case .divider:
            Divider()
        }
    }

    private func prose(_ text: AttributedString) -> some View {
        Text(text)
            .foregroundStyle(.primary)
            .fixedSize(horizontal: false, vertical: true)
            .textSelection(.enabled)
    }
}

private struct ScoutTranscriptSourceView: View {
    let source: String
    @Environment(\.dismiss) private var dismiss
    @State private var repaired: String?
    @State private var showRepair = false
    @State private var starts: [String.Index?] = [nil]

    var body: some View {
        let displayed = showRepair ? repaired ?? source : source
        let page = ScoutDocumentPage(displayed, from: starts.last ?? nil)
        NavigationStack {
            ScrollViewReader { scroll in
                ScrollView {
                    Text(verbatim: page.text).font(.body).textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                        .id("source-page")
                }
                .onChange(of: starts.count) { _, _ in scroll.scrollTo("source-page", anchor: .top) }
            }
            .safeAreaInset(edge: .bottom) {
                if page.nextStart != nil || starts.count > 1 {
                    HStack {
                        Button("Previous") { starts.removeLast() }.disabled(starts.count == 1)
                        Spacer()
                        Text("Page \(starts.count)")
                        Spacer()
                        Button("Next") { if let next = page.nextStart { starts.append(next) } }
                            .disabled(page.nextStart == nil)
                    }
                    .padding()
                    .background(.regularMaterial)
                }
            }
            .navigationTitle(showRepair ? "Encoding preview" : "Message source")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
                if repaired != nil {
                    ToolbarItem(placement: .primaryAction) {
                        Button(showRepair ? "Original" : "Preview encoding repair") {
                            starts = [nil]
                            showRepair.toggle()
                        }
                    }
                }
            }
            .task { repaired = ScoutTranscriptFormat.repairedEncodingPreview(source) }
        }
    }
}
