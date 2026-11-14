import Foundation

/// Classifies intentional horizontal sidebar swipes without taking over vertical scrolling.
enum ScoutSidebarGesture {
    static func opens(isOpen: Bool, startX: CGFloat, horizontal: CGFloat, vertical: CGFloat,
                      edgeWidth: CGFloat, minimumDistance: CGFloat) -> Bool {
        !isOpen && startX >= 0 && startX <= edgeWidth && horizontal > minimumDistance &&
            abs(vertical) < horizontal * 0.75
    }

    static func dismisses(horizontal: CGFloat, vertical: CGFloat, minimumDistance: CGFloat) -> Bool {
        horizontal < -minimumDistance && abs(vertical) < -horizontal * 0.75
    }
}
