import SwiftUI

private func widgetService(_ data: Data) throws -> ScoutSavedWidgets {
    let profile = try JSONDecoder().decode(ScoutEndpointProfile.self, from: data)
    let key = profile.authenticationMode == .localAPIKey ? try ScoutKeychainStore().loadAPIKey(for: profile) : nil
    return ScoutSavedWidgets(transport: ScoutLibraryService(endpoint: profile, apiKey: key))
}

struct ScoutSavedWidgetsView: View {
    var isActive: Bool
    @AppStorage("scout.activeEndpointProfile") private var profile = Data()
    @Environment(\.dynamicTypeSize) private var textSize
    @State private var widgets: [ScoutSavedWidget] = []
    @State private var next: Int?
    @State private var busy = false
    @State private var error: String?
    @State private var selected: ScoutSavedWidget?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Saved widgets", systemImage: "square.stack.3d.up").font(.headline)
            if let error { Text(error).foregroundStyle(.secondary) }
            if busy { ProgressView("Loading widgets…") }
            if widgets.isEmpty && !busy && error == nil { Text("Save a widget from a Guardian response to see it here.") }
            if let service = try? widgetService(profile) {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: textSize.isAccessibilitySize ? 240 : 145),
                                             spacing: ScoutVisualStyle.inset)], spacing: ScoutVisualStyle.inset) {
                    ForEach(widgets) { widget in
                        Button { selected = widget } label: {
                            VStack(alignment: .leading, spacing: ScoutVisualStyle.gap) {
                                ScoutSavedWidgetThumbnail(widget: widget, service: service)
                                    .frame(height: 126)
                                    .frame(maxWidth: .infinity)
                                    .background(.quaternary, in: RoundedRectangle(cornerRadius: ScoutVisualStyle.radius / 2))
                                    .clipShape(RoundedRectangle(cornerRadius: ScoutVisualStyle.radius / 2))
                                Text(widget.name).font(.subheadline.weight(.semibold)).lineLimit(2)
                                Text("Version \(widget.current_revision)").font(.caption).foregroundStyle(.secondary)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .modifier(ScoutPanel(secondary: true, verticalInset: ScoutVisualStyle.inset / 2))
                        }
                        .buttonStyle(.plain)
                        .accessibilityHint("Opens this widget’s launch controls")
                    }
                }
            }
            if let next { Button("Load more widgets") { Task { await load(next) } }.disabled(busy) }
            Button("Refresh widgets") { Task { await load() } }.disabled(busy)
        }
        .modifier(ScoutPanel(subtleOutline: true))
        .task(id: isActive) { if isActive { await load() } else { selected = nil } }
        .sheet(item: $selected) { widget in
            if let service = try? widgetService(profile) { ScoutSavedWidgetLaunch(widget: widget, service: service) }
        }
    }

    @MainActor private func load(_ offset: Int = 0) async {
        guard isActive else { return }
        busy = true; error = nil
        defer { busy = false }
        do {
            let page = try await widgetService(profile).list(offset: offset)
            guard !Task.isCancelled else { return }
            var seen = Set<String>()
            widgets = ((offset == 0 ? [] : widgets) + page.widgets).filter { seen.insert($0.id).inserted }
            next = page.next_offset
        } catch { if !Task.isCancelled { self.error = error.localizedDescription } }
    }
}

private struct ScoutSavedWidgetThumbnail: View {
    let widget: ScoutSavedWidget
    let service: ScoutSavedWidgets
    @State private var source: ScoutSandboxWidget?

