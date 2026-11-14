import SwiftUI
import ImageIO

struct ArtifactsView: View {
    var isActive = true
    @AppStorage("scout.activeEndpointProfile") private var storedProfileData: Data = Data()
    @AppStorage("scout.accountSessionGeneration") private var sessionGeneration = 0
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.dynamicTypeSize) private var textSize
    @Environment(\.scoutOpenAuxiliary) private var openAuxiliary
    @State private var filter: ScoutLibraryFilter = .all
    @State private var snapshot: ScoutLibrarySnapshot?
    @State private var service: ScoutLibraryService?
    @State private var error: String?
    @State private var isLoading = false
    @State private var refreshID = UUID()
    @State private var preview: ScoutLibraryResource?
    @State private var loadingPage: ScoutLibrarySource?
    @State private var pageRequestID = UUID()

    private struct ReadIdentity: Hashable {
        let profile: Data
        let account: Int
        let filter: ScoutLibraryFilter
        let active: Bool
        let refresh: UUID
    }
    private var readIdentity: ReadIdentity {
        .init(profile: storedProfileData, account: sessionGeneration, filter: filter, active: isActive, refresh: refreshID)
    }

    var body: some View {
        VStack(spacing: ScoutVisualStyle.inset) {
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Your Library").font(.title2.bold())
                    Text("All resources available to your account")
                        .font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                Button { refreshID = UUID() } label: {
                    Image(systemName: "arrow.clockwise").frame(minWidth: 44, minHeight: 44)
                }
                .accessibilityLabel("Refresh Library")
                .disabled(isLoading || loadingPage != nil)
            }
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(ScoutLibraryFilter.allCases) { item in
                        Button { filter = item } label: {
                            Text(item.title).font(.subheadline.weight(.semibold))
                                .padding(.horizontal, 16).frame(minHeight: 44)
                                .background(filter == item ? Color.accentColor.opacity(0.18) : Color.primary.opacity(0.05), in: Capsule())
                                .overlay(Capsule().strokeBorder(filter == item ? Color.accentColor : Color.primary.opacity(0.15)))
                        }
                        .buttonStyle(.plain)
                        .accessibilityAddTraits(filter == item ? .isSelected : [])
                    }
                }
            }
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ScoutVisualStyle.inset) {
                    if isLoading { ProgressView("Loading Library…").frame(maxWidth: .infinity).padding() }
                    if let error {
                        GuardianStatusRow(title: "Library unavailable", detail: error, error: true)
                    }
                    if let snapshot {
                        if let failure = snapshot.commonFailure {
                            GuardianStatusRow(title: "Connect to your Library", detail: failure, error: true)
                            Button("Connection settings") { openAuxiliary(.settings) }
                                .buttonStyle(.bordered)
                        } else {
                            ForEach(snapshot.issues, id: \.self) { issue in
                                GuardianStatusRow(title: "Some results are unavailable", detail: issue, error: true)
                            }
                            if filter == .all || filter == .images { gallery(snapshot) }
                            if filter == .all || filter == .documents { documents(snapshot) }
                        }
                    }
                    if filter == .widgets || filter == .all {
                        VStack(alignment: .leading, spacing: 10) {
                            Label("Widgets", systemImage: "square.stack.3d.up").font(.headline)
                            Text(ScoutLibraryService.widgetsMessage).font(.subheadline).foregroundStyle(.secondary)
                        }.modifier(ScoutPanel(subtleOutline: true))
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.bottom, ScoutVisualStyle.inset)
            }
            .refreshable { refreshID = UUID() }
        }
        .padding(.horizontal, ScoutVisualStyle.inset)
        .task(id: readIdentity) { await load(identity: readIdentity) }
        .onChange(of: isActive) { _, active in if !active { preview = nil } }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active && isActive { refreshID = UUID() }
        }
        .sheet(item: $preview) { resource in
            if let service { ScoutLibraryPreview(resource: resource, service: service) }
        }
    }

    private func gallery(_ snapshot: ScoutLibrarySnapshot) -> some View {
        let images = snapshot.resources.filter(\.isImage)
        return VStack(alignment: .leading, spacing: ScoutVisualStyle.inset) {
            sectionHeading("Gallery", symbol: "photo.on.rectangle", count: images.count)
            if images.isEmpty {
                emptyState("No images to display", complete: snapshot.sources.filter { $0.source != .documents }.allSatisfy { $0.issue == nil })
            } else if let service {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: textSize.isAccessibilitySize ? 240 : 145), spacing: 12)], spacing: 12) {
                    ForEach(images) { resource in
                        Button { preview = resource } label: {
                            VStack(alignment: .leading, spacing: 8) {
                                ScoutLibraryThumbnail(resource: resource, service: service)
                                    .frame(height: 140).frame(maxWidth: .infinity)
                                    .background(Color.primary.opacity(0.05), in: RoundedRectangle(cornerRadius: 12))
                                    .clipShape(RoundedRectangle(cornerRadius: 12))
                                Text(resource.title).font(.subheadline.weight(.medium)).lineLimit(2)
                                provenance(resource)
                            }
                            .padding(10)
                            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: ScoutVisualStyle.radius))
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("Open image: " + resource.title)
                    }
                }
            }
            pageButtons(snapshot.sources.filter { $0.source != .documents })
        }
    }

    private func documents(_ snapshot: ScoutLibrarySnapshot) -> some View {
        let documents = snapshot.resources.filter { !$0.isImage }
        return VStack(alignment: .leading, spacing: ScoutVisualStyle.inset) {
            sectionHeading("Documents", symbol: "doc.text", count: documents.count)
            if documents.isEmpty {
                emptyState("No documents to display", complete: snapshot.sources.filter { $0.source == .documents }.allSatisfy { $0.issue == nil })
            } else {
                ForEach(documents) { resource in
                    Button { preview = resource } label: {
                        HStack(spacing: 12) {
                            Image(systemName: "doc.text").font(.title2).foregroundStyle(.tint)
                            VStack(alignment: .leading, spacing: 5) {
                                Text(resource.title).font(.headline).multilineTextAlignment(.leading)
                                provenance(resource)
                            }
                            Spacer(minLength: 0)
                            Image(systemName: "chevron.right").font(.caption).foregroundStyle(.secondary)
                        }.modifier(ScoutPanel(subtleOutline: true))
                    }.buttonStyle(.plain)
                    .accessibilityLabel("Open document: " + resource.title)
                }
            }
            pageButtons(snapshot.sources.filter { $0.source == .documents })
        }
    }

    private func pageButtons(_ sources: [ScoutLibrarySourceResult]) -> some View {
        ForEach(sources.filter { $0.nextOffset != nil }, id: \.source) { source in
            Button {
                let identity = readIdentity
                Task { await loadNextPage(source, identity: identity) }
            } label: {
                HStack {
                    if loadingPage == source.source { ProgressView() }
                    Text("Load more " + source.source.title.lowercased())
                }.frame(maxWidth: .infinity, minHeight: 44)
            }
            .buttonStyle(.bordered)
            .disabled(isLoading || loadingPage != nil)
        }
    }

    @MainActor
    private func loadNextPage(_ source: ScoutLibrarySourceResult, identity: ReadIdentity) async {
        guard identity == readIdentity, loadingPage == nil,
              let offset = source.nextOffset, let service else { return }
        let requestID = UUID()
        pageRequestID = requestID
        loadingPage = source.source
        let page = await service.fetch(source.source, offset: offset)
        guard identity == readIdentity, requestID == pageRequestID else { return }
        loadingPage = nil
        guard let current = snapshot else { return }
        snapshot = ScoutLibrarySnapshot(sources: current.sources.map {
            $0.source == source.source ? $0.appending(page) : $0
        })
    }

    private func sectionHeading(_ title: String, symbol: String, count: Int) -> some View {
        HStack {
            Label(title, systemImage: symbol).font(.headline)
            Spacer()
            Text("\(count)").font(.caption.monospacedDigit()).foregroundStyle(.secondary)
        }.accessibilityElement(children: .combine)
    }
    private func provenance(_ resource: ScoutLibraryResource) -> some View {
        Text(resource.origin == "unknown" ? "Origin unknown" : resource.origin.capitalized)
            .font(.caption).foregroundStyle(.secondary)
    }
    private func emptyState(_ title: String, complete: Bool) -> some View {
        Text(complete ? title : "Resources could not all be loaded. Use Refresh to try again.")
            .font(.subheadline).foregroundStyle(.secondary).padding(.vertical)
    }

    @MainActor
    private func load(identity: ReadIdentity) async {
        pageRequestID = UUID()
        loadingPage = nil
        guard identity.active else { isLoading = false; return }
        snapshot = nil; error = nil; service = nil
        guard identity.filter != .widgets else { isLoading = false; return }
        guard let profile = try? JSONDecoder().decode(ScoutEndpointProfile.self, from: identity.profile) else {
            error = "Choose your hosted Codexify connection in Settings."; isLoading = false; return
        }
        isLoading = true
        do {
            let key = profile.authenticationMode == .localAPIKey ? try ScoutKeychainStore().loadAPIKey(for: profile) : nil
            let nextService = ScoutLibraryService(endpoint: profile, apiKey: key)
            let result = await nextService.load(identity.filter)
            guard !Task.isCancelled, identity == readIdentity else { return }
            service = nextService; snapshot = result; isLoading = false
        } catch {
            guard !Task.isCancelled, identity == readIdentity else { return }
            self.error = error.localizedDescription; isLoading = false
        }
    }
}

