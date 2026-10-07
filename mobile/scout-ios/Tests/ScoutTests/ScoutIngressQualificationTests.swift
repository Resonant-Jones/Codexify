import XCTest
@testable import Scout

final class ScoutIngressQualificationTests: XCTestCase {
    private func response(_ status: Int, _ headers: [String: String] = [:]) -> HTTPURLResponse {
        HTTPURLResponse(url: URL(string: "https://preview.codexify.space/api/chat/threads")!,
                        statusCode: status, httpVersion: nil, headerFields: headers)!
    }

    func testGuardianAccountMarkerTakesPrecedenceOverEdgeChallenge() {
        let r = response(401, ["X-Guardian-Auth-Failure": "ACCOUNT_SESSION_INVALID",
                               "WWW-Authenticate": "Bearer resource_metadata=\"https://preview.codexify.space/.well-known/resource\""])
        XCTAssertEqual(ScoutIngressQualification(response: r), .guardianAccountRequired)
        XCTAssertTrue(ScoutIngressQualification(response: r).message(response: r).contains("handoff is still required"))
    }

    func testEdgeChallengeDoesNotProveGuardianAdmission() {
        XCTAssertEqual(ScoutIngressQualification(response: response(401,
            ["WWW-Authenticate": "Bearer resource_metadata=\"https://preview.codexify.space/.well-known/resource\""])), .accessRequired)
    }

    func testStatusAloneNeverProvesAccountOrIngressAuthentication() {
        for status in [200, 401, 403, 530] {
            XCTAssertEqual(ScoutIngressQualification(response: response(status)), .unqualified)
        }
        XCTAssertEqual(ScoutIngressQualification(response: response(200,
            ["X-Guardian-Auth-Failure": "ACCOUNT_SESSION_INVALID"])), .unqualified)
        XCTAssertEqual(ScoutIngressQualification(response: response(401,
            ["X-Guardian-Auth-Failure": "unexpected"])), .unqualified)
    }

    func testDiagnosticNeverDisplaysUnboundedOrNonRayHeaderMaterial() {
        let r = response(530, ["CF-Ray": "not a ray / sensitive material"])
        XCTAssertFalse(ScoutIngressQualification(response: r).message(response: r).contains("sensitive material"))
        let safe = response(401, ["CF-Ray": "a444d1ff8b67de30-MIA"])
        XCTAssertTrue(ScoutIngressQualification(response: safe).message(response: safe).contains("a444d1ff8b67de30-MIA"))
    }
}
