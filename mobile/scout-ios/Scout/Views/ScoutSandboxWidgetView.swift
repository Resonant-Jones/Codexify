import AVFoundation
import SwiftUI
import UIKit
import WebKit

struct ScoutSandboxWidgetView: View {
    let widget: ScoutSandboxWidget
    let isActive: Bool

    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.scoutSystemAccent) private var systemAccent
    @StateObject private var playback = ScoutWidgetPlayback()
    @State private var focusPresentation = ScoutWidgetFocusPresentation()
    @State private var focusOwnsWebView = false

    private var title: String {
        widget.title.isEmpty ? String(localized: "Interactive widget") : widget.title
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ScoutVisualStyle.gap) {
            ViewThatFits(in: .horizontal) {
                HStack {
                    Text(title).font(.subheadline.weight(.semibold)).lineLimit(2)
                    Spacer(minLength: 0)
                    widgetActions
                }
                VStack(alignment: .leading, spacing: 0) {
                    Text(title).font(.subheadline.weight(.semibold))
                    HStack { widgetActions }
                }
            }
            ScoutWidgetAudioNotice(notice: playback.audioNotice)
            Group {
                if focusOwnsWebView {
                    Color(uiColor: .secondarySystemBackground)
                        .accessibilityHidden(true)
                } else {
                    ScoutWidgetContent(playback: playback, showLoading: isActive)
                }
            }
            .frame(height: CGFloat(widget.inlineHeight))
            .clipShape(RoundedRectangle(cornerRadius: ScoutVisualStyle.radius / 2))
        }
        .modifier(ScoutPanel(secondary: true, verticalInset: ScoutVisualStyle.inset / 2))
        .background(ScoutWidgetPresentationAnchor(presentation: focusPresentation))
        .task(id: isActive ? widget : nil) {
            if isActive { await playback.load(widget) }
        }
        .onDisappear {
            if !focusOwnsWebView { playback.close() }
        }
        .onChange(of: isActive) { _, active in
            if !active {
                focusPresentation.dismiss()
                playback.close()
            }
        }
        .onChange(of: widget) { _, _ in focusPresentation.dismiss() }
        .onChange(of: scenePhase) { _, phase in
            if phase != .active { playback.mute() }
        }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.interruptionNotification)) { notification in
            if notification.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt == AVAudioSession.InterruptionType.began.rawValue {
                playback.mute()
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.routeChangeNotification)) { notification in
            if notification.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt == AVAudioSession.RouteChangeReason.oldDeviceUnavailable.rawValue {
                playback.mute()
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.mediaServicesWereResetNotification)) { _ in
            playback.mute()
        }
    }

    @ViewBuilder
    private var widgetActions: some View {
        ScoutWidgetSoundButton(playback: playback)
            .buttonStyle(.borderless)
            .frame(minHeight: ScoutVisualStyle.controlMinimum)
        Button {
            expandWidget()
        } label: {
            Label("Expand Widget", systemImage: "arrow.up.left.and.arrow.down.right")
                .labelStyle(.iconOnly)
                .frame(width: ScoutVisualStyle.controlMinimum, height: ScoutVisualStyle.controlMinimum)
        }
        .buttonStyle(.borderless)
        .disabled(playback.session == nil || playback.failed)
    }

    private func expandWidget() {
        guard playback.session != nil, !playback.failed else { return }
        let ownership = $focusOwnsWebView
        focusPresentation.present(
            title: title, widget: widget, playback: playback, systemAccent: systemAccent
        ) { focused in
            ownership.wrappedValue = focused
        }
    }
}

private struct ScoutFocusedWidget: View {
    let title: String
    let widget: ScoutSandboxWidget
    @ObservedObject var playback: ScoutWidgetPlayback
    let isFloating: Bool
    let done: () -> Void

    @Environment(\.scoutAccentTheme) private var accentTheme
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var wantsFill = false
    @State private var phoneFitViewport: CGSize?