/// Downsample before handing images to SwiftUI; no disk cache or unauthenticated
/// AsyncImage path, and no executable SVG/HTML rendering.
private enum ScoutLibraryImage {
    static func decode(_ data: Data, maxPixel: Int) -> UIImage? {
        guard let source = CGImageSourceCreateWithData(data as CFData, nil),
              let image = CGImageSourceCreateThumbnailAtIndex(source, 0, [
                kCGImageSourceCreateThumbnailFromImageAlways: true,
                kCGImageSourceThumbnailMaxPixelSize: maxPixel,
                kCGImageSourceCreateThumbnailWithTransform: true,
                kCGImageSourceShouldCacheImmediately: true
              ] as CFDictionary) else { return nil }
        return UIImage(cgImage: image)
    }
}

private struct ScoutLibraryThumbnail: View {
    let resource: ScoutLibraryResource
    let service: ScoutLibraryService
    @State private var image: UIImage?
    @State private var failed = false
    var body: some View {
        Group {
            if let image { Image(uiImage: image).resizable().scaledToFit() }
            else if failed { Label("Preview unavailable", systemImage: "photo").font(.caption).foregroundStyle(.secondary) }
            else { ProgressView() }
        }
        .accessibilityHidden(true)
        .task(id: resource) {
            do {
                let media = try await service.media(resource)
                let decoded = ScoutLibraryImage.decode(media.data, maxPixel: 600)
                guard !Task.isCancelled else { return }
                image = decoded; failed = decoded == nil
            } catch { if !Task.isCancelled { failed = true } }
        }
    }
}

