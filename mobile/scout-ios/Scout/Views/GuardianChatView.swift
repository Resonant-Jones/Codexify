import SwiftUI

struct TaskNav: Hashable {
    let taskId: String
    let threadId: Int
}

struct DocumentDetailNav: Hashable {
    let documentId: String
}

private struct ThreadNav {
    let id: Int
    let title: String?
}

private let ScoutThreadRenamedNotification = Notification.Name("ScoutThreadRenamedNotification")

struct GuardianChatView: View {
    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @Environment(\.dynamicTypeSize) private var textSize
    @State private var selectedThread: ThreadNav?
    @State private var isRailVisible = true
    @State private var isDrawerOpen = false
    @AccessibilityFocusState private var historyButtonFocused: Bool
    @AccessibilityFocusState private var drawerCloseFocused: Bool
    @StateObject private var conversation = ScoutConversationState()
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
        NavigationStack {
            GeometryReader { geometry in
                workspace(width: geometry.size.width)
            }
            .modifier(ScoutCanvas())
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
            .navigationDestination(for: TaskNav.self) { nav in
                TaskEventsView(taskId: nav.taskId, threadId: nav.threadId, conversation: conversation)
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
            .task { await loadThreads() }
            .onReceive(NotificationCenter.default.publisher(for: ScoutThreadRenamedNotification)) { _ in
                Task { await loadThreads() }
            }
        }
    }

