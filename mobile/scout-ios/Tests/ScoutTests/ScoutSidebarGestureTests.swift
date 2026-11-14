import XCTest
@testable import Scout

final class ScoutSidebarGestureTests: XCTestCase {
    func testOpeningRequiresAnEdgeSwipeInTheCorrectDirection() {
        func opens(_ startX: CGFloat, _ x: CGFloat, _ y: CGFloat, open: Bool = false) -> Bool {
            ScoutSidebarGesture.opens(isOpen: open, startX: startX, horizontal: x, vertical: y,
                                       edgeWidth: 24, minimumDistance: 44)
        }
        XCTAssertTrue(opens(12, 80, 10))
        XCTAssertFalse(opens(25, 80, 10))
        XCTAssertFalse(opens(12, -80, 10))
        XCTAssertFalse(opens(12, 44, 0))
        XCTAssertFalse(opens(12, 80, 70))
        XCTAssertFalse(opens(12, 80, 10, open: true))
    }

    func testDismissalIgnoresShortWrongWayAndVerticalDrags() {
        func dismisses(_ x: CGFloat, _ y: CGFloat) -> Bool {
            ScoutSidebarGesture.dismisses(horizontal: x, vertical: y, minimumDistance: 44)
        }
        XCTAssertTrue(dismisses(-80, 10))
        XCTAssertFalse(dismisses(80, 10))
        XCTAssertFalse(dismisses(-44, 0))
        XCTAssertFalse(dismisses(-80, 70))
    }
}
