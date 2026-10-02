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

describe("Persona Studio V2 projection tabs", () => {
  it("switches Build/Test and Form/Manifest/Effective without reintroducing the retired seven-tab editor", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    expect(screen.getByRole("tab", { name: /^build$/i })).toHaveAttribute("aria-selected", "true");
    await user.click(screen.getByRole("tab", { name: /^test$/i }));
    expect(screen.getByTestId("persona-studio-test-mode")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: /^manifest$/i }));
    expect(screen.getByTestId("persona-studio-manifest")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: /^effective$/i }));
    expect(screen.getByTestId("persona-studio-effective")).toBeInTheDocument();
    expect(screen.queryByTestId("persona-studio-tabs")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^truth matrix$/i })).not.toBeInTheDocument();
  });
});
