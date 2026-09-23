import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import api from "@/lib/api";
import ChatBubble from "@/features/chat/components/ChatBubble";
import { serializeDocumentContextMessage } from "@/lib/documentContext";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn() } }));

const apiGet = vi.mocked(api.get);

function bubble(content: string, isGuardian = true) {
  return <ChatBubble isGuardian={isGuardian} message={{
    id: "message-1", authorId: isGuardian ? "bot" : "me",
    authorName: isGuardian ? "Guardian" : "You", content, createdAt: Date.now(),
  }} />;
}

function detail(id: string, artifactType: "uploaded" | "generated") {
  return { id, artifact_type: artifactType, title: `${artifactType} report`,
    filename: `${artifactType} report.pdf`, format: "pdf", mime_type: "application/pdf",
    src_url: artifactType === "uploaded" ? `/media/documents/${id}` : null,
    embedding_status: "ready" };
}

describe("canonical chat document artifacts", () => {
  afterEach(() => { apiGet.mockReset(); });

  it.each(["uploaded", "generated"] as const)("renders a structured %s document through DocumentTile", (artifactType) => {
    const content = serializeDocumentContextMessage("Please review", [{
      tile: { id: "doc-1", title: "Report.pdf", type: "document", artifactType },
      content: "Private body",
    }]);
    const { container } = render(bubble(content, false));
    expect(container.querySelectorAll('[data-slot="document-tile"]')).toHaveLength(1);
    expect(screen.getByText("Please review")).toBeInTheDocument();
    expect(screen.queryByText("Private body")).not.toBeInTheDocument();
  });

  it.each(["uploaded", "generated"] as const)("resolves a first-party %s link and preserves prose", async (artifactType) => {
    const id = `${artifactType}-1`;
    apiGet.mockResolvedValue({ data: detail(id, artifactType) });
    const route = artifactType === "generated" ? "document-artifacts" : "documents";
    const { container } = render(bubble(`Before [the report](/media/${route}/${id}) after.`));
    await waitFor(() => expect(container.querySelectorAll('[data-slot="document-tile"]')).toHaveLength(1));
    expect(screen.getByText(/Before/)).toBeInTheDocument();
    expect(screen.getByText(/after/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "the report" })).not.toBeInTheDocument();
    expect(apiGet).toHaveBeenCalledWith(
      `/media/${route}/${id}`,
      ...(artifactType === "generated" ? [{}] : [])
    );
  });

  it("deduplicates a structured reference and repeated canonical links", async () => {
    apiGet.mockResolvedValue({ data: detail("doc-1", "uploaded") });
    const content = serializeDocumentContextMessage("See [one](/media/documents/doc-1) and [two](/api/media/documents/doc-1).", [{
      tile: { id: "doc-1", title: "Report.pdf", type: "document", artifactType: "uploaded" },
      content: "Document body",
    }]);
    const { container } = render(bubble(content));
    await waitFor(() => expect(screen.queryByRole("link", { name: "one" })).not.toBeInTheDocument());
    expect(container.querySelectorAll('[data-slot="document-tile"]')).toHaveLength(1);
    expect(screen.queryByRole("link", { name: "two" })).not.toBeInTheDocument();
  });

  it.each([
    "https://example.com/report.pdf", "https://some-site.test/file.docx",
    "https://example.com/notes.md", "/download/foo.pdf", "/media/documents/invalid%2Fid",
  ])("keeps noncanonical %s as an ordinary link", (href) => {
    render(bubble(`[report](${href})`));
    expect(screen.getByRole("link", { name: "report" })).toBeInTheDocument();
  });

  it.each([403, 404])("keeps a canonical link when metadata lookup returns %s", async (status) => {
    apiGet.mockRejectedValue({ response: { status } });
    const { container } = render(bubble("[report](/media/documents/doc-1)"));
    await waitFor(() => expect(apiGet).toHaveBeenCalled());
    expect(screen.getByRole("link", { name: "report" })).toBeInTheDocument();
    expect(container.querySelector('[data-slot="document-tile"]')).not.toBeInTheDocument();
  });

  it("uses the artifact API type for an uploaded document-artifacts link", async () => {
    apiGet.mockResolvedValue({ data: detail("doc-1", "uploaded") });
    const { container } = render(bubble("[report](/media/document-artifacts/doc-1)"));
    await waitFor(() => expect(container.querySelectorAll('[data-slot="document-tile"]')).toHaveLength(1));
    expect(screen.queryByRole("link", { name: "report" })).not.toBeInTheDocument();
  });

  it("keeps the original link when metadata identity or artifact type is inconsistent", async () => {
    apiGet.mockResolvedValue({ data: { ...detail("other-id", "generated"), artifact_type: "image" } });
    const { container } = render(bubble("[report](/media/document-artifacts/doc-1)"));
    await waitFor(() => expect(apiGet).toHaveBeenCalled());
    expect(screen.getByRole("link", { name: "report" })).toBeInTheDocument();
    expect(container.querySelector('[data-slot="document-tile"]')).not.toBeInTheDocument();
  });
});
