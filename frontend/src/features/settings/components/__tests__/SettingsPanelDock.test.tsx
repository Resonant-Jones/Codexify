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
    expect(dock).toHaveAttribute("aria-orientation", "horizontal");
    expect(dock).toHaveStyle({
      position: "sticky",
      top: SETTINGS_DENSITY.edgeChrome,
      paddingInline: SETTINGS_DENSITY.edgeChrome,
    });
  });

  test("does not paint an opaque panel-bg surface as the rail background", () => {
    // The legacy dock forced a panel-bg-heavy inline background on the
    // glass-pill rail. The refractive-glass build must let the canonical
    // .glass-pill material show through, so no opaque surface override
    // should be applied here.
    render(
      <SettingsPanelDock>
        <button type="button" role="tab" aria-selected="true">
          Appearance
        </button>
      </SettingsPanelDock>
    );

    const dock = screen.getByRole("tablist", { name: "Settings tabs" });
    const navStyle = (dock.getAttribute("style") ?? "").toLowerCase();
    expect(navStyle).not.toContain("--settings-nav-surface");
    expect(navStyle).not.toContain("var(--panel-bg) 86%");
    expect(navStyle).not.toContain("var(--panel-bg) 92%");

    const rail = screen
      .getByTestId("settings-panel-dock")
      .querySelector(".glass-pill");
    expect(rail).toBeTruthy();
    const railStyle = (rail?.getAttribute("style") ?? "").toLowerCase();
    expect(railStyle).not.toContain("--settings-nav-surface");
    // The rail must not redeclare `background:` inline — the canonical
    // .glass-pill material is the only surface.
    expect(railStyle).not.toMatch(/(^|;|\s)background\s*:/);
  });

  test("gives the dock a bounded Settings-specific material class hook", () => {
    render(
      <SettingsPanelDock>
        <button type="button" role="tab" aria-selected="true">
          Appearance
        </button>
      </SettingsPanelDock>
    );

    const rail = screen
      .getByTestId("settings-panel-dock")
      .querySelector(".glass-pill");
    expect(rail).toHaveClass(
      "settings-panel-dock__glass",
      "glass-pill",
      "w-full",
      "overflow-x-auto"
    );
    // The bounded material hook must not be inherited from .glass-pill —
    // it is a Settings-specific identifier.
    expect(rail).not.toHaveClass("flex-wrap", "whitespace-normal");
  });

  test("does not override the canonical active-selector tokens", () => {
    // The active tab inherits the canonical .pill-tab[data-state="active"]
    // styling through the shared pill primitives — same as the Theme
    // selector. The dock does not set --pill-active-* on the <nav>, so the
    // selected tab falls back to the canonical defaults.
    render(
      <SettingsPanelDock>
        <button type="button" role="tab" aria-selected="true">
          Appearance
        </button>
      </SettingsPanelDock>
    );

    const dock = screen.getByRole("tablist", { name: "Settings tabs" });
    const navStyle = dock.getAttribute("style") ?? "";

    // The dock must not pin dock-specific --pill-active-* values.
    expect(navStyle).not.toContain("--pill-active-bg");
    expect(navStyle).not.toContain("--pill-active-border");
    expect(navStyle).not.toContain("--pill-active-shadow");
    expect(navStyle).not.toContain("--pill-active-text");

    // And it must not hardcode a brand color for the active selector.
    expect(navStyle.toLowerCase()).not.toMatch(/#[0-9a-f]{3,6}\b/);
  });

  test("preserves dock geometry, tab layout, and ARIA semantics", () => {
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

    const rail = screen
      .getByTestId("settings-panel-dock")
      .querySelector(".glass-pill");
    expect(rail).toHaveClass("glass-pill", "w-full", "overflow-x-auto");
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
    expect(
      screen.getByRole("tab", { name: "Personal Facts" })
    ).toBeInTheDocument();
  });
});
