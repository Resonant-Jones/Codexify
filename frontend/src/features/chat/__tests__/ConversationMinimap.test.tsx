import { act, fireEvent, render, screen, within } from "@testing-library/react";
import "@testing-library/jest-dom";
import { describe, expect, it, vi } from "vitest";

import ConversationMinimap from "@/features/chat/components/ConversationMinimap";
import {
  buildConversationNavigationEntries,
  deriveConversationSections,
  type ConversationSection,
} from "@/features/chat/conversationNavigation";
import type { ChatMessage } from "@/features/chat/useChat";

function buildMessage(id: number, role: string, content: string): ChatMessage {
  return {
    id,
    thread_id: 7,
    role,
    content,
    created_at: `2026-03-13T00:00:${String(id % 60).padStart(2, "0")}.000Z`,
  };
}

function buildSections(count: number): ConversationSection[] {
  return deriveConversationSections(
    Array.from({ length: count }, (_unused, index) =>
      buildMessage(index + 1, "user", `turn ${index + 1} body`)
    )
  );
}

function renderMinimap(overrides: {
  sections?: ConversationSection[];
  maxMarks?: number;
  activeSectionId?: string | null;
  hasMore?: boolean;
  threadId?: number;
  canGoBack?: boolean;
  onJump?: (sectionId: string) => boolean;
  onBack?: () => boolean;
} = {}) {
  const sections = overrides.sections ?? buildSections(3);
  const entries = buildConversationNavigationEntries(
    sections,
    overrides.maxMarks ?? 40
  );
  const onJump = overrides.onJump ?? vi.fn().mockReturnValue(true);
  const onBack = overrides.onBack ?? vi.fn().mockReturnValue(true);

  const view = render(
    <ConversationMinimap
      sections={sections}
      entries={entries}
      activeSectionId={overrides.activeSectionId ?? null}
      hasMore={overrides.hasMore ?? false}
      threadId={overrides.threadId ?? 7}
      canGoBack={overrides.canGoBack ?? false}
      onJump={onJump}
      onBack={onBack}
    />
  );

  return { view, sections, entries, onJump, onBack };
}

