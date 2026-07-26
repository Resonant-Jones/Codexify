import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import SettingsPanelShell from "@/features/settings/components/SettingsPanelShell";
import { SETTINGS_DENSITY } from "@/features/settings/settingsDensityContract";

describe("SettingsPanelShell", () => {
  test("renders as a layout-only wrapper with no visual perimeter", () => {
    render(
      <SettingsPanelShell>
        <div data-testid="shell-content">Content</div>
      </SettingsPanelShell>
    );

    const shell = screen.getByTestId("settings-panel-shell");

    // Retains structural layout classes
    expect(shell).toHaveClass(
      "flex",
      "h-full",
      "min-h-0",
      "w-full",
      "min-w-0",
      "overflow-hidden"
    );

    // Retains edge-chrome padding
    expect(shell).toHaveStyle({
      padding: SETTINGS_DENSITY.edgeChrome,
    });

    // No visible border, background, or shadow
    expect(shell.style.borderStyle).toBe("none");
    expect(shell.style.background).toBe("transparent");
    expect(shell.style.boxShadow).toBe("none");

    // No border radius
    expect(shell.style.borderRadius).toBe("");

    // Renders children
    expect(shell).toHaveTextContent("Content");
    expect(screen.getByTestId("shell-content")).toBeInTheDocument();
  });

  test("merges a caller-provided className", () => {
    render(
      <SettingsPanelShell className="extra-custom">
        <span>child</span>
      </SettingsPanelShell>
    );

    const shell = screen.getByTestId("settings-panel-shell");
    expect(shell).toHaveClass("extra-custom");
    expect(shell).toHaveClass("flex", "h-full", "overflow-hidden");
  });
});
