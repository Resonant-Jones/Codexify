import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Integrated image-action proof for Library.
 *
 * This exercises the **real** Library → GalleryGrid → MediaTile path, not a
 * mocked navigation callback: the tile renders, its context menu opens, and the
 * deletion argument is observed at the transport boundary.
 */

const { deleteAssetMock, downloadAssetMock } = vi.hoisted(() => ({
  deleteAssetMock: vi.fn(),
  downloadAssetMock: vi.fn(),
}));

vi.mock("@/lib/assetActions", () => ({
  deleteAsset: deleteAssetMock,
  downloadAsset: downloadAssetMock,
  notifyAssetActionError: vi.fn(),
  resolveAssetDownloadUrl: (url?: string) => url || "",
}));

vi.mock("@/lib/runtimeConfig", () => ({
  resolveBackendUrl: (path: string) =>
    `http://backend.test${path.startsWith("/") ? path : `/${path}`}`,
  getRuntimeConfigSync: () => ({
    mode: "web",
    backendBaseUrl: "http://backend.test",
    apiBaseUrl: "http://backend.test/api",
    sseUrl: "http://backend.test/api/events",
    sharePublicBaseUrl: "http://share.test",
    authMode: "local",
  }),
  isTauriRuntime: () => false,
  invokeTauriCommand: vi.fn(),
}));

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

const buildProjection = vi.fn();
vi.mock("@/components/library/libraryResourceProjection", async () => {
  const actual = await vi.importActual<
    typeof import("@/components/library/libraryResourceProjection")
  >("@/components/library/libraryResourceProjection");
  return {
    ...actual,
    buildLibraryResourceProjection: (...args: unknown[]) => buildProjection(...args),
  };
});

import LibraryView from "@/components/library/LibraryView";
import type {
  LibraryResource,
  LibraryResourceProjection,
} from "@/components/library/libraryResourceProjection";

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

function uploadedImage(overrides: Partial<LibraryResource> = {}): LibraryResource {
  return {
    presentationKey: "uploaded_image:img-1",
    sourceFamily: "uploaded_image",
    sourceId: "img-1",
    resourceType: "image",
    origin: "uploaded",
    title: "one.png",
    sourceTag: null,
    srcUrl: "/media/images/one.png",
    mimeType: "image/png",
    filename: "one.png",
    projectId: 7,
    threadIds: [],
    createdAt: null,
    raw: {},
    ...overrides,
  };
}

function generatedImage(): LibraryResource {
  return {
    presentationKey: "generated_image:gen-1",
    sourceFamily: "generated_image",
    sourceId: "gen-1",
    resourceType: "image",
    origin: "unknown",
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
}

function projection(
  filter: LibraryResourceProjection["filter"],
  resources: LibraryResource[]
): LibraryResourceProjection {
  return {
    filter,
    scope,
    resources,
    sources: [],
    completeness: {
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

function renderLibrary(
  filter: LibraryResourceProjection["filter"],
  resources: LibraryResource[],
  onImageSelect?: (prompt: string) => void
) {
  buildProjection.mockImplementation(
    ({ filter: requested }: { filter: LibraryResourceProjection["filter"] }) =>
      Promise.resolve(projection(requested, resources))
  );
  return render(
    <LibraryView
      scope={scope}
      extColors={extColors}
      filter={filter}
      onFilterChange={vi.fn()}
      onImageSelect={onImageSelect}
    />
  );
}

describe("Library image actions", () => {
  beforeEach(() => {
    buildProjection.mockReset();
    deleteAssetMock.mockReset();
    downloadAssetMock.mockReset();
    deleteAssetMock.mockResolvedValue(undefined);
    downloadAssetMock.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    window.localStorage.clear();
  });

  it("deletes an uploaded image by its canonical source id", async () => {
    renderLibrary("images", [uploadedImage()]);

    const tile = await screen.findByRole("button", { name: "one.png" });
    fireEvent.contextMenu(tile);
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete" }));

    await waitFor(() => {
      expect(deleteAssetMock).toHaveBeenCalledWith({ kind: "image", id: "img-1" });
    });
    // The family-qualified presentation key is never a deletion target.
    expect(deleteAssetMock).not.toHaveBeenCalledWith({
      kind: "image",
      id: "uploaded_image:img-1",
    });
  });

  it("offers no Delete action for a generated image", async () => {
    renderLibrary("images", [generatedImage()]);

    const tile = await screen.findByRole("button", { name: "generated.png" });
    fireEvent.contextMenu(tile);

    expect(screen.queryByRole("menuitem", { name: "Delete" })).not.toBeInTheDocument();
    expect(deleteAssetMock).not.toHaveBeenCalled();
  });

  it("keeps an uploaded image deletable whatever its provenance says", async () => {
    renderLibrary(
      "images",
      [uploadedImage({ origin: "unknown", sourceTag: null })]
    );

    const tile = await screen.findByRole("button", { name: "one.png" });
    fireEvent.contextMenu(tile);
    expect(screen.getByRole("menuitem", { name: "Delete" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("menuitem", { name: "Delete" }));
    await waitFor(() => {
      expect(deleteAssetMock).toHaveBeenCalledWith({ kind: "image", id: "img-1" });
    });
  });

  it("keeps an imported uploaded image deletable", async () => {
    renderLibrary(
      "images",
      [uploadedImage({ origin: "imported", sourceTag: "imported" })]
    );

    const tile = await screen.findByRole("button", { name: "one.png" });
    fireEvent.contextMenu(tile);
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete" }));

    await waitFor(() => {
      expect(deleteAssetMock).toHaveBeenCalledWith({ kind: "image", id: "img-1" });
    });
  });

  it("behaves the same in the Images and All filters", async () => {
    renderLibrary("all", [uploadedImage()]);

    const tile = await screen.findByRole("button", { name: "one.png" });
    fireEvent.contextMenu(tile);
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete" }));

    await waitFor(() => {
      expect(deleteAssetMock).toHaveBeenCalledWith({ kind: "image", id: "img-1" });
    });
  });

  it("keeps opening and downloading available", async () => {
    const onImageSelect = vi.fn();
    renderLibrary("images", [uploadedImage()], onImageSelect);

    const tile = await screen.findByRole("button", { name: "one.png" });
    fireEvent.click(tile);
    expect(onImageSelect).toHaveBeenCalledWith("one.png");

    fireEvent.contextMenu(tile);
    fireEvent.click(screen.getByRole("menuitem", { name: "Download" }));
    await waitFor(() => {
      // The download target is the resolved media URL, not the raw record src.
      expect(downloadAssetMock).toHaveBeenCalledWith({
        url: "http://backend.test/media/images/one.png",
        filename: "one.png",
      });
    });
  });
});
