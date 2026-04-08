import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import SettingsPanelDock from "@/features/settings/components/SettingsPanelDock";

describe("SettingsPanelDock", () => {
  it("renders the dock language, hides connection on web, and keeps inactive tabs subdued", () => {
    const onTabChange = vi.fn();

    render(
      <SettingsPanelDock
        activeTab="appearance"
        onTabChange={onTabChange}
      />
    );

    expect(screen.getByRole("tablist", { name: "Settings tabs" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Appearance" })).toHaveAttribute(
      "data-state",
      "active"
    );
    expect(screen.getByRole("tab", { name: "Appearance" })).toHaveClass(
      "opacity-100"
    );
    expect(screen.getByRole("tab", { name: "Personal Facts" })).toHaveClass(
      "opacity-25"
    );
    expect(screen.queryByRole("tab", { name: "Connection" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Diagnostics" })).not.toBeInTheDocument();

    fireEvent.keyDown(screen.getByRole("tab", { name: "Appearance" }), {
      key: "ArrowRight",
    });

    expect(onTabChange).toHaveBeenCalledWith("system");
  });

  it("includes the desktop-only connection tab and roves to Personal Facts", () => {
    const onTabChange = vi.fn();

    render(
      <SettingsPanelDock
        activeTab="connection"
        desktopMode
        onTabChange={onTabChange}
      />
    );

    expect(screen.getByRole("tab", { name: "Connection" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByRole("tab", { name: "Personal Facts" })).toBeInTheDocument();

    fireEvent.keyDown(screen.getByRole("tab", { name: "Connection" }), {
      key: "ArrowRight",
    });

    expect(onTabChange).toHaveBeenCalledWith("personalFacts");
  });
});
