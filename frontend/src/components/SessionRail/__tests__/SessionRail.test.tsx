import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import SessionRail from "@/components/SessionRail/SessionRail";

const mkTab = (tabId: string, title: string) => ({
  tabId,
  pendingThread: false,
  title,
  modelId: "default",
  createdAt: "2026-02-14T00:00:00.000Z",
  updatedAt: "2026-02-14T00:00:00.000Z",
});

describe("SessionRail", () => {
  it("hides pill strip for a single tab while keeping utility controls visible", () => {
    const { container } = render(
      <SessionRail
        tabs={[mkTab("tab-1", "Solo")]}
        activeTabId="tab-1"
        onActivateTab={vi.fn()}
        onCloseTab={vi.fn()}
        onOpenTab={vi.fn()}
      />
    );

    expect(
      screen.getByRole("button", { name: "New tab" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Tab overflow" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Solo" })
    ).not.toBeInTheDocument();
    expect(container.querySelector(".overflow-x-auto")).not.toBeInTheDocument();
  });

  it("renders segmented strip with active and inactive tabs separated by dividers", () => {
    render(
      <SessionRail
        tabs={[mkTab("tab-1", "Alpha"), mkTab("tab-2", "Beta")]}
        activeTabId="tab-1"
        onActivateTab={vi.fn()}
        onCloseTab={vi.fn()}
        onOpenTab={vi.fn()}
      />
    );

    const alpha = screen.getByRole("button", { name: "Alpha" });
    const beta = screen.getByRole("button", { name: "Beta" });

    expect(screen.getByTestId("session-rail-track")).toBeInTheDocument();
    expect(alpha).toBeInTheDocument();
    expect(beta).toBeInTheDocument();
    expect(alpha).toHaveAttribute("data-state", "active");
    expect(beta).toHaveAttribute("data-state", "inactive");
  });

  it("renders dividers between adjacent tabs", () => {
    render(
      <SessionRail
        tabs={[mkTab("tab-1", "Alpha"), mkTab("tab-2", "Beta")]}
        activeTabId="tab-1"
        onActivateTab={vi.fn()}
        onCloseTab={vi.fn()}
        onOpenTab={vi.fn()}
      />
    );

    const dividers = screen.getAllByTestId("session-rail-divider");
    expect(dividers).toHaveLength(1);
  });

  it("inactive tabs do not render visible close controls", () => {
    render(
      <SessionRail
        tabs={[mkTab("tab-1", "Alpha"), mkTab("tab-2", "Beta")]}
        activeTabId="tab-1"
        onActivateTab={vi.fn()}
        onCloseTab={vi.fn()}
        onOpenTab={vi.fn()}
      />
    );

    const alphaTab = screen.getByTestId("session-rail-tab-tab-1");
    const betaTab = screen.getByTestId("session-rail-tab-tab-2");

    const alphaCloseButton = alphaTab.querySelector('button[aria-label="Close Alpha"]');
    const betaCloseButton = betaTab.querySelector('button[aria-label="Close Beta"]');

    expect(alphaCloseButton).toBeInTheDocument();
    expect(betaCloseButton).not.toBeInTheDocument();
  });

  it("active tab renders close control", () => {
    render(
      <SessionRail
        tabs={[mkTab("tab-1", "Alpha"), mkTab("tab-2", "Beta")]}
        activeTabId="tab-1"
        onActivateTab={vi.fn()}
        onCloseTab={vi.fn()}
        onOpenTab={vi.fn()}
      />
    );

    const closeButton = screen.getByRole("button", { name: "Close Alpha" });
    expect(closeButton).toBeInTheDocument();
  });

  it("preserves thread switching behavior", async () => {
    const user = userEvent.setup();
    const onActivateTab = vi.fn();

    render(
      <SessionRail
        tabs={[mkTab("tab-1", "Alpha"), mkTab("tab-2", "Beta")]}
        activeTabId="tab-1"
        isCloud
        showTabs
        onActivateTab={onActivateTab}
        onCloseTab={vi.fn()}
        onOpenTab={vi.fn()}
      />
    );

    expect(screen.queryByLabelText("Cloud mode")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Beta" }));
    expect(onActivateTab).toHaveBeenCalledWith("tab-2");
  });

  it("close button on active tab calls onCloseTab without activating tab", async () => {
    const user = userEvent.setup();
    const onActivateTab = vi.fn();
    const onCloseTab = vi.fn();

    render(
      <SessionRail
        tabs={[mkTab("tab-1", "Alpha"), mkTab("tab-2", "Beta")]}
        activeTabId="tab-1"
        showTabs
        onActivateTab={onActivateTab}
        onCloseTab={onCloseTab}
        onOpenTab={vi.fn()}
      />
    );

    const closeButton = screen.getByRole("button", { name: "Close Alpha" });
    await user.click(closeButton);

    expect(onCloseTab).toHaveBeenCalledWith("tab-1");
    expect(onActivateTab).not.toHaveBeenCalled();
  });

  it("labels truncate safely with min-w-0 and truncate classes", () => {
    render(
      <SessionRail
        tabs={[mkTab("tab-1", "Very Long Tab Title That Should Truncate")]}
        activeTabId="tab-1"
        showTabs
        onActivateTab={vi.fn()}
        onCloseTab={vi.fn()}
        onOpenTab={vi.fn()}
      />
    );

    const tabContainer = screen.getByTestId("session-rail-tab-tab-1");
    const labelButton = tabContainer.querySelector('button:not([aria-label])');
    expect(labelButton).toHaveClass("min-w-0", "flex-1", "truncate");
  });
});