    var body: some View {
        instrument
            .tint(accentTheme.tint)
            .accessibilityAddTraits(.isModal)
            .accessibilityAction(.escape, done)
    }

    private var instrument: some View {
        GeometryReader { safe in
            let landscape = safe.size.width > safe.size.height
            let filling = landscape && wantsFill
            let framedFill = !isFloating && filling
            let gutter = isFloating && landscape && !filling ? ScoutVisualStyle.inset * 2 : 0

            GeometryReader { window in
                let viewport = filling ? window.size : safe.size
                let panelWidth = max(0, viewport.width - 2 * gutter)
                let panelHeight = max(0, viewport.height - 2 * gutter)
                let fittedCard = isFloating && !filling
                let fitHeight = min(CGFloat(widget.inlineHeight), max(0, panelHeight - 3 * ScoutVisualStyle.controlMinimum))
                let shape = RoundedRectangle(cornerRadius: fittedCard ? ScoutVisualStyle.radius : 0, style: .continuous)

                ZStack {
                    Color.black.opacity(fittedCard ? 0.35 : 0)
                        .accessibilityHidden(true)
                    VStack(spacing: 0) {
                        if !filling {
                            header(canFill: landscape)
                                .layoutPriority(1)
                        }
                        ScoutWidgetAudioNotice(notice: playback.audioNotice)
                        GeometryReader { content in
                            let scale = landscape ? landscapeScale(for: content.size) : 1
                            if !isFloating && !landscape {
                                ContentUnavailableView("Turn iPhone Sideways", systemImage: "iphone.landscape",
                                    description: Text("Rotate to play in landscape, or tap Done to play in chat."))
                                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                            } else {
                                ScoutWidgetContent(
                                    playback: playback,
                                    scale: scale,
                                    fixedViewport: framedFill ? phoneFitViewport : nil,
                                    framedFill: framedFill
                                )
                            }
                        }
                        .onGeometryChange(for: CGSize.self, of: { $0.size }) { size in
                            guard !isFloating, landscape, !filling, size.width > 0, size.height > 0 else { return }
                            let scale = landscapeScale(for: size)
                            phoneFitViewport = CGSize(width: size.width / scale, height: size.height / scale)
                        }
                        .frame(height: isFloating && !landscape ? fitHeight : nil)
                    }
                    .frame(width: panelWidth)
                    .frame(height: isFloating && !landscape ? nil : panelHeight)
                    .background(Color(uiColor: .systemBackground), in: shape)
                    .clipShape(shape)
                    .overlay { shape.strokeBorder(Color(uiColor: .separator), lineWidth: fittedCard ? 1 : 0).allowsHitTesting(false) }
                    .overlay(alignment: .top) {
                        if filling {
                            HStack {
                                doneButton
                                Spacer(minLength: 0)
                                actions(canFill: true, filling: true)
                            }
                            .padding(safe.safeAreaInsets)
                            .modifier(ScoutWidgetHeaderStyle())
                        }
                    }
                    .shadow(color: .black.opacity(fittedCard ? 0.25 : 0), radius: ScoutVisualStyle.inset)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .padding(filling ? EdgeInsets() : safe.safeAreaInsets)
                }
                .animation(reduceMotion ? nil : .easeInOut(duration: 0.22), value: filling)
            }
            .ignoresSafeArea(.container)
        }
    }

    private func landscapeScale(for size: CGSize) -> CGFloat {
        max(1, min(2.5, size.width / 320, size.height / CGFloat(widget.inlineHeight)))
    }