    private func workspace(width: CGFloat) -> some View {
        let railWidth: CGFloat = width >= 900 ? 220 : 200
        let canDock = !textSize.isAccessibilitySize && width >= railWidth + ScoutVisualStyle.gap + 440
        let docked = canDock && isRailVisible
        let drawer = !canDock && isDrawerOpen

        return conversationPane(canDock: canDock, historyVisible: docked || drawer)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(.leading, docked ? railWidth + ScoutVisualStyle.gap : 0)
            .allowsHitTesting(!drawer)
            .accessibilityHidden(drawer)
            .overlay(alignment: .leading) {
                if drawer {
                    Color.black.opacity(0.22)
                        .contentShape(Rectangle())
                        .onTapGesture { closeDrawer() }
                        .accessibilityHidden(true)
                }
                if docked || drawer {
                    historyPanel(isDrawer: drawer)
                        .frame(width: drawer ? min(300, width * 0.82) : railWidth)
                        .padding(ScoutVisualStyle.inset / 2)
                }
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        if canDock {
                            isRailVisible.toggle()
                        } else if drawer {
                            closeDrawer()
                        } else {
                            isDrawerOpen = true
                        }
                    } label: {
                        Label(docked || drawer ? "Hide conversations" : "Show conversations",
                              systemImage: "sidebar.left")
                    }
                    .accessibilityFocused($historyButtonFocused)
                }
                ScoutAuxiliaryMenu()
            }
            .onChange(of: canDock) { _, _ in isDrawerOpen = false }
    }

    @ViewBuilder
    private func conversationPane(canDock: Bool, historyVisible: Bool) -> some View {
        if let thread = selectedThread {
            ThreadMessagesView(threadId: thread.id, threadTitle: thread.title, conversation: conversation)
                .id(thread.id)
        } else {
            ContentUnavailableView {
                Label("Choose a conversation", systemImage: "bubble.left.and.bubble.right")
            } description: {
                Text("Select a thread from your conversation history.")
            } actions: {
                if !historyVisible {
                    Button("Show conversations") {
                        if canDock { isRailVisible = true } else { isDrawerOpen = true }
                    }
                    .buttonStyle(.bordered)
                }

                if !storedProfileData.isEmpty {
                    Button("New Thread") { showNewThread = true }
                        .buttonStyle(.bordered)
                }
            }
        }
    }

    private func historyPanel(isDrawer: Bool) -> some View {
        VStack(alignment: .leading, spacing: ScoutVisualStyle.inset / 2) {
            HStack(alignment: .top, spacing: 0) {
                Text("Conversations")
                    .font(.headline)
                    .accessibilityAddTraits(.isHeader)
                    .frame(maxWidth: .infinity, minHeight: ScoutVisualStyle.controlMinimum, alignment: .leading)
                if isDrawer {
                    Button("Close conversations", systemImage: "xmark") { closeDrawer() }
                        .labelStyle(.iconOnly)
                        .frame(width: ScoutVisualStyle.controlMinimum, height: ScoutVisualStyle.controlMinimum)
                        .accessibilityFocused($drawerCloseFocused)
                }
            }
            if !storedProfileData.isEmpty {
                HStack {
                    Button("New Thread", systemImage: "square.and.pencil") { showNewThread = true }
                    Spacer()
                    Button("Refresh Threads", systemImage: "arrow.clockwise") {
                        Task { await loadThreads() }
                    }
                    .disabled(isLoading)
                }
                .labelStyle(.iconOnly)
                .buttonStyle(.borderless)
                .frame(minHeight: ScoutVisualStyle.controlMinimum)
            }

            ScrollView {
                LazyVStack(alignment: .leading, spacing: ScoutVisualStyle.inset / 2) {
                    if isLoading {
                        ProgressView("Loading threads…")
                    }
                    if let keychainError {
                        GuardianStatusRow(title: "Unable to load threads", detail: keychainError, error: true)
                    }
                    if let message {
                        Text(message).font(.caption).foregroundStyle(.secondary)
                    }
                    if let threads {
                        if threads.isEmpty {
                            Text("No threads yet").font(.subheadline).foregroundStyle(.secondary)
                        }
                        ForEach(threads, id: \.id) { thread in
                            if let id = thread.id {
                                let selected = selectedThread?.id == id
                                Button {
                                    selectThread(id, title: thread.title)
                                } label: {
                                    GuardianThreadRow(thread: thread, compact: true, selected: selected)
                                }
                                .buttonStyle(.plain)
                                .accessibilityAddTraits(selected ? .isSelected : [])
                            }
                        }
                    } else if storedProfileData.isEmpty {
                        Text("Set up a connection in Settings to load conversations.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.bottom, ScoutVisualStyle.inset / 2)
            }
        }
        .padding(ScoutVisualStyle.inset)
        .background {
            ScoutFloatingSurface(RoundedRectangle(cornerRadius: ScoutVisualStyle.radius))
        }
        .accessibilityAction(.escape) {
            if isDrawer { closeDrawer() }
        }
        .onAppear {
            if isDrawer { drawerCloseFocused = true }
        }
    }

    private func closeDrawer() {
        isDrawerOpen = false
        historyButtonFocused = true
    }

    private func selectThread(_ id: Int, title: String?) {
        if selectedThread?.id != id {
            if let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) {
                conversation.select(.init(endpoint: profile, threadID: id))
            }
            selectedThread = ThreadNav(id: id, title: title)
        }
        if isDrawerOpen { closeDrawer() }
    }

    private func loadThreads() async {
        guard !storedProfileData.isEmpty, !isLoading else { return }

        isLoading = true
        defer { isLoading = false }
        keychainError = nil
        message = nil

        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            message = "Could not load saved endpoint profile."
            return
        }

        let apiKey: String?
        do {
            apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
        } catch {
            keychainError = "Could not load API key from Keychain."
            apiKey = nil
        }

        let result = await ScoutGuardianThreadsProbe.probe(endpoint: profile, apiKey: apiKey)
        guard !Task.isCancelled else { return }
        if let fetched = result.threads {
            threads = fetched
        } else {
            message = result.message
        }
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
            apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
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
            if let tid = result.threadId { selectThread(tid, title: trimmed) }
            await loadThreads()
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
    @ObservedObject var conversation: ScoutConversationState
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.dynamicTypeSize) private var textSize

    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @State private var displayedTitle: String?
    @State private var showRename = false
    @State private var renameTitle = ""
    @State private var renameError: String?
    @State private var isRenaming = false
    private var messages: [ScoutChatMessageSummary]? {
        conversation.selection?.threadID == threadId ? conversation.messages : nil
    }
    @State private var statusMessage: String?
    @State private var refreshNotice: UUID?
    @State private var keychainError: String?
    @State private var isLoading = false
    @State private var isRefreshing = false
    @StateObject private var composer = ScoutComposerFlow()
    @AppStorage("scout.accountSessionGeneration") private var accountGeneration = 0
    @State private var documents: [ScoutThreadDocumentSummary]?
    @State private var docMessage: String?
    @State private var isLoadingDocs = false
    @State private var ragResult: ScoutRAGTraceResult?
    @State private var ragMessage: String?
    @State private var isLoadingRAG = false
    @State private var taskReceipts: [ScoutTaskReceiptSummary]?
    @State private var tasksMessage: String?
    @State private var isLoadingTasks = false
    @State private var showThreadDetails = false
    @AccessibilityFocusState private var detailsActionFocused: Bool

    private let keychainStore = ScoutKeychainStore()

    var body: some View {
        conversationList
        .scrollContentBackground(.hidden)
        .overlay(alignment: .top) {
            if refreshNotice != nil {
                Label("Messages refreshed", systemImage: "checkmark")
                    .font(.subheadline.weight(.medium))
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.horizontal, ScoutVisualStyle.inset)
                    .padding(.vertical, ScoutVisualStyle.inset / 2)
                    .background {
                        ScoutFloatingSurface(RoundedRectangle(cornerRadius: ScoutVisualStyle.radius))
                    }
                    .padding(ScoutVisualStyle.inset)
                    .allowsHitTesting(false)
                    .accessibilityHidden(true)
            }
        }
        .safeAreaInset(edge: .top, spacing: 0) {
            threadTitleHeader
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            ScoutConversationBar(flow: composer, available: composerScope != nil,
                hasMessages: messages?.isEmpty == false || composer.acceptedMessageID != nil,
                send: { Task { await submitMessage() } },
                sendOnly: { Task { await submitMessage(messageOnly: true) } },
                requestResponse: { Task { await submitMessage(responseOnly: true) } },
                checkResponse: { Task { await checkResponse() } })
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Button {
                    showThreadDetails = true
                } label: {
                    Label("Thread details", systemImage: "info.circle")
                }
                .accessibilityFocused($detailsActionFocused)
                .accessibilityHint("Opens documents, retrieval evidence, and task receipts for this thread")
                Button {
                    renameTitle = displayedTitle ?? ""
                    renameError = nil
                    showRename = true
                } label: {
                    Label("Rename thread", systemImage: "pencil")
                }
            }
        }
        .sheet(isPresented: $showThreadDetails, onDismiss: { detailsActionFocused = true }) {
            GuardianThreadDetailsSheet {
                inspectorList
                    .navigationDestination(for: DocumentDetailNav.self) { nav in
                        DocumentDetailView(documentId: nav.documentId)
                    }
                    .navigationDestination(for: TaskNav.self) { nav in
                        TaskEventsView(taskId: nav.taskId, threadId: nav.threadId, conversation: conversation)
                    }
            }
        }
        .task {
            composer.select(composerScope)
            if displayedTitle == nil { displayedTitle = threadTitle }
            await loadMessages()
        }
        .onChange(of: composerScope) { _, scope in composer.select(scope) }
        .task(id: refreshNotice) { [refreshNotice] in
            guard let refreshNotice, !Task.isCancelled else { return }
            AccessibilityNotification.Announcement("Messages refreshed").post()
            try? await Task.sleep(for: .seconds(3))
            guard !Task.isCancelled, self.refreshNotice == refreshNotice else { return }
            self.refreshNotice = nil
        }
        .onDisappear { refreshNotice = nil }
        .task(id: composer.taskID) { await observeResponse() }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active {
                Task { await loadMessages(); await checkResponse() }
            }
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

    private var threadTitleHeader: some View {
        let title = displayedTitle ?? threadTitle
        let label = title.flatMap { $0.isEmpty ? nil : $0 } ?? "Thread \(threadId)"

        return Text(label)
            .font(.headline)
            .multilineTextAlignment(.center)
            .lineLimit(textSize.isAccessibilitySize ? 2 : 1)
            .accessibilityLabel(label)
            .accessibilityAddTraits(.isHeader)
            .accessibilityAction(named: Text("Refresh messages")) {
                Task { await refreshMessages() }
            }
            .padding(.horizontal, ScoutVisualStyle.inset)
            .padding(.vertical, ScoutVisualStyle.inset / 2)
            .background {
                ScoutFloatingSurface(RoundedRectangle(cornerRadius: ScoutVisualStyle.radius))
            }
            .frame(maxWidth: 520)
            .padding(.horizontal, ScoutVisualStyle.inset)
            .padding(.vertical, ScoutVisualStyle.inset / 2)
    }

    private var conversationList: some View {
        List {
            if isLoading && !isRefreshing && messages == nil {
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

            if let msg = statusMessage {
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
                            GuardianGenUIMessageRow(message: msg)
                            .listRowBackground(Color.clear)
                            .listRowSeparator(.hidden)
                        }
                    }
                }
            }

            if let message = composer.status {
                Section {
                    Text(message).font(.caption)
                        .foregroundStyle(composer.isError ? Color.primary : Color.secondary)
                        .accessibilityLabel(message)
                    if let taskID = composer.taskID {
                        NavigationLink("View response status", value: TaskNav(taskId: taskID, threadId: threadId))
                    }
                }
            }
        }
        .scrollDismissesKeyboard(.interactively)
        .scrollBounceBehavior(.always, axes: .vertical)
        .refreshable { await refreshMessages() }
    }

    private var inspectorList: some View {
        GuardianThreadDetailsContent(
            documents: documents, docMessage: docMessage, isLoadingDocs: isLoadingDocs,
            ragResult: ragResult, ragMessage: ragMessage, isLoadingRAG: isLoadingRAG,
            taskReceipts: taskReceipts, tasksMessage: tasksMessage, isLoadingTasks: isLoadingTasks,
            loadDocuments: { await loadDocuments() },
            loadRAGTrace: { await loadRAGTrace() },
            loadTasks: { await loadTasks() }
        )
    }

    private var composerScope: ScoutComposerFlow.Scope? {
        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else { return nil }
        return .init(connection: .init(endpoint: profile), threadID: threadId, accountGeneration: accountGeneration)
    }

    private func submitMessage(messageOnly: Bool = false, responseOnly: Bool = false) async {
        guard let scope = composerScope,
              let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else { return }
        do {
            let context = try ScoutThreadActionContext.selected()
            let apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
            let current = {
                composerScope == scope && conversation.selection == .init(endpoint: profile, threadID: threadId) &&
                    (try? ScoutThreadActionContext.selected()).map { context.isCurrent($0) } == true
            }
            let complete = { await ScoutGuardianCompleteThreadService.complete(endpoint: profile, threadId: threadId, apiKey: apiKey) }
            if responseOnly {
                await composer.requestResponse(scope: scope, isCurrent: current, complete: complete)
            } else {
                await composer.submit(scope: scope, messageOnly: messageOnly, isCurrent: current,
                    save: { text in
                        let result = await ScoutGuardianSendMessageService.send(endpoint: profile, threadId: threadId, content: text, apiKey: apiKey)
                        if current() { await loadMessages() }
                        return result
                    },
                    complete: complete)
            }
        } catch {
            composer.report("Nothing was sent. \(error.localizedDescription)")
        }
    }

    private func observeResponse() async {
        guard let taskID = composer.taskID, composer.phase == .pending,
              let scope = composerScope,
              let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else { return }
        do {
            let context = try ScoutThreadActionContext.selected()
            let apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
            let stream = ScoutTaskEventStreamService.streamEvents(endpoint: profile, taskId: taskID, apiKey: apiKey)
            for try await event in stream {
                guard !Task.isCancelled, composerScope == scope,
                      (try? ScoutThreadActionContext.selected()).map({ context.isCurrent($0) }) == true else { return }
                if event.isTerminal {
                    await finishResponse(event.eventType ?? "", taskID: taskID, scope: scope, profile: profile, apiKey: apiKey, context: context)
                    return
                }
            }
        } catch { /* Observation failure cannot change execution truth or replay work. */ }
        composer.observationEnded(taskID: taskID, scope: scope)
    }

    private func checkResponse() async {
        guard let taskID = composer.taskID, composer.phase == .pending,
              let scope = composerScope,
              let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else { return }
        do {
            let context = try ScoutThreadActionContext.selected()
            let apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
            let result = await ScoutThreadTasksProbe.probe(endpoint: profile, threadId: threadId, apiKey: apiKey)
            guard !Task.isCancelled, composerScope == scope,
                  (try? ScoutThreadActionContext.selected()).map({ context.isCurrent($0) }) == true else { return }
            if let event = result.tasks?.first(where: { $0.task_id == taskID })?.event_type,
               ["task.completed", "task.failed", "task.cancelled"].contains(event) {
                await finishResponse(event, taskID: taskID, scope: scope, profile: profile, apiKey: apiKey, context: context)
            } else {
                composer.observationEnded(taskID: taskID, scope: scope)
            }
        } catch { composer.observationEnded(taskID: taskID, scope: scope) }
    }

    private func finishResponse(_ event: String, taskID: String, scope: ScoutComposerFlow.Scope,
                                profile: ScoutEndpointProfile, apiKey: String?, context: ScoutThreadActionContext) async {
        guard composerScope == scope, composer.scope == scope, composer.phase == .pending, composer.taskID == taskID else { return }
        // Read canonical output through the established shared conversation seam.
        let outcome = await conversation.handleTerminalEvent(event, endpoint: profile, threadID: threadId, apiKey: apiKey)
        guard !Task.isCancelled, composerScope == scope,
              (try? ScoutThreadActionContext.selected()).map({ context.isCurrent($0) }) == true,
              composer.terminal(event, taskID: taskID, scope: scope) else { return }
        if let outcome { composer.report(outcome) }
    }

    private func refreshMessages() async {
        guard !isLoading, !isRefreshing else { return }
        isRefreshing = true
        defer { isRefreshing = false }
        await loadMessages(showConfirmation: true)
    }

    private func loadMessages(showConfirmation: Bool = false) async {
        guard !storedProfileData.isEmpty else { return }

        isLoading = true
        defer { isLoading = false }
        keychainError = nil
        statusMessage = nil
        refreshNotice = nil

        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            statusMessage = "Could not load saved endpoint profile."
            return
        }

        let apiKey: String?
        do {
            apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
        } catch {
            keychainError = "Could not load API key from Keychain."
            apiKey = nil
        }

        let profileData = storedProfileData
        let outcome = await conversation.refresh(endpoint: profile, threadID: threadId, apiKey: apiKey)
        guard storedProfileData == profileData else { return }
        switch outcome {
        case .refreshed:
            if showConfirmation { refreshNotice = UUID() }
        case .failed(let message):
            statusMessage = message
        case nil:
            break
        }
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
            apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
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
            apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
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
            apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
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
            apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
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
        case "user": return ScoutVisualStyle.accent
        case "assistant": return .primary
        case "system": return .orange
        default: return .secondary
        }
    }
}

