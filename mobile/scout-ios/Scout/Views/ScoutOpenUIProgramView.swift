import SwiftUI

/// A read-only projection of validated message content using native controls.
struct ScoutOpenUIProgramView: View {
    let program: ScoutOpenUIProgram
    @Environment(\.dynamicTypeSize) private var textSize
    @Environment(\.scoutAccentTheme) private var accentTheme

    var body: some View {
        if program.direction == .horizontal && !textSize.isAccessibilitySize {
            ViewThatFits(in: .horizontal) {
                HStack(alignment: .top, spacing: ScoutVisualStyle.gap) {
                    items
                }
                .fixedSize(horizontal: true, vertical: false)

                verticalItems
            }
        } else {
            verticalItems
        }
    }

    private var verticalItems: some View {
        VStack(alignment: .leading, spacing: ScoutVisualStyle.gap) {
            items
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var items: some View {
        ForEach(Array(program.items.enumerated()), id: \.offset) { _, item in
            switch item {
            case let .card(heading, children):
                VStack(alignment: .leading, spacing: ScoutVisualStyle.gap) {
                    if let heading, !heading.isEmpty {
                        Text(heading).font(.headline).accessibilityAddTraits(.isHeader)
                    }
                    ForEach(Array(children.enumerated()), id: \.offset) { _, child in
                        leaf(child)
                    }
                }
                .modifier(ScoutPanel(secondary: true))
            case let .leaf(node):
                leaf(node)
            }
        }
    }

    @ViewBuilder
    private func leaf(_ node: ScoutOpenUIProgram.Leaf) -> some View {
        switch node {
        case let .text(text, size, emphasis):
            Text(text)
                .font(textFont(size))
                .fontWeight(emphasis == .strong ? .semibold : .regular)
                .foregroundStyle(emphasis == .muted ? Color.secondary : Color.primary)
        case let .heading(text, level):
            Text(text)
                .font(level == .h2 ? .title3.weight(.semibold) : level == .h3 ? .headline : .subheadline.weight(.semibold))
                .accessibilityAddTraits(.isHeader)
        case let .badge(text, tone):
            Text(text)
                .font(.caption.weight(.semibold))
                .padding(.horizontal, ScoutVisualStyle.inset / 2)
                .padding(.vertical, ScoutVisualStyle.inset / 3)
                .background(badgeTint(tone).opacity(0.17), in: Capsule())
        case let .metric(label, value, detail):
            VStack(alignment: .leading, spacing: ScoutVisualStyle.gap / 2) {
                Text(label).font(.subheadline).foregroundStyle(.secondary)
                Text(value).font(.title2.weight(.semibold))
                if let detail, !detail.isEmpty {
                    Text(detail).font(.caption).foregroundStyle(.secondary)
                }
            }
            .modifier(ScoutPanel(secondary: true))
            .accessibilityElement(children: .combine)
        case let .progress(label, value, max, status):
            VStack(alignment: .leading, spacing: ScoutVisualStyle.gap / 2) {
                ProgressView(value: value / max) {
                    Text(label)
                }
                .tint(accentTheme.tint)
                if let status, !status.isEmpty {
                    Text(status).font(.caption).foregroundStyle(.secondary)
                }
            }
        case let .list(entries, ordered):
            VStack(alignment: .leading, spacing: ScoutVisualStyle.gap / 2) {
                ForEach(Array(entries.enumerated()), id: \.offset) { index, entry in
                    HStack(alignment: .firstTextBaseline, spacing: ScoutVisualStyle.gap / 2) {
                        if ordered {
                            Text("\(index + 1).")
                        } else {
                            Text("•").accessibilityHidden(true)
                        }
                        Text(entry)
                    }
                    .accessibilityElement(children: .combine)
                }
            }
        }
    }

    private func textFont(_ size: ScoutOpenUIProgram.TextSize) -> Font {
        switch size {
        case .sm: .subheadline
        case .md: .body
        case .lg: .title3
        }
    }

    private func badgeTint(_ tone: ScoutOpenUIProgram.Tone) -> Color {
        switch tone {
        case .neutral: .secondary
        case .info: accentTheme.tint
        case .success: .green
        case .warning: .orange
        case .danger: .red
        }
    }
}
