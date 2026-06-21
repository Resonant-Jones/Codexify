import Foundation

struct ScoutChatMessageSummary: Codable, Equatable {
    let id: Int?
    let role: String?
    let content: String?
    let created_at: String?
    let updated_at: String?
}

struct ScoutChatMessagesResponse: Codable, Equatable {
    let ok: Bool?
    let total: Int?
    let messages: [ScoutChatMessageSummary]?
}
