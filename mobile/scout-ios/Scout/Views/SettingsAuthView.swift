import SwiftUI

struct SettingsAuthView: View {
    @State private var draftProfile = ScoutEndpointProfile.emptyDraft
    @State private var validationErrors: [ScoutEndpointDraftValidationError] = []
    @State private var showValidationResults = false
    @State private var isProbing = false
    @State private var probeGeneration = 0
    @State private var connectionMessage: String?
    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @State private var saveMessage: String?
    @State private var loadError: String?
    @State private var apiKeyInput: String = ""
    @State private var isKeyStored: Bool = false
    @State private var keychainMessage: String?

    @StateObject private var accessSignIn = ScoutAccessSignIn()
    @StateObject private var accountSignIn = ScoutAccountSignIn()

    private let keychainStore = ScoutKeychainStore()

    var body: some View {
        NavigationStack {
            Form {
                Section("Endpoint Profile") {
                    TextField("Name", text: nameBinding)

                    TextField("Vault Base URL", text: baseURLBinding)
                        .keyboardType(.URL)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)

                    Picker("Transport", selection: transportBinding) {
                        ForEach(ScoutEndpointTransportType.allCases) { transport in
                            Text(transport.title).tag(transport)
                        }
                    }
                    Button("Use hosted Codexify") {
                        accessSignIn.cancel()
                        accountSignIn.cancel()
                        let saved = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData)
                        draftProfile = ScoutAccessOAuth.hostedProfile(preserving: saved ?? draftProfile)
                        persistDraft()
                    }
                }

                Section("Authentication Mode") {
                    Picker("Mode", selection: authenticationModeBinding) {
                        ForEach(ScoutEndpointAuthenticationMode.allCases) { mode in
                            Text(mode.title).tag(mode)
                                .disabled(mode == .remoteSession && !ScoutAccessOAuth.supportsAccountSignIn(draftProfile))
                        }
                    }
                    if draftProfile.authenticationMode == .remoteSession {
                        Text(ScoutAccessOAuth.supportsAccountSignIn(draftProfile)
                            ? "Authorize hosted ingress, then sign in to Guardian to obtain this connection's account session."
                            : "Scout cannot provision an account session for this personal endpoint yet. Select the explicitly supported local API key mode to connect; no authentication fallback occurs.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }

                if draftProfile.authenticationMode == .remoteSession {
                    Section("Guardian Account") {
                        Button("Sign in to Guardian") {
                            let profile = draftProfile
                            Task { await accountSignIn.signIn(profile: profile) }
                        }.disabled(accountSignIn.isWorking || accessSignIn.isWorking || !isSavedHostedProfile)
                        Button("Check account session") {
                            let profile = draftProfile
                            Task { await accountSignIn.check(profile: profile) }
                        }.disabled(accountSignIn.isWorking || accessSignIn.isWorking)
                        Button("Log out of Guardian") {
                            let profile = draftProfile
                            Task { await accountSignIn.logout(profile: profile) }
                        }.disabled(accountSignIn.isWorking || accessSignIn.isWorking)
                        if let message = accountSignIn.message { Text(message).font(.footnote) }
                    }
                    Section("Authentication Qualification") {
                        if let receipt = accountSignIn.qualification {
                            Text("Attempt " + receipt.publicID).font(.caption).textSelection(.enabled)
                            Text(receipt.correlationAvailable ? "Runtime correlation available" : "Runtime correlation unavailable")
                                .font(.footnote)
                            if let admission = receipt.hostedAdmission {
                                Text(admission.summary).font(.footnote)
                            }
                            ForEach(ScoutAuthenticationQualification.Stage.allCases) { stage in
                                VStack(alignment: .leading) {
                                    Text(stage.title)
                                    Text(receipt.result(for: stage).summary).font(.caption).foregroundStyle(.secondary)
                                }.accessibilityElement(children: .combine)
                            }
                            if let failed = receipt.firstFailedStage {
                                Text("First failed stage: " + failed.title).font(.footnote)
                            }
                            if let first = receipt.firstUnqualifiedStage {
                                Text("First unqualified stage: " + first.title).font(.footnote)
                            } else { Text("All nine stages qualified.").font(.footnote) }
                        } else {
                            Text("No sign-in attempt recorded for this connection.").font(.footnote)
                            ForEach(ScoutAuthenticationQualification.Stage.allCases) { stage in
                                VStack(alignment: .leading) {
                                    Text(stage.title)
                                    Text("Waiting · pending").font(.caption).foregroundStyle(.secondary)
                                }.accessibilityElement(children: .combine)
                            }
                        }
                    }
                    Section("Hosted Ingress") {
                        Button("Authorize hosted ingress") {
                            let profile = draftProfile
                            Task { await accessSignIn.signIn(profile: profile) }
                        }
                        .disabled(accessSignIn.isWorking || accountSignIn.isWorking || !isSavedHostedProfile)
                        Button("Check stored ingress") {
                            let profile = draftProfile
                            Task { await accessSignIn.checkStoredIngress(profile: profile) }
                        }
                        .disabled(accessSignIn.isWorking || accountSignIn.isWorking || !isSavedHostedProfile)
                        Button("Revoke hosted ingress") {
                            let profile = draftProfile
                            Task { await accessSignIn.revoke(profile: profile) }
                        }
                        .disabled(accessSignIn.isWorking || accountSignIn.isWorking || !isSavedHostedProfile)
                        if accessSignIn.isWorking { ProgressView("Waiting for sign-in…") }
                        if let message = accessSignIn.message {
                            Text(message).font(.footnote)
                        }
                        Text("Ingress admission and Guardian account authentication are separate. Personal nodes keep their own explicitly supported authentication mode.")
                            .font(.footnote).foregroundStyle(.secondary)
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
                        if draftProfile.authenticationMode == .localAPIKey,
                           let lastConnected = draftProfile.lastConnectedAt {
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
                        Button("Replace unreadable profile with a new draft", role: .destructive) {
                            storedProfileData = Data()
                            draftProfile = .emptyDraft
                            loadError = nil
                            resetCurrentConnectionEvidence()
                        }
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

                        let testedEndpoint = draftProfile
                        isKeyStored = draftProfile.authenticationMode == .localAPIKey && keychainStore.hasAPIKey(for: draftProfile)
        apiKeyInput = ""
        probeGeneration += 1
                        let testedGeneration = probeGeneration
                        isProbing = true
                        connectionMessage = nil
                        saveMessage = nil
                        draftProfile.validationState = .validating

                        Task {
                            var apiKey: String?
                            if testedEndpoint.authenticationMode == .localAPIKey {
                                do {
                                    apiKey = try keychainStore.loadAPIKey(for: testedEndpoint)
                                } catch {
                                    keychainMessage = "Could not load API key from Keychain. Testing without credentials."
                                }
                            }

                            let result = await ScoutEndpointConnectivityProbe.probe(endpoint: testedEndpoint, apiKey: apiKey)
                            guard probeGeneration == testedGeneration,
                                  draftProfile.id == testedEndpoint.id,
                                  draftProfile.name == testedEndpoint.name,
                                  draftProfile.baseURL == testedEndpoint.baseURL,
                                  draftProfile.transportType == testedEndpoint.transportType,
                                  draftProfile.authenticationMode == testedEndpoint.authenticationMode else {
                                return
                            }
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
                    .disabled(!draftProfile.isValidDraft || isProbing || loadError != nil)
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
                    .disabled(loadError != nil)
                }

                if draftProfile.authenticationMode == .localAPIKey {
                    Section("API Key") {
                        SecureField("Vault API Key", text: $apiKeyInput)
                            .disabled(isKeyStored && apiKeyInput.isEmpty)

                        if isKeyStored {
                            HStack {
                                Label("Stored in Keychain", systemImage: "lock.fill")
                                    .foregroundStyle(.green)
                                Spacer()
                                Button("Delete", role: .destructive) {
                                    try? keychainStore.deleteAPIKey(for: draftProfile)
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
                                        try keychainStore.saveAPIKey(trimmed, for: draftProfile)
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
                                    try keychainStore.saveAPIKey(trimmed, for: draftProfile)
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
                isKeyStored = draftProfile.authenticationMode == .localAPIKey && keychainStore.hasAPIKey(for: draftProfile)
                if isSavedHostedProfile { accessSignIn.restoreStatus(profile: draftProfile) }
                if draftProfile.authenticationMode == .remoteSession { accountSignIn.restoreStatus(profile: draftProfile) }
            }
        }
    }

    private var isSavedHostedProfile: Bool {
        guard (try? ScoutAccessOAuth.requireHosted(draftProfile)) != nil,
              let saved = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else { return false }
        return ScoutConnectionIdentity(endpoint: saved) == ScoutConnectionIdentity(endpoint: draftProfile)
    }

    private var nameBinding: Binding<String> {
        Binding(get: { draftProfile.name }, set: { value in
            guard value != draftProfile.name else { return }
            draftProfile.name = value
            resetCurrentConnectionEvidence()
        })
    }

    private var baseURLBinding: Binding<String> {
        Binding(get: { draftProfile.baseURL }, set: { value in
            guard value != draftProfile.baseURL else { return }
            draftProfile.baseURL = value
            resetCurrentConnectionEvidence()
        })
    }

    private var transportBinding: Binding<ScoutEndpointTransportType> {
        Binding(get: { draftProfile.transportType }, set: { value in
            guard value != draftProfile.transportType else { return }
            draftProfile.transportType = value
            resetCurrentConnectionEvidence()
        })
    }

    private var authenticationModeBinding: Binding<ScoutEndpointAuthenticationMode> {
        Binding(get: { draftProfile.authenticationMode }, set: { value in
            guard value != draftProfile.authenticationMode else { return }
            draftProfile.authenticationMode = value
            apiKeyInput = ""
            resetCurrentConnectionEvidence()
        })
    }

    private func resetCurrentConnectionEvidence() {
        accessSignIn.cancel()
        accountSignIn.cancel()
        isKeyStored = draftProfile.authenticationMode == .localAPIKey && keychainStore.hasAPIKey(for: draftProfile)
        apiKeyInput = ""
        probeGeneration += 1
        isProbing = false
        draftProfile.authenticationState = .unconfigured
        draftProfile.validationState = .unconfigured
        draftProfile.lastConnectedAt = nil
        connectionMessage = nil
        saveMessage = nil
        validationErrors = []
        showValidationResults = false
    }

    private func loadProfile() {
        guard !storedProfileData.isEmpty else { return }
        do {
            draftProfile = try JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData)
            loadError = nil
        } catch {
            loadError = "Could not load saved profile. Stored data was preserved; replace it explicitly to start a new draft."
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
