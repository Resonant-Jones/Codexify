import SwiftUI

struct ArtifactsView: View {
    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @State private var documents: [ScoutDocumentDetail]?
    @State private var statusMessage: String?
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
                            Text("Loading documents…")
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                if let msg = statusMessage, documents == nil {
                    Section {
                        Text(msg)
                            .foregroundStyle(.secondary)
                    }
                }

                if let docs = documents {
                    if docs.isEmpty {
                        Section {
                            Text("No documents found.")
                                .foregroundStyle(.secondary)
                        }
                    } else {
                        Section("Global Documents") {
                            ForEach(docs, id: \.id) { doc in
                                NavigationLink(value: DocumentDetailNav(documentId: doc.id ?? "")) {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(doc.filename ?? doc.id ?? "Untitled")
                                            .font(.body)
                                            .lineLimit(1)
                                        HStack {
                                            if let mime = doc.mime_type {
                                                Text(mime)
                                                    .font(.caption)
                                                    .foregroundStyle(.secondary)
                                            }
                                            Spacer()
                                            if let size = doc.filesize {
                                                Text(formatFileSize(size))
                                                    .font(.caption2)
                                                    .foregroundStyle(.secondary)
                                            }
                                        }
                                    }
                                    .padding(.vertical, 2)
                                }
                            }
                        }
                    }
                } else if !isLoading && storedProfileData.isEmpty {
                    Section {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("No endpoint configured.")
                            Text("Go to Settings to set up a Vault endpoint.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                if !storedProfileData.isEmpty {
                    Section {
                        Button {
                            Task { await loadDocuments() }
                        } label: {
                            HStack {
                                Spacer()
                                if isLoading {
                                    ProgressView()
                                        .padding(.trailing, 6)
                                }
                                Image(systemName: "arrow.clockwise")
                                Text("Refresh")
                                Spacer()
                            }
                        }
                        .disabled(isLoading)
                    }
                }
            }
            .navigationTitle("Artifacts")
            .navigationDestination(for: DocumentDetailNav.self) { nav in
                DocumentDetailView(documentId: nav.documentId)
            }
            .onAppear {
                if !storedProfileData.isEmpty {
                    Task { await loadDocuments() }
                }
            }
        }
    }

    private func loadDocuments() async {
        guard !storedProfileData.isEmpty else { return }

        isLoading = true
        statusMessage = nil

        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            statusMessage = "Could not load saved endpoint profile."
            isLoading = false
            return
        }

        let apiKey: String?
        do {
            apiKey = try keychainStore.loadAPIKey()
        } catch {
            apiKey = nil
        }

        let result = await ScoutMediaDocumentsProbe.probe(
            endpoint: profile, apiKey: apiKey
        )
        documents = result.documents
        if result.documents == nil {
            statusMessage = result.message
        }
        isLoading = false
    }

    private func formatFileSize(_ bytes: Int) -> String {
        if bytes < 1024 { return "\(bytes) B" }
        if bytes < 1024 * 1024 { return String(format: "%.1f KB", Double(bytes) / 1024) }
        return String(format: "%.1f MB", Double(bytes) / (1024 * 1024))
    }
}

#Preview {
    ArtifactsView()
}
