import SwiftUI
import UIKit

/// The local System Accent drives interaction tint and the default canvas.
struct ScoutAccentTheme {
    static let defaultRGB = packed(channels(CodexifyDesignTokens.Semantic.accent))

    let rgb: Int
    let scheme: ColorScheme
    let contrast: ColorSchemeContrast

    private var accent: SIMD3<Double> {
        let value = (0...0xFFFFFF).contains(rgb) ? rgb : Self.defaultRGB
        return SIMD3(
            Double((value >> 16) & 255),
            Double((value >> 8) & 255),
            Double(value & 255)
        ) / 255
    }

    var sourceColor: Color { Self.color(accent) }

    var tint: Color { Self.color(tintChannels) }

    /// Pick a legible label for an accent-filled control, including custom accents.
    var textOnTint: Color {
        Self.luminance(tintChannels) > 0.179 ? .black : .white
    }

    private var tintChannels: SIMD3<Double> {
        let dark = scheme == .dark
        // Include the colored edge when selecting a tint for canvas controls.
        let background = dark
            ? max(Self.luminance(SIMD3(repeating: 0.27)), Self.luminance(canvasEdge))
            : lightCanvasFloor
        let target = contrast == .increased ? 7.0 : 4.5
        let endpoint = SIMD3<Double>(repeating: dark ? 1 : 0)
        for step in 0...20 {
            let candidate = accent + (endpoint - accent) * (Double(step) / 20)
            let foreground = Self.luminance(candidate)
            let ratio = dark ? (foreground + 0.05) / (background + 0.05) : (background + 0.05) / (foreground + 0.05)
            if ratio >= target {
                return candidate
            }
        }
        return endpoint
    }

    var canvas: LinearGradient {
        let base = canvasBase
        let edge = canvasEdge
        return LinearGradient(
            stops: [
                .init(color: Self.color(edge), location: 0),
                .init(color: Self.color(base + (edge - base) * 0.21), location: 0.19),
                .init(color: Self.color(base), location: 0.35),
                .init(color: Self.color(base), location: 1)
            ],
            startPoint: scheme == .dark ? .top : .bottom,
            endPoint: scheme == .dark ? .bottom : .top
        )
    }

    private var canvasBase: SIMD3<Double> {
        scheme == .dark ? Self.channels(CodexifyDesignTokens.Semantic.panelBg) : SIMD3(repeating: 1)
    }

    private var canvasEdge: SIMD3<Double> {
        let base = canvasBase
        let dark = scheme == .dark
        let ceiling = contrast == .increased ? 0.10 : 0.14
        var strength = dark
            ? (contrast == .increased ? 0.26 : 0.52)
            : (contrast == .increased ? 0.40 : 0.68)
        while strength > 0 {
            let candidate = base + (accent - base) * strength
            let luminance = Self.luminance(candidate)
            if dark ? luminance <= ceiling : luminance >= lightCanvasFloor {
                return candidate
            }
            strength = max(0, strength - 0.01)
        }
        return base
    }

    private var lightCanvasFloor: Double {
        // Leave room for a visible accent while keeping the light edge bright
        // enough for dark text and adapting the tint against this same floor.
        Self.luminance(SIMD3(repeating: contrast == .increased ? 0.70 : 0.60))
    }

    static func packed(_ color: Color) -> Int? {
        guard let space = CGColorSpace(name: CGColorSpace.sRGB),
              let components = UIColor(color).cgColor.converted(
            to: space, intent: .relativeColorimetric, options: nil
        )?.components, components.count >= 3, components.prefix(3).allSatisfy(\.isFinite) else { return nil }
        return packed(SIMD3(Double(components[0]), Double(components[1]), Double(components[2])))
    }

    private static func packed(_ rgb: SIMD3<Double>) -> Int {
        func byte(_ channel: Double) -> Int { Int((min(1, max(0, channel)) * 255).rounded()) }
        return (byte(rgb.x) << 16) | (byte(rgb.y) << 8) | byte(rgb.z)
    }

    private static func channels(_ token: CodexifyDesignTokens.SRGBColor) -> SIMD3<Double> {
        SIMD3(token.red, token.green, token.blue) / 255
    }

    private static func color(_ rgb: SIMD3<Double>) -> Color {
        Color(.sRGB, red: rgb.x, green: rgb.y, blue: rgb.z)
    }

    private static func luminance(_ rgb: SIMD3<Double>) -> Double {
        func linear(_ channel: Double) -> Double {
            channel <= 0.04045 ? channel / 12.92 : pow((channel + 0.055) / 1.055, 2.4)
        }
        return 0.2126 * linear(rgb.x) + 0.7152 * linear(rgb.y) + 0.0722 * linear(rgb.z)
    }
}

private struct ScoutSystemAccentKey: EnvironmentKey {
    static let defaultValue = ScoutAccentTheme.defaultRGB
}

extension EnvironmentValues {
    var scoutSystemAccent: Int {
        get { self[ScoutSystemAccentKey.self] }
        set { self[ScoutSystemAccentKey.self] = newValue }
    }

    var scoutAccentTheme: ScoutAccentTheme {
        ScoutAccentTheme(rgb: scoutSystemAccent, scheme: colorScheme, contrast: colorSchemeContrast)
    }
}
