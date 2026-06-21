import Foundation

struct ScoutLLMCatalogResult {
    let httpStatus: Int?
    let latencyMilliseconds: Int?
    let snapshot: ScoutLLMCatalogSnapshot?
    let message: String
}

struct ScoutLLMCatalogProbe {

    static func probe(
        endpoint: ScoutEndpointProfile,
        apiKey: String? = nil,
        session: URLSession = .shared
    ) async -> ScoutLLMCatalogResult {
        var urlString = endpoint.baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !urlString.isEmpty else {
            return ScoutLLMCatalogResult(
                httpStatus: nil,
                latencyMilliseconds: nil,
                snapshot: nil,
                message: "Base URL is empty."
            )
        }

        if urlString.hasSuffix("/") {
            urlString = String(urlString.dropLast())
        }
        urlString += "/api/llm/catalog"

        guard let url = URL(string: urlString),
              let scheme = url.scheme, !scheme.isEmpty,
              url.host != nil else {
            return ScoutLLMCatalogResult(
                httpStatus: nil,
                latencyMilliseconds: nil,
                snapshot: nil,
                message: "Malformed catalog URL."
            )
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 5

        let hasApiKey = apiKey.map { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty } ?? false
        if let key = apiKey, hasApiKey {
            request.setValue(key, forHTTPHeaderField: "X-API-Key")
        }

        let requestStart = Date()

        do {
            let (data, response) = try await session.data(for: request)
            let latencyMs = Int(requestStart.distance(to: Date()) * 1000)

            guard let httpResponse = response as? HTTPURLResponse else {
                return ScoutLLMCatalogResult(
                    httpStatus: nil,
                    latencyMilliseconds: latencyMs,
                    snapshot: nil,
                    message: "Unexpected response type from server."
                )
            }

            let statusCode = httpResponse.statusCode
            let snapshot = try? JSONDecoder().decode(ScoutLLMCatalogSnapshot.self, from: data)

            if (200..<300).contains(statusCode) {
                return ScoutLLMCatalogResult(
                    httpStatus: statusCode,
                    latencyMilliseconds: latencyMs,
                    snapshot: snapshot,
                    message: "Catalog retrieved (HTTP \(statusCode))."
                )
            } else {
                return ScoutLLMCatalogResult(
                    httpStatus: statusCode,
                    latencyMilliseconds: latencyMs,
                    snapshot: nil,
                    message: "Catalog request returned HTTP \(statusCode)."
                )
            }
        } catch let error as URLError where error.code == .timedOut {
            return ScoutLLMCatalogResult(
                httpStatus: nil,
                latencyMilliseconds: nil,
                snapshot: nil,
                message: "Catalog probe timed out after 5 seconds."
            )
        } catch {
            return ScoutLLMCatalogResult(
                httpStatus: nil,
                latencyMilliseconds: nil,
                snapshot: nil,
                message: "Catalog probe failed: \(error.localizedDescription)"
            )
        }
    }
}
