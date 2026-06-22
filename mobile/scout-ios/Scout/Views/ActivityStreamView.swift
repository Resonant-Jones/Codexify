import SwiftUI

private struct ActivityRow: Identifiable {
    let id: String
    let threadId: Int
    let threadTitle: String
    let taskId: String
    let state: String?
    let eventType: String?
    let reason: String?
}

struct ActivityStreamView: View {
    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @State private var rows: [ActivityRow]?
    @State private var statusMessage: String?
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
                            Text("Loading activity…")
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

                if let msg = statusMessage, rows == nil {
                    Section {
                        Text(msg)
                            .foregroundStyle(.secondary)
                    }
                }

                if let rows = rows {
                    if rows.isEmpty {
                        Section("Recent Task Receipts") {
                            Text("No task receipts across any thread.")
                                .foregroundStyle(.secondary)
                        }
                    } else {
                        Section("Recent Task Receipts") {
                            ForEach(rows) { row in
                                VStack(alignment: .leading, spacing: 2) {
                                    HStack {
                                        Text(row.threadTitle)
                                            .font(.caption)
                                            .fontWeight(.semibold)
                                            .foregroundStyle(.blue)
                                        Spacer()
                                        if let state = row.state {
                                            Text(state)
                                                .font(.caption2)
                                                .foregroundStyle(state == "terminal" ? .green : .secondary)
                                        }
                                    }
                                    HStack {
                                        Text(row.eventType ?? row.taskId)
                                            .font(.subheadline)
                                            .lineLimit(1)
                                        Spacer()
                                    }
                                    Text(row.taskId)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                        .lineLimit(1)
                                }
                                .padding(.vertical, 2)
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

                Section {
                    VStack(alignment: .leading, spacing: 4) {
                        Label("Future Surfaces", systemImage: "clock.arrow.circlepath")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundStyle(.secondary)
                        Text("Active Tasks, SSE Observations, Completion Requests, and Notifications require additional backend routes or infrastructure.")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }

                if !storedProfileData.isEmpty {
                    Section {
                        Button {
                            Task { await loadActivity() }
                        } label: {
                            HStack {
                                Spacer()
                                if isLoading {
                                    ProgressView()
                                        .padding(.trailing, 6)
                                }
                                Image(systemName: "arrow.clockwise")
                                Text("Refresh Activity")
                                Spacer()
                            }
                        }
                        .disabled(isLoading)
                    }
                }
            }
            .navigationTitle("Activity")
            .onAppear {
                if !storedProfileData.isEmpty {
                    Task { await loadActivity() }
                }
            }
        }
    }

    private func loadActivity() async {
        guard !storedProfileData.isEmpty else { return }

        isLoading = true
        keychainError = nil
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
            keychainError = "Could not load API key from Keychain."
            apiKey = nil
        }

        // Load threads
        let threadsResult = await ScoutGuardianThreadsProbe.probe(
            endpoint: profile, apiKey: apiKey
        )
        guard let threads = threadsResult.threads, !threads.isEmpty else {
            rows = []
            isLoading = false
            return
        }

        // Load task receipts for each thread
        var allRows: [ActivityRow] = []
        for thread in threads {
            guard let tid = thread.id else { continue }
            let title = thread.title?.isEmpty == false ? thread.title! : "Thread \(tid)"

            let tasksResult = await ScoutThreadTasksProbe.probe(
                endpoint: profile, threadId: tid, apiKey: apiKey
            )
            guard let receipts = tasksResult.tasks else { continue }

            for receipt in receipts {
                let rowId = "\(tid)-\(receipt.task_id ?? UUID().uuidString)"
                allRows.append(ActivityRow(
                    id: rowId,
                    threadId: tid,
                    threadTitle: title,
                    taskId: receipt.task_id ?? "unknown",
                    state: receipt.state,
                    eventType: receipt.event_type,
                    reason: receipt.reason
                ))
            }
        }

        rows = allRows
        isLoading = false
    }
}

#Preview {
    ActivityStreamView()
}
