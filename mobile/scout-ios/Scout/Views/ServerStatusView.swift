import SwiftUI

struct ServerStatusView: View {
    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @State private var profile: ScoutEndpointProfile?
    @State private var result: ScoutEndpointConnectivityResult?
    @State private var isProbing = false
    @State private var keychainError: String?

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

                Section("Status") {
                    if isProbing {
                        HStack {
                            ProgressView()
                                .padding(.trailing, 8)
                            Text("Probing Vault…")
                                .foregroundStyle(.secondary)
                        }
                    } else if let result = result {
                        statusContent(for: result)
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

                    if let error = keychainError {
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

        let apiKey: String?
        do {
            apiKey = try keychainStore.loadAPIKey()
        } catch {
            keychainError = "Could not load API key from Keychain."
            apiKey = nil
        }

        result = await ScoutEndpointConnectivityProbe.probe(endpoint: profile, apiKey: apiKey)
        isProbing = false
    }

    @ViewBuilder
    private func statusContent(for result: ScoutEndpointConnectivityResult) -> some View {
        let isReachable = result.validationState == .reachable

        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: isReachable ? "checkmark.circle.fill" : "xmark.circle.fill")
                    .foregroundStyle(isReachable ? .green : .red)
                Text(result.validationState.title)
                    .fontWeight(.semibold)
            }

            HStack {
                Text("Authentication")
                    .foregroundStyle(.secondary)
                Spacer()
                Text(result.authenticationState.title)
            }
            .font(.subheadline)

            if let connectedAt = result.connectedAt {
                HStack {
                    Text("Last connected")
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(connectedAt.formatted(date: .abbreviated, time: .shortened))
                }
                .font(.subheadline)
            }

            Text(result.message)
                .font(.caption)
                .foregroundStyle(.secondary)
                .padding(.top, 4)
        }
    }
}

#Preview {
    ServerStatusView()
}
