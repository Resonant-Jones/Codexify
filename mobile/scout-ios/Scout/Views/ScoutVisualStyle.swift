import SwiftUI

// Integration notes: the registry owns values; SwiftUI owns semantic typography,
// Dynamic Type, safe areas and system light/high-contrast fallbacks. Web's 20pt
// implemented tile radius differs from older 19px documentation. Web's 4px phone
// perimeter and 6px root baseline are not native safe-area insets. No Material
// attempts to reproduce Web RefractiveGlassCard; native frames use a restrained
// material and accent reflection where appropriate.
enum ScoutVisualStyle {
    static let accent = color(CodexifyDesignTokens.Semantic.accent)
    static let radius = CGFloat(CodexifyDesignTokens.Semantic.tileRadius.logicalUnits)
    static let inset = CGFloat(CodexifyDesignTokens.Components.cardPadding.logicalUnits)
    static let gap = CGFloat(CodexifyDesignTokens.Semantic.shellGap.logicalUnits)
    static let controlMinimum = CGFloat(CodexifyDesignTokens.Components.handheldControlMinimum.logicalUnits)

    static func color(_ token: CodexifyDesignTokens.SRGBColor) -> Color {
        Color(.sRGB, red: token.red / 255, green: token.green / 255, blue: token.blue / 255, opacity: token.alpha)
    }
}

struct ScoutPanel: ViewModifier {
    @Environment(\.colorScheme) private var scheme
    @Environment(\.colorSchemeContrast) private var contrast
    @Environment(\.scoutAccentTheme) private var accentTheme
    var secondary = false
    var selected = false
    var subtleOutline = false
    var verticalInset = ScoutVisualStyle.inset

    func body(content: Content) -> some View {
        let shape = RoundedRectangle(cornerRadius: ScoutVisualStyle.radius, style: .continuous)
        content.padding(.horizontal, ScoutVisualStyle.inset)
            .padding(.vertical, verticalInset)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(scheme == .dark ? ScoutVisualStyle.color(secondary ? CodexifyDesignTokens.Semantic.panelSheet : CodexifyDesignTokens.Semantic.panelBg) : Color(uiColor: .secondarySystemGroupedBackground), in: shape)
            .overlay(shape.strokeBorder(selected ? accentTheme.tint : (contrast == .increased && !subtleOutline ? Color.primary : (scheme == .dark ? ScoutVisualStyle.color(CodexifyDesignTokens.Semantic.panelBorder) : Color(uiColor: .separator)))))
    }
}

struct ScoutCanvas: ViewModifier {
    @Environment(\.colorScheme) private var scheme
    @Environment(\.scoutAccentTheme) private var accentTheme
    func body(content: Content) -> some View {
        content.scrollContentBackground(.hidden)
            .background { accentTheme.canvas.ignoresSafeArea() }
            .toolbarBackground(scheme == .dark ? ScoutVisualStyle.color(CodexifyDesignTokens.Semantic.panelBg) : Color(uiColor: .systemBackground), for: .navigationBar)
    }
}

struct ScoutFloatingSurface<Shape: InsettableShape>: View {
    let shape: Shape
    let fill: Color?
    let focused: Bool

    @Environment(\.colorScheme) private var scheme
    @Environment(\.colorSchemeContrast) private var contrast
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @Environment(\.scoutAccentTheme) private var accentTheme

    init(_ shape: Shape, fill: Color? = nil, focused: Bool = false) {
        self.shape = shape
        self.fill = fill
        self.focused = focused
    }

    var body: some View {
        let border = contrast == .increased ? Color.primary : focused ? accentTheme.tint : Color(uiColor: .separator)
        Group {
            if let fill {
                shape.fill(fill)
            } else if reduceTransparency || contrast == .increased {
                shape.fill(scheme == .dark ? ScoutVisualStyle.color(CodexifyDesignTokens.Semantic.panelSheet) : Color(uiColor: .systemBackground))
            } else {
                shape.fill(.regularMaterial)
            }
        }
        .overlay { shape.strokeBorder(border) }
        .shadow(color: .black.opacity(reduceTransparency ? 0 : 0.14), radius: ScoutVisualStyle.inset / 3, y: 2)
    }
}

