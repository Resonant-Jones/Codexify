import SwiftUI

struct TaskNav: Hashable {
    let taskId: String
    let threadId: Int
}

struct DocumentDetailNav: Hashable {
    let documentId: String
}

struct ThreadNav: Hashable {
    let id: Int
    let title: String?
}

struct GuardianChatView: View {
    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @State private var threads: [ScoutChatThreadSummary]?
    @State private var message: String?
    @State private var keychainError: String?
    @State private var isLoading = false
    @State private var showNewThread = false
    @State private var newThreadTitle = ""
    @State private var isCreating = false
    @State private var createError: String?

    private let keychainStore = ScoutKeychainStore()

    var body: some View {
        NavigationStack(path: $navigationPath) {
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
                            VStack(alignment: .leading, spacing: 12) {
                                Label("No threads yet", systemImage: "tray")
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                                Text("Create your first thread to start a conversation with Guardian.")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Button {
                                    showNewThread = true
                                } label: {
                                    Label("New Thread", systemImage: "plus")
                                }
                            }
                            .padding(.vertical, 8)
                        }
                    } else {
                        Section {
                            ForEach(threads, id: \.id) { thread in
                                NavigationLink(value: ThreadNav(id: thread.id ?? 0, title: thread.title)) {
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
                            showNewThread = true
                        } label: {
                            HStack {
                                Spacer()
                                Image(systemName: "plus")
                                Text("New Thread")
                                Spacer()
                            }
                        }
                        .disabled(isLoading)

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
            .navigationDestination(for: ThreadNav.self) { nav in
                ThreadMessagesView(threadId: nav.id, threadTitle: nav.title)
            }
            .navigationDestination(for: TaskNav.self) { nav in
                TaskEventsView(taskId: nav.taskId, threadId: nav.threadId)
            }
            .navigationDestination(for: DocumentDetailNav.self) { nav in
                DocumentDetailView(documentId: nav.documentId)
            }
            .sheet(isPresented: $showNewThread) {
                NavigationStack {
                    Form {
                        Section {
                            TextField("Thread title", text: $newThreadTitle)
                        }

                        if let error = createError {
                            Section {
                                Text(error)
                                    .foregroundStyle(.red)
                                    .font(.caption)
                            }
                        }

                        Section {
                            Button {
                                Task { await createThread() }
                            } label: {
                                HStack {
                                    Spacer()
                                    if isCreating {
                                        ProgressView()
                                            .padding(.trailing, 6)
                                    }
                                    Text("Create")
                                    Spacer()
                                }
                            }
                            .disabled(newThreadTitle.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isCreating)

                            Button("Cancel", role: .cancel) {
                                showNewThread = false
                                newThreadTitle = ""
                                createError = nil
                            }
                        }
                    }
                    .navigationTitle("New Thread")
                    .navigationBarTitleDisplayMode(.inline)
                }
            }
            .onAppear {
                if !storedProfileData.isEmpty {
                    Task { await loadThreads() }
                }
            }
            .onReceive(NotificationCenter.default.publisher(for: ScoutThreadRenamedNotification)) { _ in
                Task { await loadThreads() }
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

    private func createThread() async {
        let trimmed = newThreadTitle.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        isCreating = true
        createError = nil

        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            createError = "Could not load saved endpoint profile."
            isCreating = false
            return
        }

        let apiKey: String?
        do {
            apiKey = try keychainStore.loadAPIKey()
        } catch {
            apiKey = nil
        }

        let result = await ScoutCreateThreadProbe.create(
            endpoint: profile, title: trimmed, apiKey: apiKey
        )

        if result.httpStatus != nil, (200..<300).contains(result.httpStatus!) {
            showNewThread = false
            newThreadTitle = ""
            createError = nil
            await loadThreads()
            if let tid = result.threadId {
                navigationPath.append(ThreadNav(id: tid, title: trimmed))
            }
        } else {
            createError = result.message
        }
        isCreating = false
    }
}

// MARK: - Thread Messages Detail View

private struct ThreadMessagesView: View {
    let threadId: Int
    let threadTitle: String?

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
    @State private var documents: [ScoutThreadDocumentSummary]?
    @State private var docMessage: String?
    @State private var isLoadingDocs = false
    @State private var ragResult: ScoutRAGTraceResult?
    @State private var ragMessage: String?
    @State private var isLoadingRAG = false
    @State private var taskReceipts: [ScoutTaskReceiptSummary]?
    @State private var tasksMessage: String?
    @State private var isLoadingTasks = false
    @State private var selectedTab = 0

    private let keychainStore = ScoutKeychainStore()

    var body: some View {
        VStack(spacing: 0) {
            Picker("View", selection: $selectedTab) {
                Text("Conversation").tag(0)
                Text("Inspector").tag(1)
            }
            .pickerStyle(.segmented)
            .padding(.horizontal)
            .padding(.vertical, 8)

            if selectedTab == 0 {
                conversationList
            } else {
                inspectorList
            }
        }
        .navigationTitle(displayedTitle?.isEmpty == false ? displayedTitle! : "Thread \(threadId)")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    renameTitle = displayedTitle ?? ""
                    renameError = nil
                    showRename = true
                } label: {
                    Image(systemName: "pencil")
                }
            }
        }
        .onAppear {
            if displayedTitle == nil {
                displayedTitle = threadTitle
            }
            Task { await loadMessages() }
        }
        .sheet(isPresented: $showRename) {
            NavigationStack {
                Form {
                    Section {
                        TextField("Thread title", text: $renameTitle)
                    }

                    if let error = renameError {
                        Section {
                            Text(error)
                                .foregroundStyle(.red)
                                .font(.caption)
                        }
                    }

                    Section {
                        Button {
                            Task { await doRename() }
                        } label: {
                            HStack {
                                Spacer()
                                if isRenaming {
                                    ProgressView()
                                        .padding(.trailing, 6)
                                }
                                Text("Save")
                                Spacer()
                            }
                        }
                        .disabled(renameTitle.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isRenaming)

                        Button("Cancel", role: .cancel) {
                            showRename = false
                        }
                    }
                }
                .navigationTitle("Rename Thread")
                .navigationBarTitleDisplayMode(.inline)
            }
        }
    }

