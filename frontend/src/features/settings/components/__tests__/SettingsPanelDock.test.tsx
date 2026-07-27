import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import SettingsPanelDock from "@/features/settings/components/SettingsPanelDock";
import { SETTINGS_DENSITY } from "@/features/settings/settingsDensityContract";

describe("SettingsPanelDock", () => {
  test("keeps the tab rail sticky and labeled as a control surface", () => {
    render(
      <SettingsPanelDock>
        <button type="button" role="tab" aria-selected="true">
          Appearance
        </button>
        <button type="button" role="tab" aria-selected="false">
          Imprint
        </button>
        <button type="button" role="tab" aria-selected="false">
          Personal Facts
        </button>
      </SettingsPanelDock>
    );

    const dock = screen.getByRole("tablist", { name: "Settings tabs" });
    expect(dock).toHaveClass("sticky", "flex", "w-full", "justify-center");
    expect(dock).toHaveStyle({
      "--settings-nav-surface":
        "color-mix(in srgb, var(--panel-bg) 94%, var(--text) 6%)",
      "--pill-active-bg": "transparent",
      "--pill-active-text": "var(--text)",
      "--pill-active-border": "var(--accent)",
      "--pill-active-shadow":
        "0 0 calc(var(--radius-micro) * 0.75) color-mix(in srgb, var(--accent-weak) 72%, transparent)",
      position: "sticky",
      top: SETTINGS_DENSITY.edgeChrome,
      paddingInline: SETTINGS_DENSITY.edgeChrome,
    });
    expect(dock).toHaveAttribute("aria-orientation", "horizontal");
    const rail = screen.getByTestId("settings-panel-dock").querySelector(".glass-pill");
    expect(rail).toHaveClass("glass-pill", "w-full", "overflow-x-auto");
    expect(rail).toHaveStyle({ background: "var(--settings-nav-surface)" });
    expect(rail?.getAttribute("style")).not.toContain("var(--accent)");
    expect(rail).not.toHaveClass("flex-wrap", "whitespace-normal");
    const tabGroup = rail?.firstElementChild;
    expect(tabGroup).toHaveClass(
      "flex",
      "w-max",
      "min-w-full",
      "justify-evenly",
      "whitespace-nowrap"
    );
    expect(tabGroup).not.toHaveClass("flex-wrap");
    expect(screen.getByRole("tab", { name: "Appearance" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Imprint" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Personal Facts" })).toBeInTheDocument();
  });
});
