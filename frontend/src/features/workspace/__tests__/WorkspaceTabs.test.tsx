import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import WorkspaceTabs from "../components/WorkspaceTabs";
import type { WorkspaceDrawerTab } from "../state/useWorkspaceUiState";

describe("WorkspaceTabs", () => {
  const onTabChange = vi.fn();
  const onTabClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("segmented rail structure", () => {
    it("renders as a single continuous rail without glass-pill styling", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const rail = screen.getByTestId("workspace-tabs");
      expect(rail).toHaveClass("flex", "w-full", "items-center");
      expect(rail).not.toHaveClass("glass-pill");
    });

    it("renders all tabs as segments within the shared rail", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const tabs = screen.getAllByRole("tab");
      expect(tabs).toHaveLength(3);
    });

    it("inactive tabs do not use pill-tab class", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const inactiveTabs = screen.getAllByTestId(/workspace-tab-(scratchpad|inspector)/);
      inactiveTabs.forEach((tab) => {
        expect(tab).not.toHaveClass("pill-tab");
      });
    });

    it("active tab does not use pill-tab class", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const activeTab = screen.getByTestId("workspace-tab-shelf");
      expect(activeTab).not.toHaveClass("pill-tab");
    });

    it("rail uses segment-tab class for all tabs", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const tabs = screen.getAllByRole("tab");
      tabs.forEach((tab) => {
        expect(tab).toHaveClass("segment-tab");
      });
    });
  });

  describe("divider-based inactive tabs", () => {
    it("renders dividers between adjacent tabs", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const dividers = screen.getAllByTestId("workspace-tab-divider");
      expect(dividers).toHaveLength(2);
    });

    it("first tab has no preceding divider", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const shelfTab = screen.getByTestId("workspace-tab-shelf");
      expect(shelfTab.previousSibling).toBeNull();
    });

    it("dividers are thin vertical lines", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const divider = screen.getAllByTestId("workspace-tab-divider")[0];
      expect(divider).toHaveClass("h-4", "w-px");
    });
  });

  describe("active tab styling", () => {
    it("only the active tab has data-state=active", () => {
      render(
        <WorkspaceTabs
          activeTab="scratchpad"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const scratchpadTab = screen.getByTestId("workspace-tab-scratchpad");
      const shelfTab = screen.getByTestId("workspace-tab-shelf");
      const inspectorTab = screen.getByTestId("workspace-tab-inspector");

      expect(scratchpadTab).toHaveAttribute("data-state", "active");
      expect(shelfTab).toHaveAttribute("data-state", "inactive");
      expect(inspectorTab).toHaveAttribute("data-state", "inactive");
    });

    it("active tab is visually distinct from inactive tabs", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const activeTab = screen.getByTestId("workspace-tab-shelf");
      const inactiveTab = screen.getByTestId("workspace-tab-scratchpad");

      expect(activeTab).toHaveClass("segment-tab");
      expect(inactiveTab).toHaveClass("segment-tab");
      expect(activeTab).toHaveAttribute("data-state", "active");
      expect(inactiveTab).toHaveAttribute("data-state", "inactive");
    });
  });

  describe("close button behavior", () => {
    it("does not render close controls when onTabClose is not provided", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      expect(screen.queryByTestId("workspace-tab-shelf-close")).not.toBeInTheDocument();
    });

    it("inactive tabs do not render visible close controls", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          onTabClose={onTabClose}
          idBase="workspace"
        />
      );

      const scratchpadClose = screen.queryByTestId("workspace-tab-scratchpad-close");
      const inspectorClose = screen.queryByTestId("workspace-tab-inspector-close");

      expect(scratchpadClose).not.toBeInTheDocument();
      expect(inspectorClose).not.toBeInTheDocument();
    });

    it("selected tab renders the close control", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          onTabClose={onTabClose}
          idBase="workspace"
        />
      );

      const closeButton = screen.getByTestId("workspace-tab-shelf-close");
      expect(closeButton).toBeInTheDocument();
      expect(closeButton).toHaveClass("segment-close");
    });

    it("clicking close button on selected tab calls onTabClose", async () => {
      const user = userEvent.setup();

      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          onTabClose={onTabClose}
          idBase="workspace"
        />
      );

      const closeButton = screen.getByTestId("workspace-tab-shelf-close");
      await user.click(closeButton);

      expect(onTabClose).toHaveBeenCalledTimes(1);
      expect(onTabClose).toHaveBeenCalledWith("shelf");
    });

    it("close button does not trigger tab change", async () => {
      const user = userEvent.setup();

      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          onTabClose={onTabClose}
          idBase="workspace"
        />
      );

      const closeButton = screen.getByTestId("workspace-tab-shelf-close");
      await user.click(closeButton);

      expect(onTabChange).not.toHaveBeenCalled();
    });
  });

  describe("label truncation", () => {
    it("label lane supports min-w-0 for truncation", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const shelfTab = screen.getByTestId("workspace-tab-shelf");
      const labelSpan = shelfTab.querySelector("span");
      expect(labelSpan).toHaveClass("min-w-0", "flex-1", "truncate");
    });

    it("tabs do not reserve space for hidden close buttons", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          onTabClose={onTabClose}
          idBase="workspace"
        />
      );

      const inactiveTab = screen.getByTestId("workspace-tab-scratchpad");
      const closeButton = inactiveTab.querySelector('[data-testid$="-close"]');
      expect(closeButton).toBeNull();
    });
  });

  describe("keyboard navigation", () => {
    it("ArrowRight navigates to next tab", async () => {
      const user = userEvent.setup();

      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const shelfTab = screen.getByTestId("workspace-tab-shelf");
      shelfTab.focus();
      await user.keyboard("{ArrowRight}");

      expect(onTabChange).toHaveBeenCalledWith("scratchpad");
    });

    it("ArrowLeft navigates to previous tab", async () => {
      const user = userEvent.setup();

      render(
        <WorkspaceTabs
          activeTab="scratchpad"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const scratchpadTab = screen.getByTestId("workspace-tab-scratchpad");
      scratchpadTab.focus();
      await user.keyboard("{ArrowLeft}");

      expect(onTabChange).toHaveBeenCalledWith("shelf");
    });

    it("Home navigates to first tab", async () => {
      const user = userEvent.setup();

      render(
        <WorkspaceTabs
          activeTab="inspector"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const inspectorTab = screen.getByTestId("workspace-tab-inspector");
      inspectorTab.focus();
      await user.keyboard("{Home}");

      expect(onTabChange).toHaveBeenCalledWith("shelf");
    });

    it("End navigates to last tab", async () => {
      const user = userEvent.setup();

      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const shelfTab = screen.getByTestId("workspace-tab-shelf");
      shelfTab.focus();
      await user.keyboard("{End}");

      expect(onTabChange).toHaveBeenCalledWith("inspector");
    });
  });

  describe("accessibility", () => {
    it("tablist has correct aria-label", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      expect(screen.getByRole("tablist", { name: "Workspace panels" })).toBeInTheDocument();
    });

    it("active tab has aria-selected=true", () => {
      render(
        <WorkspaceTabs
          activeTab="scratchpad"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const scratchpadTab = screen.getByTestId("workspace-tab-scratchpad");
      expect(scratchpadTab).toHaveAttribute("aria-selected", "true");
    });

    it("inactive tabs have aria-selected=false", () => {
      render(
        <WorkspaceTabs
          activeTab="scratchpad"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const shelfTab = screen.getByTestId("workspace-tab-shelf");
      const inspectorTab = screen.getByTestId("workspace-tab-inspector");

      expect(shelfTab).toHaveAttribute("aria-selected", "false");
      expect(inspectorTab).toHaveAttribute("aria-selected", "false");
    });

    it("only active tab is focusable via tab key", () => {
      render(
        <WorkspaceTabs
          activeTab="shelf"
          onTabChange={onTabChange}
          idBase="workspace"
        />
      );

      const shelfTab = screen.getByTestId("workspace-tab-shelf");
      const scratchpadTab = screen.getByTestId("workspace-tab-scratchpad");
      const inspectorTab = screen.getByTestId("workspace-tab-inspector");

      expect(shelfTab).toHaveAttribute("tabIndex", "0");
      expect(scratchpadTab).toHaveAttribute("tabIndex", "-1");
      expect(inspectorTab).toHaveAttribute("tabIndex", "-1");
    });
  });
});
