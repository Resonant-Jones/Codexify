import Foundation

struct ScoutChatThreadSummary: Codable, Equatable {
    let id: Int?
    let title: String?
    let summary: String?
    let created_at: String?
    let updated_at: String?
}

struct ScoutChatThreadsResponse: Codable, Equatable {
    let ok: Bool?
    let threads: [ScoutChatThreadSummary]?
    let limit: Int?
    let offset: Int?
    let next_offset: Int?
    let has_more: Bool?
}
