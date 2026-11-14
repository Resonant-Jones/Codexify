import CoreFoundation
import Foundation
import OSLog
import WebKit

/// One opaque child document. The only native capability is bounded local
/// audio output, behind a user-controlled mute and an isolated-world relay.
@MainActor
final class ScoutSandboxWebSession: NSObject, WKNavigationDelegate, WKUIDelegate {
    private enum SetupError: Error { case missingResourceRules, unsupportedSystem }

    private final class AudioMessageHandler: NSObject, WKScriptMessageHandler {
        weak var session: ScoutSandboxWebSession?

        init(session: ScoutSandboxWebSession) { self.session = session }

        func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
            session?.receiveAudioMessage(message)
        }
    }

    private static let audioLog = Logger(subsystem: "ai.resonantconstructs.codexify.scout", category: "WidgetAudio")
    private static let audioWorld = WKContentWorld.world(name: "ScoutWidgetAudio")
    private static let audioHandler = "scoutWidgetAudio"
    private static weak var audibleSession: ScoutSandboxWebSession?
    private static let audioShim = Bundle.main.url(forResource: "ScoutWidgetAudio", withExtension: "js")
        .flatMap { try? String(contentsOf: $0, encoding: .utf8) }

    static var supportsAudio: Bool { audioShim != nil }

    static let resourceRules: Task<WKContentRuleList, Error> = Task {
        guard let rules = try await WKContentRuleListStore.default().compileContentRuleList(
            forIdentifier: "scout-widget-deny-network-v1", encodedContentRuleList: ScoutSandboxWidget.resourceRules
        ) else { throw SetupError.missingResourceRules }
        return rules
    }

    let webView: WKWebView
    var onDocumentReady: (() -> Void)?
    var onFailure: (() -> Void)?
    var onAudioFailure: (() -> Void)?
    var onSoundDisabled: (() -> Void)?
    var onUnsupportedAudio: (() -> Void)?
    private var didAllowHost = false
    private var didAllowWidget = false
    private var closing = false
    private var framedFill = false
    private let interactive: Bool
    private let audioSession: String
    private var output: ScoutWidgetAudioOutput?
    private var lastClip: UInt32 = 0
    private var receivedAudio = false

    static func make(interactive: Bool = true) async throws -> ScoutSandboxWebSession {
        // The file-picker denial callback is available on iOS 18.4 and later.
        #if os(iOS)
        guard #available(iOS 18.4, *) else { throw SetupError.unsupportedSystem }
        #endif
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        config.userContentController.add(try await resourceRules.value)
        // Lockdown disables network-capable features outside CSP, including
        // WebRTC peer connections. Local JavaScript stays enabled.
        if #available(iOS 26.4, macOS 26.4, *) {
            config.defaultWebpagePreferences.securityRestrictionMode = .lockdown
        } else {
            config.defaultWebpagePreferences.isLockdownModeEnabled = true
        }
        config.preferences.javaScriptCanOpenWindowsAutomatically = false
        config.defaultWebpagePreferences.allowsContentJavaScript = interactive
        config.allowsAirPlayForMediaPlayback = false
        config.mediaTypesRequiringUserActionForPlayback = .all
        #if os(iOS)
        config.allowsInlineMediaPlayback = true
        config.allowsPictureInPictureMediaPlayback = false
        config.dataDetectorTypes = []
        #endif
        let session = UUID().uuidString
        if interactive && supportsAudio {
            config.userContentController.addUserScript(WKUserScript(
                source: audioRelay(session: session),
                injectionTime: .atDocumentStart,
                forMainFrameOnly: true,
                in: audioWorld
            ))
        }
        return ScoutSandboxWebSession(configuration: config, session: session, interactive: interactive)
    }

    private init(configuration: WKWebViewConfiguration, session: String, interactive: Bool) {
        self.interactive = interactive
        audioSession = session
        webView = WKWebView(frame: .zero, configuration: configuration)
        super.init()
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsLinkPreview = false
        #if os(iOS)
        webView.isOpaque = false
        #endif
        webView.setAllMediaPlaybackSuspended(true, completionHandler: nil)
        if interactive && Self.supportsAudio {
            webView.configuration.userContentController.add(
                AudioMessageHandler(session: self), contentWorld: Self.audioWorld, name: Self.audioHandler
            )
        }
    }

    func load(_ widget: ScoutSandboxWidget) {
        let shim = interactive ? Self.audioShim.map { $0 + "\ninstallScoutWidgetAudio(\"\(audioSession)\");" } : nil
        webView.loadHTMLString(widget.document(audioScript: shim, interactive: interactive), baseURL: nil)
    }

    func setFramedFill(_ enabled: Bool) {
        guard framedFill != enabled else { return }
        framedFill = enabled
        webView.backgroundColor = enabled ? .clear : nil
        webView.scrollView.backgroundColor = enabled ? .clear : nil
        webView.underPageBackgroundColor = enabled ? .clear : nil
        updateFramedFill()
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        if framedFill { updateFramedFill() }
        let ready = onDocumentReady
        onDocumentReady = nil
        ready?()
    }

    private func updateFramedFill() {
        guard !closing else { return }
        webView.callAsyncJavaScript(
            """
            document.querySelector("iframe")?.contentWindow?.postMessage({
              channel: "cfy-widget-framed-fill", enabled
            }, "*");
            """,
            arguments: ["enabled": framedFill], in: nil, in: .defaultClient,
            completionHandler: nil
        )
    }

    func enableSound() throws {
        guard interactive, output == nil, !closing, Self.supportsAudio else { return }
        Self.audibleSession?.disableSound()
        let newOutput = ScoutWidgetAudioOutput()
        do {
            try newOutput.prepare()
            try newOutput.playTestTone()
        } catch {
            newOutput.close()
            logAudioError(error)
            throw error
        }

        newOutput.onPlaybackFailure = { [weak self] error in
            guard let self else { return }
            self.logAudioError(error)
            self.disableSound()
            self.onAudioFailure?()
        }
        output = newOutput
        Self.audibleSession = self
        receivedAudio = false
        webView.setAllMediaPlaybackSuspended(false, completionHandler: nil)
        sendAudioControl(enabled: true)
        Self.audioLog.notice("Widget audio enabled and test tone scheduled")
    }

    func disableSound() {
        guard let output else { return }
        self.output = nil
        if Self.audibleSession === self { Self.audibleSession = nil }
        sendAudioControl(enabled: false)
        webView.setAllMediaPlaybackSuspended(true, completionHandler: nil)
        output.close()
        onSoundDisabled?()
    }

    private func sendAudioControl(enabled: Bool) {
        guard !closing else { return }
        webView.callAsyncJavaScript(
            """
            const frame = document.querySelector("iframe");
            frame?.contentWindow?.postMessage({
              channel: "cfy-widget-audio-control", session, enabled
            }, "*");
            """,
            arguments: ["session": audioSession, "enabled": enabled], in: nil, in: Self.audioWorld
        ) { result in
            if case let .failure(error) = result {
                Self.audioLog.debug("Audio state delivery failed (\((error as NSError).code, privacy: .public))")
            }
        }
    }

    private func logAudioError(_ error: Error) {
        let error = error as NSError
        Self.audioLog.error("Widget audio output failed (\(error.domain, privacy: .public):\(error.code, privacy: .public))")
    }

    func close() {
        guard !closing else { return }
        disableSound()
        webView.stopLoading()
        onDocumentReady = nil
        onFailure = nil
        onAudioFailure = nil
        onSoundDisabled = nil
        onUnsupportedAudio = nil
        webView.configuration.userContentController.removeScriptMessageHandler(
            forName: Self.audioHandler, contentWorld: Self.audioWorld
        )
        // Replace the document to stop scripts and audio. Keep the policy
        // delegate installed while WebKit tears down the old frame.
        closing = true
        webView.loadHTMLString("", baseURL: nil)
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let frame = action.targetFrame, !action.shouldPerformDownload,
              action.navigationType == .other else { return decisionHandler(.cancel) }
        let url = action.request.url?.absoluteString
        if closing {
            decisionHandler(frame.isMainFrame && url == ScoutSandboxWidget.navigationURL ? .allow : .cancel)
        } else if frame.isMainFrame, !didAllowHost, url == ScoutSandboxWidget.navigationURL {
            didAllowHost = true
            decisionHandler(.allow)
        } else if !frame.isMainFrame, didAllowHost, !didAllowWidget, action.sourceFrame.isMainFrame,
                  url == ScoutSandboxWidget.frameURL {
            didAllowWidget = true
            decisionHandler(.allow)
        } else {
            decisionHandler(.cancel)
        }
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        disableSound()
        onFailure?()
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        disableSound()
        onFailure?()
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        disableSound()
        onFailure?()
    }

    private func receiveAudioMessage(_ message: WKScriptMessage) {
        guard !closing, message.webView === webView, message.world === Self.audioWorld,
              message.frameInfo.isMainFrame, message.name == Self.audioHandler,
              message.frameInfo.request.url?.absoluteString == ScoutSandboxWidget.navigationURL,
              let body = message.body as? [String: Any], body["session"] as? String == audioSession else { return }
        let action = body["action"] as? String
        if action == "ready", body.count == 2 {
            Self.audioLog.debug("Widget audio shim ready")
            // The user can enable audio before the child finishes loading.
            sendAudioControl(enabled: output != nil)
            return
        }
        if action == "status", body.count == 3, body["code"] as? String == "unsupported_audio" {
            Self.audioLog.notice("Widget requested an unsupported audio operation")
            onUnsupportedAudio?()
            return
        }

        guard let output, let clipNumber = Self.number(body["clip"]),
              let clip = UInt32(exactly: clipNumber), clip > 0 else { return }
        switch action {
        case "play":
            guard body.count == 5, clip > lastClip,
                  let pcm = body["pcm"] as? String, !pcm.isEmpty, pcm.utf8.count <= 192_000,
                  let delay = Self.number(body["delay"]), (0...2).contains(delay) else { return }
            lastClip = clip
            if !receivedAudio {
                receivedAudio = true
                Self.audioLog.notice("First widget audio clip reached the player")
            }
            output.play(clip: clip, pcm: pcm, delay: delay)
        case "stop":
            guard body.count == 3, clip <= lastClip else { return }
            output.stop(clip: clip)
        default:
            break
        }
    }

    private static func number(_ value: Any?) -> Double? {
        guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(),
              number.doubleValue.isFinite else { return nil }
        return number.doubleValue
    }

    private static func audioRelay(session: String) -> String {
        """
        (() => {
          let lastRefill = performance.now();
          let messages = 24;
          let bytes = 384000;

          function withinBudget(length) {
            const now = performance.now();
            const elapsed = Math.max(0, now - lastRefill) / 1000;
            lastRefill = now;
            messages = Math.min(24, messages + elapsed * 48);
            bytes = Math.min(384000, bytes + elapsed * 384000);
            if (messages < 1 || bytes < length) return false;
            messages--;
            bytes -= length;
            return true;
          }

          window.addEventListener("message", event => {
            const frame = document.querySelector("iframe");
            const data = event.data;
            const handler = window.webkit?.messageHandlers?.scoutWidgetAudio;
            if (!handler || !frame || event.source !== frame.contentWindow || event.origin !== "null" ||
                !data || data.channel !== "cfy-widget-audio" || data.session !== "\(session)") return;
            if (data.action === "ready" && withinBudget(0)) {
              handler.postMessage({action: "ready", session: data.session});
              return;
            }
            if (data.action === "status" && data.code === "unsupported_audio" && withinBudget(0)) {
              handler.postMessage({action: "status", session: data.session, code: data.code});
              return;
            }
            if (!Number.isInteger(data.clip) || data.clip <= 0 || data.clip > 0xffffffff) return;
            if (data.action === "play" && typeof data.pcm === "string" && data.pcm.length > 0 &&
                data.pcm.length <= 192000 && data.pcm.length % 4 === 0 &&
                Number.isFinite(data.delay) && data.delay >= 0 && data.delay <= 2 && withinBudget(data.pcm.length)) {
              handler.postMessage({action: "play", session: data.session, clip: data.clip,
                                   pcm: data.pcm, delay: data.delay});
            } else if (data.action === "stop" && withinBudget(0)) {
              handler.postMessage({action: "stop", session: data.session, clip: data.clip});
            }
          });
        })();
        """
    }

    @available(iOS 18.4, macOS 10.12, *)
    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        completionHandler(nil)
    }

    func webView(_ webView: WKWebView, requestMediaCapturePermissionFor origin: WKSecurityOrigin,
                 initiatedByFrame frame: WKFrameInfo, type: WKMediaCaptureType,
                 decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        decisionHandler(.deny)
    }

    @available(iOS 27, macOS 27, *)
    func webView(_ webView: WKWebView, requestGeolocationPermissionFor origin: WKSecurityOrigin,
                 initiatedByFrame frame: WKFrameInfo, decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        decisionHandler(.deny)
    }
}
