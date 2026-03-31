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

  it("shows a continuous rail shell with one focused pill and lighter inactive segments", () => {
    const { container } = render(
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
    expect(screen.getByTestId("session-rail-endcap")).toBeInTheDocument();
    expect(alpha).toBeInTheDocument();
    expect(beta).toBeInTheDocument();
    expect(alpha).toHaveAttribute("data-state", "active");
    expect(alpha).toHaveAttribute("data-variant", "pill");
    expect(beta).toHaveAttribute("data-state", "inactive");
    expect(beta).toHaveAttribute("data-variant", "segment");
    expect(container.querySelector(".overflow-x-auto")).toBeInTheDocument();
  });

  it("removes the badge ornament and preserves thread switching behavior", async () => {
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
});
