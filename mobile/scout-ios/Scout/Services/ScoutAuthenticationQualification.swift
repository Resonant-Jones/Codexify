import Foundation

/// Non-secret, connection-scoped evidence. Never a credential or authority.
struct ScoutAuthenticationQualification: Equatable {
    enum Stage: String, CaseIterable, Identifiable {
        case ingress, browser, accountLogin, callback, state, exchange, nativeSession, keychain, protectedRead
        var id: String { rawValue }
        var title: String {
            switch self {
            case .ingress: return "Hosted ingress credential available"
            case .browser: return "Guardian web login launched"
            case .accountLogin: return "Guardian account login confirmed"
            case .callback: return "Handoff callback received"
            case .state: return "Callback state validated"
            case .exchange: return "Handoff exchange accepted"
            case .nativeSession: return "Fresh native account session issued"
            case .keychain: return "Session stored for this profile and origin"
            case .protectedRead: return "Protected Guardian read with account header"
            }
        }
    }
    enum Status: String, Decodable { case waiting, passed, failed }
    enum Classification: String {
        case pending, confirmed, rejected, unavailable, cancelled, invalidCallback, invalidSession, storageFailure, transportFailure, invalidReply
    }
    struct Evidence: Equatable {
        let status: Status
        let classification: Classification
        let httpStatus: Int?
        var summary: String {
            status.rawValue.capitalized + " · " + classification.rawValue + (httpStatus.map { " · HTTP \($0)" } ?? "")
        }
    }
    let attemptID: UUID
    let profileID: UUID
    let origin: String
    private(set) var evidence: [Stage: Evidence] = [:]
    private(set) var correlationAvailable = false

    init(attemptID: UUID = UUID(), profile: ScoutEndpointProfile) throws {
        self.attemptID = attemptID
        profileID = profile.id
        origin = try ScoutAccessOAuth.origin(for: profile)
    }
    var publicID: String { attemptID.uuidString.lowercased() }
    var firstFailedStage: Stage? { Stage.allCases.first { evidence[$0]?.status == .failed } }
    var firstUnqualifiedStage: Stage? { Stage.allCases.first { evidence[$0]?.status != .passed } }
    func result(for stage: Stage) -> Evidence { evidence[stage] ?? Evidence(status: .waiting, classification: .pending, httpStatus: nil) }
    mutating func record(_ stage: Stage, _ status: Status, _ classification: Classification, httpStatus: Int? = nil) {
        guard evidence[stage]?.status != .passed else { return }
        evidence[stage] = Evidence(status: status, classification: classification,
            httpStatus: httpStatus.flatMap { (100...599).contains($0) ? $0 : nil })
    }
    mutating func correlationReady() { correlationAvailable = true }
    mutating func correlationLost() { correlationAvailable = false }

    struct BackendReceipt: Decodable {
        struct Event: Decodable { let status: Status; let http_status: Int? }
        let attempt_id: String
        let stages: [String: Event]
    }
    mutating func merge(_ receipt: BackendReceipt) {
        guard receipt.attempt_id == publicID else { return }
        correlationAvailable = true
        if let event = receipt.stages["account_login"] {
            record(.accountLogin, event.status, event.status == .passed ? .confirmed : (event.status == .failed ? .rejected : .pending), httpStatus: event.http_status)
        }
        // A prepared server redirect is not proof that ASWebAuthenticationSession
        // received it. Only a local callback can pass that stage.
        if let event = receipt.stages["handoff_redirect"], event.status == .failed {
            record(.callback, .failed, .rejected, httpStatus: event.http_status)
        }
    }

    func receiptRequest(ingress: ScoutAccessOAuth.Credential, begin: Bool = false) -> URLRequest {
        var request = URLRequest(url: ScoutAccessOAuth.resource.appendingPathComponent("api/auth/scout/qualification/" + publicID))
        request.httpMethod = begin ? "PUT" : "GET"
        request.timeoutInterval = 5
        request.setValue("Bearer \(ingress.accessToken)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        return request
    }

    static func protectedRequest(profile: ScoutEndpointProfile, identity: UUID) throws -> URLRequest {
        try ScoutAccessOAuth.requireHosted(profile)
        var request = URLRequest(url: ScoutAccessOAuth.resource.appendingPathComponent("api/chat/threads"))
        request.timeoutInterval = 5
        try ScoutRequestAuthentication.apply(to: &request, endpoint: profile, apiKey: nil)
        guard request.value(forHTTPHeaderField: "X-Guardian-Account-Session") != nil,
              request.value(forHTTPHeaderField: "X-API-Key") == nil else { throw ScoutRequestAuthenticationError.sessionRequired }
        request.setValue(identity.uuidString.lowercased(), forHTTPHeaderField: "X-Scout-Auth-Attempt")
        return request
    }
}
