import Foundation

/// Keeps only one small piece of text in SwiftUI's layout at a time.
struct ScoutDocumentPage {
    static let byteLimit = 8 * 1024
    let text: String
    let nextStart: String.Index?

    init(_ document: String, from start: String.Index? = nil) {
        let bytes = document.utf8
        let start = start ?? bytes.startIndex
        var end = bytes.index(start, offsetBy: Self.byteLimit, limitedBy: bytes.endIndex) ?? bytes.endIndex
        // Back up to a Unicode scalar boundary. Even a very long combining
        // sequence must not turn the preview into an unbounded layout job.
        while end != bytes.endIndex && (bytes[end] & 0xC0) == 0x80 {
            bytes.formIndex(before: &end)
        }
        text = String(decoding: bytes[start..<end], as: UTF8.self)
        nextStart = end == bytes.endIndex ? nil : end
    }
}

/// Holds recent reads in memory only. Authorization is prepared before a lookup.
actor ScoutDocumentCache {
    struct Key: Hashable {
        let connection: ScoutConnectionIdentity
        let accountGeneration: Int
        let authorization: Data
        let url: URL
    }

    private struct Entry {
        let detail: ScoutDocumentDetail
        let expires: ContinuousClock.Instant
        let bytes: Int
    }

    private let maxBytes: Int
    private let maxCount: Int
    private let lifetime: Duration
    private var entries: [Key: Entry] = [:]
    private var mostRecent: [Key] = []
    private var totalBytes = 0

    init(maxBytes: Int = 32 * 1024 * 1024, maxCount: Int = 16, lifetime: Duration = .seconds(120)) {
        self.maxBytes = maxBytes
        self.maxCount = maxCount
        self.lifetime = lifetime
    }

    func detail(for key: Key, now: ContinuousClock.Instant = .now) -> ScoutDocumentDetail? {
        guard let entry = entries[key] else { return nil }
        guard entry.expires > now else { remove(key); return nil }
        mostRecent.removeAll { $0 == key }
        mostRecent.append(key)
        return entry.detail
    }

    func insert(_ detail: ScoutDocumentDetail, for key: Key, now: ContinuousClock.Instant = .now) {
        remove(key)
        let bytes = [detail.id, detail.document_id, detail.filename, detail.title, detail.mime_type,
                     detail.src_url, detail.parsed_text, detail.created_at].reduce(0) { $0 + ($1?.utf8.count ?? 0) }
        guard bytes <= maxBytes, maxCount > 0 else { return }
        while let oldest = mostRecent.first, entries.count >= maxCount || totalBytes > maxBytes - bytes {
            remove(oldest)
        }
        entries[key] = Entry(detail: detail, expires: now.advanced(by: lifetime), bytes: bytes)
        mostRecent.append(key)
        totalBytes += bytes
    }

    func remove(_ key: Key) {
        guard let entry = entries.removeValue(forKey: key) else { return }
        mostRecent.removeAll { $0 == key }
        totalBytes -= entry.bytes
    }
}
