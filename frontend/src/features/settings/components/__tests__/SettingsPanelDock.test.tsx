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
      position: "sticky",
      top: SETTINGS_DENSITY.edgeChrome,
      paddingInline: SETTINGS_DENSITY.edgeChrome,
    });
    expect(dock).toHaveAttribute("aria-orientation", "horizontal");
    expect(screen.getByRole("tab", { name: "Appearance" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Imprint" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Personal Facts" })).toBeInTheDocument();
  });
});
