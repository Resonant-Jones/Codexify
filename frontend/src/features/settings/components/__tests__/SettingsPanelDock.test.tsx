import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import SettingsPanelDock from "@/features/settings/components/SettingsPanelDock";

describe("SettingsPanelDock", () => {
  test("keeps the tab rail sticky and labeled as a control surface", () => {
    render(
      <SettingsPanelDock>
        <button type="button">Appearance</button>
        <button type="button">Imprint</button>
      </SettingsPanelDock>
    );

    const dock = screen.getByRole("tablist", { name: "Settings sections" });
    expect(dock).toHaveStyle({
      position: "sticky",
      top: "calc(var(--card-pad) + var(--board-edge))",
    });
    expect(screen.getByRole("button", { name: "Appearance" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Imprint" })).toBeInTheDocument();
  });
});
