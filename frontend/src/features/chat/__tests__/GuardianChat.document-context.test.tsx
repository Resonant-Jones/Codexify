import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import api from "@/lib/api";
import ChatBubble from "@/features/chat/components/ChatBubble";
import {
  loadDocumentContentById,
  parseDocumentContextContent,
  serializeDocumentContextMessage,
} from "@/lib/documentContext";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn() } }));

describe("Guardian chat document context persistence", () => {
  afterEach(() => { vi.mocked(api.get).mockReset(); });

  it.each(["uploaded", "generated"] as const)("rehydrates a submitted %s artifact without a fresh upload", async (artifactType) => {
    const id = `${artifactType}-1`;
    vi.mocked(api.get).mockResolvedValue({ data: {
      id, artifact_type: artifactType, title: "Canonical report.pdf",
      filename: "Canonical report.pdf", format: "pdf", mime_type: "application/pdf",
      embedding_status: "ready", parsed_text: "CODEXIFY_CANONICAL_DOCUMENT_TILE_PROBE",
    } });
    const loaded = await loadDocumentContentById(id, artifactType);
    const persistedContent = serializeDocumentContextMessage("Summarize this", [{
      tile: loaded.tile, content: loaded.content,
    }]);
    const reloaded = parseDocumentContextContent(persistedContent);
    expect(reloaded.tiles).toMatchObject([{ id, artifactType }]);
    const { container, unmount } = render(<ChatBubble isGuardian={false} message={{
      id: "persisted-1", authorId: "me", authorName: "You",
      content: persistedContent, createdAt: Date.now(),
    }} />);
    expect(container.querySelectorAll('[data-slot="document-tile"]')).toHaveLength(1);
    expect(screen.queryByText("CODEXIFY_CANONICAL_DOCUMENT_TILE_PROBE")).not.toBeInTheDocument();
    unmount();
    const reload = render(<ChatBubble isGuardian={false} message={{
      id: "persisted-1", authorId: "me", authorName: "You",
      content: persistedContent, createdAt: Date.now(),
    }} />);
    expect(reload.container.querySelectorAll('[data-slot="document-tile"]')).toHaveLength(1);
    expect(api.get).toHaveBeenCalledTimes(1);
  });
});
