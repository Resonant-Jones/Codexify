import Foundation
import Combine

/// Volatile client orchestration only. These phases are UI state, not new runtime tokens.
/// Vault owns message IDs and task outcomes; an uncertain write is never replayed here.
@MainActor
final class ScoutComposerFlow: ObservableObject {
    struct Scope: Equatable {
        let connection: ScoutConnectionIdentity
        // A nil thread ID is a new, not-yet-persisted conversation.
        let threadID: Int?
        let accountGeneration: Int
    }
    enum Phase: Equatable { case idle, saving, requesting, pending, messageRejected, responseRejected, unconfirmed }

    @Published var draft = ""
    @Published var optionsPresented = false
    @Published private(set) var phase = Phase.idle
    @Published private(set) var status: String?
    @Published private(set) var acceptedMessageID: Int?
    @Published private(set) var taskID: String?
    private(set) var scope: Scope?
    private var revision = 0

    var isWorking: Bool { phase == .saving || phase == .requesting }
    var canWrite: Bool { phase == .idle || phase == .messageRejected }
    var canSubmit: Bool { canWrite && !draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    var canRequestResponse: Bool { phase == .idle || phase == .responseRejected }
    var isError: Bool { phase == .messageRejected || phase == .responseRejected || phase == .unconfirmed }

    func select(_ scope: Scope?) {
        guard self.scope != scope else { return }
        revision += 1
        self.scope = scope
        draft = ""
        optionsPresented = false
        phase = .idle
        status = nil
        acceptedMessageID = nil
        taskID = nil
    }

    func report(_ message: String) { status = message }

    /// Move an accepted first message into its canonical thread without losing
    /// the response state that is already being observed by the composer.
    @discardableResult
    func promoteDraft(from draftScope: Scope, to threadScope: Scope) -> Bool {
        guard scope == draftScope, draftScope.threadID == nil,
              let threadID = threadScope.threadID, threadID > 0,
              draftScope.connection == threadScope.connection,
              draftScope.accountGeneration == threadScope.accountGeneration,
              acceptedMessageID != nil, !isWorking else { return false }
        revision += 1
        scope = threadScope
        return true
    }

    func submit(scope: Scope, messageOnly: Bool = false,
                isCurrent: () -> Bool,
                save: (String) async -> ScoutSendMessageResult,
                complete: () async -> ScoutCompleteThreadResult) async {
        guard self.scope == scope, canSubmit, isCurrent(), !Task.isCancelled else { return }
        let text = draft, ticket = revision
        phase = .saving // Set before suspension: repeated taps cannot dispatch another write.
        status = "Sending message…"
        acceptedMessageID = nil
        taskID = nil
        let result = await save(text)
        guard stillCurrent(scope, ticket: ticket, isCurrent: isCurrent, allowCancelled: true) else { return }
        guard let code = result.httpStatus, [200, 201].contains(code), let id = result.messageId, id > 0 else {
            phase = Self.isRejection(result.httpStatus) ? .messageRejected : .unconfirmed
            status = phase == .messageRejected ? "Message was not accepted. \(result.message)" : "Message acceptance is unconfirmed. Check the conversation before sending again. \(result.message)"
            return // Keep the exact draft. No completion or automatic retry.
        }
        acceptedMessageID = id
        if draft == text { draft = "" }
        if messageOnly {
            phase = .idle
            status = "Message saved. No response requested."
            return
        }
        guard !Task.isCancelled else {
            phase = .responseRejected
            status = "Message saved. Interaction interrupted before the response request. Request a response from message options; the message will not be sent again."
            return
        }
        await request(scope: scope, ticket: ticket, isCurrent: isCurrent, complete: complete)
    }

    /// Existing completion-only operation. Recovery never calls the message writer.
    func requestResponse(scope: Scope, isCurrent: () -> Bool,
                         complete: () async -> ScoutCompleteThreadResult) async {
        guard self.scope == scope, canRequestResponse, isCurrent(), !Task.isCancelled else { return }
        await request(scope: scope, ticket: revision, isCurrent: isCurrent, complete: complete)
    }

    private func request(scope: Scope, ticket: Int, isCurrent: () -> Bool,
                         complete: () async -> ScoutCompleteThreadResult) async {
        guard stillCurrent(scope, ticket: ticket, isCurrent: isCurrent) else { return }
        phase = .requesting
        status = "Requesting response…"
        let result = await complete()
        guard stillCurrent(scope, ticket: ticket, isCurrent: isCurrent, allowCancelled: true) else { return }
        if let code = result.httpStatus, (200..<300).contains(code),
           let id = result.taskId, !id.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            taskID = id
            phase = .pending
            status = result.acceptanceStatus == "accepted_degraded"
                ? "Response accepted; task visibility may be delayed."
                : "Response accepted. Waiting for task status…"
        } else {
            phase = Self.isRejection(result.httpStatus) ? .responseRejected : .unconfirmed
            status = (acceptedMessageID == nil ? "" : "Message saved. ") +
                (phase == .responseRejected ? "Response was not accepted. " : "Response acceptance is unconfirmed. Check thread details before requesting again. ") + result.message
        }
    }

    private func stillCurrent(_ scope: Scope, ticket: Int, isCurrent: () -> Bool, allowCancelled: Bool = false) -> Bool {
        guard self.scope == scope, revision == ticket else { return false }
        guard isCurrent() else { select(nil); return false }
        guard allowCancelled || !Task.isCancelled else {
            phase = .unconfirmed
            status = "Interaction interrupted. A dispatched operation may have succeeded; check the conversation. Nothing was retried."
            return false
        }
        return true
    }

    func observationEnded(taskID: String, scope: Scope) {
        guard self.scope == scope, self.taskID == taskID, phase == .pending else { return }
        status = "Response outcome is unconfirmed. Check response status; nothing was retried."
    }

    @discardableResult
    func terminal(_ event: String, taskID: String, scope: Scope) -> Bool {
        guard self.scope == scope, self.taskID == taskID, phase == .pending else { return false }
        switch event {
        case "task.completed": status = "Guardian reported completion."
        case "task.failed": status = "Response failed. No assistant message was synthesized."
        case "task.cancelled": status = "Response cancelled. No assistant message was synthesized."
        default: return false
        }
        phase = .idle
        return true
    }

    private static func isRejection(_ code: Int?) -> Bool {
        // Timeout/429/5xx do not prove absence of accepted work. No replay is offered.
        guard let code else { return false }
        return [400, 401, 403, 404, 422].contains(code)
    }
}
