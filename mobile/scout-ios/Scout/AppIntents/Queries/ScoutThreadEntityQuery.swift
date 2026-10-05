import AppIntents

struct ScoutThreadEntityQuery: EntityQuery {
    func entities(for identifiers: [ScoutThreadEntity.ID]) async throws -> [ScoutThreadEntity] {
        try await entities(for: identifiers, using: ScoutThreadActions())
    }

    func entities(for identifiers: [ScoutThreadEntity.ID], using actions: ScoutThreadActions) async throws -> [ScoutThreadEntity] {
        try await actions.resolve(identifiers).map(ScoutThreadEntity.init)
    }

    // Explicit list invocation is required; do not export background content suggestions.
    func suggestedEntities() async throws -> [ScoutThreadEntity] { [] }
}
