import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

describe("Persona Studio V2 workspace", () => {
  it("renders the two primary surfaces and applies Build changes only to the local draft", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    expect(screen.getByTestId("persona-studio-workspace")).toHaveAttribute("data-layout", "assistant-configuration");
    expect(screen.getByTestId("persona-studio-assistant-frame")).toBeVisible();
    expect(screen.getByTestId("persona-studio-configuration-frame")).toBeVisible();
    expect(screen.queryByTestId("persona-studio-footer")).not.toBeInTheDocument();

    await user.type(
      screen.getByRole("textbox", { name: /describe a supported draft change/i }),
      "Make this more analytical and use Claude with lower temperature"
    );
    await user.click(screen.getByRole("button", { name: /apply locally/i }));

    expect(personaStudioApiMock.updatePersonaProfile).not.toHaveBeenCalled();
    expect(screen.getByTestId("persona-studio-build-transcript")).toHaveTextContent(/updated .*local draft/i);
    expect(screen.getByTestId("persona-studio-form-section-prompt")).toHaveAttribute("data-highlighted", "true");
    expect(screen.getByTestId("persona-studio-form-section-model")).toHaveAttribute("data-highlighted", "true");
    expect(screen.getByDisplayValue("claude-sonnet")).toBeInTheDocument();
    expect(screen.getByDisplayValue("0.2")).toBeInTheDocument();
  });

  it("uses the existing ephemeral preview engine in Test mode without a nested preview heading", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    await user.click(screen.getByRole("tab", { name: /^test$/i }));
    const preview = screen.getByTestId("persona-preview-panel");
    expect(preview).toBeVisible();
    expect(within(preview).queryByTestId("persona-preview-panel-header")).not.toBeInTheDocument();
    expect(within(preview).getByTestId("persona-preview-panel-safety-row")).toHaveTextContent(/not saved to chat history/i);

    await user.type(screen.getByRole("textbox", { name: /persona preview prompt/i }), "Plan this");
    await user.click(screen.getByRole("button", { name: /^send$/i }));
    await waitFor(() => expect(within(preview).getByText(/this is the first preview turn/i)).toBeVisible());
    expect(screen.queryByTestId("composer-shell")).not.toBeInTheDocument();
    expect(screen.queryByTestId("chat-conversation-lane")).not.toBeInTheDocument();
  });

  it("round-trips valid Manifest JSON into Form and preserves the draft when JSON is invalid", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    await user.click(screen.getByRole("tab", { name: /^manifest$/i }));
    const manifestInput = screen.getByRole("textbox", { name: /persona manifest json/i });
    const manifest = JSON.parse((manifestInput as HTMLTextAreaElement).value) as Record<string, unknown>;
    const identity = manifest.identity as Record<string, unknown>;
    identity.name = "Manifest Persona";
    fireEvent.change(manifestInput, { target: { value: JSON.stringify(manifest, null, 2) } });

    await user.click(screen.getByRole("tab", { name: /^form$/i }));
    expect(screen.getByDisplayValue("Manifest Persona")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /^manifest$/i }));
    fireEvent.change(screen.getByRole("textbox", { name: /persona manifest json/i }), {
      target: { value: '{"bindings":{"project":"nope"}}' },
    });
    expect(screen.getByRole("alert")).toHaveTextContent(/manifest not applied/i);
    await user.click(screen.getByRole("tab", { name: /^form$/i }));
    expect(screen.getByDisplayValue("Manifest Persona")).toBeInTheDocument();
  });

  it("labels unresolved environmental truth honestly in Effective", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    await user.click(screen.getByRole("tab", { name: /^effective$/i }));
    expect(screen.getByTestId("persona-studio-effective")).toHaveTextContent(/unavailable to resolve here/i);
    expect(screen.getByTestId("persona-studio-effective")).toHaveTextContent(/not resolved/i);
    expect(screen.getByTestId("persona-studio-effective")).not.toHaveTextContent(/available and authorized/i);
  });
});
