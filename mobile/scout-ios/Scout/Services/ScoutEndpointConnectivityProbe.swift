import Foundation

private struct GuardianHealthDetails: Decodable {
    private struct DetailKey: CodingKey {
        let stringValue: String
        let intValue: Int? = nil

        init?(stringValue: String) {
            self.stringValue = stringValue
        }

        init?(intValue: Int) {
            return nil
        }
    }

    init(from decoder: Decoder) throws {
        _ = try decoder.container(keyedBy: DetailKey.self)
    }
}

private struct GuardianHealthResponse: Decodable {
    let status: String
    let service: String
    let timestamp: String
    let details: GuardianHealthDetails

    var isVerifiedGuardian: Bool {
        status == "ok" && service == "core" && !timestamp.isEmpty
    }

    var snapshot: ScoutHealthSnapshot {
        ScoutHealthSnapshot(status: status, service: service, timestamp: timestamp)
    }
}

struct ScoutEndpointConnectivityResult {
    let validationState: ScoutEndpointValidationState
    let authenticationState: ScoutEndpointAuthenticationState
    let message: String
    let connectedAt: Date?
    let snapshot: ScoutHealthSnapshot?
    let latencyMilliseconds: Int?
}

struct ScoutEndpointConnectivityProbe {

    static func probe(endpoint: ScoutEndpointProfile, apiKey: String? = nil, session: URLSession = .scoutAuthenticated) async -> ScoutEndpointConnectivityResult {
        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !urlString.isEmpty else {
            return ScoutEndpointConnectivityResult(
                validationState: .invalidConfiguration,
                authenticationState: endpoint.authenticationState,
                message: "Base URL is empty.",
                connectedAt: nil,
                snapshot: nil,
                latencyMilliseconds: nil
            )
        }

        if urlString.hasSuffix("/") {
            urlString = String(urlString.dropLast())
        }
        urlString += "/health"

        guard let url = URL(string: urlString), let scheme = url.scheme, !scheme.isEmpty, url.host != nil else {
            return ScoutEndpointConnectivityResult(
                validationState: .invalidConfiguration,
                authenticationState: endpoint.authenticationState,
                message: "Malformed health-check URL. Check the base URL.",
                connectedAt: nil,
                snapshot: nil,
                latencyMilliseconds: nil
            )
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 5

        let requestStart = Date()

        do {
            try ScoutRequestAuthentication.apply(to: &request, endpoint: endpoint, apiKey: apiKey)
            let (data, response) = try await session.data(for: request)
            if let http = response as? HTTPURLResponse {
                try ScoutRequestAuthentication.validate(response: http, endpoint: endpoint, request: request)
            }
            let latencyMs = Int(requestStart.distance(to: Date()) * 1000)

            guard let httpResponse = response as? HTTPURLResponse else {
                return ScoutEndpointConnectivityResult(
                    validationState: .unreachable,
                    authenticationState: endpoint.authenticationState,
                    message: "Unexpected response type from server.",
                    connectedAt: nil,
                    snapshot: nil,
                    latencyMilliseconds: latencyMs
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                guard let healthResponse = try? JSONDecoder().decode(GuardianHealthResponse.self, from: data),
                      healthResponse.isVerifiedGuardian else {
                    return ScoutEndpointConnectivityResult(
                        validationState: .unreachable,
                        authenticationState: .unconfigured,
                        message: "Endpoint responded, but did not return a valid Guardian health response.",
                        connectedAt: nil,
                        snapshot: nil,
                        latencyMilliseconds: latencyMs
                    )
                }

                return ScoutEndpointConnectivityResult(
                    validationState: .reachable,
                    authenticationState: .unconfigured,
                    message: "Guardian is reachable (HTTP \(statusCode)).",
                    connectedAt: Date(),
                    snapshot: healthResponse.snapshot,
                    latencyMilliseconds: latencyMs
                )
            case 401, 403:
                return ScoutEndpointConnectivityResult(
                    validationState: .unreachable,
                    authenticationState: .authRequired,
                    message: "Endpoint requires authentication (HTTP \(statusCode)); Guardian identity was not verified.",
                    connectedAt: nil,
                    snapshot: nil,
                    latencyMilliseconds: latencyMs
                )
            default:
                return ScoutEndpointConnectivityResult(
                    validationState: .unreachable,
                    authenticationState: endpoint.authenticationState,
                    message: "Vault returned unexpected status (HTTP \(statusCode)).",
                    connectedAt: nil,
                    snapshot: nil,
                    latencyMilliseconds: latencyMs
                )
            }
        } catch let error as ScoutRequestAuthenticationError {
            return ScoutEndpointConnectivityResult(
                validationState: .invalidConfiguration,
                authenticationState: .unconfigured,
                message: error.localizedDescription,
                connectedAt: nil,
                snapshot: nil,
                latencyMilliseconds: nil
            )
        } catch let error as URLError where error.code == .timedOut {
            return ScoutEndpointConnectivityResult(
                validationState: .unreachable,
                authenticationState: endpoint.authenticationState,
                message: "Connection timed out after 5 seconds. Vault may be offline or unreachable.",
                connectedAt: nil,
                snapshot: nil,
                latencyMilliseconds: nil
            )
        } catch {
            return ScoutEndpointConnectivityResult(
                validationState: .unreachable,
                authenticationState: endpoint.authenticationState,
                message: "Connection failed: \(error.localizedDescription)",
                connectedAt: nil,
                snapshot: nil,
                latencyMilliseconds: nil
            )
        }
    }
}
