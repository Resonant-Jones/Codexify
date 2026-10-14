import AppIntents

struct CreateScoutThreadIntent: AppIntent {
    static let title: LocalizedStringResource = "Create Scout thread"
    static let description = IntentDescription("Confirm and create a thread on the selected Scout connection. This does not send a message or request a Guardian response.")
    static let authenticationPolicy: IntentAuthenticationPolicy = .requiresLocalDeviceAuthentication

    @Parameter(title: "Thread title") var threadTitle: String

    func perform() async throws -> some IntentResult & ReturnsValue<ScoutThreadEntity> & ProvidesDialog {
        try await perform(using: ScoutThreadActions()) { context, title in
            let dialog: IntentDialog = "Create thread \(title) on \(context.endpoint.name) at \(context.endpoint.baseURL)?"
            if #available(iOS 18.0, macOS 15.0, *) {
                try await requestConfirmation(dialog: dialog)
            } else {
                try await requestConfirmation(result: .result(dialog: dialog))
            }
        }
    }

    func perform(using actions: ScoutThreadActions,
                 confirm: (ScoutThreadActionContext, String) async throws -> Void) async throws -> some IntentResult & ReturnsValue<ScoutThreadEntity> & ProvidesDialog {
        let reference = try await actions.create(title: threadTitle, confirm: confirm)
        return .result(value: ScoutThreadEntity(reference), dialog: "Created thread \(reference.title) on \(reference.node). No message was sent and no Guardian response was requested.")
    }
}
