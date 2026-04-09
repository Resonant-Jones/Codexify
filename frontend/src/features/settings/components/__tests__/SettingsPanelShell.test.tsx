import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import SettingsPanelShell from "@/features/settings/components/SettingsPanelShell";

describe("SettingsPanelShell", () => {
  test("separates the inner settings shell from its content", () => {
    render(
      <SettingsPanelShell>
        <div data-testid="shell-content">Content</div>
      </SettingsPanelShell>
    );

    const shell = screen.getByTestId("settings-panel-shell");
    expect(shell).toHaveStyle({
      padding: "calc(var(--card-pad) + var(--board-edge))",
    });
    expect(shell).toHaveTextContent("Content");
    expect(screen.getByTestId("shell-content")).toBeInTheDocument();
  });
});