/// Token-based native frame for the tablet canvas and the navigation drawer.
struct ScoutFrameSurface: View {
    var showAccentBloom = false
    var subtleOutline = false
    @Environment(\.colorScheme) private var scheme
    @Environment(\.colorSchemeContrast) private var contrast
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @Environment(\.scoutAccentTheme) private var accentTheme

    var body: some View {
        let shape = RoundedRectangle(cornerRadius: ScoutVisualStyle.radius, style: .continuous)
        let frame = CGFloat(CodexifyDesignTokens.Semantic.frame.logicalUnits)
        let face = scheme == .dark
            ? ScoutVisualStyle.color(CodexifyDesignTokens.Semantic.panelBg)
            : Color(uiColor: .systemBackground)
        let bezel = contrast == .increased && !subtleOutline
            ? Color.primary
            : ScoutVisualStyle.color(CodexifyDesignTokens.Semantic.panelBezel)
        ZStack {
            if reduceTransparency || contrast == .increased {
                shape.fill(face)
            } else {
                shape.fill(.regularMaterial)
                    .overlay(shape.fill(face.opacity(0.9)))
                    .overlay {
                        if showAccentBloom {
                            shape.fill(LinearGradient(stops: [
                                .init(color: accentTheme.sourceColor.opacity(scheme == .dark ? 0.10 : 0.07), location: 0),
                                .init(color: .clear, location: 0.35)
                            ],
                                startPoint: scheme == .dark ? .top : .bottom,
                                endPoint: scheme == .dark ? .bottom : .top
                            ))
                        }
                    }
            }
            shape.strokeBorder(bezel, lineWidth: frame)
            shape.inset(by: frame * 2)
                .strokeBorder(bezel.opacity(0.6), lineWidth: frame)
        }
        .shadow(color: .black.opacity(reduceTransparency ? 0 : 0.14), radius: ScoutVisualStyle.inset / 2, y: frame)
    }
}

struct ScoutAdaptiveContentFrame: ViewModifier {
    private static let minimumFrameWidth: CGFloat = 700
    let availableWidth: CGFloat

    @ViewBuilder func body(content: Content) -> some View {
        if UIDevice.current.userInterfaceIdiom == .pad {
            let showsFrame = availableWidth >= Self.minimumFrameWidth
            // Only the decoration branches so resizing keeps the conversation mounted.
            content
                .padding(showsFrame ? ScoutVisualStyle.inset : 0)
                .background {
                    if showsFrame {
                        ScoutFrameSurface(showAccentBloom: true)
                    }
                }
                .clipShape(RoundedRectangle(cornerRadius: showsFrame ? ScoutVisualStyle.radius : 0, style: .continuous))
                .padding(showsFrame ? ScoutVisualStyle.inset / 2 : 0)
        } else {
            content
        }
    }
}

struct ScoutActionStyle: ButtonStyle {
    @Environment(\.isEnabled) private var enabled
    @Environment(\.colorScheme) private var scheme
    var primary = false
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(.headline)
            .foregroundStyle(enabled ? Color.primary : Color.secondary)
            .frame(minHeight: ScoutVisualStyle.controlMinimum)
            .modifier(ScoutPanel(secondary: primary, selected: enabled && (primary || configuration.isPressed)))
            .contentShape(RoundedRectangle(cornerRadius: ScoutVisualStyle.radius))
    }
}

struct GuardianThreadRow: View {
    let thread: ScoutChatThreadSummary
    var compact = false
    var selected = false

