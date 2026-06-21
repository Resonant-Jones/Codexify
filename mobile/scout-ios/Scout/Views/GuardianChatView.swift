import SwiftUI

struct GuardianChatView: View {
    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @State private var threads: [ScoutChatThreadSummary]?
    @State private var message: String?
    @State private var keychainError: String?
    @State private var isLoading = false

    private let keychainStore = ScoutKeychainStore()

    var body: some View {
        NavigationStack {
            List {
                if isLoading {
                    Section {
                        HStack {
                            ProgressView()
                                .padding(.trailing, 8)
                            Text("Loading threads…")
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                if let error = keychainError {
                    Section {
                        Label(error, systemImage: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                            .font(.caption)
                    }
                }

                if let msg = message, threads == nil {
                    Section {
                        Text(msg)
                            .foregroundStyle(.secondary)
                    }
                }

                if let threads = threads {
                    if threads.isEmpty {
                        Section {
                            Text("No threads found.")
                                .foregroundStyle(.secondary)
                        }
                    } else {
                        Section {
                            ForEach(threads, id: \.id) { thread in
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(thread.title?.isEmpty == false ? thread.title! : "Untitled")
                                        .font(.body)
                                        .fontWeight(.medium)
                                        .lineLimit(1)

                                    if let summary = thread.summary, !summary.isEmpty {
                                        Text(summary)
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                            .lineLimit(2)
                                    }

                                    if let updated = thread.updated_at {
                                        Text("Updated \(updated)")
                                            .font(.caption2)
                                            .foregroundStyle(.secondary)
                                    }
                                }
                                .padding(.vertical, 2)
                            }
                        }
                    }
                } else if !isLoading && keychainError == nil && storedProfileData.isEmpty {
                    Section {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("No endpoint configured.")
                            Text("Go to Settings to set up a Vault endpoint and API key.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                if !storedProfileData.isEmpty {
                    Section {
                        Button {
                            Task { await loadThreads() }
                        } label: {
                            HStack {
                                Spacer()
                                if isLoading {
                                    ProgressView()
                                        .padding(.trailing, 6)
                                }
                                Image(systemName: "arrow.clockwise")
                                Text("Refresh Threads")
                                Spacer()
                            }
                        }
                        .disabled(isLoading)
                    }
                }
            }
            .navigationTitle("Guardian")
            .onAppear {
                if !storedProfileData.isEmpty {
                    Task { await loadThreads() }
                }
            }
        }
    }

    private func loadThreads() async {
        guard !storedProfileData.isEmpty else { return }

        isLoading = true
        keychainError = nil
        message = nil

        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            message = "Could not load saved endpoint profile."
            isLoading = false
            return
        }

        let apiKey: String?
        do {
            apiKey = try keychainStore.loadAPIKey()
        } catch {
            keychainError = "Could not load API key from Keychain."
            apiKey = nil
        }

        let result = await ScoutGuardianThreadsProbe.probe(endpoint: profile, apiKey: apiKey)
        threads = result.threads
        if result.threads == nil {
            message = result.message
        }
        isLoading = false
    }
}

#Preview {
    GuardianChatView()
}