// MARK: - Task Events Live View

private struct TaskEventsView: View {
    let taskId: String
    let threadId: Int
    @ObservedObject var conversation: ScoutConversationState

    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @State private var events: [ScoutTaskEvent] = []
    @State private var statusMessage: String?
    @State private var isConnected = false
    @State private var streamFinished = false
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
                    } else if streamFinished {
                        Label("Stream ended", systemImage: "stop.circle")
                            .foregroundStyle(.secondary)
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
        .task {
            await connect()
        }
    }

    private func handleTerminalEvent(_ eventType: String) async {
        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            return
        }

        let apiKey: String?
        do {
            apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
        } catch {
            apiKey = nil
        }

        let profileData = storedProfileData
        let outcome = await conversation.handleTerminalEvent(
            eventType, endpoint: profile, threadID: threadId, apiKey: apiKey
        )
        guard storedProfileData == profileData else { return }
        statusMessage = outcome
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
            apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
        } catch {
            apiKey = nil
        }

        isConnected = false
        streamFinished = false
        streamError = nil

        do {
            let stream = ScoutTaskEventStreamService.streamEvents(
                endpoint: profile, taskId: taskId, apiKey: apiKey
            )
            for try await event in stream {
                guard !Task.isCancelled else { break }
                isConnected = true
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
        streamFinished = true
    }
}

