import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { CodexSuggestion } from "@/api/codex";
import { CodexSuggestionCard } from "@/features/chat/components/CodexSuggestionCard";

const suggestion: CodexSuggestion = {
  suggested: true,
  confidence: 0.82,
  reason: "capture_language",
  label: "Codex Entry",
  sourceSummary: "2 messages (1 user, 1 assistant)",
  sourceMessageIds: ["10", "11"],
  threadId: "7",
  projectId: null,
  personaId: null,
  createdFrom: "semantic_suggestion",
  retrievalEnabled: false,
  suppressionKey: "codex:abc123",
};

describe("CodexSuggestionCard", () => {
  it("renders label, source summary, reason, Draft action, and Dismiss action", () => {
    render(
      <CodexSuggestionCard
        suggestion={suggestion}
        onDraft={vi.fn()}
        onDismiss={vi.fn()}
      />
    );

    expect(screen.getByText("Codex Entry")).toBeInTheDocument();
    expect(screen.getByText("2 messages (1 user, 1 assistant)")).toBeInTheDocument();
    expect(screen.getByTestId("codex-suggestion-reason")).toHaveTextContent(
      "Capture Language"
    );
    expect(
      screen.getByRole("button", { name: "Draft Codex Entry" })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dismiss" })).toBeInTheDocument();
  });

  it("invokes the draft handler with semantic suggestion lineage", () => {
    const onDraft = vi.fn();
    render(
      <CodexSuggestionCard
        suggestion={suggestion}
        onDraft={onDraft}
        onDismiss={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId("codex-suggestion-draft"));

    expect(onDraft).toHaveBeenCalledWith(suggestion);
    expect(onDraft.mock.calls[0][0]).toMatchObject({
      createdFrom: "semantic_suggestion",
      retrievalEnabled: false,
      sourceMessageIds: ["10", "11"],
      suppressionKey: "codex:abc123",
    });
  });

  it("dismisses without invoking a save path", () => {
    const onDraft = vi.fn();
    const onDismiss = vi.fn();
    render(
      <CodexSuggestionCard
        suggestion={suggestion}
        onDraft={onDraft}
        onDismiss={onDismiss}
      />
    );

    fireEvent.click(screen.getByTestId("codex-suggestion-dismiss"));

    expect(onDismiss).toHaveBeenCalledWith(suggestion);
    expect(onDraft).not.toHaveBeenCalled();
  });

  it("does not render a standalone global trigger button", () => {
    render(
      <CodexSuggestionCard
        suggestion={suggestion}
        onDraft={vi.fn()}
        onDismiss={vi.fn()}
      />
    );

    expect(
      screen.queryByRole("button", { name: /^Codex Entry$/ })
    ).not.toBeInTheDocument();
  });
});
