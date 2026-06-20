import SwiftUI

struct GuardianChatView: View {
    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                Text("Guardian Chat")
                    .font(.largeTitle)
                    .fontWeight(.semibold)

                Text("Future work will send authenticated intent to Guardian while keeping Guardian as the operator and Vault as the long-term authority.")
                    .font(.body)
                    .foregroundStyle(.secondary)

                Spacer()
            }
            .padding()
            .navigationTitle("Guardian")
        }
    }
}

#Preview {
    GuardianChatView()
}
