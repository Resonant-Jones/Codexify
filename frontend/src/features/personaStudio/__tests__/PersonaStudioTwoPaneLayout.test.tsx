import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import PersonaStudioPage from "../PersonaStudioPage";
import { personaStudioApiMock, resetPersonaStudioApiMock } from "./personaStudioApiMock";

vi.mock("@/features/personaStudio/personaStudioApi", async () =>
  (await import("./personaStudioApiMock")).personaStudioApiMock
);

beforeEach(() => {
  window.localStorage.clear();
  resetPersonaStudioApiMock();
});

describe("Persona Studio V2 responsive two-pane layout", () => {
  it("uses the approved unequal desktop columns and a one-column narrow fallback", async () => {
    await act(async () => {
      render(<PersonaStudioPage />);
    });

    const workspace = screen.getByTestId("persona-studio-workspace");
    const assistant = screen.getByTestId("persona-studio-assistant-frame");
    const configuration = screen.getByTestId("persona-studio-configuration-frame");
    expect(Array.from(workspace.children)).toEqual([assistant, configuration]);

    // Assert emitted CSS, not a Tailwind class whose responsive rule may be absent.
    // JSDOM cannot lay out container queries; real-browser bounding boxes are also required.
    const css = screen.getByTestId("persona-studio-layout-styles").textContent!;
    const [narrow, desktop] = css.split("@container persona-studio (min-width: 900px)");
    expect(narrow).toMatch(/grid-template-columns:\s*minmax\(0, 1fr\)/);
    expect(narrow).toMatch(/grid-auto-rows:\s*minmax\(34rem, auto\)/);
    expect(desktop).toMatch(/grid-template-columns:\s*minmax\(0, 0\.75fr\) minmax\(0, 1\.35fr\)/);
    expect(desktop).toMatch(/grid-template-rows:\s*minmax\(0, 1fr\)/);
    expect(desktop).toMatch(/> \.fc-root\s*\{\s*grid-row:\s*1;/);
    expect(desktop).toMatch(/height:\s*100%;\s*min-height:\s*0;/);
    expect(narrow).toContain("container: persona-studio / inline-size");
    expect(narrow).toContain("box-sizing: border-box");
    expect(narrow).toMatch(/\.fc-inner > div,[\s\S]*?min-height:\s*0;/);
    expect(narrow).toMatch(/\[data-testid="persona-studio-configuration-viewport"\],[\s\S]*?min-height:\s*0;\s*overflow-y:\s*auto;/);
    expect(screen.getByTestId("persona-studio-configuration-viewport")).toHaveClass("min-h-0", "flex-1", "overflow-y-auto");
    expect(screen.getByTestId("persona-studio-build-transcript")).toHaveClass("min-h-0", "flex-1", "overflow-y-auto");
  });

  it("keeps compact profile/save controls and all three projections reachable", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    expect(screen.getByTestId("persona-studio-profile-selector-trigger")).toBeVisible();
    expect(screen.getByTestId("persona-studio-action-save")).toHaveTextContent("Save");
    expect(screen.getByTestId("persona-studio-action-reset")).toHaveTextContent("Revert");
    for (const projection of ["manifest", "effective", "form"] as const) {
      await user.click(screen.getByRole("tab", { name: new RegExp(`^${projection}$`, "i") }));
      expect(screen.getByRole("tab", { name: new RegExp(`^${projection}$`, "i") })).toHaveAttribute("aria-selected", "true");
    }
  });
});
