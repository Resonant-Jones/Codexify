import Foundation

struct ScoutRAGTraceSnapshot: Equatable {
    let threadId: Int?
    let traceAvailable: Bool?
    let traceUnavailableReason: String?
    let documentCount: Int?
    let graphCount: Int?
    let retrievalSummary: [String: Any]?
    let retrievalPolicy: [String: Any]?
    let effectivePolicy: [String: Any]?
    let modelSelection: [String: Any]?
    let retrievalProvenance: [String: Any]?

    init?(from dict: [String: Any]) {
        threadId = dict["thread_id"] as? Int
        traceAvailable = dict["trace_available"] as? Bool
        traceUnavailableReason = dict["trace_unavailable_reason"] as? String

        if let docs = dict["documents"] as? [Any] {
            documentCount = docs.count
        } else {
            documentCount = nil
        }

        if let graph = dict["graph"] as? [Any] {
            graphCount = graph.count
        } else {
            graphCount = nil
        }

        retrievalSummary = dict["retrieval_summary"] as? [String: Any]
        retrievalPolicy = dict["retrieval_policy"] as? [String: Any]
        effectivePolicy = dict["effective_policy"] as? [String: Any]
        modelSelection = dict["model_selection"] as? [String: Any]
        retrievalProvenance = dict["retrieval_provenance"] as? [String: Any]
    }

    static func == (lhs: ScoutRAGTraceSnapshot, rhs: ScoutRAGTraceSnapshot) -> Bool {
        lhs.threadId == rhs.threadId
            && lhs.traceAvailable == rhs.traceAvailable
            && lhs.traceUnavailableReason == rhs.traceUnavailableReason
            && lhs.documentCount == rhs.documentCount
            && lhs.graphCount == rhs.graphCount
    }
}
