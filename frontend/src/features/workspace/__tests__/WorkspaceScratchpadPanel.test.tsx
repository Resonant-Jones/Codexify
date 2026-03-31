import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WorkspaceScratchpadPanel from "../components/WorkspaceScratchpadPanel";
import {
  WORKSPACE_SCRATCHPAD_AUTOSAVE_DEBOUNCE_MS,
  getWorkspaceScratchpadStorageKey,
} from "../state/useWorkspaceScratchpadState";

function advanceAutosave() {
  act(() => {
    vi.advanceTimersByTime(WORKSPACE_SCRATCHPAD_AUTOSAVE_DEBOUNCE_MS);
  });
}

describe("WorkspaceScratchpadPanel", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("renders a real textarea, updates immediately, and autosaves with debounce", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const storageKey = getWorkspaceScratchpadStorageKey("thread-1");

    render(<WorkspaceScratchpadPanel threadIdentity="thread-1" />);

    const textarea = screen.getByTestId("workspace-scratchpad-textarea");
    expect(screen.queryByText(/Autosaves locally per thread/i)).not.toBeInTheDocument();
    expect(textarea).toHaveAttribute(
      "placeholder",
      "Stage plaintext notes, prompts, or fragments before moving them into the composer."
    );
    expect(screen.getByTestId("workspace-scratchpad-actions")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Move to composer" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Copy to Clipboard" })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Clear" })).toBeInTheDocument();
    expect(screen.getByTestId("workspace-scratchpad-status")).toHaveTextContent(
      "Scratchpad stays local to this browser."
    );

    await user.type(textarea, "hello");

    expect(textarea).toHaveValue("hello");
    expect(localStorage.getItem(storageKey)).toBeNull();

    act(() => {
      vi.advanceTimersByTime(WORKSPACE_SCRATCHPAD_AUTOSAVE_DEBOUNCE_MS - 1);
    });
    expect(localStorage.getItem(storageKey)).toBeNull();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(localStorage.getItem(storageKey)).toBe("hello");
  });

  it("restores saved text for the same thread after remount", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { unmount } = render(
      <WorkspaceScratchpadPanel threadIdentity="thread-restore" />
    );

    await user.type(
      screen.getByTestId("workspace-scratchpad-textarea"),
      "restore me"
    );
    advanceAutosave();

    unmount();

    render(<WorkspaceScratchpadPanel threadIdentity="thread-restore" />);

    expect(screen.getByTestId("workspace-scratchpad-textarea")).toHaveValue(
      "restore me"
    );
  });

  it("restores different scratchpad content for different threads", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { rerender } = render(
      <WorkspaceScratchpadPanel threadIdentity="thread-a" />
    );

    await user.type(screen.getByTestId("workspace-scratchpad-textarea"), "alpha");
    advanceAutosave();

    rerender(<WorkspaceScratchpadPanel threadIdentity="thread-b" />);
    expect(screen.getByTestId("workspace-scratchpad-textarea")).toHaveValue("");

    await user.type(screen.getByTestId("workspace-scratchpad-textarea"), "beta");
    advanceAutosave();

    rerender(<WorkspaceScratchpadPanel threadIdentity="thread-a" />);
    expect(screen.getByTestId("workspace-scratchpad-textarea")).toHaveValue(
      "alpha"
    );

    rerender(<WorkspaceScratchpadPanel threadIdentity="thread-b" />);
    expect(screen.getByTestId("workspace-scratchpad-textarea")).toHaveValue(
      "beta"
    );
  });

  it("moves scratchpad content into the expected composer integration path", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const onMoveToComposer = vi.fn();

    render(
      <WorkspaceScratchpadPanel
        threadIdentity="thread-move"
        onMoveToComposer={onMoveToComposer}
      />
    );

    await user.type(
      screen.getByTestId("workspace-scratchpad-textarea"),
      "move this"
    );
    await user.click(screen.getByRole("button", { name: "Move to composer" }));

    expect(onMoveToComposer).toHaveBeenCalledWith("move this");
    expect(screen.getByTestId("workspace-scratchpad-textarea")).toHaveValue(
      "move this"
    );
  });

  it("copies scratchpad content to the clipboard", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const writeText = vi.fn().mockResolvedValue(undefined);

    Object.defineProperty(window.navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(<WorkspaceScratchpadPanel threadIdentity="thread-copy" />);

    await user.type(
      screen.getByTestId("workspace-scratchpad-textarea"),
      "copy me"
    );
    await user.click(screen.getByRole("button", { name: "Copy to Clipboard" }));

    expect(writeText).toHaveBeenCalledWith("copy me");
  });

  it("clears the current thread scratchpad state", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const storageKey = getWorkspaceScratchpadStorageKey("thread-clear");

    render(<WorkspaceScratchpadPanel threadIdentity="thread-clear" />);

    await user.type(
      screen.getByTestId("workspace-scratchpad-textarea"),
      "clear me"
    );
    advanceAutosave();
    expect(localStorage.getItem(storageKey)).toBe("clear me");

    await user.click(screen.getByRole("button", { name: "Clear" }));

    expect(screen.getByTestId("workspace-scratchpad-textarea")).toHaveValue("");
    expect(localStorage.getItem(storageKey)).toBeNull();
  });
});
