import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CHAT_COMPOSER_SEND_EDGE_INSET_CLASS } from "@/features/chat/chatLane";
import { Composer } from "@/features/chat/components/Composer";

const projectOptions = [
  { value: "1", label: "General" },
  { value: "2", label: "Project Knowledge Base" },
];
const providerOptions = [
  { value: "local", label: "Local" },
  {
    value: "cloud",
    label: "Cloud",
    description: "Cloud providers are disabled.",
    disabled: true,
  },
];
const modelOptions = [
  { value: "qwen3.5:9b", label: "qwen3.5:9b" },
  { value: "qwen3.5:32b", label: "qwen3.5:32b" },
];
const inferenceModeOptions = [
  { value: "default", label: "Auto" },
  { value: "no_think", label: "Fast" },
];
const sourceOptions = [
  { value: "project", label: "Project" },
  { value: "personal_knowledge", label: "Personal Knowledge" },
];

function renderComposer(
  overrides: Partial<React.ComponentProps<typeof Composer>> = {}
) {
  const props: React.ComponentProps<typeof Composer> = {
    onSend: vi.fn(),
    draftValue: "",
    mobileProjectionEnabled: true,
    activeProviderId: "local",
    providerOptions,
    onProviderChange: vi.fn(),
    activeModelId: "qwen3.5:9b",
    modelOptions,
    onModelChange: vi.fn(),
    activeInferenceMode: "default",
    inferenceModeOptions,
    onInferenceModeChange: vi.fn(),
    sourceMode: "project",
    sourceOptions,
    onSourceModeChange: vi.fn(),
    projectId: "1",
    projectName: "General",
    projectOptions,
    onProjectChange: vi.fn(),
    onVoiceTurn: vi.fn(),
    voiceTurnLabel: "Start voice input",
    ...overrides,
  };
  return { ...render(<Composer {...props} />), props };
}

function focusAndType(value: string) {
  act(() => screen.getByTestId("composer-textarea").focus());
  // After focus, projection may activate and move the textarea.
  // Re-query to get the active (projected) textarea.
  const activeTextarea = screen.getByTestId("composer-textarea");
  fireEvent.change(activeTextarea, { target: { value } });
  return activeTextarea;
}

