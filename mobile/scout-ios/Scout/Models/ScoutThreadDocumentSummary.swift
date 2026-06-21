import Foundation

struct ScoutThreadDocumentSummary: Codable, Equatable {
    let id: String?
    let title: String?
    let relation: String?
    let created_at: String?
}

struct ScoutThreadDocumentsResponse: Codable, Equatable {
    let ok: Bool?
    let documents: [ScoutThreadDocumentSummary]?
}
