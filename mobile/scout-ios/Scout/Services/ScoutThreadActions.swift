import Foundation
import CryptoKit

// A projection/reference only. Guardian remains the authority for every operation.
struct ScoutThreadReference: Equatable {
    let id: String
    let threadID: Int
    let title: String
    let node: String
}

enum ScoutThreadActionError: LocalizedError, Equatable {
    case configureConnection, authenticationRequired, changedConnection, unavailableReference
    case incompleteCatalog, invalidResponse, readFailed, uncertainWrite, emptyTitle

    var errorDescription: String? {
        switch self {
        case .configureConnection: return "Select a valid connection in Scout Settings."
        case .authenticationRequired: return "Authenticate the selected connection in Scout Settings."
        case .changedConnection: return "The connection or account changed. Open Scout to check the selected node. A dispatched write may have succeeded; it was not retried."
        case .unavailableReference: return "This thread reference is unavailable on the selected connection."
        case .incompleteCatalog: return "This thread is outside Scout's current thread-list page. Open Scout to locate it."
        case .invalidResponse: return "Vault did not return a valid thread list."
        case .readFailed: return "The protected thread read failed. Check the selected connection in Scout."
        case .uncertainWrite: return "Thread creation could not be confirmed. Open Scout to check before retrying; no automatic retry was sent."
        case .emptyTitle: return "Enter a non-empty thread title."
        }
    }
}

struct ScoutThreadActionContext {
    let endpoint: ScoutEndpointProfile
    private let apiKey: String?
    private let accountSession: ScoutAccountSession?
    let scope: String

    init(endpoint: ScoutEndpointProfile, apiKey: String? = nil, accountSession: ScoutAccountSession? = nil) throws {
        let origin = try ScoutAccessOAuth.origin(for: endpoint)
        guard endpoint.isValidDraft else { throw ScoutThreadActionError.configureConnection }
        let path = URLComponents(string: endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines))?.percentEncodedPath ?? ""
        let basePath = path.hasSuffix("/") ? String(path.dropLast()) : path
        let principal: String
        switch endpoint.authenticationMode {
        case .localAPIKey:
            guard let apiKey, !apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                throw ScoutThreadActionError.authenticationRequired
            }
            principal = "operator-connection" // Never infer an account subject from a key.
            self.apiKey = apiKey
            self.accountSession = nil
        case .remoteSession:
            guard let accountSession else { throw ScoutThreadActionError.authenticationRequired }
            try accountSession.validate(for: endpoint)
            if origin == ScoutAccessOAuth.resource.absoluteString { try ScoutAccessOAuth.requireHosted(endpoint) }
            principal = "account:" + accountSession.userID
            self.apiKey = nil
            self.accountSession = accountSession
        }
        self.endpoint = endpoint
        // Unambiguous, non-secret scope. Credentials never contribute to entity identifiers.
        let metadata = [endpoint.id.uuidString, origin, basePath, endpoint.authenticationMode.rawValue, principal]
        scope = ScoutAccessOAuth.base64URL(Data(SHA256.hash(data: try JSONEncoder().encode(metadata))))
    }

    static func selected() throws -> Self {
        guard let data = UserDefaults.standard.data(forKey: "scout.activeEndpointProfile"),
              let endpoint = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: data) else {
            throw ScoutThreadActionError.configureConnection
        }
        switch endpoint.authenticationMode {
        case .localAPIKey:
            return try Self(endpoint: endpoint, apiKey: ScoutKeychainStore().loadAPIKey(for: endpoint))
        case .remoteSession:
            return try Self(endpoint: endpoint, accountSession: ScoutAccountSessionStore().load(for: endpoint))
        }
    }

    func isCurrent(_ other: Self) -> Bool {
        scope == other.scope && apiKey == other.apiKey && accountSession?.token == other.accountSession?.token
    }

    func reference(id: Int, title: String?) -> ScoutThreadReference {
        ScoutThreadReference(id: "thread.v1." + scope + "." + String(id), threadID: id,
            title: title?.isEmpty == false ? title! : "Thread \(id)", node: endpoint.name)
    }

    func threadID(for reference: String) -> Int? {
        let prefix = "thread.v1." + scope + "."
        guard reference.hasPrefix(prefix), let id = Int(reference.dropFirst(prefix.count)), id > 0,
              reference == prefix + String(id) else { return nil }
        return id
    }

    fileprivate func list(session: URLSession) async -> ScoutGuardianThreadsResult {
        await ScoutGuardianThreadsProbe.probe(endpoint: endpoint, apiKey: apiKey, accountSession: accountSession, session: session)
    }

    fileprivate func create(title: String, session: URLSession) async -> ScoutCreateThreadResult {
        await ScoutCreateThreadProbe.create(endpoint: endpoint, title: title, apiKey: apiKey, accountSession: accountSession, session: session)
    }
}

