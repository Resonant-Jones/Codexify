import React from "react";
import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WorkspaceDrawer from "../components/WorkspaceDrawer";
import { useWorkspaceUiState } from "../state/useWorkspaceUiState";

vi.mock("@/components/surface/FrameCard", () => ({
  default: ({
    children,
    className,
  }: {
    children?: React.ReactNode;
    className?: string;
  }) => <div className={className}>{children}</div>,
}));

type WorkspaceHarnessRoute = "dashboard" | "guardian" | "documents";

function WorkspaceDrawerHarness({
  routeContext,
  activeThreadId = null,
  onMoveScratchpadToComposer,
}: {
  routeContext: WorkspaceHarnessRoute;
  activeThreadId?: string | number | null;
  onMoveScratchpadToComposer?: (text: string) => void;
}) {
  const { isOpen, activeTab, open, close, setActiveTab } = useWorkspaceUiState({
    routeContext,
  });

  return (
    <>
      <button
        type="button"
        data-testid="workspace-open-button"
        onClick={() => open()}
      >
        Open workspace
      </button>
      <WorkspaceDrawer
        routeContext={routeContext}
        isOpen={isOpen}
        activeTab={activeTab}
        activeThreadId={activeThreadId}
        onMoveScratchpadToComposer={onMoveScratchpadToComposer}
        onOpenChange={(nextOpen) => {
          if (nextOpen) {
            open();
            return;
          }
          close();
        }}
        onActiveTabChange={setActiveTab}
      />
    </>
  );
}

describe("WorkspaceDrawer shell", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it.each([
    {
      routeContext: "dashboard" as const,
      expectedLabel: "Shelf",
      expectedText: "Shelf items will appear here in a later phase.",
    },
    {
      routeContext: "guardian" as const,
      expectedLabel: "Scratchpad",
      expectedText: "Plaintext staging area.",
    },
    {
      routeContext: "documents" as const,
      expectedLabel: "Inspector",
      expectedText: "Inspector renderers will plug into this panel in a later phase.",
    },
  ])(
    "defaults $routeContext to $expectedLabel",
    async ({ routeContext, expectedLabel, expectedText }) => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      render(<WorkspaceDrawerHarness routeContext={routeContext} />);

      await user.click(screen.getByTestId("workspace-open-button"));

      expect(screen.getByRole("tab", { name: expectedLabel })).toHaveAttribute(
        "aria-selected",
        "true"
      );
      expect(screen.getByRole("tabpanel")).toHaveTextContent(expectedText);
    }
  );

  it("keeps Shelf and Inspector as placeholders while Scratchpad is interactive", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(<WorkspaceDrawerHarness routeContext="dashboard" />);

    await user.click(screen.getByTestId("workspace-open-button"));
    await user.click(screen.getByRole("tab", { name: "Scratchpad" }));

    expect(
      screen.getByTestId("workspace-scratchpad-textarea")
    ).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Inspector" }));
    expect(screen.getByRole("tabpanel")).toHaveTextContent(
      "Inspector renderers will plug into this panel in a later phase."
    );

    await user.click(screen.getByRole("tab", { name: "Shelf" }));
    expect(screen.getByRole("tabpanel")).toHaveTextContent(
      "Shelf items will appear here in a later phase."
    );
  });

  it("drawer close and reopen preserves the current thread scratchpad content", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(
      <WorkspaceDrawerHarness
        routeContext="guardian"
        activeThreadId="thread-77"
      />
    );

    await user.click(screen.getByTestId("workspace-open-button"));
    await user.type(
      screen.getByTestId("workspace-scratchpad-textarea"),
      "Thread scoped draft"
    );
    await user.click(screen.getByTestId("workspace-drawer-close"));

    expect(screen.queryByTestId("workspace-drawer")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("workspace-open-button"));

    expect(screen.getByTestId("workspace-scratchpad-textarea")).toHaveValue(
      "Thread scoped draft"
    );
  });

  it("moves scratchpad content through the drawer integration path", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const onMoveScratchpadToComposer = vi.fn();

    render(
      <WorkspaceDrawerHarness
        routeContext="guardian"
        activeThreadId="thread-88"
        onMoveScratchpadToComposer={onMoveScratchpadToComposer}
      />
    );

    await user.click(screen.getByTestId("workspace-open-button"));
    await user.type(
      screen.getByTestId("workspace-scratchpad-textarea"),
      "Stage this for the composer"
    );
    await user.click(screen.getByRole("button", { name: "Move to composer" }));

    expect(onMoveScratchpadToComposer).toHaveBeenCalledWith(
      "Stage this for the composer"
    );
  });
});
