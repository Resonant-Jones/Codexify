import Foundation
import Combine

/// Only endpoint and auth selection define the connection; display metadata does not.
struct ScoutConnectionIdentity: Hashable {
    let profileID: UUID
    let baseURL: String
    let authenticationMode: String

    init(endpoint: ScoutEndpointProfile) {
        profileID = endpoint.id
        baseURL = endpoint.baseURL
        authenticationMode = endpoint.authenticationMode.rawValue
    }
}

/// A transient projection of one node's persisted conversation, never server authority.
@MainActor
final class ScoutConversationState: ObservableObject {
    struct Selection: Equatable {
        let connection: ScoutConnectionIdentity
        let threadID: Int

        init(endpoint: ScoutEndpointProfile, threadID: Int) {
            connection = ScoutConnectionIdentity(endpoint: endpoint)
            self.threadID = threadID
        }
    }

    enum RefreshOutcome {
        case refreshed
        case failed(String)
    }

    @Published private(set) var messages: [ScoutChatMessageSummary]?
    private(set) var selection: Selection?
    private var revision = 0

    func select(_ selection: Selection) {
        guard self.selection != selection else { return }
        revision += 1
        self.selection = selection
        messages = nil
    }

    /// Apply only a persisted read for the selected node/thread. Latest-started read wins.
    func refresh(
        endpoint: ScoutEndpointProfile,
        threadID: Int,
        apiKey: String?,
        session: URLSession = .scoutAuthenticated
    ) async -> RefreshOutcome? {
        let requested = Selection(endpoint: endpoint, threadID: threadID)
        guard selection == requested else { return nil }
        revision += 1
        let requestedRevision = revision
        let result = await ScoutGuardianThreadMessagesProbe.probe(
            endpoint: endpoint, threadId: threadID, apiKey: apiKey, session: session
        )
        guard !Task.isCancelled, selection == requested, revision == requestedRevision else { return nil }
        guard let persisted = result.messages else { return .failed(result.message) }
        messages = persisted
        return .refreshed
    }

    func handleTerminalEvent(
        _ eventType: String,
        endpoint: ScoutEndpointProfile,
        threadID: Int,
        apiKey: String?,
        session: URLSession = .scoutAuthenticated
    ) async -> String? {
        guard selection == Selection(endpoint: endpoint, threadID: threadID) else { return nil }
        switch eventType {
        case "task.completed":
            guard let outcome = await refresh(endpoint: endpoint, threadID: threadID, apiKey: apiKey, session: session) else { return nil }
            switch outcome {
            case .refreshed: return "Task completed. Messages refreshed."
            case .failed(let message): return "Task completed. \(message)"
            }
        case "task.failed":
            return "Task failed. No assistant message was synthesized."
        case "task.cancelled":
            return "Task cancelled. No assistant message was synthesized."
        default:
            return nil
        }
    }
}
