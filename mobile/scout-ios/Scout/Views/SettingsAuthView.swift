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
                            let result = await ScoutEndpointConnectivityProbe.probe(endpoint: draftProfile)
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
                    Text("Only non-secret endpoint configuration is stored locally. Credential and API key storage belongs to a future Keychain slice.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Settings")
            .onAppear {
                loadProfile()
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
