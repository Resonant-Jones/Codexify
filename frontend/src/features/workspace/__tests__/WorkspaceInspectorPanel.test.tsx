import React from "react";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import WorkspaceInspectorPanel from "../components/WorkspaceInspectorPanel";
import type { WorkspaceSelection } from "../workspaceSelection";

function documentSelection(
  overrides: Partial<Extract<WorkspaceSelection, { kind: "document" }>["item"]> = {}
): Extract<WorkspaceSelection, { kind: "document" }> {
  return {
    kind: "document",
    item: {
      id: "doc-1",
      filename: "notes.md",
      src_url: "/media/documents/notes.md",
      artifact_type: "uploaded",
      mime_type: "text/markdown",
      ...overrides,
    },
  };
}

function imageSelection(
  overrides: Partial<Extract<WorkspaceSelection, { kind: "image" }>["item"]> = {}
): Extract<WorkspaceSelection, { kind: "image" }> {
  return {
    kind: "image",
    item: {
      id: "image-1",
      filename: "diagram.png",
      src_url: "/media/images/diagram.png",
      project_id: 7,
      ...overrides,
    },
  };
}

function mockDocumentDetail(payload: Record<string, unknown>) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve(payload),
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("WorkspaceInspectorPanel", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows an empty state without selecting an item automatically", () => {
    render(<WorkspaceInspectorPanel selectedItem={null} />);

    expect(screen.getByText(/Select a document or image from the Shelf/i)).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("renders generated document content as inert text and prefers it to parsed text", () => {
    const generated = documentSelection({
      filename: "assistant-notes.md",
      artifact_type: "generated",
      source_tag: "generated",
      content: "# Saved note\n<script>doNotRun()</script>",
      parsed_text: "older extracted text",
    });
    render(<WorkspaceInspectorPanel selectedItem={generated} />);

    expect(screen.getByTestId("workspace-document-text").textContent).toBe(
      "# Saved note\n<script>doNotRun()</script>"
    );
    expect(screen.queryByRole("heading", { name: "Saved note" })).not.toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
    expect(screen.queryByRole("link", { name: "Open original" })).not.toBeInTheDocument();
  });

  it("loads generated content from the existing artifact detail response when Shelf has metadata only", async () => {
    const fetchMock = mockDocumentDetail({
      id: "doc-1",
      artifact_type: "generated",
      title: "Saved Note",
      format: "md",
      content: "Generated note body\nwith preserved lines",
      parsed_text: "Generated note body\nwith preserved lines",
    });
    const generated = documentSelection({
      title: "Saved Note",
      filename: "Saved Note.md",
      artifact_type: "generated",
      content: undefined,
      parsed_text: undefined,
    });

    render(<WorkspaceInspectorPanel selectedItem={generated} />);

    expect((await screen.findByTestId("workspace-document-text")).textContent).toBe(
      "Generated note body\nwith preserved lines"
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/media/document-artifacts/doc-1?artifact_type=generated",
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
  });

  it("uses uploaded parsed_text when canonical content is unavailable", () => {
    const uploaded = documentSelection({
      filename: "uploaded.docx",
      mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      parsed_text: "Extracted upload text",
    });
    render(<WorkspaceInspectorPanel selectedItem={uploaded} />);

    expect(screen.getByTestId("workspace-document-text")).toHaveTextContent(
      "Extracted upload text"
    );
    expect(screen.getByText("uploaded.docx")).toBeInTheDocument();
  });

  it("shows a truthful unavailable state and safe original link for unsupported documents", async () => {
    mockDocumentDetail({ id: "doc-1", content: null, parsed_text: null });
    const unsupported = documentSelection({
      filename: "archive.docx",
      src_url: "/media/documents/archive.docx",
      mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      content: undefined,
      parsed_text: undefined,
    });

    render(<WorkspaceInspectorPanel selectedItem={unsupported} />);

    expect(await screen.findByText("Preview unavailable for this document.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open original" })).toHaveAttribute(
      "href",
      expect.stringContaining("/media/documents/archive.docx")
    );
    expect(screen.getByTestId("workspace-document-viewport")).toBeInTheDocument();
  });

  it("shows PDF parsed text with an Open original fallback", () => {
    const pdf = documentSelection({
      filename: "report.pdf",
      src_url: "https://cdn.example.test/report.pdf?signature=read-only",
      mime_type: "application/pdf",
      parsed_text: "Extracted PDF page text",
    });
    render(<WorkspaceInspectorPanel selectedItem={pdf} />);

    expect(screen.getByTestId("workspace-document-text")).toHaveTextContent(
      "Extracted PDF page text"
    );
    expect(screen.getByRole("link", { name: "Open original" })).toHaveAttribute(
      "href",
      "https://cdn.example.test/report.pdf?signature=read-only"
    );
    expect(screen.queryByTestId("workspace-pdf-preview")).not.toBeInTheDocument();
  });

  it("uses the existing PDF URL when the detail response has no extracted text", async () => {
    mockDocumentDetail({ id: "doc-1", content: null, parsed_text: null });
    const pdf = documentSelection({
      filename: "report.pdf",
      src_url: "/media/documents/report.pdf",
      mime_type: "application/pdf",
      content: undefined,
      parsed_text: undefined,
    });
    render(<WorkspaceInspectorPanel selectedItem={pdf} />);

    expect(await screen.findByTestId("workspace-pdf-preview")).toHaveAttribute(
      "src",
      expect.stringContaining("/media/documents/report.pdf")
    );
    expect(screen.getByRole("link", { name: "Open original" })).toBeInTheDocument();
  });

  it("renders an image in the Inspector and keeps zoom within 50%–400%", async () => {
    const user = userEvent.setup();
    render(<WorkspaceInspectorPanel selectedItem={imageSelection()} />);

    const image = screen.getByRole("img", { name: "diagram.png" });
    expect(image).toHaveAttribute("src", expect.stringContaining("/media/images/diagram.png"));
    expect(screen.getByTestId("workspace-image-viewport")).toHaveAttribute("data-zoom", "100");
    fireEvent.load(image);

    const zoomOut = screen.getByRole("button", { name: "Zoom out" });
    const zoomIn = screen.getByRole("button", { name: "Zoom in" });
    await user.click(zoomOut);
    await user.click(zoomOut);
    await user.click(zoomOut);
    expect(screen.getByTestId("workspace-image-zoom")).toHaveTextContent("50%");
    expect(zoomOut).toBeDisabled();

    for (let count = 0; count < 14; count += 1) await user.click(zoomIn);
    expect(screen.getByTestId("workspace-image-zoom")).toHaveTextContent("400%");
    expect(zoomIn).toBeDisabled();
    expect(screen.getByTestId("workspace-image-viewport")).toHaveAttribute("data-zoom", "400");

    await user.click(screen.getByRole("button", { name: "Reset / Fit" }));
    expect(screen.getByTestId("workspace-image-zoom")).toHaveTextContent("100%");
  });

  it("shows a non-destructive image error and prevents opening an empty lightbox", async () => {
    const user = userEvent.setup();
    render(<WorkspaceInspectorPanel selectedItem={imageSelection()} />);
    fireEvent.error(screen.getByRole("img", { name: "diagram.png" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/Shelf item is unchanged/i);
    expect(screen.getByText("diagram.png")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Expand image" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Expand image" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("preserves image selection and zoom through lightbox open and Escape close", async () => {
    const user = userEvent.setup();
    render(<WorkspaceInspectorPanel selectedItem={imageSelection()} />);
    fireEvent.load(screen.getByRole("img", { name: "diagram.png" }));
    await user.click(screen.getByRole("button", { name: "Zoom in" }));
    expect(screen.getByTestId("workspace-image-zoom")).toHaveTextContent("125%");

    await user.click(screen.getByRole("button", { name: "Expand image" }));
    const dialog = screen.getByRole("dialog", { name: "diagram.png" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(within(dialog).getByRole("img", { name: "diagram.png" })).toBeInTheDocument();
    expect(within(dialog).getByTestId("workspace-image-zoom")).toHaveTextContent("125%");
    expect(document.activeElement).toBe(
      within(dialog).getByRole("button", { name: "Close image viewer" })
    );

    await user.click(within(dialog).getByRole("button", { name: "Zoom in" }));
    expect(within(dialog).getByTestId("workspace-image-zoom")).toHaveTextContent("150%");
    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Expand image" }));
    expect(screen.getByRole("img", { name: "diagram.png" })).toBeInTheDocument();
    expect(screen.getByTestId("workspace-image-viewport")).toHaveAttribute("data-zoom", "150");
  });

  it("rejects executable media URLs", async () => {
    const user = userEvent.setup();
    const unsafeImage = imageSelection({ src_url: "javascript:alert(1)" });
    const { rerender } = render(<WorkspaceInspectorPanel selectedItem={unsafeImage} />);

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/no safe image URL/i);
    expect(screen.getByRole("button", { name: "Expand image" })).toBeDisabled();

    mockDocumentDetail({ id: "doc-1", content: null, parsed_text: null });
    rerender(
      <WorkspaceInspectorPanel
        selectedItem={documentSelection({
          filename: "unsafe.pdf",
          src_url: "javascript:alert(2)",
          mime_type: "application/pdf",
          content: undefined,
          parsed_text: undefined,
        })}
      />
    );
    await waitFor(() =>
      expect(screen.getByText("Preview unavailable for this document.")).toBeInTheDocument()
    );
    expect(screen.queryByTestId("workspace-pdf-preview")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Open original" })).not.toBeInTheDocument();
    await user.keyboard("{Escape}");
  });
});
