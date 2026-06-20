import SwiftUI

struct SettingsAuthView: View {
    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                Text("Settings")
                    .font(.largeTitle)
                    .fontWeight(.semibold)

                Text("Future work will store the Vault URL and credentials using iOS Keychain while keeping auth and secret management explicit.")
                    .font(.body)
                    .foregroundStyle(.secondary)

                Spacer()
            }
            .padding()
            .navigationTitle("Settings")
        }
    }
}

#Preview {
    SettingsAuthView()
}
