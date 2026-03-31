import React from "react";
import {
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
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
  }) => (
    <div className={className}>{children}</div>
  ),
}));

type WorkspaceHarnessRoute = "dashboard" | "guardian" | "documents";

function WorkspaceDrawerHarness({
  routeContext,
}: {
  routeContext: WorkspaceHarnessRoute;
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
  });

  afterEach(() => {
    cleanup();
  });

  it.each([
    ["dashboard", "Shelf"],
    ["guardian", "Scratchpad"],
    ["documents", "Inspector"],
  ] as const)(
    "defaults %s to %s when no tab is persisted yet",
    async (routeContext, expectedLabel) => {
      const user = userEvent.setup();

      render(<WorkspaceDrawerHarness routeContext={routeContext} />);

      await user.click(screen.getByTestId("workspace-open-button"));

      expect(screen.getByRole("tab", { name: expectedLabel })).toHaveAttribute(
        "aria-selected",
        "true"
      );
      expect(screen.getByRole("tabpanel")).toHaveTextContent(expectedLabel);
    }
  );

  it("switches tabs and updates the visible panel", async () => {
    const user = userEvent.setup();

    render(<WorkspaceDrawerHarness routeContext="dashboard" />);

    await user.click(screen.getByTestId("workspace-open-button"));

    const shelfTab = screen.getByRole("tab", { name: "Shelf" });
    shelfTab.focus();
    fireEvent.keyDown(shelfTab, { key: "ArrowRight" });

    expect(screen.getByRole("tab", { name: "Scratchpad" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Scratchpad");

    await user.click(screen.getByRole("tab", { name: "Inspector" }));

    expect(screen.getByRole("tab", { name: "Inspector" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Inspector");
  });

  it("close and reopen restores the chosen tab", async () => {
    const user = userEvent.setup();

    render(<WorkspaceDrawerHarness routeContext="dashboard" />);

    await user.click(screen.getByTestId("workspace-open-button"));
    await user.click(screen.getByRole("tab", { name: "Inspector" }));
    await user.click(screen.getByTestId("workspace-drawer-close"));

    expect(screen.queryByTestId("workspace-drawer")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("workspace-open-button"));

    expect(screen.getByRole("tab", { name: "Inspector" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Inspector");
  });

  it("persists the open state and chosen tab across remounts", async () => {
    const user = userEvent.setup();
    const { unmount } = render(
      <WorkspaceDrawerHarness routeContext="dashboard" />
    );

    await user.click(screen.getByTestId("workspace-open-button"));
    await user.click(screen.getByRole("tab", { name: "Inspector" }));

    unmount();

    render(<WorkspaceDrawerHarness routeContext="dashboard" />);

    expect(screen.getByTestId("workspace-drawer")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Inspector" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Inspector");
  });
});
