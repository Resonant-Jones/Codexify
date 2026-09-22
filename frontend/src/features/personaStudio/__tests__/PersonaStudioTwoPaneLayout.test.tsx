import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
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
  it("uses the approved unequal desktop columns and a one-column narrow fallback", () => {
    render(<PersonaStudioPage />);

    const workspace = screen.getByTestId("persona-studio-workspace");
    expect(workspace).toHaveClass("grid", "grid-cols-1", "xl:grid-cols-[minmax(330px,0.76fr)_minmax(570px,1.38fr)]");
    expect(workspace).toHaveClass("gap-[var(--shell-gap)]");
    expect(screen.getByTestId("persona-studio-assistant-frame").compareDocumentPosition(screen.getByTestId("persona-studio-configuration-frame")) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
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
