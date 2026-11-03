import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import LibraryView from "@/components/library/LibraryView";
import { dispatchAccountImportRefresh } from "@/hooks/useLiveEvents";
import type { LiveEvent } from "@/lib/events/types";
import type { LibraryResourceProjection } from "@/components/library/libraryResourceProjection";

const buildProjection = vi.fn();
vi.mock("@/components/library/libraryResourceProjection", async () => {
  const actual = await vi.importActual<typeof import("@/components/library/libraryResourceProjection")>(
    "@/components/library/libraryResourceProjection"
  );
  return { ...actual, buildLibraryResourceProjection: (...args: unknown[]) => buildProjection(...args) };
});
vi.mock("@/hooks/useUploader", () => ({
  default: () => ({
    onDrop: vi.fn(),
    onDragOver: vi.fn(),
    pick: vi.fn(),
  }),
}));
vi.mock("@/components/documents/DocumentsView", () => ({
  default: () => <div data-testid="documents-view-mock">Documents mode</div>,
}));
vi.mock("@/components/documents/DocumentTile", () => ({
  default: () => <div data-testid="document-tile-mock">Document tile</div>,
}));
vi.mock("@/components/gallery/GalleryGrid", () => ({
  default: ({ items }: { items: Array<{ id?: string; deletionId?: string }> }) => (
    <>
      <div data-testid="gallery-grid-mock">{items.length} images</div>
      <div data-testid="gallery-grid-identities">
        {items
          .map((item) => `${item.id ?? "none"}|${item.deletionId ?? "none"}`)
          .join(",")}
      </div>
    </>
  ),
}));

const extColors = {
  pdf: "#ef4444",
  doc: "#0ea5e9",
  md: "#6366f1",
  png: "#06b6d4",
  sketch: "#f59e0b",
  txt: "#06b6d4",
  docx: "#2563eb",
  jpeg: "#d946ef",
  codex: "#22c55e",
};

const scope = { kind: "project" as const, projectId: 7, threadId: null };
const image = {
  presentationKey: "uploaded_image:img-1",
  sourceFamily: "uploaded_image" as const,
  sourceId: "img-1",
  resourceType: "image" as const,
  origin: "uploaded" as const,
  title: "one.png",
  sourceTag: null,
  srcUrl: "/media/images/one.png",
  mimeType: "image/png",
  filename: "one.png",
  projectId: 7,
  threadIds: [],
  createdAt: null,
  raw: {},
};
const generatedImage = {
  presentationKey: "generated_image:gen-1",
  sourceFamily: "generated_image" as const,
  sourceId: "gen-1",
  resourceType: "image" as const,
  origin: "unknown" as const,
  title: "generated.png",
  sourceTag: null,
  srcUrl: "/media/images/generated.png",
  mimeType: "image/png",
  filename: "generated.png",
  projectId: 7,
  threadIds: [],
  createdAt: null,
  raw: {},
};
const document = {
  presentationKey: "uploaded_document:doc-1",
  sourceFamily: "uploaded_document" as const,
  sourceId: "doc-1",
  resourceType: "document" as const,
  origin: "imported" as const,
  title: "notes.pdf",
  sourceTag: "imported",
  srcUrl: null,
  mimeType: "application/pdf",
  filename: "notes.pdf",
  projectId: 7,
  threadIds: [],
  createdAt: null,
  raw: {},
};

function projection(filter: LibraryResourceProjection["filter"]): LibraryResourceProjection {
  return {
    filter,
    scope,
    resources: filter === "images" ? [image] : filter === "documents" ? [document] : filter === "widgets" ? [] : [image, document],
    sources: [],
    completeness: filter === "widgets"
      ? {
          complete: false,
          coverage: "unavailable",
          detail: "No authoritative Widget backing record, persistence, or versioned listing mechanism exists yet.",
          incompleteSources: [],
          boundedSources: [],
          failedSources: [],
          uncertainSources: [],
        }
      : {
          complete: true,
          coverage: "known",
          detail: "All contributing source(s) reported proven coverage.",
          incompleteSources: [],
          boundedSources: [],
          failedSources: [],
          uncertainSources: [],
        },
    widgetDiscovery: { available: false, reason: "unavailable" },
    rejected: [],
  };
}

