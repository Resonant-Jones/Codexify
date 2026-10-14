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

describe("Lens Editor projection tabs", () => {
  it("switches Build/Test, and reaches Manifest/Effective only through the Advanced disclosure", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    expect(screen.getByRole("tab", { name: /^build$/i })).toHaveAttribute("aria-selected", "true");
    await user.click(screen.getByRole("tab", { name: /^test$/i }));
    expect(screen.getByTestId("persona-studio-test-mode")).toBeInTheDocument();

    // Implementation-oriented projections stay undisclosed until requested.
    expect(screen.getByTestId("persona-studio-advanced-toggle")).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByTestId("persona-studio-advanced-region")).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /^manifest$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /^effective$/i })).not.toBeInTheDocument();

    await user.click(screen.getByTestId("persona-studio-advanced-toggle"));

    await user.click(screen.getByRole("tab", { name: /^manifest$/i }));
    expect(screen.getByTestId("persona-studio-manifest")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: /^effective$/i }));
    expect(screen.getByTestId("persona-studio-effective")).toBeInTheDocument();
    expect(screen.queryByTestId("persona-studio-tabs")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^truth matrix$/i })).not.toBeInTheDocument();
  });

  it("keeps advanced form mechanics reachable behind the same disclosure", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    for (const section of ["model", "capabilities", "retrieval", "bindings"]) {
      expect(screen.queryByTestId(`persona-studio-form-section-${section}`)).not.toBeInTheDocument();
    }

    await user.click(screen.getByTestId("persona-studio-advanced-toggle"));

    for (const section of ["model", "capabilities", "retrieval", "bindings"]) {
      expect(screen.getByTestId(`persona-studio-form-section-${section}`)).toBeInTheDocument();
    }
  });
});
