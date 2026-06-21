import SwiftUI

struct ServerStatusView: View {
    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @State private var profile: ScoutEndpointProfile?
    @State private var result: ScoutEndpointConnectivityResult?
    @State private var isProbing = false
    @State private var keychainError: String?
    @State private var llmResult: ScoutLLMHealthResult?
    @State private var catalogResult: ScoutLLMCatalogResult?

    private let keychainStore = ScoutKeychainStore()

    var body: some View {
        NavigationStack {
            List {
                if let profile = profile {
                    Section("Endpoint") {
                        HStack {
                            Text("Name")
                                .foregroundStyle(.secondary)
                            Spacer()
                            Text(profile.name.isEmpty ? "Unnamed" : profile.name)
                        }
                        HStack {
                            Text("URL")
                                .foregroundStyle(.secondary)
                            Spacer()
                            Text(profile.baseURL)
                                .lineLimit(1)
                                .truncationMode(.middle)
                        }
                        HStack {
                            Text("Transport")
                                .foregroundStyle(.secondary)
                            Spacer()
                            Text(profile.transportType.title)
                        }
                    }
                }

                Section("Reachability") {
                    if isProbing {
                        HStack {
                            ProgressView()
                                .padding(.trailing, 8)
                            Text("Probing Vault…")
                                .foregroundStyle(.secondary)
                        }
                    } else if let result = result {
                        HStack(spacing: 8) {
                            Image(systemName: result.validationState == .reachable
                                  ? "checkmark.circle.fill" : "xmark.circle.fill")
                                .foregroundStyle(result.validationState == .reachable ? .green : .red)
                            Text(result.validationState.title)
                                .fontWeight(.semibold)
                        }

                        Text(result.message)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    } else if profile != nil {
                        Text("Tap Refresh to check server status.")
                            .foregroundStyle(.secondary)
                    } else {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("No endpoint configured.")
                            Text("Go to Settings to set up a Vault endpoint.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                if let result = result {
                    Section("Authentication") {
                        HStack {
                            Text(result.authenticationState.title)
                            Spacer()
                        }

                        if let error = keychainError {
                            Label(error, systemImage: "exclamationmark.triangle.fill")
                                .foregroundStyle(.orange)
                                .font(.caption)
                        }
                    }

                    Section("Probe Evidence") {
                        if let connectedAt = result.connectedAt {
                            HStack {
                                Text("Last connected")
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(connectedAt.formatted(date: .abbreviated, time: .shortened))
                            }
                            .font(.subheadline)
                        }

                        if let latency = result.latencyMilliseconds {
                            HStack {
                                Text("Latency")
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text("\(latency) ms")
                            }
                            .font(.subheadline)
                        }

                        if let snapshot = result.snapshot {
                            HStack {
                                Text("Service")
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(snapshot.service)
                            }
                            .font(.subheadline)

                            HStack {
                                Text("Health")
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(snapshot.status)
                            }
                            .font(.subheadline)

                            HStack {
                                Text("Timestamp")
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(snapshot.timestamp)
                                    .font(.caption)
                                    .lineLimit(1)
                                    .truncationMode(.middle)
                            }
                        }

                        if let llm = llmResult {
                            Divider()

                            if let httpStatus = llm.httpStatus {
                                HStack {
                                    Text("LLM HTTP Status")
                                        .foregroundStyle(.secondary)
                                    Spacer()
                                    Text("\(httpStatus)")
                                }
                                .font(.subheadline)
                            }

                            if let llmLatency = llm.latencyMilliseconds {
                                HStack {
                                    Text("LLM Probe Latency")
                                        .foregroundStyle(.secondary)
                                    Spacer()
                                    Text("\(llmLatency) ms")
                                }
                                .font(.subheadline)
                            }

                            if let snapshot = llm.snapshot {
                                if let status = snapshot.status {
                                    HStack {
                                        Text("LLM Health Status")
                                            .foregroundStyle(.secondary)
                                        Spacer()
                                        Text(status)
                                    }
                                    .font(.subheadline)
                                }

                                if let provider = snapshot.provider {
                                    HStack {
                                        Text("Provider")
                                            .foregroundStyle(.secondary)
                                        Spacer()
                                        Text(provider)
                                    }
                                    .font(.subheadline)
                                }

                                if let model = snapshot.model {
                                    HStack {
                                        Text("Model")
                                            .foregroundStyle(.secondary)
                                        Spacer()
                                        Text(model)
                                    }
                                    .font(.subheadline)
                                }
                            }

                            Text(llm.message)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }

                        if let catalog = catalogResult {
                            Divider()

                            Text("Catalog Evidence")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundStyle(.secondary)

                            if let httpStatus = catalog.httpStatus {
                                HStack {
                                    Text("Catalog HTTP Status")
                                        .foregroundStyle(.secondary)
                                    Spacer()
                                    Text("\(httpStatus)")
                                }
                                .font(.subheadline)
                            }

                            if let catLatency = catalog.latencyMilliseconds {
                                HStack {
                                    Text("Catalog Probe Latency")
                                        .foregroundStyle(.secondary)
                                    Spacer()
                                    Text("\(catLatency) ms")
                                }
                                .font(.subheadline)
                            }

                            if let snapshot = catalog.snapshot {
                                let modelCount = snapshot.providers?.reduce(0) { $0 + ($1.models?.count ?? 0) } ?? 0
                                HStack {
                                    Text("Catalog Model Count")
                                        .foregroundStyle(.secondary)
                                    Spacer()
                                    Text("\(modelCount)")
                                }
                                .font(.subheadline)

                                if let providers = snapshot.providers {
                                    let providerNames = providers.compactMap { $0.displayName ?? $0.id }.joined(separator: ", ")
                                    if !providerNames.isEmpty {
                                        HStack {
                                            Text("Catalog Providers")
                                                .foregroundStyle(.secondary)
                                            Spacer()
                                            Text(providerNames)
                                                .lineLimit(2)
                                                .truncationMode(.tail)
                                        }
                                        .font(.subheadline)
                                    }

                                    let modelNames = providers.flatMap { provider in
                                        provider.models?.compactMap { $0.displayName ?? $0.id } ?? []
                                    }.joined(separator: ", ")
                                    if !modelNames.isEmpty {
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text("Catalog Models")
                                                .foregroundStyle(.secondary)
                                            Text(modelNames)
                                                .font(.caption)
                                                .foregroundStyle(.secondary)
                                        }
                                    }
                                }
                            }

                            Text(catalog.message)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                } else if let error = keychainError {
                    Section("Authentication") {
                        Label(error, systemImage: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                            .font(.caption)
                    }
                }

                if profile != nil {
                    Section {
                        Button {
                            Task { await refresh() }
                        } label: {
                            HStack {
                                Spacer()
                                if isProbing {
                                    ProgressView()
                                        .padding(.trailing, 6)
                                }
                                Image(systemName: "arrow.clockwise")
                                Text("Refresh")
                                Spacer()
                            }
                        }
                        .disabled(isProbing)
                    }
                }
            }
            .navigationTitle("Server")
            .onAppear {
                loadProfile()
                if profile != nil {
                    Task { await refresh() }
                }
            }
        }
    }

    private func loadProfile() {
        guard !storedProfileData.isEmpty else {
            profile = nil
            return
        }
        profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData)
    }

    private func refresh() async {
        guard let profile = profile else { return }

        isProbing = true
        keychainError = nil
        result = nil
        llmResult = nil
        catalogResult = nil

        let apiKey: String?
        do {
            apiKey = try keychainStore.loadAPIKey()
        } catch {
            keychainError = "Could not load API key from Keychain."
            apiKey = nil
        }

        result = await ScoutEndpointConnectivityProbe.probe(endpoint: profile, apiKey: apiKey)
        llmResult = await ScoutLLMHealthProbe.probe(endpoint: profile, apiKey: apiKey)
        catalogResult = await ScoutLLMCatalogProbe.probe(endpoint: profile, apiKey: apiKey)
        isProbing = false
    }

}

#Preview {
    ServerStatusView()
}
