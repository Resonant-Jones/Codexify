import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WorkspacePane from "../WorkspacePane";
import { setRuntimeApiKey } from "@/lib/api";
import api from "@/lib/api";
import { initRuntimeConfig } from "@/lib/runtimeConfig";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import type { DocumentLike } from "@/types/documents";

function buildDocument(
  overrides: Partial<DocumentLike> &
    Pick<DocumentLike, "title" | "ext" | "type"> &
    Record<string, unknown>
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

  afterEach(async () => {
    setRuntimeApiKey(null);
    window.localStorage.removeItem("cfy.desktop.backendBaseUrl");
    await initRuntimeConfig({ force: true });
    vi.restoreAllMocks();
  });

  it("does not attach auth headers to arbitrary external preview URLs", async () => {
    setRuntimeApiKey("preview-secret");
    fetchMock.mockResolvedValueOnce({
      ok: true,
      text: async () => "# External Preview\n\nFetched from a third-party origin.",
    } as Response);

    render(
      <WorkspacePane
        activeDoc={buildDocument({
          id: "doc-external",
          title: "External Notes",
          ext: "md",
          type: "file",
          src_url: "https://example.com/external-notes.md",
        })}
      />
    );

    const previewSurface = screen.getByTestId("workspace-preview-surface");

    await waitFor(() => {
      expect(
        within(previewSurface).getByRole("heading", { name: "External Preview" })
      ).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] ?? [];
    expect(init).toMatchObject({ credentials: "omit" });
    const headers = init?.headers as Record<string, string> | undefined;
    expect(headers?.["X-API-Key"]).toBeUndefined();
    expect(headers?.Authorization).toBeUndefined();
  });

  it("keeps auth headers for trusted backend preview URLs", async () => {
    setRuntimeApiKey("preview-secret");
    fetchMock.mockResolvedValueOnce({
      ok: true,
      text: async () => "# Backend Preview\n\nFetched from the trusted backend origin.",
    } as Response);

    render(
      <WorkspacePane
        activeDoc={buildDocument({
          id: "doc-backend",
          title: "Backend Notes",
          ext: "md",
          type: "file",
          src_url: "/media/documents/backend-notes.md",
        })}
      />
    );

    const previewSurface = screen.getByTestId("workspace-preview-surface");

    await waitFor(() => {
      expect(
        within(previewSurface).getByRole("heading", { name: "Backend Preview" })
      ).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] ?? [];
    const headers = init?.headers as Record<string, string> | undefined;
    expect(headers?.["X-API-Key"]).toBe("preview-secret");
  });

  it("renders markdown previews with the chat markdown contract", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      text: async () =>
        "# Rendered Notes\n\n- Scope\n- Verify\n\nThis is **important**.\n\n```ts\nconst answer = 42;\n```",
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
        within(previewSurface).getByRole("heading", { name: "Rendered Notes" })
      ).toBeInTheDocument();
    });

    expect(within(previewSurface).getByText("Scope")).toBeInTheDocument();
    expect(within(previewSurface).getByText("Verify")).toBeInTheDocument();
    expect(within(previewSurface).getByText("important")).toBeInTheDocument();
    expect(within(previewSurface).getByRole("button", { name: "Copy" })).toBeInTheDocument();
    expect(previewSurface.querySelector(".codexifyCodeBlock")).not.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(within(metadataSurface).getByText("Markdown (.md)")).toBeInTheDocument();
    expect(within(previewSurface).queryByText("Markdown (.md)")).not.toBeInTheDocument();
  });

  it("normalizes markdown image sources before rendering", async () => {
    window.localStorage.setItem("cfy.desktop.backendBaseUrl", "http://127.0.0.1:8888");
    await initRuntimeConfig({ force: true });
    fetchMock.mockResolvedValueOnce({
      ok: true,
      text: async () => "![Inline diagram](/media/documents/inline-diagram.png)",
    } as Response);

    render(
      <WorkspacePane
        activeDoc={buildDocument({
          id: "doc-md-image",
          title: "Diagram Notes",
          ext: "md",
          type: "file",
          src_url: "/media/documents/diagram-notes.md",
        })}
      />
    );

    const previewSurface = screen.getByTestId("workspace-preview-surface");
    const image = await within(previewSurface).findByRole("img", {
      name: "Inline diagram",
    });

    expect(image).toHaveAttribute(
      "src",
      normalizeMediaUrl("/media/documents/inline-diagram.png")
    );
    expect(previewSurface).toHaveAttribute("data-state", "markdown");
    expect(screen.getByTestId("workspace-metadata")).toHaveTextContent("Markdown (.md)");
  });

  it("renders text-like documents as actual content", () => {
    render(
      <WorkspacePane
        activeDoc={buildDocument({
          id: "doc-txt",
          title: "Session Notes",
          ext: "txt",
          type: "file",
          content: "First line\n*literal stars*",
        })}
      />
    );

    const previewSurface = screen.getByTestId("workspace-preview-surface");
    const previewContent = within(previewSurface).getByTestId("workspace-preview-content");

    expect(fetchMock).not.toHaveBeenCalled();
    expect(previewSurface).toHaveAttribute("data-state", "text");
    expect(previewContent).toHaveTextContent("First line");
    expect(previewContent).toHaveTextContent("*literal stars*");
    expect(screen.getByTestId("workspace-metadata")).toHaveTextContent("Text (.txt)");
  });

  it("loads full document content when only a preview snippet is present", async () => {
    const apiGetSpy = vi.spyOn(api, "get").mockResolvedValueOnce({
      data: {
        id: "doc-snippet",
        title: "Snippet Notes",
        content: "# Full Notes\n\nExpanded body text.",
      },
    } as any);

    render(
      <WorkspacePane
        activeDoc={buildDocument({
          id: "doc-snippet",
          title: "Snippet Notes",
          ext: "md",
          type: "file",
          previewText: "Short excerpt",
        })}
      />
    );

    const previewSurface = screen.getByTestId("workspace-preview-surface");

    await waitFor(() => {
      expect(
        within(previewSurface).getByRole("heading", { name: "Full Notes" })
      ).toBeInTheDocument();
    });

    expect(apiGetSpy).toHaveBeenCalledWith("/media/documents/doc-snippet");
    expect(within(previewSurface).getByText("Expanded body text.")).toBeInTheDocument();
    expect(within(previewSurface).queryByText("Short excerpt")).not.toBeInTheDocument();
  });

  it("detects signed image preview URLs using the parsed pathname", () => {
    render(
      <WorkspacePane
        activeDoc={buildDocument({
          id: "doc-img",
          title: "Signed Photo",
          ext: "jpg",
          type: "file",
          src_url: "https://cdn.example.com/assets/photo.jpg?sig=abc123#page=1",
        })}
      />
    );

    const previewSurface = screen.getByTestId("workspace-preview-surface");

    expect(fetchMock).not.toHaveBeenCalled();
    expect(previewSurface).toHaveAttribute("data-state", "image");
    expect(screen.getByRole("img", { name: "Signed Photo" })).toBeInTheDocument();
    expect(screen.getByTestId("workspace-metadata")).toHaveTextContent("Image");
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
      screen.getByText("This file type does not have an inline preview yet.")
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByTestId("workspace-preview-surface")).toHaveAttribute(
      "data-state",
      "unsupported"
    );
    expect(
      screen.getByRole("link", { name: "Open in a new tab" })
    ).toHaveAttribute("target", "_blank");
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
        `# Long Notes\n\n${Array.from({ length: 80 }, (_, index) => `Line ${index + 1}`).join("\n")}\n\n\`\`\`ts\nconst answer = 42;\n\`\`\``,
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

    expect(previewSurface).toHaveAttribute("data-state", "markdown");
    expect(previewSurface.style.overflow).toBe("auto");
    expect(previewSurface.style.minHeight).toBe("0");
  });
});
