import SwiftUI
import WebKit

struct ScoutMermaidSheet: View {
    let source: String
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme
    @State private var showSource = false
    @State private var phase = Phase.loading

    fileprivate enum Phase { case loading, ready, failed }

    static func canPreview(_ source: String) -> Bool {
        source.utf8.count <= 16 * 1024
    }

    var body: some View {
        NavigationStack {
            Group {
                if showSource {
                    ScrollView {
                        Text(verbatim: source).font(.system(.body, design: .monospaced))
                            .textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding()
                    }
                } else if phase == .failed {
                    ContentUnavailableView("Diagram unavailable", systemImage: "exclamationmark.triangle",
                        description: Text("Open Source to read the diagram definition."))
                } else {
                    MermaidWebView(source: source, dark: colorScheme == .dark, phase: $phase)
                        .overlay { if phase == .loading { ProgressView("Rendering diagram…") } }
                }
            }
            .navigationTitle("Mermaid diagram")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Done") { dismiss() } }
                ToolbarItem(placement: .primaryAction) {
                    Button(showSource ? "Diagram" : "Source") {
                        if showSource { phase = .loading }
                        showSource.toggle()
                    }
                }
            }
        }
    }
}

private struct MermaidWebView: UIViewRepresentable {
    let source: String
    let dark: Bool
    @Binding var phase: ScoutMermaidSheet.Phase

    private static let engine: String? = {
        guard let url = Bundle.main.url(forResource: "ScoutMermaid", withExtension: "zlib"),
              let compressed = try? Data(contentsOf: url),
              let script = try? (compressed as NSData).decompressed(using: .zlib) else { return nil }
        return String(data: script as Data, encoding: .utf8)
    }()

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        if let engine = Self.engine {
            config.userContentController.addUserScript(WKUserScript(source: engine,
                injectionTime: .atDocumentEnd, forMainFrameOnly: true, in: .defaultClient))
        }
        let view = WKWebView(frame: .zero, configuration: config)
        view.navigationDelegate = context.coordinator
        view.isOpaque = false
        view.backgroundColor = .clear
        view.accessibilityLabel = "Mermaid diagram"
        // Imported text enters as a JavaScript argument. The page has no
        // network, file read access, credential bridge, or clickable links.
        view.loadHTMLString("""
            <!doctype html>
            <html><head><meta charset="utf-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
            <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
            <style>
              :root { color-scheme: light dark; }
              body { margin: 16px; font-family: -apple-system, sans-serif; }
              svg { display: block; max-width: 100%; height: auto; }
            </style></head>
            <body><main id="diagram"></main></body></html>
            """, baseURL: nil)
        return view
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(source: source, dark: dark, phase: $phase) }

    final class Coordinator: NSObject, WKNavigationDelegate {
        let source: String
        let dark: Bool
        @Binding var phase: ScoutMermaidSheet.Phase
        private var initialLoad = true

        init(source: String, dark: Bool, phase: Binding<ScoutMermaidSheet.Phase>) {
            self.source = source
            self.dark = dark
            _phase = phase
        }

        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            let isInitialPage = initialLoad && navigationAction.request.url?.absoluteString == "about:blank"
            decisionHandler(isInitialPage ? .allow : .cancel)
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            initialLoad = false
            webView.callAsyncJavaScript("""
                mermaid.initialize({
                  startOnLoad: false, securityLevel: 'strict', htmlLabels: false,
                  maxTextSize: 16384, maxEdges: 150, suppressErrorRendering: true,
                  theme: dark ? 'dark' : 'default',
                  secure: ['secure', 'securityLevel', 'startOnLoad', 'maxTextSize',
                           'maxEdges', 'suppressErrorRendering', 'htmlLabels', 'theme', 'themeCSS']
                });
                const diagram = await mermaid.render('scout-diagram', source);
                const template = document.createElement('template');
                template.innerHTML = diagram.svg;
                const svg = template.content.querySelector('svg');
                if (!svg) throw new Error('Missing diagram');
                svg.querySelectorAll('a').forEach(anchor => {
                    anchor.removeAttribute('href');
                    anchor.removeAttributeNS('http://www.w3.org/1999/xlink', 'href');
                    anchor.removeAttribute('target');
                });
                document.getElementById('diagram').replaceChildren(svg);
                """, arguments: ["source": source, "dark": dark], in: nil, in: .defaultClient) { [weak self] result in
                    switch result {
                    case .success: self?.phase = .ready
                    case .failure: self?.phase = .failed
                    }
                }
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            phase = .failed
        }

        func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
            phase = .failed
        }
    }
}