// Shared thread services plus selection checks; no App Intents, HTTP or auth implementation here.
struct ScoutThreadActions {
    let current: () throws -> ScoutThreadActionContext
    let session: URLSession

    init(current: @escaping () throws -> ScoutThreadActionContext = ScoutThreadActionContext.selected,
         session: URLSession = .scoutAuthenticated) {
        self.current = current
        self.session = session
    }

    func requireCurrent(_ captured: ScoutThreadActionContext) throws {
        // A removed/expired/locked credential also invalidates a suspended operation.
        guard let selected = try? current(), captured.isCurrent(selected) else {
            throw ScoutThreadActionError.changedConnection
        }
    }

    func list() async throws -> (threads: [ScoutThreadReference], hasMore: Bool) {
        let context = try current()
        return try await list(context: context)
    }

    private func list(context: ScoutThreadActionContext) async throws -> (threads: [ScoutThreadReference], hasMore: Bool) {
        try requireCurrent(context)
        let result = await context.list(session: session)
        try requireCurrent(context)
        guard result.httpStatus == 200 else { throw ScoutThreadActionError.readFailed }
        guard let threads = result.threads, threads.allSatisfy({ ($0.id ?? 0) > 0 }),
              Set(threads.compactMap(\.id)).count == threads.count else { throw ScoutThreadActionError.invalidResponse }
        // Absence of pagination metadata cannot prove a complete catalog.
        return (threads.map { context.reference(id: $0.id!, title: $0.title) }, result.hasMore ?? true)
    }

    func resolve(_ identifiers: [String]) async throws -> [ScoutThreadReference] {
        guard !identifiers.isEmpty else { return [] }
        let context = try current()
        guard identifiers.allSatisfy({ context.threadID(for: $0) != nil }) else {
            throw ScoutThreadActionError.unavailableReference // Reject cross-node/account references before dispatch.
        }
        let page = try await list(context: context)
        let byID = Dictionary(uniqueKeysWithValues: page.threads.map { ($0.id, $0) })
        if page.hasMore && identifiers.contains(where: { byID[$0] == nil }) { throw ScoutThreadActionError.incompleteCatalog }
        return identifiers.compactMap { byID[$0] }
    }

    func create(title: String, confirm: (ScoutThreadActionContext, String) async throws -> Void) async throws -> ScoutThreadReference {
        let title = title.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty else { throw ScoutThreadActionError.emptyTitle }
        let context = try current()
        try await confirm(context, title)
        try Task.checkCancellation()
        try requireCurrent(context) // Confirmation may suspend while the app changes profile/account.
        let result = await context.create(title: title, session: session)
        try requireCurrent(context)
        // HTTP 202 is only acceptance, even if a response contains an identifier.
        guard let status = result.httpStatus, [200, 201].contains(status),
              let id = result.threadId ?? result.thread?.id, id > 0,
              result.thread?.id == nil || result.thread?.id == id else { throw ScoutThreadActionError.uncertainWrite }
        return context.reference(id: id, title: result.thread?.title ?? title)
    }
}