private struct ScoutLibraryPreview: View {
    let resource: ScoutLibraryResource
    let service: ScoutLibraryService
    @Environment(\.dismiss) private var dismiss
    @State private var image: UIImage?
    @State private var text: String?
    @State private var starts: [String.Index] = []
    @State private var error: String?
    @State private var loading = true
    @State private var reload = UUID()

    var body: some View {
        NavigationStack {
            Group {
                if loading { ProgressView("Opening preview…") }
                else if let image {
                    Image(uiImage: image).resizable().scaledToFit().padding()
                        .accessibilityLabel(resource.title)
                } else if let text {
                    reader(text)
                } else {
                    ContentUnavailableView {
                        Label("Preview unavailable", systemImage: "doc.questionmark")
                    } description: { Text(error ?? "No readable content was returned.") }
                    actions: { Button("Try again") { reload = UUID() } }
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .modifier(ScoutCanvas())
            .navigationTitle(resource.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
            .task(id: reload) { await load() }
        }
    }

    private func reader(_ text: String) -> some View {
        let page = ScoutDocumentPage(text, from: starts.last)
        return VStack {
            ScrollView {
                Text(verbatim: page.text).font(.body).textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading).padding()
            }.id(starts.count)
            if page.nextStart != nil || !starts.isEmpty {
                HStack {
                    Button("Previous") { _ = starts.popLast() }.disabled(starts.isEmpty)
                    Spacer()
                    Text("Page \(starts.count + 1)").font(.caption)
                    Spacer()
                    Button("Next") { if let next = page.nextStart { starts.append(next) } }.disabled(page.nextStart == nil)
                }.padding()
            }
        }
    }

    @MainActor
    private func load() async {
        loading = true; image = nil; text = nil; error = nil; starts = []
        do {
            if resource.isImage {
                let media = try await service.media(resource)
                guard let decoded = ScoutLibraryImage.decode(media.data, maxPixel: 2400) else { throw ScoutLibraryError.unavailablePreview }
                try Task.checkCancellation(); image = decoded
            } else {
                let value = try await service.documentText(resource)
                try Task.checkCancellation()
                guard let value else { throw ScoutLibraryError.unavailablePreview }
                text = value
            }
            loading = false
        } catch {
            guard !Task.isCancelled else { return }
            self.error = error.localizedDescription; loading = false
        }
    }
}
