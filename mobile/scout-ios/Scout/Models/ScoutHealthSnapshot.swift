import Foundation

struct ScoutHealthSnapshot: Codable, Equatable {
    let status: String
    let service: String
    let timestamp: String
}
