import Foundation

struct ScoutLLMHealthSnapshot: Codable, Equatable {
    let status: String?
    let service: String?
    let timestamp: String?
    let provider: String?
    let model: String?
    let local_base_url: String?
    let models_available: Bool?
    let release_hold: Bool?
}