describe("LibraryView", () => {
  beforeEach(() => {
    buildProjection.mockReset();
    buildProjection.mockImplementation(({ filter }: { filter: LibraryResourceProjection["filter"] }) =>
      Promise.resolve(projection(filter))
    );
  });

  it("renders the approved four filters as accessible tabs", async () => {
    render(
      <LibraryView
        scope={scope}
        extColors={extColors}
        filter="all"
        onFilterChange={vi.fn()}
      />
    );
    await waitFor(() => expect(screen.getByTestId("library-filter-all")).toHaveAttribute("aria-selected", "true"));
    expect(screen.getByRole("tab", { name: "All" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Images" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Documents" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Widgets" })).toBeInTheDocument();
  });

  it("renders the surface for the filter it is given", async () => {
    render(
      <LibraryView
        scope={scope}
        extColors={extColors}
        filter="documents"
        onFilterChange={vi.fn()}
      />
    );
    await waitFor(() => expect(buildProjection).toHaveBeenLastCalledWith(expect.objectContaining({ filter: "documents" })));
    expect(screen.getByTestId("documents-view-mock")).toBeInTheDocument();
    expect(screen.getByTestId("library-filter-documents")).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByTestId("library-filter-all")).toHaveAttribute(
      "aria-selected",
      "false"
    );
  });

  it("reports a filter change to its owner instead of holding filter state", async () => {
    const onFilterChange = vi.fn();
    render(
      <LibraryView
        scope={scope}
        extColors={extColors}
        filter="all"
        onFilterChange={onFilterChange}
      />
    );
    await waitFor(() => expect(screen.getByTestId("gallery-grid-mock")).toHaveTextContent("1 images"));

    fireEvent.click(screen.getByRole("tab", { name: "Documents" }));

    expect(onFilterChange).toHaveBeenCalledWith("documents");
    // The view does not move itself; the owner decides, and the URL decides
    // for the owner.
    expect(screen.getByTestId("library-filter-all")).toHaveAttribute(
      "aria-selected",
      "true"
    );
  });

  it("states that Widgets are unavailable without creating records", async () => {
    render(
      <LibraryView
        scope={scope}
        extColors={extColors}
        filter="widgets"
        onFilterChange={vi.fn()}
      />
    );
    await waitFor(() => expect(screen.getByTestId("library-widgets-unavailable")).toBeInTheDocument());
    expect(screen.getByTestId("library-unavailable")).toHaveTextContent(/no authoritative widget/i);
    expect(buildProjection).toHaveBeenLastCalledWith(expect.objectContaining({ filter: "widgets" }));
  });

  it("keeps the family-qualified presentation key as the tile identity", async () => {
    render(
      <LibraryView
        scope={scope}
        extColors={extColors}
        filter="images"
        onFilterChange={vi.fn()}
      />
    );

    await waitFor(() => expect(screen.getByTestId("gallery-grid-identities")).toHaveTextContent("uploaded_image:img-1"));
  });

  it("carries the canonical source id as the deletion target for uploaded images", async () => {
    render(
      <LibraryView
        scope={scope}
        extColors={extColors}
        filter="images"
        onFilterChange={vi.fn()}
      />
    );

    await waitFor(() =>
      expect(screen.getByTestId("gallery-grid-identities")).toHaveTextContent(
        "uploaded_image:img-1|img-1"
      )
    );
  });

  it("carries no deletion target for generated images", async () => {
    buildProjection.mockImplementation(
      ({ filter }: { filter: LibraryResourceProjection["filter"] }) =>
        Promise.resolve({
          ...projection(filter),
          resources:
            filter === "documents" || filter === "widgets"
              ? []
              : filter === "images"
                ? [generatedImage]
                : [generatedImage],
        })
    );

    render(
      <LibraryView
        scope={scope}
        extColors={extColors}
        filter="images"
        onFilterChange={vi.fn()}
      />
    );

    await waitFor(() =>
      expect(screen.getByTestId("gallery-grid-identities")).toHaveTextContent(
        "generated_image:gen-1|none"
      )
    );
  });
});

describe("LibraryView gallery refresh event", () => {
  beforeEach(() => {
    buildProjection.mockReset();
    buildProjection.mockImplementation(
      ({ filter }: { filter: LibraryResourceProjection["filter"] }) =>
        Promise.resolve(projection(filter))
    );
  });

  const renderLibrary = (filter: LibraryResourceProjection["filter"]) =>
    render(
      <LibraryView
        scope={scope}
        extColors={extColors}
        filter={filter}
        onFilterChange={vi.fn()}
      />
    );

  const dispatchGalleryRefresh = () => {
    window.dispatchEvent(
      new CustomEvent("cfy:gallery:refresh", {
        detail: { source: "openai-account-import", job_id: "job-1" },
      })
    );
  };

  it("re-queries the projection when the Images filter is active", async () => {
    renderLibrary("images");
    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(1));

    dispatchGalleryRefresh();

    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(2));
  });

  it("re-queries the projection when the All filter is active", async () => {
    renderLibrary("all");
    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(1));

    dispatchGalleryRefresh();

    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(2));
  });

  it("causes exactly one additional projection invocation per event", async () => {
    renderLibrary("images");
    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(1));

    dispatchGalleryRefresh();
    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(2));

    dispatchGalleryRefresh();
    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(3));
    expect(buildProjection).toHaveBeenCalledTimes(3);
  });

  it("preserves the filter and the exact scope on the refresh", async () => {
    renderLibrary("images");
    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(1));

    dispatchGalleryRefresh();

    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(2));
    expect(buildProjection).toHaveBeenLastCalledWith({
      filter: "images",
      scope,
    });
  });

  it("shows the updated authoritative projection results after a refresh", async () => {
    renderLibrary("images");
    await waitFor(() =>
      expect(screen.getByTestId("gallery-grid-identities")).toHaveTextContent(
        "uploaded_image:img-1|img-1"
      )
    );

    // The authoritative source now reports a different record.
    buildProjection.mockImplementation(
      ({ filter }: { filter: LibraryResourceProjection["filter"] }) =>
        Promise.resolve(
          filter === "images"
            ? {
                ...projection(filter),
                resources: [
                  {
                    ...image,
                    presentationKey: "uploaded_image:img-2",
                    sourceId: "img-2",
                    title: "two.png",
                    filename: "two.png",
                    srcUrl: "/media/images/two.png",
                  },
                ],
              }
            : projection(filter)
        )
    );

    dispatchGalleryRefresh();

    await waitFor(() =>
      expect(screen.getByTestId("gallery-grid-identities")).toHaveTextContent(
        "uploaded_image:img-2|img-2"
      )
    );
  });

  it("does not re-query for a Gallery event on Documents or Widgets", async () => {
    renderLibrary("documents");
    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(1));

    dispatchGalleryRefresh();

    await waitFor(() => expect(screen.getByTestId("documents-view-mock")).toBeInTheDocument());
    expect(buildProjection).toHaveBeenCalledTimes(1);

    cleanup();
    buildProjection.mockClear();
    renderLibrary("widgets");
    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(1));

    dispatchGalleryRefresh();

    await waitFor(() =>
      expect(screen.getByTestId("library-widgets-unavailable")).toBeInTheDocument()
    );
    expect(buildProjection).toHaveBeenCalledTimes(1);
  });

  it("removes the listener on unmount so no request follows", async () => {
    const { unmount } = renderLibrary("images");
    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(1));

    unmount();
    dispatchGalleryRefresh();

    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(buildProjection).toHaveBeenCalledTimes(1);
  });

  it("refreshes from the real account-import producer after a committed media batch", async () => {
    renderLibrary("images");
    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(1));

    dispatchAccountImportRefresh({
      id: "event-media-library",
      type: "account_import.batch_committed",
      data: { job_id: "job-library", status: "running", batch_kind: "media" },
    } as LiveEvent);

    await waitFor(() => expect(buildProjection).toHaveBeenCalledTimes(2));
    expect(buildProjection).toHaveBeenLastCalledWith({
      filter: "images",
      scope,
    });
  });
});
