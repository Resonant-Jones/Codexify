import Foundation

// Serialize refreshes per connection because a provider may rotate refresh tokens.
actor ScoutIngressRenewal {
    static let shared = ScoutIngressRenewal()
    typealias Credential = ScoutAccessOAuth.Credential
    private var flights: [String: Task<Credential, Error>] = [:]
    private let load: (ScoutEndpointProfile) throws -> Credential?
    private let replace: (Credential, Credential, ScoutEndpointProfile) throws -> Bool
    private let exchange: (URLRequest) async throws -> (Data, URLResponse)

    init(load: @escaping (ScoutEndpointProfile) throws -> Credential? = { try ScoutAccessCredentialStore().load(for: $0) },
         replace: @escaping (Credential, Credential, ScoutEndpointProfile) throws -> Bool = {
             try ScoutAccessCredentialStore().replace($0, ifMatching: $1, for: $2)
         },
         exchange: @escaping (URLRequest) async throws -> (Data, URLResponse) = {
             try await URLSession.scoutAuthenticated.data(for: $0)
         }) {
        self.load = load
        self.replace = replace
        self.exchange = exchange
    }

    func credential(for profile: ScoutEndpointProfile, now: Date = Date()) async throws -> Credential {
        try ScoutAccessOAuth.requireHosted(profile)
        let key = try ScoutAccessOAuth.credentialAccount(for: profile)
        if let existing = flights[key] { return try await existing.value }
        guard let current = try load(profile) else { throw ScoutRequestAuthenticationError.ingressRequired }
        if current.expiresAt > now.addingTimeInterval(30) { return current }
        let request = try ScoutAccessOAuth.refreshRequest(credential: current, profile: profile)
        let task = Task<Credential, Error> {
            let (data, response) = try await exchange(request)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                throw ScoutRequestAuthenticationError.ingressRequired
            }
            let renewed = try ScoutAccessOAuth.Credential.decode(data, retainingRefreshToken: current.refreshToken)
            guard try replace(renewed, current, profile) else { throw ScoutRequestAuthenticationError.ingressRequired }
            return renewed
        }
        flights[key] = task
        defer { flights[key] = nil }
        return try await task.value
    }
}
