import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import SettingsPanelShell from "@/features/settings/components/SettingsPanelShell";

describe("SettingsPanelShell", () => {
  it("centers the settings lane, keeps the dock sticky, and exposes shared spacing", () => {
    render(
      <SettingsPanelShell
        activeTab="appearance"
        onTabChange={vi.fn()}
      >
        <section data-testid="shell-child">Body</section>
      </SettingsPanelShell>
    );

    expect(screen.getByTestId("settings-panel-shell")).toHaveClass(
      "w-full",
      "min-w-0",
      "overflow-x-clip"
    );
    expect(screen.getByTestId("settings-panel-dock")).toHaveClass(
      "sticky",
      "top-0",
      "z-30",
      "lg:grid",
      "lg:overflow-visible"
    );
    expect(screen.getByTestId("shell-child")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Appearance" })).toBeInTheDocument();
  });
});