    private func header(canFill: Bool) -> some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: ScoutVisualStyle.gap) {
                doneButton
                headerTitle
                actions(canFill: canFill, filling: false)
            }
            VStack(spacing: ScoutVisualStyle.gap) {
                HStack(spacing: ScoutVisualStyle.gap) {
                    doneButton
                    Spacer(minLength: 0)
                    actions(canFill: canFill, filling: false)
                }
                headerTitle
            }
        }
        .modifier(ScoutWidgetHeaderStyle())
    }

    private var doneButton: some View {
        Button("Done", action: done).keyboardShortcut(.escape, modifiers: [])
    }

    private var headerTitle: some View {
        Text(title)
            .font(.headline)
            .lineLimit(1)
            .frame(maxWidth: .infinity, minHeight: ScoutVisualStyle.controlMinimum)
            .allowsHitTesting(false)
            .accessibilityAddTraits(.isHeader)
    }

    private func actions(canFill: Bool, filling: Bool) -> some View {
        HStack(spacing: ScoutVisualStyle.gap) {
            ScoutWidgetSoundButton(playback: playback)
            if canFill {
                Button {
                    wantsFill.toggle()
                } label: {
                    Label(filling ? "Fit Widget" : "Fill Screen",
                          systemImage: filling ? "arrow.down.right.and.arrow.up.left" : "arrow.up.left.and.arrow.down.right")
                        .labelStyle(.iconOnly)
                }
            }
        }
    }
}

private struct ScoutWidgetHeaderStyle: ViewModifier {
    func body(content: Content) -> some View {
        let header = content
            .padding(.horizontal, ScoutVisualStyle.inset)
            .padding(.vertical, ScoutVisualStyle.inset / 2)
            .controlSize(.large)
        if #available(iOS 26.0, *) {
            header.buttonStyle(.glass)
        } else {
            header.buttonStyle(.bordered).buttonBorderShape(.capsule)
        }
    }
}

private struct ScoutWidgetSoundButton: View {
    @ObservedObject var playback: ScoutWidgetPlayback

    var body: some View {
        if ScoutSandboxWebSession.supportsAudio, playback.session != nil, !playback.failed {
            Button(playback.soundEnabled ? "Mute" : "Enable Sound",
                   systemImage: playback.soundEnabled ? "speaker.wave.2" : "speaker.slash") {
                playback.toggleSound()
            }
            .labelStyle(.titleOnly)
        }
    }
}

private struct ScoutWidgetAudioNotice: View {
    let notice: LocalizedStringKey?

    var body: some View {
        if let notice {
            Text(notice)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity)
                .padding(ScoutVisualStyle.inset / 2)
        }
    }
}

private struct ScoutWidgetContent: View {
    @ObservedObject var playback: ScoutWidgetPlayback
    var showLoading = false
    var zoom: CGFloat = 1
    var scale: CGFloat = 1
    var fixedViewport: CGSize?
    var framedFill = false

