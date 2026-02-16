import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import SessionRail from "@/components/SessionRail/SessionRail";

vi.mock("@/components/ProviderSelect", () => ({
  ProviderSelect: ({
    value,
    onChange,
  }: {
    value: string;
    onChange?: (value: string) => void;
  }) => (
    <button
      type="button"
      data-testid="provider-select"
      onClick={() => onChange?.("default")}
    >
      provider:{value}
    </button>
  ),
}));

const mkTab = (tabId: string, title: string) => ({
  tabId,
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
        activeModelId="default"
        onActivateTab={vi.fn()}
        onCloseTab={vi.fn()}
        onOpenTab={vi.fn()}
        onSetModel={vi.fn()}
      />
    );

    expect(screen.getByTestId("provider-select")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "New tab" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Tab overflow" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Solo" })
    ).not.toBeInTheDocument();
    expect(container.querySelector(".overflow-x-auto")).not.toBeInTheDocument();
  });

  it("shows pill strip with overflow container when multiple tabs are present", () => {
    const { container } = render(
      <SessionRail
        tabs={[mkTab("tab-1", "Alpha"), mkTab("tab-2", "Beta")]}
        activeTabId="tab-1"
        activeModelId="default"
        onActivateTab={vi.fn()}
        onCloseTab={vi.fn()}
        onOpenTab={vi.fn()}
        onSetModel={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "Alpha" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Beta" })).toBeInTheDocument();
    expect(container.querySelector(".overflow-x-auto")).toBeInTheDocument();
  });

  it("renders active system profile badge near model controls", () => {
    render(
      <SessionRail
        tabs={[mkTab("tab-1", "Alpha")]}
        activeTabId="tab-1"
        activeModelId="default"
        activeProfileId="local_mode"
        activeProfileName="Local Mode"
        activeProfileMode="local"
        profiles={[
          { id: "default", name: "Default", mode: "cloud" },
          { id: "local_mode", name: "Local Mode", mode: "local" },
        ]}
        onActivateTab={vi.fn()}
        onCloseTab={vi.fn()}
        onOpenTab={vi.fn()}
        onSetModel={vi.fn()}
        onSetProfile={vi.fn()}
      />
    );

    const profileTrigger = screen.getByRole("button", {
      name: "Switch system profile",
    });
    expect(profileTrigger).toHaveTextContent("Local Mode");
  });
});