    private var conversationList: some View {
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
                        VStack(alignment: .leading, spacing: 8) {
                            Label("Thread ready", systemImage: "checkmark.circle")
                                .font(.subheadline)
                                .fontWeight(.medium)
                                .foregroundStyle(.green)
                            Text("Send the first message below to start the conversation. No completion has been requested yet.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .padding(.vertical, 4)
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
                    NavigationLink(value: TaskNav(taskId: taskId, threadId: threadId)) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Task accepted: \(taskId)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text("View live task status →")
                                .font(.caption2)
                                .foregroundStyle(.blue)
                        }
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
    }

    private var inspectorList: some View {
        List {
            // Thread Documents section
            if isLoadingDocs {
                Section {
                    HStack {
                        ProgressView()
                            .padding(.trailing, 8)
                        Text("Loading documents…")
                            .foregroundStyle(.secondary)
                    }
                }
            }

            if let msg = docMessage {
                Section {
                    Text(msg)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            if let docs = documents, !docs.isEmpty {
                Section("Thread Documents") {
                    ForEach(docs, id: \.id) { doc in
                        NavigationLink(value: DocumentDetailNav(documentId: doc.id ?? "")) {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(doc.title ?? doc.id ?? "Untitled")
                                    .font(.body)
                                    .lineLimit(1)
                                HStack {
                                    if let relation = doc.relation {
                                        Text(relation)
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                    if let created = doc.created_at {
                                        Text(created)
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

            Section {
                Button {
                    Task { await loadDocuments() }
                } label: {
                    HStack {
                        Spacer()
                        if isLoadingDocs {
                            ProgressView()
                                .padding(.trailing, 6)
                        }
                        Image(systemName: "doc.on.doc")
                        Text("Refresh Documents")
                        Spacer()
                    }
                }
                .disabled(isLoadingDocs)
            }

            // Retrieval Evidence section
            Section("Retrieval Evidence") {
                if isLoadingRAG {
                    HStack {
                        ProgressView()
                            .padding(.trailing, 8)
                        Text("Loading trace…")
                            .foregroundStyle(.secondary)
                    }
                } else if let result = ragResult {
                    if let snapshot = result.snapshot {
                        if let available = snapshot.traceAvailable {
                            HStack {
                                Text("Trace")
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(available ? "Available" : "Unavailable")
                                    .foregroundStyle(available ? .green : .secondary)
                            }
                        }

                        if let reason = snapshot.traceUnavailableReason {
                            HStack {
                                Text("Reason")
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(reason)
                                    .font(.caption)
                                    .lineLimit(2)
                            }
                        }

                        if let count = snapshot.documentCount {
                            HStack {
                                Text("Documents retrieved")
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text("\(count)")
                            }
                        }

                        if let count = snapshot.graphCount {
                            HStack {
                                Text("Graph entries")
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text("\(count)")
                            }
                        }

                        if let latency = result.latencyMilliseconds {
                            HStack {
                                Text("Latency")
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text("\(latency) ms")
                            }
                        }

                        if let policy = snapshot.retrievalPolicy {
                            ForEach(policy.keys.sorted(), id: \.self) { key in
                                HStack {
                                    Text(key)
                                        .foregroundStyle(.secondary)
                                        .font(.caption)
                                    Spacer()
                                    Text(stringValue(policy[key]))
                                        .font(.caption)
                                        .lineLimit(1)
                                }
                            }
                        }

                        if let model = snapshot.modelSelection {
                            ForEach(model.keys.sorted(), id: \.self) { key in
                                HStack {
                                    Text(key)
                                        .foregroundStyle(.secondary)
                                        .font(.caption)
                                    Spacer()
                                    Text(stringValue(model[key]))
                                        .font(.caption)
                                        .lineLimit(1)
                                }
                            }
                        }

                        Text(result.message)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    } else {
                        Text(result.message)
                            .foregroundStyle(.secondary)
                    }
                } else if let msg = ragMessage {
                    Text(msg)
                        .foregroundStyle(.secondary)
                } else {
                    Text("Tap Refresh Trace to load retrieval evidence.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Section {
                Button {
                    Task { await loadRAGTrace() }
                } label: {
                    HStack {
                        Spacer()
                        if isLoadingRAG {
                            ProgressView()
                                .padding(.trailing, 6)
                        }
                        Image(systemName: "magnifyingglass")
                        Text("Refresh Trace")
                        Spacer()
                    }
                }
                .disabled(isLoadingRAG)
            }

            // Task Receipts section
            Section("Task Receipts") {
                if isLoadingTasks {
                    HStack {
                        ProgressView()
                            .padding(.trailing, 8)
                        Text("Loading tasks…")
                            .foregroundStyle(.secondary)
                    }
                } else if let receipts = taskReceipts {
                    if receipts.isEmpty {
                        Text("No task receipts for this thread.")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(Array(receipts.enumerated()), id: \.offset) { _, receipt in
                            VStack(alignment: .leading, spacing: 2) {
                                HStack {
                                    Text(receipt.event_type ?? receipt.task_id ?? "Unknown")
                                        .font(.caption)
                                        .fontWeight(.medium)
                                    Spacer()
                                    if let state = receipt.state {
                                        Text(state)
                                            .font(.caption2)
                                            .foregroundStyle(state == "terminal" ? .green : .secondary)
                                    }
                                }
                                if let taskId = receipt.task_id {
                                    Text(taskId)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                        .lineLimit(1)
                                }
                            }
                            .padding(.vertical, 1)
                        }
                    }
                } else if let msg = tasksMessage {
                    Text(msg)
                        .foregroundStyle(.secondary)
                } else {
                    Text("Tap Refresh Tasks to load receipts.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Section {
                Button {
                    Task { await loadTasks() }
                } label: {
                    HStack {
                        Spacer()
                        if isLoadingTasks {
                            ProgressView()
                                .padding(.trailing, 6)
                        }
                        Image(systemName: "list.bullet.clipboard")
                        Text("Refresh Tasks")
                        Spacer()
                    }
                }
                .disabled(isLoadingTasks)
            }
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

    private func doRename() async {
        let trimmed = renameTitle.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        isRenaming = true
        renameError = nil

        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            renameError = "Could not load saved endpoint profile."
            isRenaming = false
            return
        }

        let apiKey: String?
        do {
            apiKey = try keychainStore.loadAPIKey()
        } catch {
            apiKey = nil
        }

        let result = await ScoutRenameThreadProbe.rename(
            endpoint: profile, threadId: threadId, title: trimmed, apiKey: apiKey
        )

        if result.httpStatus != nil, (200..<300).contains(result.httpStatus!) {
            displayedTitle = trimmed
            showRename = false
            NotificationCenter.default.post(name: ScoutThreadRenamedNotification, object: nil)
        } else {
            renameError = result.message
        }
        isRenaming = false
    }

    private func loadDocuments() async {
        guard !storedProfileData.isEmpty else { return }

        isLoadingDocs = true
        docMessage = nil

        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            docMessage = "Could not load saved endpoint profile."
            isLoadingDocs = false
            return
        }

        let apiKey: String?
        do {
            apiKey = try keychainStore.loadAPIKey()
        } catch {
            apiKey = nil
        }

        let result = await ScoutThreadDocumentsProbe.probe(
            endpoint: profile, threadId: threadId, apiKey: apiKey
        )
        documents = result.documents
        if result.documents == nil {
            docMessage = result.message
        }
        isLoadingDocs = false
    }

    private func loadRAGTrace() async {
        guard !storedProfileData.isEmpty else { return }

        isLoadingRAG = true
        ragMessage = nil

        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            ragMessage = "Could not load saved endpoint profile."
            isLoadingRAG = false
            return
        }

        let apiKey: String?
        do {
            apiKey = try keychainStore.loadAPIKey()
        } catch {
            apiKey = nil
        }

        ragResult = await ScoutRAGTraceProbe.probe(
            endpoint: profile, threadId: threadId, apiKey: apiKey
        )
        isLoadingRAG = false
    }

    private func loadTasks() async {
        guard !storedProfileData.isEmpty else { return }

        isLoadingTasks = true
        tasksMessage = nil

        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            tasksMessage = "Could not load saved endpoint profile."
            isLoadingTasks = false
            return
        }

        let apiKey: String?
        do {
            apiKey = try keychainStore.loadAPIKey()
        } catch {
            apiKey = nil
        }

        let result = await ScoutThreadTasksProbe.probe(
            endpoint: profile, threadId: threadId, apiKey: apiKey
        )
        taskReceipts = result.tasks
        if result.tasks == nil {
            tasksMessage = result.message
        }
        isLoadingTasks = false
    }

    private func stringValue(_ value: Any?) -> String {
        guard let value = value else { return "—" }
        if let str = value as? String { return str }
        if let num = value as? NSNumber { return num.stringValue }
        if let bool = value as? Bool { return bool ? "true" : "false" }
        return String(describing: value)
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

// MARK: - Task Events Live View

private struct TaskEventsView: View {
    let taskId: String
    let threadId: Int

    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @State private var events: [ScoutTaskEvent] = []
    @State private var statusMessage: String?
    @State private var isConnected = false
    @State private var streamError: String?

    private let keychainStore = ScoutKeychainStore()

    var body: some View {
        List {
            Section {
                HStack {
                    Text("Task")
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(taskId)
                        .font(.caption)
                        .lineLimit(1)
                        .truncationMode(.middle)
                }

                HStack {
                    Text("Status")
                        .foregroundStyle(.secondary)
                    Spacer()
                    if streamError != nil {
                        Label("Error", systemImage: "xmark.circle.fill")
                            .foregroundStyle(.red)
                            .font(.caption)
                    } else if isConnected {
                        Label("Connected", systemImage: "circle.fill")
                            .foregroundStyle(.green)
                            .font(.caption)
                    } else {
                        Label("Connecting…", systemImage: "circle")
                            .foregroundStyle(.secondary)
                            .font(.caption)
                    }
                }
            }

            if let error = streamError {
                Section {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                }
            }

            if let msg = statusMessage {
                Section {
                    Text(msg)
                        .foregroundStyle(.secondary)
                }
            }

            if !events.isEmpty {
                Section("Events") {
                    ForEach(Array(events.enumerated()), id: \.offset) { _, event in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(event.eventType ?? "task.event")
                                    .font(.caption)
                                    .fontWeight(.semibold)
                                    .foregroundStyle(event.isTerminal ? .green : .blue)
                                Spacer()
                                if let id = event.eventId {
                                    Text(id)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                        .lineLimit(1)
                                }
                            }

                            if let data = event.parsedData {
                                Text(String(describing: data))
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(3)
                            } else if let raw = event.data {
                                Text(raw)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(3)
                            }
                        }
                        .padding(.vertical, 2)
                    }
                }
            }
        }
        .navigationTitle("Task Status")
        .onAppear {
            Task { await connect() }
        }
        .onDisappear {
            isConnected = false
        }
    }

    private func handleTerminalEvent(_ eventType: String) async {
        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            return
        }

        let apiKey: String?
        do {
            apiKey = try keychainStore.loadAPIKey()
        } catch {
            apiKey = nil
        }

        switch eventType {
        case "task.completed":
            _ = await ScoutGuardianThreadMessagesProbe.probe(
                endpoint: profile, threadId: threadId, apiKey: apiKey
            )
            statusMessage = "Task completed. Messages refreshed."
        case "task.failed":
            statusMessage = "Task failed. No assistant message was synthesized."
        case "task.cancelled":
            statusMessage = "Task cancelled. No assistant message was synthesized."
        default:
            break
        }
    }

    private func connect() async {
        guard !storedProfileData.isEmpty else {
            streamError = "No endpoint configured."
            return
        }

        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            streamError = "Could not load saved endpoint profile."
            return
        }

        let apiKey: String?
        do {
            apiKey = try keychainStore.loadAPIKey()
        } catch {
            apiKey = nil
        }

        isConnected = true
        streamError = nil

        do {
            let stream = ScoutTaskEventStreamService.streamEvents(
                endpoint: profile, taskId: taskId, apiKey: apiKey
            )
            for try await event in stream {
                events.append(event)
                if event.isTerminal {
                    await handleTerminalEvent(event.eventType ?? "unknown")
                    break
                }
            }
        } catch {
            streamError = "Stream error: \(error.localizedDescription)"
        }

        isConnected = false
    }
}

// MARK: - Document Detail View

private struct DocumentDetailView: View {
    let documentId: String

    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @State private var detail: ScoutDocumentDetail?
    @State private var statusMessage: String?
    @State private var isLoading = false

    private let keychainStore = ScoutKeychainStore()

    var body: some View {
        List {
            if isLoading {
                Section {
                    HStack {
                        ProgressView()
                            .padding(.trailing, 8)
                        Text("Loading document…")
                            .foregroundStyle(.secondary)
                    }
                }
            }

            if let msg = statusMessage, detail == nil {
                Section {
                    Text(msg)
                        .foregroundStyle(.secondary)
                }
            }

            if let detail = detail {
                Section("Info") {
                    if let filename = detail.filename {
                        HStack {
                            Text("Filename")
                                .foregroundStyle(.secondary)
                            Spacer()
                            Text(filename)
                                .lineLimit(1)
                        }
                    }
                    if let mime = detail.mime_type {
                        HStack {
                            Text("Type")
                                .foregroundStyle(.secondary)
                            Spacer()
                            Text(mime)
                        }
                    }
                    if let size = detail.filesize {
                        HStack {
                            Text("Size")
                                .foregroundStyle(.secondary)
                            Spacer()
                            Text(formatFileSize(size))
                        }
                    }
                    if let created = detail.created_at {
                        HStack {
                            Text("Created")
                                .foregroundStyle(.secondary)
                            Spacer()
                            Text(created)
                                .font(.caption)
                        }
                    }
                }

                if let text = detail.parsed_text, !text.isEmpty {
                    Section("Content") {
                        Text(text)
                            .font(.body)
                            .textSelection(.enabled)
                    }
                }
            }
        }
        .navigationTitle("Document")
        .onAppear {
            Task { await loadDetail() }
        }
    }

    private func loadDetail() async {
        guard !storedProfileData.isEmpty else { return }

        isLoading = true

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

        let result = await ScoutDocumentDetailProbe.probe(
            endpoint: profile, documentId: documentId, apiKey: apiKey
        )
        detail = result.detail
        if result.detail == nil {
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
    GuardianChatView()
}