    var body: some View {
        if playback.failed {
            ContentUnavailableView("Widget unavailable", systemImage: "exclamationmark.triangle")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if let session = playback.session {
            ScoutSandboxWebView(session: session, zoom: zoom, scale: scale,
                                fixedViewport: fixedViewport, framedFill: framedFill)
        } else if showLoading {
            ProgressView("Opening widget…")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}

private struct ScoutWidgetPresentationAnchor: UIViewRepresentable {
    let presentation: ScoutWidgetFocusPresentation

    func makeCoordinator() -> ScoutWidgetFocusPresentation { presentation }

    func makeUIView(context: Context) -> UIView {
        let anchor = UIView()
        anchor.isUserInteractionEnabled = false
        presentation.anchor = anchor
        return anchor
    }

    func updateUIView(_ uiView: UIView, context: Context) {}

    static func dismantleUIView(_ uiView: UIView, coordinator: ScoutWidgetFocusPresentation) {
        guard coordinator.anchor === uiView else { return }
        coordinator.anchor = nil
    }
}

@MainActor
private final class ScoutWidgetFocusPresentation {
    weak var anchor: UIView?
    private weak var host: ScoutWidgetFocusHost<AnyView>?
    private var onFocusChange: ((Bool) -> Void)?
    private var isPresenting = false
    private var dismissalRequested = false
    private var isDismissing = false

    func present(
        title: String, widget: ScoutSandboxWidget, playback: ScoutWidgetPlayback,
        systemAccent: Int, onFocusChange: @escaping (Bool) -> Void
    ) {
        guard host == nil, let anchor, let window = anchor.window, let scene = window.windowScene,
              let presenter = window.rootViewController, presenter.viewIfLoaded?.window === window,
              presenter.presentedViewController == nil, !presenter.isBeingDismissed else { return }
        let isFloating = window.traitCollection.userInterfaceIdiom != .phone
        let orientation = scene.effectiveGeometry.interfaceOrientation
        let landscape = UIApplication.shared.supportedInterfaceOrientations(for: window).intersection(.landscape)
        // The presented controller keeps this coordinator alive if the list
        // recycles the inline row while the phone rotates.
        let focus = ScoutFocusedWidget(
            title: title, widget: widget, playback: playback, isFloating: isFloating,
            done: { self.dismiss() }
        )
        let controller = ScoutWidgetFocusHost(rootView: AnyView(focus.environment(\.scoutSystemAccent, systemAccent)))
        controller.playback = playback
        controller.landscape = isFloating ? [] : landscape
        controller.previousOrientation = orientation
        controller.modalPresentationStyle = isFloating ? .overFullScreen : .fullScreen
        controller.view.backgroundColor = isFloating ? .clear : .systemBackground
        controller.view.accessibilityViewIsModal = true

        host = controller
        self.onFocusChange = onFocusChange
        isPresenting = true
        onFocusChange(true)
        presenter.present(controller, animated: true) { [self] in
            isPresenting = false
            if dismissalRequested {
                dismiss(animated: false)
            } else if !controller.landscape.isEmpty, !scene.effectiveGeometry.interfaceOrientation.isLandscape {
                controller.setNeedsUpdateOfSupportedInterfaceOrientations()
                scene.requestGeometryUpdate(.iOS(interfaceOrientations: controller.landscape))
            }
        }
    }

    func dismiss(animated: Bool = true) {
        guard let host, !isDismissing else { return }
        if isPresenting {
            dismissalRequested = true
            return
        }
        isDismissing = true
        let presenter = host.presentingViewController
        let scene = host.view.window?.windowScene
        host.dismiss(animated: animated) { [self] in
            if !host.landscape.isEmpty, let scene, let presenter,
               presenter.viewIfLoaded?.window?.windowScene === scene,
               scene.effectiveGeometry.interfaceOrientation != host.previousOrientation,
               let previous = host.previousOrientation.mask {
                presenter.setNeedsUpdateOfSupportedInterfaceOrientations()
                scene.requestGeometryUpdate(.iOS(interfaceOrientations: previous))
            }
            self.host = nil
            if anchor == nil { host.playback?.close() }
            isDismissing = false
            dismissalRequested = false
            let callback = onFocusChange
            onFocusChange = nil
            callback?(false)
        }
    }
}

private final class ScoutWidgetFocusHost<Content: View>: UIHostingController<Content> {
    weak var playback: ScoutWidgetPlayback?
    var landscape: UIInterfaceOrientationMask = []
    var previousOrientation: UIInterfaceOrientation = .unknown

    override var supportedInterfaceOrientations: UIInterfaceOrientationMask {
        landscape.isEmpty ? super.supportedInterfaceOrientations : landscape
    }

    override var preferredInterfaceOrientationForPresentation: UIInterfaceOrientation {
        guard !landscape.isEmpty else { return super.preferredInterfaceOrientationForPresentation }
        if previousOrientation.isLandscape, let mask = previousOrientation.mask, landscape.contains(mask) {
            return previousOrientation
        }
        return landscape.contains(.landscapeRight) ? .landscapeRight : .landscapeLeft
    }
}

private extension UIInterfaceOrientation {
    var mask: UIInterfaceOrientationMask? {
        switch self {
        case .portrait: .portrait
        case .portraitUpsideDown: .portraitUpsideDown
        case .landscapeLeft: .landscapeLeft
        case .landscapeRight: .landscapeRight
        default: nil
        }
    }
}

@MainActor
private final class ScoutWidgetPlayback: ObservableObject {
    @Published private(set) var session: ScoutSandboxWebSession?
    @Published private(set) var failed = false
    @Published private(set) var soundEnabled = false
    @Published private(set) var audioNotice: LocalizedStringKey?

    private var widget: ScoutSandboxWidget?
    private var loadID: UUID?

    func load(_ widget: ScoutSandboxWidget) async {
        if self.widget == widget, session != nil || failed || loadID != nil { return }
        close()
        self.widget = widget
        let id = UUID()
        loadID = id
        defer { if loadID == id { loadID = nil } }

        do {
            let session = try await ScoutSandboxWebSession.make()
            guard !Task.isCancelled, loadID == id else {
                session.close()
                return
            }
            session.onFailure = { [weak self] in self?.failed = true }
            session.onSoundDisabled = { [weak self] in self?.soundEnabled = false }
            session.onAudioFailure = { [weak self] in self?.audioUnavailable() }
            session.onUnsupportedAudio = { [weak self] in
                self?.audioNotice = "This widget uses an audio feature Scout doesn’t support."
            }
            self.session = session
            session.load(widget)
        } catch {
            if !Task.isCancelled, loadID == id { failed = true }
        }
    }

    func toggleSound() {
        guard let session else { return }
        if soundEnabled {
            mute()
        } else {
            do {
                try session.enableSound()
                soundEnabled = true
                audioNotice = nil
            } catch {
                audioUnavailable()
            }
        }
    }

    func mute() {
        session?.disableSound()
        soundEnabled = false
    }

    func close() {
        loadID = nil
        widget = nil
        session?.close()
        session = nil
        failed = false
        soundEnabled = false
        audioNotice = nil
    }

    private func audioUnavailable() {
        soundEnabled = false
        audioNotice = "Couldn’t start audio. Try Enable Sound again."
    }
}

private struct ScoutSandboxWebView: UIViewRepresentable {
    let session: ScoutSandboxWebSession
    let zoom: CGFloat
    let scale: CGFloat
    let fixedViewport: CGSize?
    let framedFill: Bool

    func makeUIView(context: Context) -> Container {
        Container()
    }

    func updateUIView(_ container: Container, context: Context) {
        let webView = session.webView
        session.setFramedFill(framedFill)
        if webView.superview !== container.content {
            webView.frame = container.content.bounds
            webView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
            container.content.addSubview(webView)
        }
        if webView.pageZoom != zoom { webView.pageZoom = zoom }
        webView.scrollView.contentInsetAdjustmentBehavior = fixedViewport == nil ? .automatic : .never
        container.widgetScale = scale
        container.fixedViewport = fixedViewport
        container.setNeedsLayout()
    }

    static func dismantleUIView(_ container: Container, coordinator: ()) {
        // The other presentation may already own the view.
        container.content.subviews.forEach { $0.removeFromSuperview() }
    }

    final class Container: UIView {
        let content = UIView()
        var widgetScale: CGFloat = 1
        var fixedViewport: CGSize?

        init() {
            super.init(frame: .zero)
            clipsToBounds = true
            addSubview(content)
        }

        @available(*, unavailable)
        required init?(coder: NSCoder) { fatalError() }

        override func layoutSubviews() {
            super.layoutSubviews()
            guard bounds.width > 0, bounds.height > 0 else { return }

            let size: CGSize
            let scale: CGFloat
            if let fixedViewport {
                // Keep the Fit viewport so scaling does not reflow the widget.
                scale = min(bounds.width / fixedViewport.width, bounds.height / fixedViewport.height)
                // Give the web page the full available height at this scale.
                // Its content can then center inside a taller viewport.
                size = CGSize(width: fixedViewport.width, height: bounds.height / scale)
            } else {
                size = CGSize(width: bounds.width / widgetScale, height: bounds.height / widgetScale)
                scale = widgetScale
            }
            content.bounds.size = size
            content.center = CGPoint(x: bounds.midX, y: bounds.midY)
            content.transform = CGAffineTransform(scaleX: scale, y: scale)
        }
    }
}
