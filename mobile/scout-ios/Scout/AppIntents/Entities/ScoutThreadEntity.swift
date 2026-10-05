import AppIntents

struct ScoutThreadEntity: AppEntity {
    let id: String
    let title: String
    let node: String

    static let typeDisplayRepresentation: TypeDisplayRepresentation = "Scout thread"
    static let defaultQuery = ScoutThreadEntityQuery()

    init(_ reference: ScoutThreadReference) {
        id = reference.id
        title = reference.title
        node = reference.node
    }

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: "\(title)", subtitle: "\(node)", image: .init(systemName: "bubble.left.and.bubble.right"))
    }
}
