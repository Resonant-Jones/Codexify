import CoreFoundation
import Foundation

/// The widget is derived from an authorized assistant message and held in memory.
struct ScoutSandboxWidget: Equatable {
    let title: String
    let html: String
    let css: String
    let javascript: String
    let inlineHeight: Double

    init?(envelope: [String: Any]) {
        guard let html = envelope["html"] as? String,
              !html.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return nil }
        let css = envelope["css"] as? String ?? ""
        let javascript = envelope["js"] as? String ?? ""
        let title = (envelope["title"] as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        guard html.utf16.count <= 120_000, css.utf16.count <= 60_000,
              javascript.utf16.count <= 80_000, title.utf16.count <= 200 else { return nil }
        if let height = envelope["initialHeight"] as? String,
           Double(height.trimmingCharacters(in: .whitespacesAndNewlines))?.isFinite != true {
            return nil
        }

        self.title = title
        self.html = html
        self.css = css
        self.javascript = javascript
        if let height = envelope["initialHeight"] as? NSNumber,
           CFGetTypeID(height) != CFBooleanGetTypeID(),
           height.doubleValue.isFinite {
            inlineHeight = min(400, max(144, height.doubleValue))
        } else {
            inlineHeight = 220
        }
    }

    static let navigationURL = "about:blank"
    static let frameURL = "about:srcdoc"

    // Resource policy also covers loads that do not invoke a navigation delegate,
    // including preconnect and DNS prefetch in WebKit.
    static let resourceRules = #"""
    [
      {"trigger":{"url-filter":".*"},"action":{"type":"block"}},
      {"trigger":{"url-filter":"^about:"},"action":{"type":"ignore-previous-rules"}},
      {"trigger":{"url-filter":"^data:"},"action":{"type":"ignore-previous-rules"}},
      {"trigger":{"url-filter":"^blob:"},"action":{"type":"ignore-previous-rules"}}
    ]
    """#

    func document(audioScript: String? = nil, interactive: Bool = true) -> String {
        let policy = """
        default-src 'none'; script-src \(interactive ? "'unsafe-inline'" : "'none'"); style-src 'unsafe-inline';
        img-src data: blob:; media-src \(interactive ? "data: blob:" : "'none'"); connect-src 'none';
        frame-src 'none'; form-action 'none'; base-uri 'none'
        """
        let bootstrap = """
        <script>
          // Keep sizing calls compatible in Scout's scrollable viewport.
          Object.defineProperty(window, "cfyUI", {
            value: Object.freeze({resize() {}, resizeTo() {}})
          });
          window.addEventListener("message", event => {
            if (!event.isTrusted || event.source !== window.parent ||
                event.data?.channel !== "cfy-widget-framed-fill" ||
                typeof event.data.enabled !== "boolean") return;
            document.documentElement.toggleAttribute("data-scout-framed-fill", event.data.enabled);
          });
        </script>
        <script>\(Self.escapeRawText(audioScript ?? "", element: "script"))</script>
        """
        let widgetScript = "<script>\(Self.escapeRawText(javascript, element: "script"))</script>"
        let content = """
        <!doctype html><html lang="en"><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <meta http-equiv="Content-Security-Policy" content="\(policy)">
        <meta name="referrer" content="no-referrer">
        <meta http-equiv="X-DNS-Prefetch-Control" content="off">
        <style>
          :root { color-scheme: light dark; }
          * { box-sizing: border-box; }
          body { margin: 0; padding: .75rem; color: CanvasText;
                 background: var(--scout-widget-background, Canvas);
                 font: 1rem/1.45 system-ui; overflow-wrap: anywhere; }
          html[data-scout-framed-fill] { --scout-widget-background: transparent; }
          html[data-scout-framed-fill] body { min-block-size: 100vh; align-content: safe center; }
          button, input, textarea, select { font: inherit; }
          button, button * {
            -webkit-user-select: none !important;
            user-select: none !important;
            -webkit-touch-callout: none !important;
          }
        </style>
        <style>\(Self.escapeRawText(css, element: "style"))</style>
        </head><body>
        \(interactive ? bootstrap : "")
        \(html)
        \(interactive ? widgetScript : "")
        </body></html>
        """

        // Generated markup is only an attribute value in the trusted document.
        // The parent's policy survives any attempted navigation of its child.
        return """
        <!doctype html><html lang="en"><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <meta http-equiv="Content-Security-Policy" content="\(policy)">
        <style>
          :root { color-scheme: light dark; }
          html, body { margin: 0; width: 100%; height: 100%; overflow: hidden; }
          iframe { display: block; width: 100%; height: 100%; border: 0; }
        </style>
        </head><body>
        <iframe title="\(Self.escapeAttribute(title.isEmpty ? "Interactive widget" : title))"
          sandbox="\(interactive ? "allow-scripts" : "")" referrerpolicy="no-referrer" srcdoc="\(Self.escapeAttribute(content))"></iframe>
        </body></html>
        """
    }

    private static func escapeAttribute(_ text: String) -> String {
        text.replacingOccurrences(of: "&", with: "&amp;")
            .replacingOccurrences(of: "\"", with: "&quot;")
            .replacingOccurrences(of: "<", with: "&lt;")
            .replacingOccurrences(of: ">", with: "&gt;")
    }

    private static func escapeRawText(_ text: String, element: String) -> String {
        text.replacingOccurrences(of: "</" + element, with: "<\\/" + element, options: .caseInsensitive)
    }
}
