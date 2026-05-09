import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import WorkspaceTabs from "../components/WorkspaceTabs";

describe("WorkspaceTabs", () => {
  const onTabChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the shared rail with pill tabs for each workspace", () => {
    render(
      <WorkspaceTabs
        activeTab="shelf"
        onTabChange={onTabChange}
        idBase="workspace"
      />
    );

    const rail = screen.getByTestId("workspace-tabs");
    expect(rail).toHaveClass("glass-pill", "flex", "w-full", "items-center");

    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(3);
    tabs.forEach((tab) => {
      expect(tab).toHaveClass("pill-tab");
      expect(tab.tagName).toBe("BUTTON");
    });
  });

  it("marks only the active tab as selected", () => {
    render(
      <WorkspaceTabs
        activeTab="scratchpad"
        onTabChange={onTabChange}
        idBase="workspace"
      />
    );

    expect(screen.getByTestId("workspace-tab-shelf")).toHaveAttribute("data-state", "inactive");
    expect(screen.getByTestId("workspace-tab-scratchpad")).toHaveAttribute("data-state", "active");
    expect(screen.getByTestId("workspace-tab-inspector")).toHaveAttribute("data-state", "inactive");
  });

  it("switches tabs by click and arrow-key navigation", async () => {
    const user = userEvent.setup();

    render(
      <WorkspaceTabs
        activeTab="shelf"
        onTabChange={onTabChange}
        idBase="workspace"
      />
    );

    await user.click(screen.getByRole("tab", { name: "Scratchpad" }));
    expect(onTabChange).toHaveBeenCalledWith("scratchpad");

    const shelfTab = screen.getByRole("tab", { name: "Shelf" });
    shelfTab.focus();

    await user.keyboard("{ArrowRight}");
    expect(onTabChange).toHaveBeenCalledWith("scratchpad");

    await user.keyboard("{End}");
    expect(onTabChange).toHaveBeenCalledWith("inspector");

    await user.keyboard("{Home}");
    expect(onTabChange).toHaveBeenCalledWith("shelf");
  });
});
