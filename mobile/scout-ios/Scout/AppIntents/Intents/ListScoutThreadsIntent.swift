import AppIntents

struct ListScoutThreadsIntent: AppIntent {
    static let title: LocalizedStringResource = "List Scout threads"
    static let description = IntentDescription("Read the current thread-list page from the connection selected in Scout Settings. Returns only thread titles and references.")
    static let authenticationPolicy: IntentAuthenticationPolicy = .requiresLocalDeviceAuthentication

    func perform() async throws -> some IntentResult & ReturnsValue<[ScoutThreadEntity]> & ProvidesDialog {
        try await perform(using: ScoutThreadActions())
    }

    // Test the actual adapter with synthetic transport, without invoking Siri.
    func perform(using actions: ScoutThreadActions) async throws -> some IntentResult & ReturnsValue<[ScoutThreadEntity]> & ProvidesDialog {
        let page = try await actions.list()
        let entities = page.threads.map(ScoutThreadEntity.init)
        if page.hasMore {
            return .result(value: entities, dialog: "Read \(entities.count) threads from the current page. More threads may be available in Scout.")
        }
        return .result(value: entities, dialog: "Read \(entities.count) threads from the selected Scout connection.")
    }
}
