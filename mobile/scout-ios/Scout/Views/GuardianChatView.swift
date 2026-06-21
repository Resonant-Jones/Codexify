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
                                NavigationLink(value: thread.id) {
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
            .navigationDestination(for: Int.self) { threadId in
                ThreadMessagesView(threadId: threadId)
            }
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

// MARK: - Thread Messages Detail View

private struct ThreadMessagesView: View {
    let threadId: Int

    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @State private var messages: [ScoutChatMessageSummary]?
    @State private var statusMessage: String?
    @State private var keychainError: String?
    @State private var isLoading = false
    @State private var composeText = ""
    @State private var isSending = false
    @State private var sendMessage: String?
    @State private var isRequestingCompletion = false
    @State private var completionMessage: String?
    @State private var completionTaskId: String?

    private let keychainStore = ScoutKeychainStore()

    var body: some View {
        List {
            if isLoading {
                Section {
                    HStack {
                        ProgressView()
                            .padding(.trailing, 8)
                        Text("Loading messages…")
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

            if let msg = statusMessage, messages == nil {
                Section {
                    Text(msg)
                        .foregroundStyle(.secondary)
                }
            }

            if let messages = messages {
                if messages.isEmpty {
                    Section {
                        Text("No messages in this thread.")
                            .foregroundStyle(.secondary)
                    }
                } else {
                    Section {
                        ForEach(Array(messages.enumerated()), id: \.offset) { _, msg in
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text(roleLabel(msg.role))
                                        .font(.caption)
                                        .fontWeight(.semibold)
                                        .foregroundStyle(roleColor(msg.role))
                                    Spacer()
                                    if let created = msg.created_at {
                                        Text(created)
                                            .font(.caption2)
                                            .foregroundStyle(.secondary)
                                    }
                                }

                                if let content = msg.content, !content.isEmpty {
                                    Text(content)
                                        .font(.body)
                                        .lineLimit(10)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
            }

            Section {
                Button {
                    Task { await loadMessages() }
                } label: {
                    HStack {
                        Spacer()
                        if isLoading {
                            ProgressView()
                                .padding(.trailing, 6)
                        }
                        Image(systemName: "arrow.clockwise")
                        Text("Refresh Messages")
                        Spacer()
                    }
                }
                .disabled(isLoading)
            }

            if let sendMsg = sendMessage {
                Section {
                    Text(sendMsg)
                        .font(.caption)
                        .foregroundStyle(sendMsg == "Message sent." ? .green : .secondary)
                }
            }

            Section {
                Button {
                    completionMessage = nil
                    completionTaskId = nil
                    Task { await requestCompletion() }
                } label: {
                    HStack {
                        Spacer()
                        if isRequestingCompletion {
                            ProgressView()
                                .padding(.trailing, 6)
                        }
                        Image(systemName: "sparkles")
                        Text("Request Guardian Response")
                        Spacer()
                    }
                }
                .disabled(isRequestingCompletion)

                if let taskId = completionTaskId {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Task accepted: \(taskId)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text("Use Refresh Messages to check for the Guardian response.")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }

                if let msg = completionMessage {
                    Text(msg)
                        .font(.caption)
                        .foregroundStyle(msg == "Completion accepted by Vault." ? .green : .secondary)
                }
            }

            Section {
                HStack {
                    TextField("Type a message…", text: $composeText)
                        .disabled(isSending)

                    if isSending {
                        ProgressView()
                            .padding(.horizontal, 4)
                    }

                    Button("Send") {
                        let text = composeText
                        composeText = ""
                        sendMessage = nil
                        Task { await sendContent(text) }
                    }
                    .disabled(composeText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSending)
                }
            }
        }
        .navigationTitle("Thread \(threadId)")
        .onAppear {
            Task { await loadMessages() }
        }
    }

    private func requestCompletion() async {
        guard !storedProfileData.isEmpty else { return }

        isRequestingCompletion = true

        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            completionMessage = "Could not load saved endpoint profile."
            isRequestingCompletion = false
            return
        }

        let apiKey: String?
        do {
            apiKey = try keychainStore.loadAPIKey()
        } catch {
            apiKey = nil
        }

        let result = await ScoutGuardianCompleteThreadService.complete(
            endpoint: profile, threadId: threadId, apiKey: apiKey
        )
        completionMessage = result.message
        completionTaskId = result.taskId
        isRequestingCompletion = false
    }

    private func sendContent(_ text: String) async {
        guard !storedProfileData.isEmpty else { return }

        isSending = true

        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            sendMessage = "Could not load saved endpoint profile."
            isSending = false
            return
        }

        let apiKey: String?
        do {
            apiKey = try keychainStore.loadAPIKey()
        } catch {
            apiKey = nil
        }

        let result = await ScoutGuardianSendMessageService.send(
            endpoint: profile, threadId: threadId, content: text, apiKey: apiKey
        )
        sendMessage = result.message
        isSending = false

        if result.httpStatus != nil, (200..<300).contains(result.httpStatus!) {
            await loadMessages()
        }
    }

    private func loadMessages() async {
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

        let result = await ScoutGuardianThreadMessagesProbe.probe(
            endpoint: profile, threadId: threadId, apiKey: apiKey
        )
        messages = result.messages
        if result.messages == nil {
            statusMessage = result.message
        }
        isLoading = false
    }

    private func roleLabel(_ role: String?) -> String {
        switch role {
        case "user": return "You"
        case "assistant": return "Guardian"
        case "system": return "System"
        default: return role ?? "Unknown"
        }
    }

    private func roleColor(_ role: String?) -> Color {
        switch role {
        case "user": return .blue
        case "assistant": return .green
        case "system": return .orange
        default: return .secondary
        }
    }
}

#Preview {
    GuardianChatView()
}
