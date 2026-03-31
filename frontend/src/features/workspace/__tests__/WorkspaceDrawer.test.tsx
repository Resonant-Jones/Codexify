import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WorkspaceDrawer from "../components/WorkspaceDrawer";
import { useWorkspaceUiState } from "../state/useWorkspaceUiState";
import {
  BALANCED_SPLIT_MIN_RATIO,
  DEFAULT_WORKSPACE_PANE_RATIO,
  MAX_WORKSPACE_PANE_RATIO,
  MIN_WORKSPACE_PANE_RATIO,
  WORKSPACE_FOCUS_MIN_RATIO,
  clampWorkspacePaneRatio,
  deriveWorkspaceLayoutMode,
  getWorkspaceLayoutRatioBucket,
  type WorkspaceLayoutMode,
} from "../state/useWorkspaceLayoutMode";

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
  layoutMode = "balanced_split",
  paneRatio = DEFAULT_WORKSPACE_PANE_RATIO,
  minPaneRatio = MIN_WORKSPACE_PANE_RATIO,
  maxPaneRatio = MAX_WORKSPACE_PANE_RATIO,
}: {
  routeContext: WorkspaceHarnessRoute;
  activeThreadId?: string | number | null;
  onMoveScratchpadToComposer?: (text: string) => void;
  layoutMode?: WorkspaceLayoutMode;
  paneRatio?: number;
  minPaneRatio?: number;
  maxPaneRatio?: number;
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
        layoutMode={layoutMode}
        paneRatio={paneRatio}
        minPaneRatio={minPaneRatio}
        maxPaneRatio={maxPaneRatio}
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

describe("workspace layout mode contract", () => {
  it("derives layout mode from deterministic thresholds and clamps pane bounds", () => {
    expect(clampWorkspacePaneRatio(MIN_WORKSPACE_PANE_RATIO - 0.2)).toBe(
      MIN_WORKSPACE_PANE_RATIO
    );
    expect(clampWorkspacePaneRatio(MAX_WORKSPACE_PANE_RATIO + 0.2)).toBe(
      MAX_WORKSPACE_PANE_RATIO
    );
    expect(
      deriveWorkspaceLayoutMode({
        isOpen: false,
        paneRatio: MAX_WORKSPACE_PANE_RATIO,
      })
    ).toBe("chat_focus");
    expect(
      deriveWorkspaceLayoutMode({
        isOpen: true,
        paneRatio: BALANCED_SPLIT_MIN_RATIO,
      })
    ).toBe("balanced_split");
    expect(
      deriveWorkspaceLayoutMode({
        isOpen: true,
        paneRatio: WORKSPACE_FOCUS_MIN_RATIO,
      })
    ).toBe("workspace_focus");
    expect(getWorkspaceLayoutRatioBucket("chat_focus")).toBe("chat_first");
    expect(getWorkspaceLayoutRatioBucket("balanced_split")).toBe("shared");
    expect(getWorkspaceLayoutRatioBucket("workspace_focus")).toBe(
      "workspace_first"
    );
  });
});

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
      expectedPlaceholder:
        "Stage plaintext notes, prompts, or fragments before moving them into the composer.",
    },
    {
      routeContext: "documents" as const,
      expectedLabel: "Inspector",
      expectedText: "Inspector renderers will plug into this panel in a later phase.",
    },
  ])(
    "defaults $routeContext to $expectedLabel",
    async ({
      routeContext,
      expectedLabel,
      expectedText,
      expectedPlaceholder,
    }) => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      render(<WorkspaceDrawerHarness routeContext={routeContext} />);

      await user.click(screen.getByTestId("workspace-open-button"));

      expect(screen.getByRole("tab", { name: expectedLabel })).toHaveAttribute(
        "aria-selected",
        "true"
      );
      if (expectedText) {
        expect(screen.getByRole("tabpanel")).toHaveTextContent(expectedText);
      }
      if (expectedPlaceholder) {
        expect(
          screen.getByTestId("workspace-scratchpad-textarea")
        ).toHaveAttribute("placeholder", expectedPlaceholder);
      }
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

  it("renders posture as passive status text while tabs remain the interactive controls", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(
      <WorkspaceDrawerHarness
        routeContext="documents"
        layoutMode="workspace_focus"
        paneRatio={MAX_WORKSPACE_PANE_RATIO}
      />
    );

    await user.click(screen.getByTestId("workspace-open-button"));

    expect(screen.getByTestId("workspace-drawer-header")).toHaveAttribute(
      "data-header-layout",
      "centered"
    );
    expect(screen.getByTestId("workspace-drawer-title")).toHaveTextContent(
      "Workspace"
    );
    const posture = screen.getByTestId("workspace-drawer-posture");
    expect(posture.tagName).toBe("P");
    expect(posture).toHaveTextContent("Workspace focus");
    expect(
      screen.queryByRole("button", { name: "Workspace focus" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("tab", { name: "Workspace focus" })
    ).not.toBeInTheDocument();

    const tablist = screen.getByRole("tablist", { name: "Workspace panels" });
    expect(tablist).toBeInTheDocument();
    expect(screen.getByTestId("workspace-tabs")).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(3);
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

  it("keeps the header honest and preserves scratchpad meaning and actions", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(<WorkspaceDrawerHarness routeContext="guardian" />);

    await user.click(screen.getByTestId("workspace-open-button"));

    expect(screen.queryByText("Guardian surface")).not.toBeInTheDocument();
    expect(screen.getByTestId("workspace-drawer-header")).toHaveAttribute(
      "data-header-layout",
      "centered"
    );
    expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
      "Balanced split"
    );
    expect(screen.queryByText(/Autosaves locally per thread/i)).not.toBeInTheDocument();
    expect(
      screen.getByTestId("workspace-scratchpad-textarea")
    ).toHaveAttribute(
      "placeholder",
      "Stage plaintext notes, prompts, or fragments before moving them into the composer."
    );
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
  });

  it("renders distinct visible posture labels for balanced and dominant layouts", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { rerender } = render(
      <WorkspaceDrawerHarness
        routeContext="documents"
        layoutMode="balanced_split"
        paneRatio={DEFAULT_WORKSPACE_PANE_RATIO}
      />
    );

    await user.click(screen.getByTestId("workspace-open-button"));

    expect(screen.getByTestId("workspace-drawer")).toHaveAttribute(
      "data-layout-label",
      "Balanced split"
    );
    expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
      "Balanced split"
    );

    rerender(
      <WorkspaceDrawerHarness
        routeContext="documents"
        layoutMode="workspace_focus"
        paneRatio={MAX_WORKSPACE_PANE_RATIO}
      />
    );

    expect(screen.getByTestId("workspace-drawer")).toHaveAttribute(
      "data-layout-label",
      "Workspace focus"
    );
    expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
      "Workspace focus"
    );
  });

  it("keeps layout mode stable while active tabs change", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(
      <WorkspaceDrawerHarness
        routeContext="dashboard"
        layoutMode="workspace_focus"
        paneRatio={MAX_WORKSPACE_PANE_RATIO}
      />
    );

    await user.click(screen.getByTestId("workspace-open-button"));

    const drawer = screen.getByTestId("workspace-drawer");
    expect(drawer).toHaveAttribute("data-layout-mode", "workspace_focus");
    expect(drawer).toHaveAttribute("data-layout-label", "Workspace focus");
    expect(drawer).toHaveAttribute(
      "data-pane-ratio",
      MAX_WORKSPACE_PANE_RATIO.toFixed(2)
    );
    expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
      "Workspace focus"
    );

    await user.click(screen.getByRole("tab", { name: "Scratchpad" }));
    expect(drawer).toHaveAttribute("data-layout-mode", "workspace_focus");
    expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
      "Workspace focus"
    );

    await user.click(screen.getByRole("tab", { name: "Inspector" }));
    expect(drawer).toHaveAttribute("data-layout-mode", "workspace_focus");
    expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
      "Workspace focus"
    );
  });
});