    var body: some View {
        VStack(alignment: .leading, spacing: compact ? ScoutVisualStyle.inset / 3 : ScoutVisualStyle.inset) {
            Text(thread.title.flatMap { $0.isEmpty ? nil : $0 } ?? "Untitled")
                .font(compact ? .subheadline.weight(.semibold) : .headline)
                .foregroundStyle(.primary)
                .lineLimit(compact ? 1 : nil)
                .truncationMode(.tail)
                .fixedSize(horizontal: false, vertical: true)
            if !compact, let summary = thread.summary, !summary.isEmpty {
                Text(summary).font(.subheadline).foregroundStyle(.secondary)
            }
            if let updated = thread.updated_at {
                timestamp(updated)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(minHeight: compact ? ScoutVisualStyle.controlMinimum - ScoutVisualStyle.inset * 4 / 3 : nil,
               alignment: .leading)
        .modifier(ScoutPanel(selected: selected, subtleOutline: true, verticalInset: compact ? ScoutVisualStyle.inset * 2 / 3 : ScoutVisualStyle.inset))
        .contentShape(RoundedRectangle(cornerRadius: ScoutVisualStyle.radius))
        .accessibilityElement(children: .combine)
    }

    private func timestamp(_ raw: String) -> Text {
        let date = (try? Date.ISO8601FormatStyle(includingFractionalSeconds: true).parse(raw))
            ?? (try? Date.ISO8601FormatStyle().parse(raw))
        if let date {
            return Text(date, format: Calendar.current.isDateInToday(date)
                        ? .dateTime.hour().minute() : .dateTime.month(.abbreviated).day())
        }
        return Text(verbatim: raw)
    }
}

struct GuardianMessageRow: View {
    let message: ScoutChatMessageSummary
    @Environment(\.horizontalSizeClass) private var widthClass
    @Environment(\.dynamicTypeSize) private var textSize

    var body: some View {
        Group {
            if message.role == "user" {
                let widthFraction: CGFloat = widthClass == .regular && !textSize.isAccessibilitySize ? 2.0 / 3.0 : 0.85
                ScoutRequestWidthLimit(fraction: widthFraction) {
                    content.modifier(ScoutRaisedRequestMaterial())
                }
                .frame(maxWidth: .infinity, alignment: .trailing)
            } else if message.role == "assistant" {
                content.frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, ScoutVisualStyle.inset)
            } else {
                content.modifier(ScoutPanel())
            }
        }
        .accessibilityElement(children: .contain)
    }

    private var content: some View {
        VStack(alignment: .leading, spacing: ScoutVisualStyle.inset) {
            ViewThatFits(in: .horizontal) {
                HStack(spacing: ScoutVisualStyle.gap) {
                    role
                    timestamp
                }
                VStack(alignment: .leading, spacing: 2) {
                    role
                    timestamp
                }
            }
            if let content = message.content, !content.isEmpty {
                ScoutTranscriptView(source: content, markdown: message.role == "assistant")
            }
        }
    }

    private var role: some View {
        Text(message.role == "user" ? "You" : message.role == "assistant" ? "Guardian" : message.role?.capitalized ?? "Unknown")
            .font(.headline).foregroundStyle(.primary)
    }

    private var timestamp: some View {
        Group {
            if let created = message.created_at {
                let date = (try? Date.ISO8601FormatStyle(includingFractionalSeconds: true).parse(created))
                    ?? (try? Date.ISO8601FormatStyle().parse(created))
                if let date {
                    Text(date, format: Calendar.current.isDateInToday(date)
                         ? .dateTime.hour().minute() : .dateTime.month(.abbreviated).day().hour().minute())
                        .accessibilityLabel(Text(date, format: .dateTime.year().month().day().hour().minute()))
                } else {
                    Text(verbatim: created)
                }
            }
        }
        .font(.caption2)
        .foregroundStyle(.secondary)
    }
}

/// Let short requests size to their text, with room reserved on the leading side.
private struct ScoutRequestWidthLimit: Layout {
    let fraction: CGFloat

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        subviews[0].sizeThatFits(capped(proposal))
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        subviews[0].place(at: bounds.origin, anchor: .topLeading, proposal: capped(proposal))
    }

