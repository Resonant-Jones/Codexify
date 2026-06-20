import SwiftUI

struct SettingsAuthView: View {
    @State private var draftProfile = ScoutEndpointProfile.emptyDraft
    @State private var validationErrors: [ScoutEndpointDraftValidationError] = []
    @State private var showValidationResults = false
    @State private var isProbing = false
    @State private var connectionMessage: String?
    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @State private var saveMessage: String?
    @State private var loadError: String?
    @State private var apiKeyInput: String = ""
    @State private var isKeyStored: Bool = false
    @State private var keychainMessage: String?

    private let keychainStore = ScoutKeychainStore()

    var body: some View {
        NavigationStack {
            Form {
                Section("Endpoint Profile") {
                    TextField("Name", text: $draftProfile.name)

                    TextField("Vault Base URL", text: $draftProfile.baseURL)
                        .keyboardType(.URL)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)

                    Picker("Transport", selection: $draftProfile.transportType) {
                        ForEach(ScoutEndpointTransportType.allCases) { transport in
                            Text(transport.title).tag(transport)
                        }
                    }
                }

                Section("Status") {
                    HStack {
                        Text("Authentication")
                        Spacer()
                        Text(draftProfile.authenticationState.title)
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("Validation")
                        Spacer()
                        Text(draftProfile.validationState.title)
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("Last Connected")
                        Spacer()
                        if let lastConnected = draftProfile.lastConnectedAt {
                            Text(lastConnected, style: .date)
                                .foregroundStyle(.secondary)
                        } else {
                            Text("Never")
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                if let error = loadError {
                    Section {
                        Label(error, systemImage: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                    }
                }

                Section {
                    Button("Validate Draft") {
                        let errors = draftProfile.draftValidationErrors
                        validationErrors = errors
                        showValidationResults = true
                        draftProfile.validateDraft()
                    }
                }

                Section {
                    Button("Test Connection") {
                        let errors = draftProfile.draftValidationErrors
                        if !errors.isEmpty {
                            validationErrors = errors
                            showValidationResults = true
                            return
                        }

                        isProbing = true
                        connectionMessage = nil
                        saveMessage = nil
                        draftProfile.validationState = .validating

                        Task {
                            let apiKey: String?
                            do {
                                apiKey = try keychainStore.loadAPIKey()
                            } catch {
                                keychainMessage = "Could not load API key from Keychain. Testing without credentials."
                                apiKey = nil
                            }

                            let result = await ScoutEndpointConnectivityProbe.probe(endpoint: draftProfile, apiKey: apiKey)
                            draftProfile.validationState = result.validationState
                            draftProfile.authenticationState = result.authenticationState
                            if let connectedAt = result.connectedAt {
                                draftProfile.lastConnectedAt = connectedAt
                            }
                            connectionMessage = result.message
                            isProbing = false

                            if result.validationState == .reachable {
                                autoSave()
                            }
                        }
                    }
                    .disabled(!draftProfile.isValidDraft || isProbing)
                }

                Section {
                    Button("Save Profile") {
                        let errors = draftProfile.draftValidationErrors
                        if !errors.isEmpty {
                            validationErrors = errors
                            showValidationResults = true
                            saveMessage = nil
                            return
                        }
                        persistDraft()
                    }
                }

                Section("API Key") {
                    SecureField("Vault API Key", text: $apiKeyInput)
                        .disabled(isKeyStored && apiKeyInput.isEmpty)

                    if isKeyStored {
                        HStack {
                            Label("Stored in Keychain", systemImage: "lock.fill")
                                .foregroundStyle(.green)
                            Spacer()
                            Button("Delete", role: .destructive) {
                                try? keychainStore.deleteAPIKey()
                                isKeyStored = false
                                apiKeyInput = ""
                                keychainMessage = "API key removed from Keychain."
                            }
                        }

                        if !apiKeyInput.isEmpty {
                            Button("Update") {
                                let trimmed = apiKeyInput.trimmingCharacters(in: .whitespacesAndNewlines)
                                guard !trimmed.isEmpty else { return }
                                do {
                                    try keychainStore.saveAPIKey(trimmed)
                                    apiKeyInput = ""
                                    keychainMessage = "API key updated in Keychain."
                                } catch {
                                    keychainMessage = "Failed to update API key."
                                }
                            }
                        }
                    } else {
                        Button("Save to Keychain") {
                            let trimmed = apiKeyInput.trimmingCharacters(in: .whitespacesAndNewlines)
                            guard !trimmed.isEmpty else { return }
                            do {
                                try keychainStore.saveAPIKey(trimmed)
                                isKeyStored = true
                                apiKeyInput = ""
                                keychainMessage = "API key saved to Keychain."
                            } catch {
                                keychainMessage = "Failed to save API key."
                            }
                        }
                        .disabled(apiKeyInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    }

                    if let msg = keychainMessage {
                        Label(msg, systemImage: msg.contains("Failed") ? "xmark.circle.fill" : "checkmark.circle.fill")
                            .foregroundStyle(msg.contains("Failed") ? .red : .green)
                            .font(.caption)
                    }

                    Text("The API key is stored in the iOS Keychain and never written to UserDefaults or included in unencrypted backups.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                if isProbing {
                    Section {
                        HStack {
                            ProgressView()
                                .padding(.trailing, 8)
                            Text("Testing connection…")
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                if let message = connectionMessage {
                    Section("Connection Result") {
                        Label(message, systemImage: draftProfile.validationState == .reachable ? "checkmark.circle.fill" : "xmark.circle.fill")
                            .foregroundStyle(draftProfile.validationState == .reachable ? .green : .red)
                    }
                }

                if let message = saveMessage {
                    Section {
                        Label(message, systemImage: "square.and.arrow.down.fill")
                            .foregroundStyle(.green)
                    }
                }

                if showValidationResults {
                    Section("Validation Results") {
                        if validationErrors.isEmpty {
                            Label("Draft looks valid — ready for connection testing.", systemImage: "checkmark.circle.fill")
                                .foregroundStyle(.green)
                        } else {
                            ForEach(validationErrors) { error in
                                Label(error.title, systemImage: "xmark.circle.fill")
                                    .foregroundStyle(.red)
                            }
                        }
                    }
                }

                Section {
                    Text("Endpoint configuration is stored in UserDefaults. The API key is stored in the iOS Keychain.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Settings")
            .onAppear {
                loadProfile()
                isKeyStored = keychainStore.hasAPIKey()
            }
        }
    }

    private func loadProfile() {
        guard !storedProfileData.isEmpty else { return }
        do {
            draftProfile = try JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData)
            loadError = nil
        } catch {
            draftProfile = .emptyDraft
            loadError = "Could not load saved profile. Starting with a blank configuration."
        }
    }

    private func persistDraft() {
        do {
            storedProfileData = try JSONEncoder().encode(draftProfile)
            saveMessage = "Profile saved."
            loadError = nil
        } catch {
            saveMessage = "Failed to save profile."
        }
    }

    private func autoSave() {
        if let data = try? JSONEncoder().encode(draftProfile) {
            storedProfileData = data
        }
    }
}

#Preview {
    SettingsAuthView()
}
