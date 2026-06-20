import Foundation

struct ScoutEndpointConnectivityResult {
    let validationState: ScoutEndpointValidationState
    let authenticationState: ScoutEndpointAuthenticationState
    let message: String
    let connectedAt: Date?
}

struct ScoutEndpointConnectivityProbe {

    static func probe(endpoint: ScoutEndpointProfile) async -> ScoutEndpointConnectivityResult {
        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !urlString.isEmpty else {
            return ScoutEndpointConnectivityResult(
                validationState: .invalidConfiguration,
                authenticationState: endpoint.authenticationState,
                message: "Base URL is empty.",
                connectedAt: nil
            )
        }

        if urlString.hasSuffix("/") {
            urlString = String(urlString.dropLast())
        }
        urlString += "/health"

        guard let url = URL(string: urlString) else {
            return ScoutEndpointConnectivityResult(
                validationState: .invalidConfiguration,
                authenticationState: endpoint.authenticationState,
                message: "Malformed health-check URL. Check the base URL.",
                connectedAt: nil
            )
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 5

        do {
            let (_, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                return ScoutEndpointConnectivityResult(
                    validationState: .unreachable,
                    authenticationState: endpoint.authenticationState,
                    message: "Unexpected response type from server.",
                    connectedAt: nil
                )
            }

            let statusCode = httpResponse.statusCode

            switch statusCode {
            case 200..<300:
                return ScoutEndpointConnectivityResult(
                    validationState: .reachable,
                    authenticationState: .authenticated,
                    message: "Vault is reachable (HTTP \(statusCode)).",
                    connectedAt: Date()
                )
            case 401, 403:
                return ScoutEndpointConnectivityResult(
                    validationState: .reachable,
                    authenticationState: .authRequired,
                    message: "Vault is reachable but authentication is required (HTTP \(statusCode)).",
                    connectedAt: Date()
                )
            default:
                return ScoutEndpointConnectivityResult(
                    validationState: .unreachable,
                    authenticationState: endpoint.authenticationState,
                    message: "Vault returned unexpected status (HTTP \(statusCode)).",
                    connectedAt: nil
                )
            }
        } catch let error as URLError where error.code == .timedOut {
            return ScoutEndpointConnectivityResult(
                validationState: .unreachable,
                authenticationState: endpoint.authenticationState,
                message: "Connection timed out after 5 seconds. Vault may be offline or unreachable.",
                connectedAt: nil
            )
        } catch {
            return ScoutEndpointConnectivityResult(
                validationState: .unreachable,
                authenticationState: endpoint.authenticationState,
                message: "Connection failed: \(error.localizedDescription)",
                connectedAt: nil
            )
        }
    }
}
