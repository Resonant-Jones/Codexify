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

  test("drives the active selector from the system-accent tokens", () => {
    // The selected tab must read as a luminous accent-backed pill, not a
    // transparent placeholder. The color must follow the resolved
    // --accent-strong token so it changes automatically when the system
    // accent changes.
    render(
      <SettingsPanelDock>
        <button type="button" role="tab" aria-selected="true">
          Appearance
        </button>
      </SettingsPanelDock>
    );

    const dock = screen.getByRole("tablist", { name: "Settings tabs" });
    const navStyle = dock.getAttribute("style") ?? "";

    // The active fill is token-driven and non-transparent.
    const activeBg = dock.style.getPropertyValue("--pill-active-bg");
    expect(activeBg).not.toBe("");
    expect(activeBg.trim().toLowerCase()).not.toBe("transparent");
    expect(activeBg).toContain("var(--accent-strong)");

    // The active border / shadow must derive from accent tokens.
    const activeBorder = dock.style.getPropertyValue("--pill-active-border");
    expect(activeBorder).toContain("var(--accent-strong)");

    const activeShadow = dock.style.getPropertyValue("--pill-active-shadow");
    expect(activeShadow).not.toBe("");
    expect(activeShadow).toContain("var(--accent-strong)");
    expect(activeShadow).toContain("var(--accent-weak)");

    // No hardcoded hex/rgb brand color should be embedded in the active
    // selector overrides — the accent must follow the token system.
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
