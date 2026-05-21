import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { CodexDraft } from "@/api/codex";
import { CodexDraftCard } from "@/features/chat/components/CodexDraftCard";

const semanticDraft: CodexDraft = {
  title: "Semantic Draft",
  body: "## Assistant\n\nUse explicit capability envelopes.",
  source_summary: "1 messages (0 user, 1 assistant)",
  created_from: "semantic_suggestion",
  retrieval_enabled: false,
  project_id: null,
  persona_id: null,
  semantic_suggestion: {
    reason: "capture_language",
    suppressionKey: "codex:abc123",
  },
  lineage: {
    thread_id: 9,
    trigger_message_id: null,
    source_message_ids: [90],
    first_source_message_id: 90,
    last_source_message_id: 90,
  },
};

describe("CodexDraftCard", () => {
  it("renders semantic-suggestion draft origin", () => {
    render(
      <CodexDraftCard
        draft={semanticDraft}
        onSave={vi.fn()}
        onDownload={vi.fn()}
        onDismiss={vi.fn()}
      />
    );

    expect(screen.getByTestId("codex-draft-origin")).toHaveTextContent(
      "Suggested"
    );
  });

  it("passes semantic-suggestion lineage to Save", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <CodexDraftCard
        draft={semanticDraft}
        onSave={onSave}
        onDownload={vi.fn()}
        onDismiss={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId("codex-draft-save"));

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(semanticDraft);
    });
    expect(onSave.mock.calls[0][0]).toMatchObject({
      created_from: "semantic_suggestion",
      retrieval_enabled: false,
      lineage: {
        trigger_message_id: null,
        source_message_ids: [90],
      },
    });
  });

  it("downloads Markdown without saving", () => {
    const onSave = vi.fn();
    const onDownload = vi.fn();
    render(
      <CodexDraftCard
        draft={semanticDraft}
        onSave={onSave}
        onDownload={onDownload}
        onDismiss={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId("codex-draft-download"));

    expect(onDownload).toHaveBeenCalledWith(semanticDraft);
    expect(onSave).not.toHaveBeenCalled();
  });

  it("dismisses without persisting", () => {
    const onSave = vi.fn();
    const onDismiss = vi.fn();
    render(
      <CodexDraftCard
        draft={semanticDraft}
        onSave={onSave}
        onDownload={vi.fn()}
        onDismiss={onDismiss}
      />
    );

    fireEvent.click(screen.getByTestId("codex-draft-dismiss"));

    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(onSave).not.toHaveBeenCalled();
  });
});
