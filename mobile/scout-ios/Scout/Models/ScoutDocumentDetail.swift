import Foundation

struct ScoutDocumentDetail: Codable, Equatable {
    let id: String?
    let document_id: String?
    let filename: String?
    let title: String?
    let mime_type: String?
    let filesize: Int?
    let src_url: String?
    let parsed_text: String?
    let created_at: String?
}
