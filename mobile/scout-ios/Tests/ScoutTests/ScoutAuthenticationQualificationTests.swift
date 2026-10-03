import Foundation
import XCTest
@testable import Scout

final class ScoutAuthenticationQualificationTests: XCTestCase {
    private func profile() -> ScoutEndpointProfile {
        ScoutEndpointProfile(id: UUID(), name: "Qualification fixture", baseURL: "https://preview.codexify.space", transportType: .custom,
            authenticationState: .unconfigured, validationState: .unconfigured, lastConnectedAt: nil, authenticationMode: .remoteSession)
    }

    func testServerRedirectPreparationDoesNotClaimNativeCallbackReceipt() throws {
        var receipt = try ScoutAuthenticationQualification(profile: profile())
        receipt.record(.ingress, .passed, .confirmed)
        receipt.record(.browser, .passed, .confirmed)
        let data = Data("{\"attempt_id\":\"\(receipt.publicID)\",\"stages\":{\"account_login\":{\"status\":\"passed\",\"http_status\":200},\"handoff_redirect\":{\"status\":\"passed\",\"http_status\":200}}}".utf8)
        receipt.merge(try JSONDecoder().decode(ScoutAuthenticationQualification.BackendReceipt.self, from: data))
        XCTAssertEqual(receipt.result(for: .accountLogin).status, .passed)
        XCTAssertEqual(receipt.result(for: .callback).status, .waiting)
        XCTAssertEqual(receipt.firstUnqualifiedStage, .callback)
    }

    func testFailedBrowserLoginHasExactStageAndOnlySafeClassification() throws {
        var receipt = try ScoutAuthenticationQualification(profile: profile())
        receipt.record(.ingress, .passed, .confirmed)
        receipt.record(.browser, .passed, .confirmed)
        let data = Data("{\"attempt_id\":\"\(receipt.publicID)\",\"stages\":{\"account_login\":{\"status\":\"failed\",\"http_status\":401,\"detail\":\"fixture-secret-cookie\"},\"fixture-secret-stage\":{\"status\":\"passed\"}}}".utf8)
        receipt.merge(try JSONDecoder().decode(ScoutAuthenticationQualification.BackendReceipt.self, from: data))
        XCTAssertEqual(receipt.firstUnqualifiedStage, .accountLogin)
        XCTAssertEqual(receipt.result(for: .accountLogin).summary, "Failed · rejected · HTTP 401")
        XCTAssertFalse(String(describing: receipt).contains("fixture-secret"))
    }

    func testAnotherAttemptsBackendEvidenceCannotQualifyCurrentConnection() throws {
        var receipt = try ScoutAuthenticationQualification(profile: profile())
        let data = Data("{\"attempt_id\":\"\(UUID().uuidString.lowercased())\",\"stages\":{\"account_login\":{\"status\":\"passed\"}}}".utf8)
        receipt.merge(try JSONDecoder().decode(ScoutAuthenticationQualification.BackendReceipt.self, from: data))
        XCTAssertEqual(receipt.result(for: .accountLogin).status, .waiting)
        XCTAssertFalse(receipt.correlationAvailable)
    }

    func testSafeReceiptNeverContainsOAuthStateCodeVerifierOrSessionMaterial() throws {
        let profile = profile()
        let receipt = try ScoutAuthenticationQualification(profile: profile)
        var handoff = ScoutAccountHandoffAttempt(verifier: String(repeating: "v", count: 43), state: String(repeating: "s", count: 43), qualificationID: receipt.attemptID)
        let params = URLComponents(url: handoff.browserURL, resolvingAgainstBaseURL: false)!.queryItems!
        XCTAssertEqual(params.first(where: { $0.name == "scout_attempt" })?.value, receipt.publicID)
        let ingress = ScoutAccessOAuth.Credential(accessToken: "oauth:fixture-private-ingress", refreshToken: nil, expiresAt: .distantFuture)
        let callback = URL(string: ScoutAccessOAuth.callback.absoluteString + "?code=" + String(repeating: "c", count: 43) + "&state=" + String(repeating: "s", count: 43))!
        let request = try handoff.exchangeRequest(callback: callback, ingress: ingress)
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-Scout-Auth-Attempt"), receipt.publicID)
        XCTAssertEqual(try JSONDecoder().decode([String: String].self, from: request.httpBody!).keys.sorted(), ["code", "verifier"])
        let diagnostic = String(describing: receipt)
        for sensitive in [ingress.accessToken, String(repeating: "s", count: 43), String(repeating: "c", count: 43), String(repeating: "v", count: 43)] {
            XCTAssertFalse(diagnostic.contains(sensitive))
        }
        XCTAssertNil(receipt.receiptRequest(ingress: ingress).value(forHTTPHeaderField: "X-Guardian-Account-Session"))
        XCTAssertNil(receipt.receiptRequest(ingress: ingress).httpBody)
    }

    func testObservedFailureIsDistinguishedFromEarlierMissingEvidence() throws {
        var receipt = try ScoutAuthenticationQualification(profile: profile())
        receipt.record(.ingress, .passed, .confirmed)
        receipt.record(.browser, .passed, .confirmed)
        receipt.record(.callback, .passed, .confirmed)
        receipt.record(.state, .failed, .invalidCallback)
        XCTAssertEqual(receipt.firstFailedStage, .state)
        XCTAssertEqual(receipt.firstUnqualifiedStage, .accountLogin)
        receipt.correlationReady()
        receipt.correlationLost()
        XCTAssertFalse(receipt.correlationAvailable)
        XCTAssertEqual(receipt.firstFailedStage, .state)
    }

    func testAllNineStagesMustPassAndCompletedEvidenceCannotBeRetracted() throws {
        var receipt = try ScoutAuthenticationQualification(profile: profile())
        for stage in ScoutAuthenticationQualification.Stage.allCases {
            XCTAssertEqual(receipt.firstUnqualifiedStage, stage)
            receipt.record(stage, .passed, .confirmed)
            receipt.record(stage, .failed, .rejected, httpStatus: 401)
            XCTAssertEqual(receipt.result(for: stage).status, .passed)
        }
        XCTAssertNil(receipt.firstUnqualifiedStage)
    }

    func testUntrustedStatusAndHttpValuesCannotEnterDisplayedReceipt() throws {
        var receipt = try ScoutAuthenticationQualification(profile: profile())
        receipt.record(.exchange, .failed, .rejected, httpStatus: -42)
        XCTAssertNil(receipt.result(for: .exchange).httpStatus)
        let data = Data("{\"attempt_id\":\"\(receipt.publicID)\",\"stages\":{\"account_login\":{\"status\":\"fixture-sensitive-token\"}}}".utf8)
        XCTAssertThrowsError(try JSONDecoder().decode(ScoutAuthenticationQualification.BackendReceipt.self, from: data))
    }
}
