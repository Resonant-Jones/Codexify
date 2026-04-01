import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WorkspacePane from "../WorkspacePane";
import type { DocumentLike } from "@/types/documents";

function buildDocument(
  overrides: Partial<DocumentLike> & Pick<DocumentLike, "title" | "ext" | "type">
): DocumentLike {
  return {
    id: overrides.id ?? "doc-1",
    title: overrides.title,
    ext: overrides.ext,
    type: overrides.type,
    src_url: overrides.src_url,
    srcUrl: overrides.srcUrl,
    src: overrides.src,
    url: overrides.url,
    createdAt: overrides.createdAt,
    threadId: overrides.threadId,
    thread_id: overrides.thread_id,
    embeddingStatus: overrides.embeddingStatus,
    embeddingError: overrides.embeddingError,
    ...overrides,
  };
}

describe("WorkspacePane preview surface", () => {
  let fetchMock: any;

  beforeEach(() => {
    fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock.mockReset();
    fetchMock.mockResolvedValue({
      ok: true,
      text: async () => "",
    } as Response);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders actual markdown content for a previewable document", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      text: async () => "# Project Plan\n\n- Scope\n- Verify",
    } as Response);

    render(
      <WorkspacePane
        activeDoc={buildDocument({
          id: "doc-md",
          title: "Project Plan",
          ext: "md",
          type: "file",
          src_url: "/media/documents/project-plan.md",
        })}
      />
    );

    const previewSurface = screen.getByTestId("workspace-preview-surface");
    const metadataSurface = screen.getByTestId("workspace-metadata");

    await waitFor(() => {
      expect(
        within(previewSurface).getByRole("heading", { name: "Project Plan" })
      ).toBeInTheDocument();
    });

    expect(within(previewSurface).getByText("Scope")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(within(metadataSurface).getByText("Markdown (.md)")).toBeInTheDocument();
  });

  it("keeps metadata secondary to the preview surface", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      text: async () => "# Release Notes\n\nDocument body.",
    } as Response);

    render(
      <WorkspacePane
        activeDoc={buildDocument({
          id: "doc-release",
          title: "Release Notes",
          ext: "md",
          type: "file",
          src_url: "/media/documents/release-notes.md",
        })}
      />
    );

    const previewSurface = screen.getByTestId("workspace-preview-surface");
    const metadataSurface = screen.getByTestId("workspace-metadata");

    await waitFor(() => {
      expect(
        within(previewSurface).getByRole("heading", { name: "Release Notes" })
      ).toBeInTheDocument();
    });

    expect(within(previewSurface).queryByText("Markdown (.md)")).not.toBeInTheDocument();
    expect(within(metadataSurface).getByText("Markdown (.md)")).toBeInTheDocument();
    expect(
      previewSurface.compareDocumentPosition(metadataSurface) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });

  it("shows an explicit fallback for unsupported file types", () => {
    render(
      <WorkspacePane
        activeDoc={buildDocument({
          id: "doc-zip",
          title: "Archive",
          ext: "zip",
          type: "file",
          src_url: "/media/documents/archive.zip",
        })}
      />
    );

    expect(
      screen.getByText("Preview unavailable for this file type")
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByTestId("workspace-preview-surface")).toHaveAttribute(
      "data-state",
      "unsupported"
    );
    expect(screen.getByTestId("workspace-metadata")).toHaveTextContent(
      "Unsupported (.zip)"
    );
  });

  it("renders the no-selection state explicitly", () => {
    render(<WorkspacePane activeDoc={null} />);

    const emptyState = screen.getByTestId("workspace-empty-state");
    expect(emptyState).toHaveTextContent("No document selected");
    expect(emptyState).toHaveTextContent(
      "Select a workspace document to see its preview here."
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("keeps the preview surface bounded and scrollable", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      text: async () =>
        `# Long Notes\n\n${Array.from({ length: 80 }, (_, index) => `Line ${index + 1}`).join("\n")}`,
    } as Response);

    render(
      <WorkspacePane
        activeDoc={buildDocument({
          id: "doc-long",
          title: "Long Notes",
          ext: "md",
          type: "file",
          src_url: "/media/documents/long-notes.md",
        })}
      />
    );

    const previewSurface = screen.getByTestId("workspace-preview-surface");

    await waitFor(() => {
      expect(
        within(previewSurface).getByRole("heading", { name: "Long Notes" })
      ).toBeInTheDocument();
    });

    expect(previewSurface.style.overflow).toBe("auto");
    expect(previewSurface.style.minHeight).toBe("0");
  });
});
