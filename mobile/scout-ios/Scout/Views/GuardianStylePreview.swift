#if DEBUG
import SwiftUI

// Preview data is local, immutable, and never referenced by ScoutApp or services.
struct GuardianStylePreview: View {
    var conversation = false
    var genUIExample: String? = nil
    var detailsInitiallyOpen = false
    var unavailableDetails = false
    @State private var showDetails = false
    private let thread = ScoutChatThreadSummary(id: 1, title: "A resilient local network", summary: "Review identity boundaries, offline behavior, and the next smallest implementation.", created_at: nil, updated_at: "Today, 14:05", project_id: nil, origin_system: nil, archived_at: nil)
    var body: some View {
        NavigationStack {
            List {
                if conversation {
                    GuardianGenUIMessageRow(message: .init(id: 1, role: "user", content: "What breaks first when a peer goes offline?", created_at: "14:05", updated_at: nil))
                        .listRowBackground(Color.clear).listRowSeparator(.hidden)
                    if let example = genUIExample {
                        GuardianGenUIMessageRow(message: Self.genUIMessage(example), renderingEnabled: example != "disabled")
                            .listRowBackground(Color.clear).listRowSeparator(.hidden)
                    } else {
                    GuardianGenUIMessageRow(message: .init(id: 2, role: "assistant", content: "The local queue remains available. Delivery retries after reconnection; the receipt must distinguish accepted work from completed work.", created_at: "14:06", updated_at: nil))
                        .listRowBackground(Color.clear).listRowSeparator(.hidden)
                    }

                } else {
                    NavigationLink { GuardianStylePreview(conversation: true) } label: { GuardianThreadRow(thread: thread) }
                    GuardianThreadRow(thread: .init(id: 2, title: "Scout visual language", summary: "Native typography and canonical surfaces.", created_at: nil, updated_at: "Yesterday", project_id: nil, origin_system: nil, archived_at: nil))
                    GuardianStatusRow(title: "No threads yet", detail: "Create your first thread to start a conversation with Guardian.")
                    GuardianStatusRow(title: "Loading threads…", detail: "", loading: true)
                    GuardianStatusRow(title: "Unable to load threads", detail: "The endpoint could not be reached. Refresh to try again.", error: true)
                    Button("New Thread") {}.buttonStyle(ScoutActionStyle(primary: true))
                    Button("Refresh Threads") {}.buttonStyle(ScoutActionStyle())
                    Button("Loading…") {}.buttonStyle(ScoutActionStyle()).disabled(true)
                }
            }
            .modifier(ScoutCanvas())
            .navigationTitle(conversation ? "Local network" : "Guardian")
            .toolbar {
                if conversation {
                    Button { showDetails = true } label: { Label("Thread details", systemImage: "info.circle") }
                }
            }
            .sheet(isPresented: $showDetails) {
                GuardianThreadDetailsSheet { details }
            }
            .onAppear { showDetails = detailsInitiallyOpen }
        }
    }
    static func genUIMessage(_ example: String) -> ScoutChatMessageSummary {
        let component: String
        let props: [String: Any]
        if example == "openui" {
            component = "openui.program"
            props = ["libraryVersion": 2, "program": #"""
                metric = CodexifyMetric("Nodes ready", "3", "Last observed locally")
                root = CodexifyStack("horizontal", [
                    metric,
                    CodexifyCard([CodexifyProgress("Indexing", 3, 4)], "Local queue")
                ], true)
                """#]
        } else {
            component = example == "unsupported" ? "unknown.component" : "table.rows"
            props = ["title": "Node readiness", "columns": ["Node", "Status"],
                     "rows": example == "empty" ? [] : [["Node": "ScoutNode", "Status": "Observed locally."]]]
        }
        let artifact: [String: Any] = ["version": 1, "kind": "native", "component": component, "props": props]
        let payload = try! JSONSerialization.data(withJSONObject: artifact).base64EncodedString().replacingOccurrences(of: "+", with: "-").replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "=", with: "")
        let marker = example == "malformed" ? "<!-- cfy-ui:not valid -->" : "<!-- cfy-ui:\(payload) -->"
        let message = ScoutChatMessageSummary(id: 2, role: "assistant", content: "Here is the observed summary.\n\(marker)\nCheck the node for current status.", created_at: "14:06", updated_at: nil)
        if example == "reload" { return try! JSONDecoder().decode(ScoutChatMessageSummary.self, from: JSONEncoder().encode(message)) }
        return message
    }
    private var details: some View {
        GuardianThreadDetailsContent(
            documents: unavailableDetails ? [] : [.init(id: "preview-document", title: "Local network notes", relation: "attachment", created_at: "Today")],
            docMessage: unavailableDetails ? "No documents are available for this preview thread." : nil,
            ragResult: unavailableDetails ? nil : .init(httpStatus: 200, latencyMilliseconds: 24,
                snapshot: .init(from: ["thread_id": 1, "trace_available": true, "documents": ["preview-document"], "graph": [], "retrieval_policy": ["mode": "local"]]),
                message: "Local preview evidence only."),
            ragMessage: unavailableDetails ? "Retrieval evidence unavailable. Access may be denied or the node offline." : nil,
            taskReceipts: unavailableDetails ? [] : [.init(task_id: "preview-task", state: "terminal", event_type: "task.completed", reason: nil)],
            loadDocuments: {}, loadRAGTrace: {}, loadTasks: {}
        )
    }

}
// Real message/GenUI views only; fixture state is never used by ScoutApp.
struct ScoutMessageMaterialPreview: View {
    var longRequest = false
    var includeResponse = true
    var includeTable = false
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ScoutVisualStyle.gap) {
                GuardianGenUIMessageRow(message: .init(id: 1, role: "user", content: longRequest ? "Review this network design before we proceed.\n\nExplain how local ownership, scoped identity, and interrupted delivery affect the smallest useful implementation. Keep the response readable on a narrow phone and distinguish observed state from proposed behavior.\n\nThen identify what we should verify first." : "What should we verify first?", created_at: "14:05", updated_at: nil))
                if includeResponse {
                    GuardianGenUIMessageRow(message: includeTable ? GuardianStylePreview.genUIMessage("table") : .init(id: 2, role: "assistant", content: "Start with the local conversation path. Verify that requests remain scoped to the selected account and that persisted output can be read again after an interruption.", created_at: "14:06", updated_at: nil), renderingEnabled: includeTable)
                }
            }
            .padding(ScoutVisualStyle.inset)
        }
        .modifier(ScoutCanvas())
    }
}
struct ScoutComposerPreview: View {
    @StateObject private var flow = ScoutComposerFlow()
    var longDraft = false
    var sending = false
    var options = false
    var empty = false
    var unavailable = false
    var body: some View {
        ScoutMessageMaterialPreview(includeTable: true)
            .safeAreaInset(edge: .bottom, spacing: 0) {
                ScoutConversationBar(flow: flow, available: !unavailable, hasMessages: true)
            }
            .task {
                let endpoint = ScoutEndpointProfile(id: UUID(), name: "Preview", baseURL: "https://preview.example.test", transportType: .custom, authenticationState: .authenticated, validationState: .reachable, lastConnectedAt: nil)
                let scope = ScoutComposerFlow.Scope(connection: .init(endpoint: endpoint), threadID: 1, accountGeneration: 0)
                flow.select(scope)
                flow.draft = longDraft ? "Review the network design.\nKeep local ownership explicit.\nExplain interrupted delivery.\nDistinguish acceptance from completion.\nUse only authorized evidence.\nThen choose the next step." : "What should we verify next?"
                if empty { flow.draft = "" }
                flow.optionsPresented = options
                if sending {
                    await flow.submit(scope: scope, isCurrent: { true }, save: { _ in
                        try? await Task.sleep(for: .seconds(60))
                        return .init(httpStatus: nil, messageId: nil, message: "Preview only")
                    }, complete: { .init(httpStatus: nil, taskId: nil, turnId: nil, messagesUrl: nil, traceUrl: nil, acceptanceStatus: nil, message: "Preview only") })
                }
            }
    }
}
#Preview("Composer · dark") { ScoutComposerPreview().preferredColorScheme(.dark) }
#Preview("Composer · light") { ScoutComposerPreview().preferredColorScheme(.light) }
#Preview("Composer · multiline") { ScoutComposerPreview(longDraft: true) }
#Preview("Composer · large text") { ScoutComposerPreview().dynamicTypeSize(.accessibility3) }
#Preview("Composer · empty") { ScoutComposerPreview(empty: true) }
#Preview("Composer · unavailable") { ScoutComposerPreview(unavailable: true) }
#Preview("Composer · options") { ScoutComposerPreview(options: true) }
#Preview("Composer · sending") { ScoutComposerPreview(sending: true) }
#Preview("Raised request · dark") { ScoutMessageMaterialPreview(includeResponse: false).preferredColorScheme(.dark) }
#Preview("Raised request · light") { ScoutMessageMaterialPreview(includeResponse: false).preferredColorScheme(.light) }
#Preview("Raised request · multiline") { ScoutMessageMaterialPreview(longRequest: true).preferredColorScheme(.dark) }
#Preview("Unframed Guardian and table") { ScoutMessageMaterialPreview(includeTable: true) }
#Preview("Raised request · large text") { ScoutMessageMaterialPreview(longRequest: true).dynamicTypeSize(.accessibility3) }
#Preview("Raised request · opaque face") { ScoutMessageMaterialPreview().preferredColorScheme(.light) }
#Preview("Threads · light") { GuardianStylePreview().preferredColorScheme(.light) }
#Preview("Conversation · dark") { GuardianStylePreview(conversation: true).preferredColorScheme(.dark) }
#Preview("Accessible text") { GuardianStylePreview(conversation: true).dynamicTypeSize(.accessibility3) }
#Preview("Thread details · populated") { GuardianStylePreview(conversation: true, detailsInitiallyOpen: true).preferredColorScheme(.dark) }
#Preview("Thread details · unavailable") { GuardianStylePreview(conversation: true, detailsInitiallyOpen: true, unavailableDetails: true).preferredColorScheme(.light) }
#Preview("Thread details · accessible") { GuardianStylePreview(conversation: true, detailsInitiallyOpen: true).dynamicTypeSize(.accessibility3) }
#Preview("OpenUI · foundation cards") { GuardianStylePreview(conversation: true, genUIExample: "openui") }
#Preview("GenUI · light") { GuardianStylePreview(conversation: true, genUIExample: "table").preferredColorScheme(.light) }
#Preview("GenUI · dark") { GuardianStylePreview(conversation: true, genUIExample: "table").preferredColorScheme(.dark) }
#Preview("GenUI · large text") { GuardianStylePreview(conversation: true, genUIExample: "table").dynamicTypeSize(.accessibility3) }
#Preview("GenUI · empty") { GuardianStylePreview(conversation: true, genUIExample: "empty") }
#Preview("GenUI · unsupported") { GuardianStylePreview(conversation: true, genUIExample: "unsupported") }
#Preview("GenUI · malformed") { GuardianStylePreview(conversation: true, genUIExample: "malformed") }
#Preview("GenUI · reloaded") { GuardianStylePreview(conversation: true, genUIExample: "reload") }
#Preview("GenUI · disabled") { GuardianStylePreview(conversation: true, genUIExample: "disabled") }
#endif
