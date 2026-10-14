import Foundation

enum ScoutIngressQualification: Equatable {
    case guardianAccountRequired
    case accessRequired
    case unqualified

    init(response: HTTPURLResponse) {
        // Canonical Guardian account-route marker. Check it before the edge
        // challenge: Managed OAuth can replace a protected resource's 401.
        if response.statusCode == 401,
           response.value(forHTTPHeaderField: "X-Guardian-Auth-Failure") == "ACCOUNT_SESSION_INVALID" {
            self = .guardianAccountRequired
        } else if (response.value(forHTTPHeaderField: "WWW-Authenticate") ?? "").contains("resource_metadata") {
            self = .accessRequired
        } else {
            self = .unqualified
        }
    }

    func message(response: HTTPURLResponse) -> String {
        var diagnostic = " (HTTP \(response.statusCode)"
        if let ray = response.value(forHTTPHeaderField: "CF-Ray"), ray.count <= 64,
           ray.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "-") }) {
            diagnostic += ", Cloudflare Ray " + ray
        }
        diagnostic += ")."
        switch self {
        case .guardianAccountRequired:
            return "Native request reached Guardian's account gate" + diagnostic
                + " Ingress admission is qualified; Guardian account-session handoff is still required."
        case .accessRequired:
            return "Cloudflare Access still requires admission" + diagnostic
                + " No Guardian account session was issued."
        case .unqualified:
            return "API returned a response" + diagnostic
                + " Guardian account authentication remains unqualified; no account session was issued."
        }
    }
}
