import Foundation

struct ScoutSavedWidget: Decodable, Identifiable, Hashable {
    let widget_id: String
    let name: String
    let current_revision: Int
    var id: String { widget_id }
}

struct ScoutSavedWidgetPage: Decodable {
    let widgets: [ScoutSavedWidget]
    let count: Int
    let next_offset: Int?
}

struct ScoutSavedWidgets {
    let transport: ScoutLibraryService
    private func path(_ id: String) throws -> String {
        guard id.hasPrefix("sw_"), id.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "_" || $0 == "-") }) else {
            throw ScoutLibraryError.invalidResponse
        }
        return "/api/saved-widgets/" + id
    }

    func list(offset: Int = 0) async throws -> ScoutSavedWidgetPage {
        let url = try transport.apiURL(path: "/api/saved-widgets", query: [.init(name: "limit", value: "100"), .init(name: "offset", value: String(offset))])
        let data = try await transport.read(url, maxBytes: 4 * 1024 * 1024).data
        let page = try JSONDecoder().decode(ScoutSavedWidgetPage.self, from: data)
        guard page.count == page.widgets.count, page.count <= 100,
              page.next_offset == nil || (page.count > 0 && page.next_offset == offset + page.count),
              page.widgets.allSatisfy({ !$0.name.isEmpty && $0.current_revision > 0 }) else { throw ScoutLibraryError.invalidResponse }
        return page
    }

    func revisions(_ widget: ScoutSavedWidget) async throws -> [Int] {
        let url = try transport.apiURL(path: path(widget.id) + "/revisions")
        let data = try await transport.read(url, maxBytes: 4 * 1024 * 1024).data
        struct Response: Decodable { struct Revision: Decodable { let revision: Int }; let revisions: [Revision] }
        return try JSONDecoder().decode(Response.self, from: data).revisions.map(\.revision)
    }

    func artifact(_ widget: ScoutSavedWidget, revision: Int) async throws -> ScoutSandboxWidget {
        guard revision > 0 else { throw ScoutLibraryError.invalidResponse }
        let url = try transport.apiURL(path: path(widget.id) + "/revisions/" + String(revision))
        let data = try await transport.read(url, maxBytes: 2 * 1024 * 1024).data
        guard let response = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              response["widget_id"] as? String == widget.id, response["revision"] as? Int == revision,
              let envelope = response["artifact_snapshot"] as? [String: Any],
              envelope["kind"] as? String == "sandbox", envelope["version"] as? Int == 1,
              let result = ScoutSandboxWidget(envelope: envelope) else { throw ScoutLibraryError.unavailablePreview }
        return result
    }

    func save(thread: Int, message: Int, index: Int, name: String, target: ScoutSavedWidget?) async throws -> Int {
        var body: [String: Any] = ["thread_id": thread, "message_id": message, "artifact_index": index]
        let route: String
        if let target {
            route = try path(target.id) + "/revisions"
            body["base_revision"] = target.current_revision
        } else { route = "/api/saved-widgets"; body["name"] = name.trimmingCharacters(in: .whitespacesAndNewlines) }
        let url = try transport.apiURL(path: route)
        let data = try await transport.read(url, maxBytes: 1024 * 1024, body: JSONSerialization.data(withJSONObject: body)).data
        guard let result = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let revision = result["revision"] as? Int, revision > 0 else { throw ScoutLibraryError.invalidResponse }
        return revision
    }

    struct Candidate: Identifiable { let id: Int; let title: String }

    static func saveFailureMessage(_ error: Error) -> String {
        let status: Int
        var reasons: [String] = []
        switch error {
        case ScoutLibraryError.rejected(let code, let data):
            status = code
            if let response = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let detail = response["detail"] as? [String: Any],
               detail["error"] as? String == "artifact_not_eligible" {
                reasons = detail["reasons"] as? [String] ?? []
            }
        case ScoutLibraryError.http(let code): status = code
        case is ScoutRequestAuthenticationError: return error.localizedDescription
        default: return error.localizedDescription + " Check Library before retrying to avoid a duplicate."
        }
        if [401, 403].contains(status) { return "Sign in again in Settings, then reopen this save form." }
        if status == 409 { return "The widget changed. Reopen this form to refresh its versions, then save again." }
        if status == 404 { return "The widget or source response is no longer available. Refresh Guardian and Library." }
        if status == 422 {
            if reasons.contains(where: { $0.hasPrefix("source_provenance_") }) {
                return "Not saved: this response has no verified successful completion record. Ask Guardian to generate the widget again, then save the new response."
            }
            if reasons.contains("artifact_missing_executable_code") {
                return "Not saved: this response contains no supported widget program. Ask Guardian for a self-contained interactive widget."
            }
            if reasons.contains(where: { ["artifact_external_dependency", "artifact_unavailable_local_dependency", "artifact_ambiguous_dependency"].contains($0) }) {
                return "Not saved: this widget depends on resources unavailable in Library. Ask Guardian for a self-contained version with its code and assets included."
            }
            if reasons.contains("source_not_authorized") || reasons.contains("source_artifact_selection_invalid") {
                return "Not saved: the source widget is unavailable to this account. Refresh the conversation and try its current response."
            }
            return "Not saved: the widget did not pass validation. Ask Guardian to generate a valid self-contained widget, then save the new response."
        }
        if status == 400 { return "Not saved: check the widget name and reopen this form." }
        return error.localizedDescription + " Check Library before retrying to avoid a duplicate."
    }

    static func candidates(_ message: ScoutChatMessageSummary) -> [Candidate] {
        guard message.role == "assistant", let id = message.id, id > 0 else { return [] }
        let content = message.content ?? ""
        let expression = try! NSRegularExpression(pattern: "<!--\\s*cfy-ui:(.*?)-->", options: [.caseInsensitive, .dotMatchesLineSeparators])
        return expression.matches(in: content, range: NSRange(content.startIndex..., in: content)).enumerated().compactMap { index, match in
            guard let range = Range(match.range, in: content) else { return nil }
            let single = ScoutChatMessageSummary(id: id, role: "assistant", content: String(content[range]), created_at: nil, updated_at: nil)
            guard case .sandbox(let widget) = ScoutGenerativeUI.presentation(for: single).artifacts.first else { return nil }
            return Candidate(id: index, title: widget.title.isEmpty ? "My widget" : widget.title)
        }
    }
}
