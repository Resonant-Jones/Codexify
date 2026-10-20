import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import LibraryView from "@/components/library/LibraryView";
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
  default: ({ items }: { items: unknown[] }) => (
    <div data-testid="gallery-grid-mock">{items.length} images</div>
  ),
}));

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
    render(<LibraryView scope={scope} extColors={{}} />);
    await waitFor(() => expect(screen.getByTestId("library-filter-all")).toHaveAttribute("aria-selected", "true"));
    expect(screen.getByRole("tab", { name: "All" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Images" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Documents" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Widgets" })).toBeInTheDocument();
  });

  it("changes the projection filter and renders the matching presentation surface", async () => {
    render(<LibraryView scope={scope} extColors={{}} />);
    await waitFor(() => expect(screen.getByTestId("gallery-grid-mock")).toHaveTextContent("1 images"));
    fireEvent.click(screen.getByRole("tab", { name: "Documents" }));
    await waitFor(() => expect(buildProjection).toHaveBeenLastCalledWith(expect.objectContaining({ filter: "documents" })));
    expect(screen.getByTestId("documents-view-mock")).toBeInTheDocument();
  });

  it("states that Widgets are unavailable without creating records", async () => {
    render(<LibraryView scope={scope} extColors={{}} />);
    await waitFor(() => screen.getByRole("tab", { name: "Widgets" }));
    fireEvent.click(screen.getByRole("tab", { name: "Widgets" }));
    await waitFor(() => expect(screen.getByTestId("library-widgets-unavailable")).toBeInTheDocument());
    expect(screen.getByTestId("library-unavailable")).toHaveTextContent(/no authoritative widget/i);
    expect(buildProjection).toHaveBeenLastCalledWith(expect.objectContaining({ filter: "widgets" }));
  });
});
