import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WorkspaceDrawer from "../components/WorkspaceDrawer";
import { useWorkspaceUiState } from "../state/useWorkspaceUiState";
import {
  BALANCED_SPLIT_MIN_RATIO,
  BALANCED_SPLIT_WORKSPACE_PANE_RATIO,
  MAX_WORKSPACE_PANE_RATIO,
  MIN_WORKSPACE_PANE_RATIO,
  WORKSPACE_FOCUS_MIN_RATIO,
  clampWorkspacePaneRatio,
  deriveWorkspaceLayoutMode,
  getNextWorkspaceLayoutMode,
  getWorkspaceLayoutRatioBucket,
  getWorkspacePaneRatioForLayoutMode,
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

vi.mock("@/components/documents/DocumentTile", () => ({
  default: ({
    file,
    onClick,
  }: {
    file: { name?: string; ext?: string };
    onClick?: () => void;
  }) => (
    <button type="button" data-testid="document-tile" onClick={onClick}>
      {file?.name || "Untitled"}
    </button>
  ),
}));

type WorkspaceHarnessRoute = "dashboard" | "guardian" | "documents";

function WorkspaceDrawerHarness({
  routeContext,
  activeThreadId = null,
  onMoveScratchpadToComposer,
  initialLayoutMode = "chat_focus",
  minPaneRatio = MIN_WORKSPACE_PANE_RATIO,
  maxPaneRatio = MAX_WORKSPACE_PANE_RATIO,
}: {
  routeContext: WorkspaceHarnessRoute;
  activeThreadId?: string | number | null;
  onMoveScratchpadToComposer?: (text: string) => void;
  initialLayoutMode?: WorkspaceLayoutMode;
  minPaneRatio?: number;
  maxPaneRatio?: number;
}) {
  const { isOpen, activeTab, open, close, setActiveTab } = useWorkspaceUiState({
    routeContext,
  });
  const [layoutMode, setLayoutMode] = React.useState<WorkspaceLayoutMode>(
    initialLayoutMode
  );
  const paneRatio = getWorkspacePaneRatioForLayoutMode(layoutMode);

  return (
    <>
      <button
        type="button"
        data-testid="workspace-open-button"
        onClick={() => {
          if (isOpen) {
            close();
            return;
          }
          open();
        }}
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
        onLayoutModeChange={setLayoutMode}
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
        paneRatio: MIN_WORKSPACE_PANE_RATIO,
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
    expect(getWorkspacePaneRatioForLayoutMode("chat_focus")).toBe(
      MIN_WORKSPACE_PANE_RATIO
    );
    expect(getWorkspacePaneRatioForLayoutMode("balanced_split")).toBe(
      BALANCED_SPLIT_WORKSPACE_PANE_RATIO
    );
    expect(getWorkspacePaneRatioForLayoutMode("workspace_focus")).toBe(
      MAX_WORKSPACE_PANE_RATIO
    );
    expect(getNextWorkspaceLayoutMode("chat_focus")).toBe("balanced_split");
    expect(getNextWorkspaceLayoutMode("balanced_split")).toBe(
      "workspace_focus"
    );
    expect(getNextWorkspaceLayoutMode("workspace_focus")).toBe("chat_focus");
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
      expectedText: "Select a thread or project to see linked items.",
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
      expectedText: "Select a document from the Shelf to preview it here.",
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

      await user.click(screen.getByTestId("workspace-open-button"));
      expect(screen.queryByTestId("workspace-drawer")).not.toBeInTheDocument();
    }
  );

  it("keeps Shelf as real panel, Inspector as placeholder while Scratchpad is interactive", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(<WorkspaceDrawerHarness routeContext="dashboard" />);

    await user.click(screen.getByTestId("workspace-open-button"));
    await user.click(screen.getByRole("tab", { name: "Scratchpad" }));

    expect(
      screen.getByTestId("workspace-scratchpad-textarea")
    ).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Inspector" }));
    expect(screen.getByRole("tabpanel")).toHaveTextContent(
      "Select a document from the Shelf to preview it here."
    );
    expect(screen.getAllByText(/^Inspector$/)).toHaveLength(1);

    await user.click(screen.getByRole("tab", { name: "Shelf" }));
    expect(screen.getByRole("tabpanel")).toHaveTextContent(
      "Select a thread or project to see linked items."
    );
    expect(screen.getAllByRole("tab", { name: "Shelf" })).toHaveLength(1);
  });

  it("renders posture as a quiet button that cycles and resets the layout mode", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(<WorkspaceDrawerHarness routeContext="documents" />);

    await user.click(screen.getByTestId("workspace-open-button"));

    expect(screen.getByTestId("workspace-drawer-header")).toHaveAttribute(
      "data-header-layout",
      "centered"
    );
    expect(screen.getByTestId("workspace-drawer-title")).toHaveTextContent(
      "Workspace"
    );
    const posture = screen.getByTestId("workspace-drawer-posture");
    expect(posture.tagName).toBe("BUTTON");
    expect(posture).toHaveTextContent("Chat Focus");
    expect(posture).toHaveClass("cursor-pointer");
    expect(screen.getByTestId("workspace-drawer")).toHaveAttribute(
      "data-layout-mode",
      "chat_focus"
    );
    expect(screen.getByTestId("workspace-drawer")).toHaveAttribute(
      "data-layout-label",
      "Chat Focus"
    );

    await user.click(posture);
    expect(posture).toHaveTextContent("Balanced Split");
    expect(screen.getByTestId("workspace-drawer")).toHaveAttribute(
      "data-layout-mode",
      "balanced_split"
    );

    await user.click(posture);
    expect(posture).toHaveTextContent("Workspace Focus");
    expect(screen.getByTestId("workspace-drawer")).toHaveAttribute(
      "data-layout-mode",
      "workspace_focus"
    );

    await user.click(posture);
    expect(posture).toHaveTextContent("Chat Focus");
    expect(screen.getByTestId("workspace-drawer")).toHaveAttribute(
      "data-layout-mode",
      "chat_focus"
    );

    await user.dblClick(posture);
    expect(posture).toHaveTextContent("Chat Focus");
    expect(screen.getByTestId("workspace-drawer")).toHaveAttribute(
      "data-layout-mode",
      "chat_focus"
    );
    expect(
      screen.queryByRole("button", { name: "Close workspace" })
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("workspace-drawer-close")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Workspace Focus" })
    ).not.toBeInTheDocument();

    const tablist = screen.getByRole("tablist", { name: "Workspace panels" });
    expect(tablist).toBeInTheDocument();
    expect(screen.getByTestId("workspace-tabs")).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(3);
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
      "Chat Focus"
    );
    expect(screen.queryByTestId("workspace-drawer-close")).not.toBeInTheDocument();
    expect(screen.queryByText(/Autosaves locally per thread/i)).not.toBeInTheDocument();
    expect(screen.getAllByText(/^Scratchpad$/)).toHaveLength(1);
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

  it("keeps layout mode stable while active tabs change", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(
      <WorkspaceDrawerHarness
        routeContext="dashboard"
        initialLayoutMode="workspace_focus"
      />
    );

    await user.click(screen.getByTestId("workspace-open-button"));

    const drawer = screen.getByTestId("workspace-drawer");
    expect(drawer).toHaveAttribute("data-layout-mode", "workspace_focus");
    expect(drawer).toHaveAttribute("data-layout-label", "Workspace Focus");
    expect(drawer).toHaveAttribute(
      "data-pane-ratio",
      MAX_WORKSPACE_PANE_RATIO.toFixed(2)
    );
    expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
      "Workspace Focus"
    );

    await user.click(screen.getByRole("tab", { name: "Scratchpad" }));
    expect(drawer).toHaveAttribute("data-layout-mode", "workspace_focus");
    expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
      "Workspace Focus"
    );

    await user.click(screen.getByRole("tab", { name: "Inspector" }));
    expect(drawer).toHaveAttribute("data-layout-mode", "workspace_focus");
    expect(screen.getByTestId("workspace-drawer-posture")).toHaveTextContent(
      "Workspace Focus"
    );
  });

  it("switches to inspector tab when shelf document is clicked", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    const docResponse = {
      ok: true,
      json: () =>
        Promise.resolve({
          documents: [
            {
              id: "doc-1",
              filename: "test-doc.pdf",
              src_url: "/media/documents/doc-1.pdf",
              mime_type: "application/pdf",
            },
          ],
          images: [],
        }),
    };

    const globalFetch = vi.fn()
      .mockResolvedValueOnce(docResponse)
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ images: [] }) });
    vi.stubGlobal("fetch", globalFetch);

    render(<WorkspaceDrawerHarness routeContext="dashboard" activeThreadId="thread-123" />);

    await user.click(screen.getByTestId("workspace-open-button"));

    expect(screen.getByRole("tab", { name: "Shelf" })).toHaveAttribute(
      "aria-selected",
      "true"
    );

    await user.click(await screen.findByTestId("document-tile"));

    expect(screen.getByRole("tab", { name: "Inspector" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByRole("tabpanel")).toHaveTextContent(/test-doc.pdf/i);
  });
});
