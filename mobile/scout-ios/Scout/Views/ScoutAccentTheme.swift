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

    var tint: Color {
        let dark = scheme == .dark
        // Bound the tint against the brightest dark or darkest light canvas.
        let background = dark ? Self.luminance(SIMD3(repeating: 0.27)) : lightCanvasFloor
        let target = contrast == .increased ? 7.0 : 4.5
        let endpoint = SIMD3<Double>(repeating: dark ? 1 : 0)
        for step in 0...20 {
            let candidate = accent + (endpoint - accent) * (Double(step) / 20)
            let foreground = Self.luminance(candidate)
            let ratio = dark ? (foreground + 0.05) / (background + 0.05) : (background + 0.05) / (foreground + 0.05)
            if ratio >= target {
                return Self.color(candidate)
            }
        }
        return Self.color(endpoint)
    }

    var canvas: LinearGradient {
        let dark = scheme == .dark
        let base = dark ? Self.channels(CodexifyDesignTokens.Semantic.panelBg) : SIMD3(repeating: 1)
        let difference = (accent - base) * (contrast == .increased ? 0.5 : 1)
        var bottomStrength = dark ? 0.02 : 0.28
        var bottom = base + difference * bottomStrength
        if !dark {
            // Deep accents can reach the reading canvas's luminance limit sooner.
            let floor = lightCanvasFloor
            while Self.luminance(bottom) < floor {
                bottomStrength -= 0.01
                bottom = base + difference * bottomStrength
            }
        }
        return LinearGradient(
            colors: [
                Self.color(base + difference * (dark ? 0.16 : 0.055)),
                Self.color(bottom)
            ],
            startPoint: .top,
            endPoint: .bottom
        )
    }

    private var lightCanvasFloor: Double {
        Self.luminance(SIMD3(repeating: contrast == .increased ? 0.86 : 0.80))
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