describe("Guardian mobile composer inline commands", () => {
  afterEach(() => cleanup());

  it("renders the compact mobile pill without persistent advanced selectors and without context summary", () => {
    renderComposer();

    const textarea = screen.getByTestId("composer-textarea");
    const compactRow = screen.getByTestId("composer-control-row");
    expect(
      textarea.closest("[data-composer-root]")
    ).toHaveAttribute("data-mobile-compact", "true");
    expect(textarea.parentElement).toBe(compactRow);
    expect(
      screen.getByRole("button", { name: "Open composer actions" })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();

    // Send remains the final control and uses the canonical right-action inset token.
    const sendSlot = screen.getByTestId("composer-send-slot");
    expect(sendSlot).toHaveClass("mr-[var(--composer-text-pad-x,14px)]");
    expect(sendSlot.className).not.toMatch(/\bpr-\[/);
    const sendButton = screen.getByRole("button", { name: "Send" });
    expect(sendButton.className).not.toMatch(/\b-mr-\[/);
    expect(sendButton.className).not.toMatch(/\btranslate[Xx]\b/);

    // Mobile control row does not use the desktop send-edge-inset class.
    expect(compactRow.className).not.toContain(CHAT_COMPOSER_SEND_EDGE_INSET_CLASS);

    expect(screen.queryByRole("button", { name: "Select provider" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Select model" })).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Select inference mode" })
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Select retrieval source" })
    ).toBeNull();
    // Provider/model summary chip is NOT present on mobile
    expect(
      screen.queryByTestId("composer-mobile-context-summary")
    ).toBeNull();
  });

  it("preserves the existing visible selector row on desktop", () => {
    renderComposer({ mobileProjectionEnabled: false });

    expect(
      screen.getByTestId("composer-textarea").closest("[data-composer-root]")
    ).toHaveAttribute("data-mobile-compact", "false");
    expect(
      screen.getByRole("button", { name: "Select provider" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Select model" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Select inference mode" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Select retrieval source" })
    ).toBeInTheDocument();
  });

  it("keeps attachment, voice, and send actions directly reachable", async () => {
    const onVoiceTurn = vi.fn();
    renderComposer({ onVoiceTurn });

    fireEvent.click(
      screen.getByRole("button", { name: "Open composer actions" })
    );
    expect(await screen.findByText("Attach file")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Start voice input"));
    expect(onVoiceTurn).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();
  });

  it("opens canonical command and value suggestions for supported controls", () => {
    renderComposer();
    focusAndType("/");

    expect(
      screen.getByRole("listbox", { name: "Composer commands" })
    ).toBeInTheDocument();
    for (const command of [
      "/project",
      "/provider",
      "/model",
      "/mode",
      "/retrieval",
    ]) {
      expect(
        screen.getByText(command, { selector: "span" }).closest('[role="option"]'),
      ).toBeInTheDocument();
    }
    expect(screen.queryByRole("option", { name: /profile/i })).toBeNull();

    fireEvent.change(screen.getByTestId("composer-textarea"), {
      target: { value: "/project " },
    });
    expect(
      screen.getByRole("listbox", { name: "Project values" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /Project Knowledge Base/ })
    ).toBeInTheDocument();
  });

  it("executes a command through the existing callback without submitting a message", async () => {
    const onProjectChange = vi.fn();
    const onSend = vi.fn();
    renderComposer({ onProjectChange, onSend });
    const textarea = focusAndType("/project Project Knowledge Base");

    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(onProjectChange).toHaveBeenCalledWith("2");
    expect(onSend).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(textarea).toHaveValue("");
      expect(textarea).toHaveFocus();
      expect(screen.getByRole("status")).toHaveTextContent(
        "Project set to Project Knowledge Base"
      );
    });
  });

  it.each([
    ["/provider local", "onProviderChange", "local"],
    ["/model qwen3.5:9b", "onModelChange", "qwen3.5:9b"],
    ["/mode auto", "onInferenceModeChange", "default"],
    ["/retrieval personal knowledge", "onSourceModeChange", "personal_knowledge"],
  ] as const)(
    "maps %s to its canonical callback",
    (draft, callbackName, expectedValue) => {
      const callback = vi.fn();
      const { props } = renderComposer({ [callbackName]: callback });
      const textarea = focusAndType(draft);

      fireEvent.keyDown(textarea, { key: "Enter" });

      expect(callback).toHaveBeenCalledWith(expectedValue);
      expect(props.onSend).not.toHaveBeenCalled();
    }
  );

  it("supports keyboard navigation and Escape without losing the draft", () => {
    renderComposer();
    const textarea = focusAndType("/");

    fireEvent.keyDown(textarea, { key: "ArrowDown" });
    expect(
      screen.getByText("/provider", { selector: "span" }).closest('[role="option"]'),
    ).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(textarea, { key: "Enter" });
    expect(textarea).toHaveValue("/provider ");

    fireEvent.keyDown(textarea, { key: "Escape" });
    expect(screen.queryByTestId("composer-command-palette")).toBeNull();
    expect(textarea).toHaveValue("/provider ");
    expect(textarea).toHaveFocus();
  });

  it.each(["/unknown keep me", "//model local", "Explain /model routing"])(
    "submits ordinary authored text for %s",
    async (draft) => {
      const onSend = vi.fn().mockResolvedValue(undefined);
      renderComposer({ onSend });
      const activeTextarea = focusAndType(draft);

      fireEvent.keyDown(activeTextarea, { key: "Enter" });

      await waitFor(() => expect(onSend).toHaveBeenCalledWith(
        draft,
        expect.any(Object)
      ));
    }
  );

  it("does not execute disabled or ambiguous values", () => {
    const onProviderChange = vi.fn();
    const onModelChange = vi.fn();
    const view = renderComposer({ onProviderChange, onModelChange });
    let textarea = focusAndType("/provider cloud");

    fireEvent.keyDown(textarea, { key: "Enter" });
    expect(onProviderChange).not.toHaveBeenCalled();
    expect(textarea).toHaveValue("/provider cloud");
    expect(screen.getByRole("option", { name: /Cloud providers are disabled/ }))
      .toHaveAttribute("aria-disabled", "true");

    view.rerender(
      <Composer
        {...view.props}
        onModelChange={onModelChange}
        draftValue=""
      />
    );
    textarea = focusAndType("/model qwen");
    fireEvent.keyDown(textarea, { key: "Enter" });
    expect(onModelChange).not.toHaveBeenCalled();
    expect(textarea).toHaveValue("/model qwen");
  });

  it("keeps projection active during commands and closes the palette when suspended", async () => {
    const onProjectionChange = vi.fn();
    const view = renderComposer({ onMobileProjectionChange: onProjectionChange });
    const textarea = focusAndType("/");

    await waitFor(() =>
      expect(onProjectionChange).toHaveBeenLastCalledWith(true)
    );
    expect(screen.getByTestId("composer-command-palette")).toBeInTheDocument();

    view.rerender(
      <Composer
        {...view.props}
        projectionSuspended
      />
    );

    await waitFor(() => {
      expect(screen.queryByTestId("composer-command-palette")).toBeNull();
      expect(textarea).not.toHaveFocus();
      expect(textarea).toHaveValue("/");
      expect(onProjectionChange).toHaveBeenLastCalledWith(false);
    });
  });
});
