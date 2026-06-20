import SwiftUI

struct SettingsAuthView: View {
    @State private var draftProfile = ScoutEndpointProfile.emptyDraft

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

                Section {
                    Text("Saving, Keychain storage, validation, and connection testing are future work.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Settings")
        }
    }
}

#Preview {
    SettingsAuthView()
}
