import Foundation

struct ScoutTaskReceiptSummary: Codable, Equatable {
    let task_id: String?
    let state: String?
    let event_type: String?
    let reason: String?
}

struct ScoutThreadTasksResponse: Codable, Equatable {
    let ok: Bool?
    let thread_id: Int?
    let tasks: [ScoutTaskReceiptSummary]?
    let count: Int?
}