// MARK: - Document Detail View

struct DocumentDetailView: View {
    let documentId: String

    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @AppStorage("scout.accountSessionGeneration") private var accountGeneration = 0
    @State private var detail: ScoutDocumentDetail?
    @State private var page: ScoutDocumentPage?
    @State private var pageStarts: [String.Index?] = [nil]
    @State private var refreshCount = 0
    @State private var statusMessage: String?
    @State private var isLoading = true
    @State private var isLoadingRemainder = false

    private let keychainStore = ScoutKeychainStore()

    var body: some View {
        ScrollViewReader { scroll in
            documentList
                .onChange(of: pageStarts.count) { _, _ in
                    scroll.scrollTo("document-content", anchor: .top)
                }
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            if pageStarts.count > 1 || page?.nextStart != nil || isLoadingRemainder {
                pageControls
            }
        }
        .navigationTitle("Document")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    refreshCount += 1
                } label: {
                    Label("Reload document", systemImage: "arrow.clockwise")
                }
                .disabled(isLoading || isLoadingRemainder || storedProfileData.isEmpty)
            }
        }
        .task(id: refreshCount) { await loadDetail(reload: refreshCount > 0) }
    }

    private var documentList: some View {
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

            if let msg = statusMessage {
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

                Section("Content") {
                    if let page {
                        Text(page.text)
                            .font(.body)
                            .textSelection(.enabled)
                            .id("document-content")
                    } else {
                        Text("No text preview available.")
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
    }

    private var pageControls: some View {
        HStack {
            Button {
                pageStarts.removeLast()
                showPage(from: pageStarts.last ?? nil)
            } label: {
                Image(systemName: "chevron.left")
                    .frame(minWidth: ScoutVisualStyle.controlMinimum, minHeight: ScoutVisualStyle.controlMinimum)
            }
            .accessibilityLabel("Previous page")
            .disabled(pageStarts.count == 1)
            Spacer()
            Text("Page \(pageStarts.count)").font(.subheadline)
            Spacer()
            Button {
                guard let nextStart = page?.nextStart else { return }
                pageStarts.append(nextStart)
                showPage(from: nextStart)
            } label: {
                Group {
                    if isLoadingRemainder {
                        ProgressView()
                    } else {
                        Image(systemName: "chevron.right")
                    }
                }
                .frame(minWidth: ScoutVisualStyle.controlMinimum, minHeight: ScoutVisualStyle.controlMinimum)
            }
            .accessibilityLabel(isLoadingRemainder ? "Loading more pages" : "Next page")
            .disabled(page?.nextStart == nil)
        }
        .padding(.horizontal, ScoutVisualStyle.inset)
        .background(Color(uiColor: .systemBackground))
    }

    private func showPage(from start: String.Index? = nil) {
        if let text = detail?.parsed_text, !text.isEmpty {
            page = ScoutDocumentPage(text, from: start)
        } else {
            page = nil
        }
    }

    private func loadDetail(reload: Bool) async {
        isLoading = true
        isLoadingRemainder = false
        detail = nil
        page = nil
        pageStarts = [nil]
        statusMessage = nil
        let selectedProfileData = storedProfileData
        let selectedGeneration = accountGeneration
        let selectedRefresh = refreshCount
        func isCurrentLoad() -> Bool {
            !Task.isCancelled && storedProfileData == selectedProfileData
                && accountGeneration == selectedGeneration && refreshCount == selectedRefresh
        }

        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else {
            statusMessage = storedProfileData.isEmpty ? "No endpoint configured." : "Could not load saved endpoint profile."
            isLoading = false
            return
        }

        let apiKey: String?
        do {
            apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
        } catch {
            apiKey = nil
        }

        let result = await ScoutDocumentDetailProbe.probe(
            endpoint: profile, documentId: documentId, apiKey: apiKey,
            cache: ScoutDocumentDetailProbe.recentDocuments,
            accountGeneration: selectedGeneration, reload: reload, preview: true
        )
        guard isCurrentLoad() else { return }
        detail = result.detail
        showPage()
        if result.detail == nil {
            statusMessage = result.message
        }
        isLoading = false

        guard result.detail?.text_preview_truncated == true else { return }
        isLoadingRemainder = true
        let full = await ScoutDocumentDetailProbe.probe(
            endpoint: profile, documentId: documentId, apiKey: apiKey,
            cache: ScoutDocumentDetailProbe.recentDocuments, accountGeneration: selectedGeneration
        )
        guard isCurrentLoad() else { return }
        isLoadingRemainder = false
        if let complete = full.detail, complete.text_preview_truncated != true {
            // Rebuild from the current document snapshot if it changed after the preview.
            detail = complete
            showPage()
        } else {
            if let status = full.httpStatus, [401, 403, 404].contains(status) {
                detail = nil
                page = nil
            }
            statusMessage = "Could not load more pages. Reload to try again."
        }
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

// Shared by the real conversation and local previews. Owns presentation only.
struct GuardianThreadDetailsSheet<Content: View>: View {
    @Environment(\.dismiss) private var dismiss
    @ViewBuilder var content: () -> Content
    var body: some View {
        NavigationStack {
            content()
                .modifier(ScoutCanvas())
                .navigationTitle("Thread details")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Done") { dismiss() }
                            .accessibilityLabel("Close thread details")
                    }
                }
        }
    }
}

struct GuardianThreadDetailsContent: View {
    var documents: [ScoutThreadDocumentSummary]? = nil
    var docMessage: String? = nil
    var isLoadingDocs = false
    var ragResult: ScoutRAGTraceResult? = nil
    var ragMessage: String? = nil
    var isLoadingRAG = false
    var taskReceipts: [ScoutTaskReceiptSummary]? = nil
    var tasksMessage: String? = nil
    var isLoadingTasks = false
    var loadDocuments: () async -> Void
    var loadRAGTrace: () async -> Void
    var loadTasks: () async -> Void
    var body: some View {
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

    private func stringValue(_ value: Any?) -> String {
        guard let value = value else { return "—" }
        if let str = value as? String { return str }
        if let num = value as? NSNumber { return num.stringValue }
        if let bool = value as? Bool { return bool ? "true" : "false" }
        return String(describing: value)
    }
}

// Derived on each render from this message; thread/account changes reuse the
// existing conversation identity/reset path and cannot reuse an artifact cache.
struct GuardianGenUIMessageRow: View {
    let message: ScoutChatMessageSummary
    var renderingEnabled = ScoutGenerativeUI.renderingEnabled
    var body: some View {
        let presentation = ScoutGenerativeUI.presentation(for: message, enabled: renderingEnabled)
        let visible = ScoutChatMessageSummary(id: message.id, role: message.role,
            content: presentation.text, created_at: message.created_at, updated_at: message.updated_at)
        VStack(alignment: .leading, spacing: ScoutVisualStyle.inset) {
            GuardianMessageRow(message: visible)
            ForEach(Array(presentation.tables.enumerated()), id: \.offset) { _, table in
                ScoutGenUITableView(table: table)
            }
        }
    }
}

/// Shared by the live thread and presentation previews. Opening options only
/// changes sheet state; every network operation requires an explicit action.
struct ScoutConversationBar: View {
    @ObservedObject var flow: ScoutComposerFlow
    var available = true
    var hasMessages = false
    var send: () -> Void = {}
    var sendOnly: () -> Void = {}
    var requestResponse: () -> Void = {}
    var checkResponse: () -> Void = {}
    @Environment(\.colorScheme) private var scheme
    @Environment(\.scoutAccentTheme) private var accentTheme
    @Environment(\.dynamicTypeSize) private var textSize
    @FocusState private var inputFocused: Bool
    @AccessibilityFocusState private var optionsFocused: Bool

    private var canSend: Bool { available && flow.canSubmit }

    var body: some View {
        HStack(alignment: .bottom, spacing: ScoutVisualStyle.inset) {
            Button {
                inputFocused = false
                flow.optionsPresented = true
            } label: {
                Image(systemName: "plus").font(.title3)
                    .frame(width: ScoutVisualStyle.controlMinimum, height: ScoutVisualStyle.controlMinimum)
                    .background { ScoutFloatingSurface(Circle()) }
                    .contentShape(Circle())
            }
            .accessibilityLabel("Composer options")
            .accessibilityHint("Opens message and response options without sending")
            .accessibilityFocused($optionsFocused)

            TextField("Message Guardian…", text: $flow.draft, axis: .vertical)
                .lineLimit(1...5)
                .font(.body)
                .focused($inputFocused)
                .disabled(!available || flow.isWorking)
                .accessibilityLabel("Message Guardian")
                .padding(.horizontal, ScoutVisualStyle.inset)
                .padding(.vertical, ScoutVisualStyle.inset * 0.75)
                .frame(minHeight: ScoutVisualStyle.controlMinimum)
                .background {
                    ScoutFloatingSurface(RoundedRectangle(cornerRadius: ScoutVisualStyle.radius), focused: inputFocused)
                }

            Button(action: send) {
                Group {
                    if flow.isWorking { ProgressView().accessibilityLabel("Sending") }
                    else { Image(systemName: "arrow.up").font(.headline) }
                }
                .frame(width: ScoutVisualStyle.controlMinimum, height: ScoutVisualStyle.controlMinimum)
                .foregroundStyle(canSend ? (scheme == .dark ? Color.black : Color.white) : Color.secondary)
                .background { ScoutFloatingSurface(Circle(), fill: canSend ? accentTheme.tint : nil) }
                .contentShape(Circle())
            }
            .accessibilityLabel(flow.isWorking ? "Sending message" : "Send message and request Guardian response")
            .disabled(!canSend)
        }
        .buttonStyle(.plain)
        .foregroundStyle(Color.primary)
        .padding(ScoutVisualStyle.inset)
        .sheet(isPresented: $flow.optionsPresented, onDismiss: { optionsFocused = true }) {
            NavigationStack {
                List {
                    Button("Send message only") {
                        flow.optionsPresented = false
                        sendOnly()
                    }
                    .disabled(!available || !flow.canSubmit)
                    .accessibilityHint("Saves this draft without requesting a Guardian response")
                    Button("Request response") {
                        flow.optionsPresented = false
                        requestResponse()
                    }
                    .disabled(!available || !hasMessages || !flow.canRequestResponse)
                    .accessibilityHint("Requests a response to saved conversation content; does not send your draft")
                    if flow.phase == .pending {
                        Button("Check response status") {
                            flow.optionsPresented = false
                            checkResponse()
                        }
                        .accessibilityHint("Reads the existing task receipt without requesting new work")
                    }
                }
                .navigationTitle("Message options")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Done") { flow.optionsPresented = false }
                            .frame(minHeight: ScoutVisualStyle.controlMinimum)
                    }
                }
            }
            .presentationDetents(textSize.isAccessibilitySize ? [.medium, .large] : [.height(240), .medium])
            .presentationDragIndicator(.visible)
        }
    }
}