    private func capped(_ proposal: ProposedViewSize) -> ProposedViewSize {
        ProposedViewSize(width: proposal.width.map { $0 * fraction }, height: proposal.height)
    }
}

struct GuardianStatusRow: View {
    let title: String
    let detail: String
    var loading = false
    var error = false
    var body: some View {
        VStack(alignment: .leading, spacing: ScoutVisualStyle.inset) {
            HStack {
                if loading { ProgressView().accessibilityLabel("Loading") }
                if error { Image(systemName: "exclamationmark.triangle").accessibilityHidden(true) }
                Text(title).font(.headline)
            }
            if !detail.isEmpty { Text(detail).font(.subheadline).foregroundStyle(.secondary) }
        }
        .modifier(ScoutPanel())
        .accessibilityElement(children: .combine)
    }
}

// Native translation of FrameCard/PreviewTile with a shallower chat bezel.
private struct ScoutRaisedRequestMaterial: ViewModifier {
    @Environment(\.colorScheme) private var scheme
    @Environment(\.colorSchemeContrast) private var contrast
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency

    func body(content: Content) -> some View {
        let bezel = CGFloat(CodexifyDesignTokens.Semantic.bezel.logicalUnits) / 2
        let frame = CGFloat(CodexifyDesignTokens.Semantic.frame.logicalUnits)
        let stroke = contrast == .increased ? frame : frame / 2
        let zero = CGFloat(CodexifyDesignTokens.Primitives.zero.logicalUnits)
        let outer = RoundedRectangle(cornerRadius: ScoutVisualStyle.radius, style: .continuous)
        let rimInset = max(zero, bezel - stroke)
        let rim = RoundedRectangle(cornerRadius: ScoutVisualStyle.radius - rimInset, style: .continuous)
        let face = RoundedRectangle(cornerRadius: ScoutVisualStyle.radius - bezel, style: .continuous)
        let base = scheme == .dark ? ScoutVisualStyle.color(CodexifyDesignTokens.Semantic.panelBg) : Color(uiColor: .systemGray4)
        let top = scheme == .dark ? ScoutVisualStyle.color(CodexifyDesignTokens.Semantic.chipBg) : Color(uiColor: .systemGray6)
        let paper = scheme == .dark ? ScoutVisualStyle.color(CodexifyDesignTokens.Semantic.panelSheet) : Color(uiColor: .systemBackground)
        let highlight = scheme == .dark ? ScoutVisualStyle.color(CodexifyDesignTokens.Semantic.panelBezel) : Color(uiColor: .systemBackground)

        content.padding(ScoutVisualStyle.inset)
            .background {
                // An opaque face in both accessibility modes. Reduce Transparency
                // additionally removes face illumination; rim geometry is retained.
                face.fill(paper)
                    .overlay {
                        if !reduceTransparency {
                            face.fill(LinearGradient(colors: [highlight, .clear], startPoint: .topLeading, endPoint: .bottomTrailing))
                        }
                    }
                    .overlay(face.strokeBorder(contrast == .increased ? Color.primary : base, lineWidth: stroke))
            }
            .padding(bezel)
            .background {
                ZStack {
                    outer.fill(LinearGradient(colors: [top, base], startPoint: .topLeading, endPoint: .bottomTrailing))
                    rim.fill(LinearGradient(colors: [base, top], startPoint: .top, endPoint: .bottom))
                        .padding(rimInset)
                }
                .clipShape(outer)
                .overlay(outer.strokeBorder(LinearGradient(colors: [highlight, .clear, base], startPoint: .topLeading, endPoint: .bottomTrailing), lineWidth: stroke))
                .shadow(color: ScoutVisualStyle.color(CodexifyDesignTokens.Semantic.panelBg).opacity(CodexifyDesignTokens.Semantic.panelBezel.alpha), radius: frame, x: zero, y: frame)
            }
        // Static geometry and lighting: Reduce Motion needs no alternate path.
        // Decorative shapes live in backgrounds, outside VoiceOver reading order.
    }
}
