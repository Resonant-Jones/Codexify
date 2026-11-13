import Foundation

enum ScoutSidebarThreadFilter {
    static func withoutProjects(_ threads: [ScoutChatThreadSummary], source: String, searchText: String) -> [ScoutChatThreadSummary] {
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        return threads.filter { thread in
            thread.archived_at == nil && (source == "all" || thread.origin_system == source) &&
                (query.isEmpty || (thread.title ?? "Untitled").localizedCaseInsensitiveContains(query))
        }
    }
}

struct ScoutProject: Decodable, Identifiable, Equatable {
    let id: Int
    let name: String
    let system_role: String?
    let archived_at: String?

    var isGeneral: Bool {
        if let role = system_role { return role == "general" }
        return ["general", "loose threads"].contains(name.trimmingCharacters(in: .whitespacesAndNewlines).lowercased())
    }
}

struct ScoutProjectsResult {
    let projects: [ScoutProject]?
    let message: String?
}

struct ScoutProjectsService {
    static func request(endpoint: ScoutEndpointProfile, apiKey: String?, name: String? = nil,
                        session: URLSession = .scoutAuthenticated) async -> ScoutProjectsResult {
        let base = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard let url = URL(string: base + "/api/projects"), url.host != nil else {
            return ScoutProjectsResult(projects: nil, message: "Malformed projects URL.")
        }
        var request = URLRequest(url: url)
        request.timeoutInterval = 5
        if let name = name {
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try? JSONEncoder().encode(["name": name])
        }
        do {
            try await ScoutRequestAuthentication.prepare(to: &request, endpoint: endpoint, apiKey: apiKey)
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                return ScoutProjectsResult(projects: nil, message: "Unexpected projects response.")
            }
            try ScoutRequestAuthentication.validate(response: http, endpoint: endpoint, request: request)
            guard (200..<300).contains(http.statusCode) else {
                return ScoutProjectsResult(projects: nil, message: "Projects request returned HTTP \(http.statusCode).")
            }
            if name != nil {
                guard let project = try? JSONDecoder().decode(ScoutProject.self, from: data) else {
                    return ScoutProjectsResult(projects: nil, message: "Could not read the created project.")
                }
                return ScoutProjectsResult(projects: [project], message: nil)
            }
            if let projects = try? JSONDecoder().decode([ScoutProject].self, from: data) {
                return ScoutProjectsResult(projects: projects, message: nil)
            }
            struct Envelope: Decodable { let projects: [ScoutProject] }
            let projects = try JSONDecoder().decode(Envelope.self, from: data).projects
            return ScoutProjectsResult(projects: projects, message: nil)
        } catch {
            return ScoutProjectsResult(projects: nil, message: "Projects request failed: \(error.localizedDescription)")
        }
    }
}
