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
    @Environment(\.scoutAccentTheme) private var accentTheme
    @Environment(\.scoutOpenAuxiliary) private var openAuxiliary
    @FocusState private var searchFocused: Bool
    @State private var selectedThread: ThreadNav?
    @State private var selectedRoute: ScoutAppRoute = .guardian
    @State private var visitedRoutes: Set<ScoutAppRoute> = [.guardian]
    @State private var navigationPath = NavigationPath()
    @State private var isSidebarOpen = false
    @State private var isNavigationExpanded = false
    @AccessibilityFocusState private var historyButtonFocused: Bool
    @AccessibilityFocusState private var sidebarCloseFocused: Bool
    @StateObject private var conversation = ScoutConversationState()
    @StateObject private var composer = ScoutComposerFlow()
    @State private var threads: [ScoutChatThreadSummary]?
    @State private var projects: [ScoutProject]?
    @State private var selectedProjectID: Int?
    @State private var sidebarTab = 0
    @State private var searchText = ""
    @State private var source = "all"
    @State private var projectsError: String?
    @State private var showNewProject = false
    @State private var newProjectName = ""
    @State private var projectCreateError: String?
    @State private var isCreatingProject = false
    @State private var message: String?
    @State private var keychainError: String?
    @State private var isLoading = false
    @State private var isNewThread = false
    @State private var draftID = UUID()
    @State private var draftProjectID: Int?

    private let keychainStore = ScoutKeychainStore()

    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                NavigationStack(path: $navigationPath) {
                    workspaceContent
                        .modifier(ScoutAdaptiveContentFrame(availableWidth: geometry.size.width))
                        .modifier(ScoutCanvas())
                        .navigationBarTitleDisplayMode(.inline)
                        .toolbarBackground(.hidden, for: .navigationBar)
                        .toolbar {
                            ToolbarItem(placement: .topBarLeading) {
                                Button("Show sidebar", systemImage: "sidebar.left") { openSidebar() }
                                    .accessibilityFocused($historyButtonFocused)
                            }
                            ScoutAuxiliaryMenu()
                        }
                        .navigationDestination(for: TaskNav.self) { nav in
                            TaskEventsView(taskId: nav.taskId, threadId: nav.threadId, conversation: conversation)
                        }
                        .navigationDestination(for: DocumentDetailNav.self) { nav in
                            DocumentDetailView(documentId: nav.documentId)
                        }
                        .sheet(isPresented: $showNewProject) {
                            NavigationStack {
                                Form {
                                    TextField("Project name", text: $newProjectName)
                                    if let error = projectCreateError { Text(error).foregroundStyle(.red) }
                                    Button("Create") { Task { await createProject() } }
                                        .disabled(newProjectName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isCreatingProject)
                                    Button("Cancel", role: .cancel) {
                                        showNewProject = false; projectCreateError = nil
                                    }
                                }.navigationTitle("New Project")
                            }
                        }
                }
                .allowsHitTesting(!isSidebarOpen)
                .accessibilityHidden(isSidebarOpen)

                if isSidebarOpen {
                    Color.black.opacity(0.4)
                        .ignoresSafeArea()
                        .contentShape(Rectangle())
                        .onTapGesture { closeSidebar() }
                        .accessibilityHidden(true)
                    historyPanel
                        .frame(width: min(360, geometry.size.width * 0.9))
                        .frame(maxHeight: .infinity)
                        .padding(ScoutVisualStyle.inset / 2)
                        .simultaneousGesture(sidebarDismissGesture)
                }
            }
            .simultaneousGesture(sidebarOpenGesture)
        }
        .task { await loadThreads() }
        .onReceive(NotificationCenter.default.publisher(for: ScoutThreadRenamedNotification)) { _ in
            Task { await loadThreads() }
        }
        .onChange(of: sidebarTab) { _, _ in searchText = "" }
    }

    private var workspaceContent: some View {
        ZStack {
            routeLayer(.guardian) { conversationPane }
            if visitedRoutes.contains(.feed) {
                routeLayer(.feed) { ActivityStreamView() }
            }
            if visitedRoutes.contains(.library) {
                routeLayer(.library) { ArtifactsView() }
            }
            if visitedRoutes.contains(.spaces) {
                routeLayer(.spaces) { SpacesView() }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .navigationTitle(selectedRoute == .guardian ? "" : selectedRoute.title)
    }

    private func routeLayer<Content: View>(_ route: ScoutAppRoute, @ViewBuilder content: () -> Content) -> some View {
        content()
            .opacity(selectedRoute == route ? 1 : 0)
            .allowsHitTesting(selectedRoute == route)
            .accessibilityHidden(selectedRoute != route)
    }

    @ViewBuilder
    private var conversationPane: some View {
        if isNewThread {
            let selectedDraftID = draftID
            DraftThreadView(projectID: draftProjectID,
                projectName: projects?.first(where: { $0.id == draftProjectID })?.name ?? "General", composer: composer,
                isDraftCurrent: { isNewThread && draftID == selectedDraftID },
                onCreated: { id, title in
                    openCreatedThread(id, title: title, draftID: selectedDraftID)
                })
                .id(selectedDraftID)
        } else if let thread = selectedThread {
            ThreadMessagesView(threadId: thread.id, threadTitle: thread.title, conversation: conversation,
                               composer: composer, isActive: selectedRoute == .guardian)
                .id(thread.id)
        } else {
            ContentUnavailableView {
                Label("Choose a conversation", systemImage: "bubble.left.and.bubble.right")
            } description: {
                Text("Select a thread from your conversation history.")
            } actions: {
                Button("Show conversations") { openSidebar() }
                    .buttonStyle(.bordered)

                if !storedProfileData.isEmpty {
                    Button("New Thread") { startNewThread() }
                        .buttonStyle(.bordered)
                        .disabled(projects == nil || isLoading)
                }
            }
        }
    }

    private var historyPanel: some View {
        VStack(alignment: .leading, spacing: 0) {
            sidebarHeader
            Divider().padding(.horizontal, ScoutVisualStyle.inset)
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ScoutVisualStyle.inset / 2) {
                    if isNavigationExpanded { sidebarNavigation }
                    sidebarTabs
                        .frame(maxWidth: textSize.isAccessibilitySize ? .infinity : 220)
                        .frame(maxWidth: .infinity)
                        .padding(.top, ScoutVisualStyle.inset / 2)
                    let searchShape = RoundedRectangle(
                        cornerRadius: CGFloat(CodexifyDesignTokens.Semantic.microRadius.logicalUnits),
                        style: .continuous
                    )
                    HStack(spacing: ScoutVisualStyle.inset / 2) {
                        Image(systemName: "magnifyingglass")
                            .foregroundStyle(.secondary)
                            .accessibilityHidden(true)
                        TextField(sidebarTab == 0 ? "Search threads…" : "Search projects…", text: $searchText)
                            .textFieldStyle(.plain)
                            .autocorrectionDisabled()
                            .focused($searchFocused)
                    }
                    .padding(.horizontal, ScoutVisualStyle.inset)
                    .frame(minHeight: ScoutVisualStyle.controlMinimum)
                    .background(Color(uiColor: .secondarySystemBackground), in: searchShape)
                    .overlay(searchShape.strokeBorder(searchFocused ? accentTheme.tint : Color(uiColor: .separator)))
                    if !storedProfileData.isEmpty || sidebarTab == 0 {
                        HStack(spacing: ScoutVisualStyle.inset / 2) {
                            if !storedProfileData.isEmpty {
                                Button("New Thread", systemImage: "square.and.pencil") {
                                    startNewThread()
                                }
                                .labelStyle(.iconOnly)
                                .disabled(projects == nil || isLoading)
                            }

                            if sidebarTab == 0 {
                                sidebarProjectMenu
                            } else {
                                Spacer(minLength: 0)
                            }

                            if !storedProfileData.isEmpty {
                                Button("Refresh Threads", systemImage: "arrow.clockwise") {
                                    Task { await loadThreads() }
                                }
                                .labelStyle(.iconOnly)
                                .disabled(isLoading)
                            }
                        }
                        .buttonStyle(.borderless)
                        .frame(minHeight: ScoutVisualStyle.controlMinimum)
                    }
                    if sidebarTab == 0 {
                        sourceFilter
                    }
                    if isLoading { ProgressView("Loading sidebar…") }
                    if let keychainError { GuardianStatusRow(title: "Unable to load sidebar", detail: keychainError, error: true) }
                    if let projectsError { Text(projectsError).font(.caption).foregroundStyle(.secondary) }
                    if let message { Text(message).font(.caption).foregroundStyle(.secondary) }
                    if storedProfileData.isEmpty {
                        Text("Set up a connection in Settings to load conversations.").font(.subheadline).foregroundStyle(.secondary)
                    } else if sidebarTab == 0, let threads {
                        let visible =
                            projects == nil
                            ? ScoutSidebarThreadFilter.withoutProjects(threads, source: source, searchText: searchText)
                            : visibleThreads(threads)
                        if projects == nil {
                            Text("Showing threads without project grouping because projects could not be loaded.")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                        if visible.isEmpty && !isLoading {
                            Text(searchText.isEmpty ? "No threads in this project and source." : "No matching threads.").foregroundStyle(.secondary)
                        }
                        ForEach(visible, id: \.id) { thread in
                            if let id = thread.id {
                                let selected = selectedThread?.id == id
                                Button {
                                    selectThread(id, title: thread.title)
                                } label: {
                                    GuardianThreadRow(thread: thread, compact: true, selected: selected)
                                }.buttonStyle(.plain).accessibilityAddTraits(selected ? .isSelected : [])
                            }
                        }
                    } else if sidebarTab == 1 {
                        if let projects {
                            let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
                            let visible = projects.filter { $0.archived_at == nil && (query.isEmpty || $0.name.localizedCaseInsensitiveContains(query)) }
                            if visible.isEmpty && !isLoading { Text("No matching projects.").foregroundStyle(.secondary) }
                            ForEach(visible) { project in
                                Button {
                                    selectProject(project.id); searchText = ""; sidebarTab = 0
                                } label: {
                                    HStack {
                                        Label(project.name, systemImage: "folder"); Spacer(); if project.id == selectedProjectID { Image(systemName: "checkmark") }
                                    }
                                }
                                .disabled(isNewThread && composer.isWorking)
                            }
                        }
                        Button {
                            closeSidebar()
                            showNewProject = true
                        } label: {
                            Label("New Project", systemImage: "plus.circle")
                        }.disabled(isLoading || (isNewThread && composer.isWorking))
                    }
                }
                .padding(ScoutVisualStyle.inset)
            }
        }
        .background {
            ScoutFrameSurface(subtleOutline: true)
        }
        .clipShape(RoundedRectangle(cornerRadius: ScoutVisualStyle.radius, style: .continuous))
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Application navigation and conversations")
        .accessibilityAction(.escape) { closeSidebar() }
        .onAppear { sidebarCloseFocused = true }
    }

    private var sidebarHeader: some View {
        HStack {
            Button {
                isNavigationExpanded.toggle()
            } label: {
                Image("CodexifyMark")
                    .renderingMode(.template)
                    .resizable()
                    .scaledToFit()
                    .frame(width: 28, height: 28)
                    .frame(width: ScoutVisualStyle.controlMinimum, height: ScoutVisualStyle.controlMinimum)
                    .contentShape(Rectangle())
            }
            .accessibilityLabel(isNavigationExpanded ? "Collapse application navigation" : "Expand application navigation")
            .accessibilityValue(isNavigationExpanded ? "Expanded" : "Collapsed")
            Spacer()
            Button("Close sidebar", systemImage: "xmark") { closeSidebar() }
                .labelStyle(.iconOnly)
                .frame(width: ScoutVisualStyle.controlMinimum, height: ScoutVisualStyle.controlMinimum)
                .accessibilityFocused($sidebarCloseFocused)
        }
        .buttonStyle(.plain)
        .padding(.horizontal, ScoutVisualStyle.inset)
        .padding(.top, ScoutVisualStyle.inset)
        .padding(.bottom, ScoutVisualStyle.inset / 2)
    }

    private var sidebarNavigation: some View {
        VStack(alignment: .leading, spacing: ScoutVisualStyle.inset / 2) {
            ForEach(ScoutAppRoute.allCases) { route in
                Button {
                    visitedRoutes.insert(route)
                    if !navigationPath.isEmpty { navigationPath.removeLast(navigationPath.count) }
                    selectedRoute = route
                    closeSidebar()
                } label: {
                    Text(route.title)
                        .font(.subheadline.weight(.semibold))
                        .frame(maxWidth: .infinity, minHeight: ScoutVisualStyle.controlMinimum, alignment: .leading)
                        .padding(.horizontal, ScoutVisualStyle.inset)
                        .background {
                            if selectedRoute == route {
                                RoundedRectangle(cornerRadius: ScoutVisualStyle.radius, style: .continuous)
                                    .fill(accentTheme.tint.opacity(0.24))
                            }
                        }
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(selectedRoute == route ? .isSelected : [])
            }
            Divider()
            Button("Settings") {
                closeSidebar()
                openAuxiliary(.settings)
            }
            .frame(maxWidth: .infinity, minHeight: ScoutVisualStyle.controlMinimum, alignment: .leading)
            .padding(.horizontal, ScoutVisualStyle.inset)
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Application destinations")
    }

    private var sidebarTabs: some View {
        let layout =
            textSize.isAccessibilitySize
            ? AnyLayout(VStackLayout(spacing: 2))
            : AnyLayout(HStackLayout(spacing: 2))
        return layout {
            sidebarTabButton("Threads", value: 0)
            sidebarTabButton("Projects", value: 1)
        }
        .padding(2)
        .background(
            Color.primary.opacity(0.08),
            in: RoundedRectangle(cornerRadius: ScoutVisualStyle.radius, style: .continuous)
        )
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Browse")
    }

    private var sidebarProjectMenu: some View {
        Menu {
            Button("General") { selectProject(generalProject?.id) }
            ForEach((projects ?? []).filter { !$0.isGeneral && $0.archived_at == nil }) { project in
                Button(project.name) { selectProject(project.id) }
            }
        } label: {
            HStack(spacing: ScoutVisualStyle.inset / 2) {
                Text(selectedProjectName)
                    .lineLimit(1)
                    .truncationMode(.tail)
                Image(systemName: "chevron.down")
                    .font(.caption.weight(.semibold))
                    .fixedSize()
            }
            .frame(maxWidth: .infinity, minHeight: ScoutVisualStyle.controlMinimum)
            .contentShape(Rectangle())
        }
        .menuIndicator(.hidden)
        .accessibilityLabel("Project")
        .accessibilityValue(Text(selectedProjectName))
        .disabled(projects == nil || (isNewThread && composer.isWorking))
    }

    @ViewBuilder
    private var sourceFilter: some View {
        if textSize.isAccessibilitySize {
            Picker("Source", selection: $source) {
                Text("All").tag("all")
                Text("Codexify").tag("codexify")
                Text("ChatGPT").tag("openai")
                Text("Claude").tag("anthropic")
            }
        } else {
            HStack(spacing: 0) {
                Text("SOURCE")
                    .font(.caption2.weight(.semibold))
                    .tracking(1)
                    .foregroundStyle(.secondary)
                    .padding(.leading, ScoutVisualStyle.inset / 2)
                Spacer(minLength: 0)
                sourceButton("All", value: "all", image: nil)
                sourceButton("Codexify", value: "codexify", image: "CodexifyMark")
                sourceButton("ChatGPT", value: "openai", image: "OpenAIMark")
                sourceButton("Claude", value: "anthropic", image: "AnthropicMark")
            }
            .padding(ScoutVisualStyle.inset / 3)
            .background(Color.primary.opacity(0.06), in: Capsule())
            .overlay(Capsule().strokeBorder(Color(uiColor: .separator)))
            .accessibilityElement(children: .contain)
            .accessibilityLabel("Conversation source")
        }
    }

    private func sourceButton(_ title: String, value: String, image: String?) -> some View {
        let selected = source == value
        return Button {
            source = value
        } label: {
            Group {
                if let image {
                    Image(image).renderingMode(.template).resizable().scaledToFit()
                        .frame(width: ScoutVisualStyle.inset * 1.5, height: ScoutVisualStyle.inset * 1.5)
                } else {
                    Text(title).font(.caption.weight(.semibold))
                }
            }
            .foregroundStyle(selected ? accentTheme.textOnTint : Color.primary)
            .frame(width: ScoutVisualStyle.controlMinimum, height: ScoutVisualStyle.controlMinimum)
            .background { if selected { Capsule().fill(accentTheme.tint) } }
            .contentShape(Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(title)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }

    private func sidebarTabButton(_ title: String, value: Int) -> some View {
        let selected = sidebarTab == value
        return Button(title) { sidebarTab = value }
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(selected ? accentTheme.textOnTint : Color.primary)
            .frame(maxWidth: .infinity, minHeight: ScoutVisualStyle.controlMinimum)
            .background {
                if selected { Capsule().fill(accentTheme.tint) }
            }
            .contentShape(Capsule())
            .buttonStyle(.plain)
            .accessibilityAddTraits(selected ? .isSelected : [])
    }

    private var sidebarOpenGesture: some Gesture {
        DragGesture(minimumDistance: ScoutVisualStyle.inset)
            .onEnded { gesture in
                let movement = gesture.translation
                if ScoutSidebarGesture.opens(isOpen: isSidebarOpen, startX: gesture.startLocation.x,
                                             horizontal: movement.width, vertical: movement.height,
                                             edgeWidth: ScoutVisualStyle.inset * 2,
                                             minimumDistance: ScoutVisualStyle.controlMinimum) {
                    openSidebar()
                }
            }
    }

    private var sidebarDismissGesture: some Gesture {
        DragGesture(minimumDistance: ScoutVisualStyle.inset)
            .onEnded { gesture in
                let movement = gesture.translation
                if ScoutSidebarGesture.dismisses(horizontal: movement.width, vertical: movement.height,
                                                 minimumDistance: ScoutVisualStyle.controlMinimum) {
                    closeSidebar()
                }
            }
    }

    private func openSidebar() {
        isSidebarOpen = true
    }

    private func closeSidebar() {
        isSidebarOpen = false
        searchFocused = false
        historyButtonFocused = true
    }

    private func selectThread(_ id: Int, title: String?) {
        if !navigationPath.isEmpty { navigationPath.removeLast(navigationPath.count) }
        if isNewThread || selectedThread?.id != id {
            composer.select(nil)
            isNewThread = false
            if let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) {
                conversation.select(.init(endpoint: profile, threadID: id))
            }
            selectedThread = ThreadNav(id: id, title: title)
        }
        selectedRoute = .guardian
        if isSidebarOpen { closeSidebar() }
    }

    private func startNewThread() {
        if !navigationPath.isEmpty { navigationPath.removeLast(navigationPath.count) }
        if !isNewThread {
            composer.select(nil)
            selectedThread = nil
            draftID = UUID()
            draftProjectID = selectedProjectID
            isNewThread = true
        }
        selectedRoute = .guardian
        if isSidebarOpen { closeSidebar() }
    }

    private func selectProject(_ id: Int?) {
        selectedProjectID = id
        if isNewThread { draftProjectID = id }
    }

    private func openCreatedThread(_ id: Int, title: String?, draftID: UUID) {
        guard isNewThread, self.draftID == draftID,
              let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else { return }
        conversation.select(.init(endpoint: profile, threadID: id))
        selectedThread = ThreadNav(id: id, title: title)
        isNewThread = false
        Task { await loadThreads() }
    }

    private var generalProject: ScoutProject? { projects?.first { $0.isGeneral && $0.archived_at == nil } }
    private var selectedProjectName: String { projects?.first { $0.id == selectedProjectID }?.name ?? "General" }

    private func visibleThreads(_ rows: [ScoutChatThreadSummary]) -> [ScoutChatThreadSummary] {
        let knownIDs = Set((projects ?? []).map(\.id))
        let generalID = generalProject?.id
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        return rows.filter { thread in
            let bucket = thread.project_id.flatMap { knownIDs.contains($0) ? $0 : nil } ?? generalID
            return thread.archived_at == nil && bucket == selectedProjectID && (source == "all" || thread.origin_system == source) &&
                (query.isEmpty || (thread.title ?? "Untitled").localizedCaseInsensitiveContains(query))
        }
    }

    private func loadThreads() async {
        guard !storedProfileData.isEmpty, !isLoading else { return }
        isLoading = true
        defer { isLoading = false }
        keychainError = nil; message = nil; projectsError = nil
        let profileData = storedProfileData
        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: profileData) else {
            message = "Could not load saved endpoint profile."; return
        }
        let apiKey: String?
        do { apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil }
        catch { keychainError = "Could not load API key from Keychain."; return }
        let projectResult = await ScoutProjectsService.request(endpoint: profile, apiKey: apiKey)
        var allThreads: [ScoutChatThreadSummary] = []
        var offset = 0
        var threadError: String?
        while !Task.isCancelled {
            let result = await ScoutGuardianThreadsProbe.probe(endpoint: profile, apiKey: apiKey, offset: offset)
            guard let page = result.threads else { threadError = result.message; break }
            allThreads.append(contentsOf: page)
            guard result.hasMore == true, !page.isEmpty else { break }
            offset += page.count
        }
        guard !Task.isCancelled, storedProfileData == profileData else { return }
        if let fetched = projectResult.projects {
            var seenGeneral = false
            let loaded = fetched.filter { project in
                guard project.isGeneral else { return true }
                if seenGeneral { return false }
                seenGeneral = true; return true
            }
            projects = loaded
            if selectedProjectID == nil || !loaded.contains(where: { $0.id == selectedProjectID && $0.archived_at == nil }) {
                selectProject(loaded.first(where: { $0.isGeneral && $0.archived_at == nil })?.id)
            }
        } else { projectsError = projectResult.message }
        if let error = threadError { message = error } else { threads = allThreads }
    }

    private func createProject() async {
        let name = newProjectName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty, let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else { return }
        isCreatingProject = true
        defer { isCreatingProject = false }
        projectCreateError = nil
        let apiKey: String?
        do { apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil }
        catch { projectCreateError = "Could not load API key from Keychain."; return }
        let result = await ScoutProjectsService.request(endpoint: profile, apiKey: apiKey, name: name)
        if let project = result.projects?.first {
            showNewProject = false; newProjectName = ""
            projects = (projects ?? []).filter { $0.id != project.id } + [project]
            selectProject(project.id); sidebarTab = 0; searchText = ""
            await loadThreads()
        } else { projectCreateError = result.message }
    }

}

// MARK: - New Thread Draft

private struct DraftThreadView: View {
    let projectID: Int?
    let projectName: String
    @ObservedObject var composer: ScoutComposerFlow
    let isDraftCurrent: () -> Bool
    let onCreated: (Int, String?) -> Void

    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @AppStorage("scout.accountSessionGeneration") private var accountGeneration = 0
    private let keychainStore = ScoutKeychainStore()

    private var composerScope: ScoutComposerFlow.Scope? {
        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else { return nil }
        return .init(connection: .init(endpoint: profile), threadID: nil, accountGeneration: accountGeneration)
    }

    var body: some View {
        VStack(spacing: ScoutVisualStyle.inset) {
            Spacer()
            ContentUnavailableView("New Thread", systemImage: "bubble.left.and.bubble.right",
                                   description: Text("Send a message to start the conversation."))
            Text("Project: \(projectName)")
                .font(.caption)
                .foregroundStyle(.secondary)
            if composer.isWaitingForReply {
                GuardianReplyProgress()
            } else if let status = composer.status {
                Text(status)
                    .font(.caption)
                    .foregroundStyle(composer.isError ? Color.primary : Color.secondary)
                    .padding(.horizontal, ScoutVisualStyle.inset)
            }
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .safeAreaInset(edge: .bottom, spacing: 0) {
            ScoutConversationBar(flow: composer, available: composerScope != nil, focusOnAppear: true,
                send: { Task { await submitMessage() } },
                sendOnly: { Task { await submitMessage(messageOnly: true) } })
        }
        .task { composer.select(composerScope) }
        .onChange(of: composerScope) { _, scope in composer.select(scope) }
    }

    private func submitMessage(messageOnly: Bool = false) async {
        guard let scope = composerScope,
              let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: storedProfileData) else { return }
        do {
            let context = try ScoutThreadActionContext.selected()
            let apiKey = profile.authenticationMode == .localAPIKey ? try keychainStore.loadAPIKey(for: profile) : nil
            let current = {
                composerScope == scope && isDraftCurrent() &&
                    (try? ScoutThreadActionContext.selected()).map { context.isCurrent($0) } == true
            }
            var created: ScoutFirstMessageResult?
            await composer.submit(scope: scope, messageOnly: messageOnly, isCurrent: current,
                save: { text in
                    let result = await ScoutGuardianFirstMessageService.send(
                        endpoint: profile, content: text, projectID: projectID, apiKey: apiKey
                    )
                    if result.threadID != nil, result.messageID != nil { created = result }
                    return .init(httpStatus: result.httpStatus, messageId: result.messageID, message: result.message)
                },
                complete: {
                    guard let id = created?.threadID else {
                        return .init(httpStatus: nil, taskId: nil, turnId: nil, messagesUrl: nil,
                                     traceUrl: nil, acceptanceStatus: nil, message: "New thread was not confirmed.")
                    }
                    return await ScoutGuardianCompleteThreadService.complete(endpoint: profile, threadId: id, apiKey: apiKey)
                })
            guard let created, let id = created.threadID, let messageID = created.messageID,
                  composer.acceptedMessageID == messageID, current() else { return }
            let threadScope = ScoutComposerFlow.Scope(connection: scope.connection, threadID: id,
                                                       accountGeneration: scope.accountGeneration)
            guard composer.promoteDraft(from: scope, to: threadScope) else { return }
            onCreated(id, created.threadTitle)
        } catch {
            composer.report("Nothing was sent. \(error.localizedDescription)")
        }
    }
}

private struct GuardianReplyProgress: View {
    var stage: ScoutComposerFlow.ReplyProgress? = nil

    private var title: String {
        switch stage {
        case .preparing: return "Guardian is preparing a reply…"
        case .writing: return "Guardian is writing…"
        case nil: return "Waiting for Guardian…"
        }
    }

    var body: some View {
        HStack(spacing: ScoutVisualStyle.gap) {
            ProgressView()
                .controlSize(.small)
                .accessibilityHidden(true)
            Text(title)
                .lineLimit(1)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }
}

// MARK: - Thread Messages Detail View

private struct ThreadMessagesView: View {
    let threadId: Int
    let threadTitle: String?
    @ObservedObject var conversation: ScoutConversationState
    @ObservedObject var composer: ScoutComposerFlow
    let isActive: Bool
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
            if isActive {
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
                            GuardianGenUIMessageRow(message: msg, isActive: isActive)
                                .listRowBackground(Color.clear)
                                .listRowSeparator(.hidden)
                        }
                    }
                }
            }

            if composer.isWaitingForReply {
                Section {
                    GuardianReplyProgress(stage: composer.replyProgress)
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                }
            } else if let message = composer.status {
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
            responseTask: composer.taskID.map { TaskNav(taskId: $0, threadId: threadId) },
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
                composer.observeProgress(event, taskID: taskID, scope: scope)
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
    var responseTask: TaskNav? = nil
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
                if let responseTask {
                    NavigationLink("View response status", value: responseTask)
                }
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
    var isActive = true
    var body: some View {
        let presentation = ScoutGenerativeUI.presentation(for: message, enabled: renderingEnabled)
        let visible = ScoutChatMessageSummary(id: message.id, role: message.role,
            content: presentation.text, created_at: message.created_at, updated_at: message.updated_at)
        VStack(alignment: .leading, spacing: ScoutVisualStyle.inset) {
            if !presentation.text.isEmpty || presentation.artifacts.isEmpty {
                GuardianMessageRow(message: visible)
            }
            ForEach(Array(presentation.artifacts.enumerated()), id: \.offset) { _, artifact in
                switch artifact {
                case let .table(table):
                    ScoutGenUITableView(table: table)
                case let .openUI(program):
                    ScoutOpenUIProgramView(program: program)
                case let .sandbox(widget):
                    ScoutSandboxWidgetView(widget: widget, isActive: isActive)
                        .id(message.id)
                }
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
    var focusOnAppear = false
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
        .onAppear { if focusOnAppear { inputFocused = true } }
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