describe("ConversationMinimap rail", () => {
  it("renders one mark per navigable section", () => {
    renderMinimap({ sections: buildSections(4) });

    const marks = screen.getAllByTestId("conversation-minimap-mark");
    expect(marks).toHaveLength(4);
    expect(marks[0]).toHaveAttribute("aria-label", "Turn 1");
  });

  it("does not render a preview until a destination is previewed", () => {
    renderMinimap();

    expect(screen.queryByTestId("conversation-minimap-preview")).not.toBeInTheDocument();
  });

  it("opens a bounded non-modal preview on hover without committing a jump", () => {
    const { onJump } = renderMinimap();

    fireEvent.mouseEnter(screen.getAllByTestId("conversation-minimap-mark")[1]);

    const preview = screen.getByTestId("conversation-minimap-preview");
    expect(preview).toBeInTheDocument();
    expect(preview).toHaveAttribute("aria-modal", "false");
    // Previewing must not scroll or navigate.
    expect(onJump).not.toHaveBeenCalled();
  });

  it("opens the preview on keyboard focus without committing a jump", () => {
    const { onJump } = renderMinimap();

    fireEvent.focus(screen.getAllByTestId("conversation-minimap-mark")[0]);

    expect(screen.getByTestId("conversation-minimap-preview")).toBeInTheDocument();
    expect(onJump).not.toHaveBeenCalled();
  });

  it("marks the active reading section separately from the previewed destination", () => {
    const sections = buildSections(6);
    // Three marks over six turns, so each range previews two destinations.
    renderMinimap({ sections, maxMarks: 3, activeSectionId: sections[3].id });

    const marks = screen.getAllByTestId("conversation-minimap-mark");
    expect(marks).toHaveLength(3);
    expect(marks[1]).toHaveAttribute("data-active", "true");
    expect(marks[0]).toHaveAttribute("data-active", "false");

    fireEvent.mouseEnter(marks[1]);

    const destinations = screen.getAllByTestId("conversation-minimap-destination");
    expect(destinations).toHaveLength(2);

    // The previewed destination is the range head; the active reading section
    // is a different turn in the same range.
    expect(destinations[0]).toHaveAttribute("data-selected", "true");
    expect(destinations[0]).toHaveAttribute("data-active", "false");
    expect(destinations[1]).toHaveAttribute("data-active", "true");
    expect(destinations[1]).toHaveAttribute("data-selected", "false");
  });

  it("commits a jump when a pointer-selected destination is clicked", () => {
    const sections = buildSections(3);
    const { onJump } = renderMinimap({ sections });

    fireEvent.mouseEnter(screen.getAllByTestId("conversation-minimap-mark")[2]);

    // A single-section entry previews exactly that destination.
    const destinations = screen.getAllByTestId("conversation-minimap-destination");
    expect(destinations).toHaveLength(1);

    fireEvent.click(destinations[0]);

    expect(onJump).toHaveBeenCalledTimes(1);
    expect(onJump).toHaveBeenCalledWith(sections[2].id);
  });

  it("shows the following assistant reply in the section preview", () => {
    const sections = deriveConversationSections([
      buildMessage(1, "user", "the question"),
      buildMessage(2, "assistant", "the answer"),
    ]);
    renderMinimap({ sections });

    fireEvent.mouseEnter(screen.getAllByTestId("conversation-minimap-mark")[0]);

    expect(screen.getByTestId("conversation-minimap-reply")).toHaveTextContent(
      "the answer"
    );
  });

  it("dismisses the preview on Escape", () => {
    renderMinimap();

    fireEvent.mouseEnter(screen.getAllByTestId("conversation-minimap-mark")[0]);
    expect(screen.getByTestId("conversation-minimap-preview")).toBeInTheDocument();

    fireEvent.keyDown(screen.getByTestId("conversation-minimap-preview"), {
      key: "Escape",
    });

    expect(screen.queryByTestId("conversation-minimap-preview")).not.toBeInTheDocument();
  });

  it("dismisses the preview on an outside interaction", () => {
    renderMinimap();

    fireEvent.mouseEnter(screen.getAllByTestId("conversation-minimap-mark")[0]);
    expect(screen.getByTestId("conversation-minimap-preview")).toBeInTheDocument();

    fireEvent.pointerDown(document.body);

    expect(screen.queryByTestId("conversation-minimap-preview")).not.toBeInTheDocument();
  });

  it("never displays another thread's stale preview after a thread switch", () => {
    const sections = buildSections(3);
    const { view } = renderMinimap({ sections, threadId: 7 });

    fireEvent.mouseEnter(screen.getAllByTestId("conversation-minimap-mark")[0]);
    expect(screen.getByTestId("conversation-minimap-preview")).toBeInTheDocument();

    view.rerender(
      <ConversationMinimap
        sections={sections}
        entries={buildConversationNavigationEntries(sections, 40)}
        activeSectionId={null}
        hasMore={false}
        threadId={8}
        canGoBack={false}
        onJump={vi.fn()}
        onBack={vi.fn()}
      />
    );

    expect(screen.queryByTestId("conversation-minimap-preview")).not.toBeInTheDocument();
  });

  it("labels the projection as loaded history when more messages remain", () => {
    renderMinimap({ hasMore: true });

    fireEvent.mouseEnter(screen.getAllByTestId("conversation-minimap-mark")[0]);

    expect(screen.getByTestId("conversation-minimap-loaded-note")).toHaveTextContent(
      "Loaded history"
    );
  });

  it("exposes a single back-to-previous-position action", () => {
    const { onBack } = renderMinimap({ canGoBack: true });

    const back = screen.getByTestId("conversation-minimap-back");
    expect(back).toHaveAttribute("aria-label", "Back to previous position");

    fireEvent.click(back);
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("hides the back action when there is no return position", () => {
    renderMinimap({ canGoBack: false });

    expect(screen.queryByTestId("conversation-minimap-back")).not.toBeInTheDocument();
  });
});

describe("ConversationMinimap keyboard navigation", () => {
  it("moves focus between marks with arrow keys without trapping focus", async () => {
    renderMinimap({ sections: buildSections(3) });

    const marks = screen.getAllByTestId("conversation-minimap-mark");
    // Moving DOM focus fires the focus handler, which opens the preview.
    await act(async () => {
      marks[0].focus();
    });
    expect(marks[0]).toHaveFocus();

    fireEvent.keyDown(marks[0], { key: "ArrowDown" });
    expect(marks[1]).toHaveFocus();

    fireEvent.keyDown(marks[1], { key: "ArrowUp" });
    expect(marks[0]).toHaveFocus();

    fireEvent.keyDown(marks[0], { key: "End" });
    expect(marks[2]).toHaveFocus();

    fireEvent.keyDown(marks[2], { key: "Home" });
    expect(marks[0]).toHaveFocus();
  });

  it("lets a keyboard user reach the destinations of a non-final range", async () => {
    const sections = buildSections(240);
    renderMinimap({ sections, maxMarks: 12 });

    const marks = screen.getAllByTestId("conversation-minimap-mark");
    // A grouped range that is not the last one.
    const firstRange = marks[0];

    await act(async () => {
      firstRange.focus();
    });
    expect(firstRange).toHaveFocus();

    fireEvent.keyDown(firstRange, { key: "Enter" });

    // Activating a range must not leave the keyboard user stranded on the
    // rail: the preview for that exact range has to be reachable.
    const destinations = screen.getAllByTestId("conversation-minimap-destination");
    expect(destinations.length).toBeGreaterThan(0);
    expect(
      document.activeElement?.getAttribute("data-testid")
    ).toBe("conversation-minimap-destination");

    // Escape returns the keyboard user to the mark they came from.
    fireEvent.keyDown(document.activeElement as HTMLElement, {
      key: "Escape",
    });

    expect(firstRange).toHaveFocus();
  });

  it("commits a jump when a focused mark is activated", () => {
    const sections = buildSections(3);
    const { onJump } = renderMinimap({ sections });

    const marks = screen.getAllByTestId("conversation-minimap-mark");
    fireEvent.click(marks[1]);

    expect(onJump).toHaveBeenCalledWith(sections[1].id);
  });
});

describe("ConversationMinimap touch behavior", () => {
  it("opens the preview on tap and requires a separate go-to-turn action", () => {
    const sections = buildSections(3);
    const { onJump } = renderMinimap({ sections });

    const marks = screen.getAllByTestId("conversation-minimap-mark");
    fireEvent.pointerDown(marks[1], { pointerType: "touch" });
    fireEvent.click(marks[1]);

    // A tap must not navigate on its own.
    expect(onJump).not.toHaveBeenCalled();
    expect(screen.getByTestId("conversation-minimap-preview")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("conversation-minimap-go-to-turn"));

    expect(onJump).toHaveBeenCalledTimes(1);
    expect(onJump).toHaveBeenCalledWith(sections[1].id);
  });

  it("keeps touch selection from navigating when a destination is tapped", () => {
    const sections = buildSections(3);
    const { onJump } = renderMinimap({ sections });

    fireEvent.pointerDown(screen.getAllByTestId("conversation-minimap-mark")[0], {
      pointerType: "touch",
    });
    fireEvent.click(screen.getAllByTestId("conversation-minimap-mark")[0]);

    const destinations = screen.getAllByTestId("conversation-minimap-destination");
    fireEvent.pointerDown(destinations[0], { pointerType: "touch" });
    fireEvent.click(destinations[0]);

    expect(onJump).not.toHaveBeenCalled();
    expect(destinations[0]).toHaveAttribute("data-selected", "true");
  });
});

describe("ConversationMinimap dense history", () => {
  it("coalesces dense marks into ranges and keeps every destination reachable", () => {
    const sections = buildSections(240);
    const { onJump } = renderMinimap({ sections, maxMarks: 12 });

    const marks = screen.getAllByTestId("conversation-minimap-mark");
    expect(marks.length).toBeLessThanOrEqual(12);
    expect(
      marks.some((mark) => mark.getAttribute("data-entry-kind") === "range")
    ).toBe(true);

    fireEvent.mouseEnter(marks[0]);
    const preview = screen.getByTestId("conversation-minimap-preview");
    const destinations = within(preview).getAllByTestId(
      "conversation-minimap-destination"
    );

    // Every loaded destination stays reachable through the range preview.
    expect(destinations.length).toBe(sections.length / marks.length);
    expect(destinations.length * marks.length).toBe(sections.length);

    fireEvent.click(destinations[0]);
    expect(onJump).toHaveBeenCalledTimes(1);
  });

  it("does not navigate when a range mark is clicked", () => {
    const sections = buildSections(240);
    const { onJump } = renderMinimap({ sections, maxMarks: 12 });

    const marks = screen.getAllByTestId("conversation-minimap-mark");
    fireEvent.click(marks[0]);

    expect(onJump).not.toHaveBeenCalled();
    expect(screen.getByTestId("conversation-minimap-preview")).toBeInTheDocument();
  });
});
