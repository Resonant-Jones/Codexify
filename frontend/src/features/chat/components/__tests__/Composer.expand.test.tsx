import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Composer } from "@/features/chat/components/Composer";

vi.mock("@/lib/api", () => ({
  default: {
    post: vi.fn(),
  },
}));

describe("Composer expansion", () => {
  afterEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("renders collapsed with an accessible desktop expand control", () => {
    render(<Composer onSend={vi.fn()} draftScopeKey="thread-1" draftValue="" />);

    const expandButton = screen.getByRole("button", {
      name: "Expand composer",
    });

    expect(expandButton).toHaveAttribute("type", "button");
    expect(expandButton).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByTestId("composer-textarea-surface")).toHaveAttribute(
      "data-expanded",
      "false"
    );
  });

  it("expands without sending, committing, or replacing the current draft", () => {
    const onSend = vi.fn();
    const onDraftValueChange = vi.fn();

    render(
      <Composer
        onSend={onSend}
        draftScopeKey="thread-1"
        draftValue=""
        draftSyncDebounceMs={10_000}
        onDraftValueChange={onDraftValueChange}
      />
    );

    const textarea = screen.getByTestId("composer-textarea");
    const expandButton = screen.getByRole("button", {
      name: "Expand composer",
    });

    textarea.focus();
    fireEvent.change(textarea, { target: { value: "Long-form task draft" } });
    fireEvent.mouseDown(expandButton);
    fireEvent.click(expandButton);

    expect(textarea).toHaveValue("Long-form task draft");
    expect(textarea).toHaveFocus();
    expect(onDraftValueChange).not.toHaveBeenCalled();
    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Collapse composer" })).toHaveAttribute(
      "aria-expanded",
      "true"
    );
    expect(screen.getByTestId("composer-textarea-surface")).toHaveAttribute(
      "data-expanded",
      "true"
    );
    expect(textarea.style.maxHeight).toBe("var(--composer-expanded-max-h)");
    expect(textarea.style.overflowY).toBe("auto");
  });

  it("collapses back to the normal autosize mode without changing the draft", () => {
    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="thread-1"
        draftValue="Retain this draft"
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Expand composer" }));
    fireEvent.click(screen.getByRole("button", { name: "Collapse composer" }));

    const textarea = screen.getByTestId("composer-textarea");
    expect(textarea).toHaveValue("Retain this draft");
    expect(screen.getByRole("button", { name: "Expand composer" })).toHaveAttribute(
      "aria-expanded",
      "false"
    );
    expect(screen.getByTestId("composer-textarea-surface")).toHaveAttribute(
      "data-expanded",
      "false"
    );
    expect(textarea.style.maxHeight).not.toBe(
      "var(--composer-expanded-max-h)"
    );
    expect(textarea.style.overflowY).toBe("hidden");
  });

  it("contains expansion to the desktop composer and resets it on compact mobile", () => {
    const { rerender } = render(
      <Composer onSend={vi.fn()} draftScopeKey="thread-1" draftValue="" />
    );

    fireEvent.click(screen.getByRole("button", { name: "Expand composer" }));

    rerender(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="thread-1"
        draftValue=""
        compactMobile
      />
    );

    expect(
      screen.queryByRole("button", { name: "Expand composer" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Collapse composer" })
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("composer-textarea-surface")).toHaveAttribute(
      "data-expanded",
      "false"
    );
    expect(screen.getByTestId("composer-textarea")).toHaveAttribute(
      "rows",
      "1"
    );
  });
});
