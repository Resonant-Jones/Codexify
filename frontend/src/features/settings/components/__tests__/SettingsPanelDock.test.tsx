import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import SettingsPanelDock from "@/features/settings/components/SettingsPanelDock";

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
      </SettingsPanelDock>
    );

    const dock = screen.getByRole("tablist", { name: "Settings tabs" });
    expect(dock).toHaveClass("sticky", "flex", "w-full", "justify-center");
    expect(dock).toHaveStyle({
      position: "sticky",
      top: "calc(var(--card-pad) + var(--board-edge))",
    });
    expect(dock).toHaveAttribute("aria-orientation", "horizontal");
    expect(screen.getByRole("tab", { name: "Appearance" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Imprint" })).toBeInTheDocument();
  });
});
