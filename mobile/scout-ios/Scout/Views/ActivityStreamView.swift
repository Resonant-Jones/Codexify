import SwiftUI

struct ActivityStreamView: View {
    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()

    var body: some View {
        NavigationStack {
            List {
                if storedProfileData.isEmpty {
                    Section {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("No endpoint configured.")
                            Text("Go to Settings to set up a Vault endpoint.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                Section {
                    VStack(alignment: .leading, spacing: 4) {
                        Label("Activity Timeline", systemImage: "clock.arrow.circlepath")
                            .font(.body)
                            .fontWeight(.semibold)
                        Text("Activity will surface cross-thread task receipts, completion requests, and operator-visible lifecycle events as a unified timeline. This is a contract scaffold — no probes or backend routes are wired yet.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                Section("Planned Surfaces") {
                    VStack(alignment: .leading, spacing: 8) {
                        activityRow(
                            icon: "play.circle",
                            title: "Active Tasks",
                            description: "Running completions across threads. Requires cross-thread task aggregation route."
                        )
                        activityRow(
                            icon: "list.bullet.rectangle",
                            title: "Recent Task Receipts",
                            description: "Terminal task evidence from completed, failed, or cancelled Guardian requests. Per-thread route exists; cross-thread aggregation route needed."
                        )
                        activityRow(
                            icon: "antenna.radiowaves.left.and.right",
                            title: "SSE Observations",
                            description: "Live task event streams currently being observed. Connected to existing SSE task event endpoint."
                        )
                        activityRow(
                            icon: "sparkles",
                            title: "Completion Requests",
                            description: "Accepted but not yet terminal completion requests. Queue acceptance evidence already available."
                        )
                        activityRow(
                            icon: "bell.badge",
                            title: "Notifications",
                            description: "Future push/local notifications derived from task lifecycle events. Requires background refresh infrastructure."
                        )
                    }
                }

                Section {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Architecture Note")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundStyle(.secondary)
                        Text("Activity is a cross-thread observability surface. It observes task lifecycle evidence published by Vault without interpreting completion, readiness, or provider state. Scout remains an observer; Vault remains the authority.")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Activity")
        }
    }

    private func activityRow(icon: String, title: String, description: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .frame(width: 24)
                .foregroundStyle(.secondary)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.medium)
                Text(description)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }
}

#Preview {
    ActivityStreamView()
}