    var body: some View {
        Group {
            if let source {
                ScoutWidgetThumbnail(widget: source)
            } else {
                Image(systemName: "square.stack.3d.up").foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .accessibilityHidden(true)
        .task(id: widget) {
            source = nil
            let preview = try? await service.artifact(widget, revision: widget.current_revision)
            if !Task.isCancelled { source = preview }
        }
    }
}

private struct ScoutSavedWidgetLaunch: View {
    let widget: ScoutSavedWidget
    let service: ScoutSavedWidgets
    @Environment(\.dismiss) private var dismiss
    @State private var revisions: [Int] = []
    @State private var revision = 0
    @State private var running: ScoutSandboxWidget?
    @State private var busy = false
    @State private var error: String?
    var body: some View {
        NavigationStack {
            VStack(spacing: ScoutVisualStyle.gap) {
                Picker("Version", selection: $revision) {
                    ForEach(revisions, id: \.self) { Text("Version \($0)").tag($0) }
                }.disabled(busy)
                if let error { Text(error).font(.footnote).foregroundStyle(.secondary) }
                if let running {
                    ScoutSandboxWidgetView(widget: running, isActive: true, fillsAvailableHeight: true).id(revision)
                } else {
                    Spacer()
                    if busy {
                        ProgressView("Opening widget…")
                    } else {
                        Button("Launch widget") { Task { await launch() } }
                            .buttonStyle(.borderedProminent)
                            .disabled(revision < 1)
                    }
                    Spacer()
                }
            }
            .padding(ScoutVisualStyle.inset)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .navigationTitle(widget.name)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { running = nil; dismiss() } } }
        }
        .onChange(of: revision) { _, _ in running = nil }
        .task {
            revision = widget.current_revision
            revisions = [revision]
            do {
                let available = try await service.revisions(widget)
                if !Task.isCancelled { revisions = available.isEmpty ? [revision] : available }
            } catch { if !Task.isCancelled { self.error = error.localizedDescription } }
        }
    }
    @MainActor private func launch() async {
        busy = true; error = nil
        defer { busy = false }
        let requested = revision
        do {
            let artifact = try await service.artifact(widget, revision: requested)
            if !Task.isCancelled, revision == requested { running = artifact }
        } catch { if !Task.isCancelled { self.error = error.localizedDescription } }
    }
}

struct ScoutWidgetSaveControls: View {
    let message: ScoutChatMessageSummary
    let thread: Int
    @AppStorage("scout.activeEndpointProfile") private var profile = Data()
    @State private var candidate: ScoutSavedWidgets.Candidate?
    var body: some View {
        ForEach(ScoutSavedWidgets.candidates(message)) { item in
            Button("Save \(item.title) to Library") { candidate = item }.buttonStyle(.bordered)
        }
        .sheet(item: $candidate) { item in
            if let id = message.id, let service = try? widgetService(profile) {
                ScoutWidgetSaveForm(service: service, thread: thread, message: id, candidate: item)
            }
        }
    }
}

private struct ScoutWidgetSaveForm: View {
    let service: ScoutSavedWidgets
    let thread: Int
    let message: Int
    let candidate: ScoutSavedWidgets.Candidate
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var widgets: [ScoutSavedWidget] = []
    @State private var target = ""
    @State private var next: Int?
    @State private var busy = false
    @State private var notice: String?
    @State private var saved = false
    var body: some View {
        NavigationStack {
            Form {
                Picker("Save as", selection: $target) {
                    Text("New widget / separate copy").tag("")
                    ForEach(widgets) { Text("\($0.name) · after version \($0.current_revision)").tag($0.id) }
                }.disabled(busy || saved)
                if target.isEmpty { TextField("Widget name", text: $name).disabled(busy || saved) }
                if let next { Button("Load more widgets") { Task { await load(next) } }.disabled(busy || saved) }
                Text("Earlier versions remain available. A separate copy preserves the original widget.").font(.caption)
                if let notice { Text(notice) }
                Button(busy ? "Saving…" : target.isEmpty ? "Save as new" : "Save new version") {
                    Task { await save() }
                }.disabled(busy || saved || (target.isEmpty && name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty))
            }
            .navigationTitle("Save widget")
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() }.disabled(busy) } }
        }
        .task { name = candidate.title; await load() }
    }
    @MainActor private func load(_ offset: Int = 0) async {
        do { let page = try await service.list(offset: offset); widgets += page.widgets; next = page.next_offset }
        catch { notice = "Existing widgets could not be loaded. You can still save as new." }
    }
    @MainActor private func save() async {
        busy = true; notice = nil
        defer { busy = false }
        do {
            let version = try await service.save(thread: thread, message: message, index: candidate.id,
                                                 name: name, target: widgets.first { $0.id == target })
            saved = true; notice = "Saved version \(version) to Library."
        } catch { notice = ScoutSavedWidgets.saveFailureMessage(error) }
    }
}
