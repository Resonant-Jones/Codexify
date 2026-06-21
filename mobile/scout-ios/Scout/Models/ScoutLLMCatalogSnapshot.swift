import Foundation

struct ScoutCatalogModel: Codable, Equatable {
    let id: String?
    let displayName: String?
    let supports_chat: Bool?
    let supports_vision: Bool?
    let model_kind: String?
}

struct ScoutCatalogProvider: Codable, Equatable {
    let id: String?
    let displayName: String?
    let enabled: Bool?
    let available: Bool?
    let models: [ScoutCatalogModel]?
}

struct ScoutLLMCatalogSnapshot: Codable, Equatable {
    let providers: [ScoutCatalogProvider]?
}
