import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Composer, deriveComposerState } from "@/features/chat/components/Composer";
import {
  CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS,
} from "@/features/chat/chatLane";
import {
  buildSlashCommandIntentPayload,
  resolveSlashCommandIntent,
} from "@/contracts/slashCommands";
import api from "@/lib/api";
import composerSource from "@/features/chat/components/Composer.tsx?raw";

vi.mock("@/lib/api", () => ({
  default: {
    post: vi.fn(),
  },
}));

const originalInnerWidth = Object.getOwnPropertyDescriptor(window, "innerWidth");

describe("Composer draft sync", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    window.localStorage.clear();
    if (originalInnerWidth) {
      Object.defineProperty(window, "innerWidth", originalInnerWidth);
    }
  });

  it("opens the slash palette when the composer starts with /", async () => {
    render(<Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />);

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "/" } });

    await waitFor(() => {
      expect(screen.getByRole("menu", { name: "Slash commands" })).toBeInTheDocument();
    });

    expect(
      screen.getByRole("menuitem", { name: /Thread/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("menuitem", { name: /Document/i })
    ).toBeInTheDocument();
  });

  it("refreshes slash results as more characters are typed and fuzzy matches partial input", async () => {
    render(<Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />);

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "/" } });

    await waitFor(() => {
      expect(screen.getByRole("menu", { name: "Slash commands" })).toBeInTheDocument();
    });

    expect(screen.getByRole("menuitem", { name: /Thread/i })).toBeInTheDocument();

    fireEvent.change(textarea, { target: { value: "/prj" } });

    await waitFor(() => {
      expect(screen.getByRole("menuitem", { name: /Project/i })).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("menuitem", { name: /Thread/i })
    ).not.toBeInTheDocument();
  });

  it("resolves alias tokens through the shared slash parser", () => {
    expect(resolveSlashCommandIntent("/repo scope planning")).toEqual(
      expect.objectContaining({
        rawToken: "/repo",
        queryText: "scope planning",
        command: expect.objectContaining({
          id: "project",
          scaffold: "/project",
        }),
      })
    );
  });

  it("surfaces semantic hint metadata for a resolved command", async () => {
    render(<Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />);

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "/repo scope planning" } });

    await waitFor(() => {
      expect(screen.getByRole("menu", { name: "Slash commands" })).toBeInTheDocument();
    });

    expect(screen.getByText(/intent kind:\s*workspace/i)).toBeInTheDocument();
    expect(screen.getByText(/retrieval hint:\s*project/i)).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /Project/i })).toBeInTheDocument();
  });

  describe("buildSlashCommandIntentPayload", () => {
    it("produces the expected canonical slash intent payload for a recognized slash command", () => {
      const payload = buildSlashCommandIntentPayload("/doc query text");
      expect(payload).toEqual({
        commandId: "doc",
        intentKind: "knowledge",
        retrievalHint: "personal_knowledge",
        rawInput: "/doc query text",
      });
    });

    it("produces correct canonical commandId for alias-based resolution", () => {
      const payload = buildSlashCommandIntentPayload("/repo scope planning");
      expect(payload).toEqual(
        expect.objectContaining({
          commandId: "project",
          intentKind: "workspace",
          retrievalHint: "project",
          rawInput: "/repo scope planning",
        })
      );
    });

    it("produces null for non-slash input", () => {
      const payload = buildSlashCommandIntentPayload("hello world");
      expect(payload).toBeNull();
    });

    it("produces null for empty input", () => {
      expect(buildSlashCommandIntentPayload("")).toBeNull();
      expect(buildSlashCommandIntentPayload("/")).toBeNull();
    });
  });

  describe("deriveComposerState", () => {
    it("maps runtime request states into the token-compliant composer interaction states", () => {
      expect(deriveComposerState("dispatching", "offline", "draft")).toBe("submitting");
      expect(deriveComposerState("awaiting_ack", "online", "draft")).toBe("submitting");
      expect(deriveComposerState("awaiting_model", "degraded", "draft")).toBe("awaiting_model");
      expect(deriveComposerState("streaming", "online", "draft")).toBe("streaming");
      expect(deriveComposerState(undefined, "online", "   ")).toBe("idle");
      expect(deriveComposerState(undefined, "online", "hello")).toBe("typing");
    });
  });

  it("closes the slash palette when the slash token is removed", async () => {
    render(<Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />);

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "/doc" } });

    await waitFor(() => {
      expect(screen.getByRole("menu", { name: "Slash commands" })).toBeInTheDocument();
    });

    fireEvent.change(textarea, { target: { value: "hello world" } });

    await waitFor(() => {
      expect(screen.queryByRole("menu", { name: "Slash commands" })).not.toBeInTheDocument();
    });
  });

  it("moves through the palette with arrow keys and inserts the selected scaffold on Enter", async () => {
    render(<Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />);

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "/" } });

    await waitFor(() => {
      expect(screen.getByRole("menu", { name: "Slash commands" })).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(
        screen.getByRole("menuitem", { name: /Thread/i })
      ).toHaveAttribute("aria-current", "true");
    });

    fireEvent.keyDown(textarea, { key: "ArrowDown" });
    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(textarea).toHaveValue("/doc");
    expect(screen.queryByRole("menu", { name: "Slash commands" })).not.toBeInTheDocument();
  });

  it("keeps typing local and commits draft only after debounce", async () => {
    vi.useFakeTimers();
    const onDraftValueChange = vi.fn();

    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="tab-1"
        draftValue=""
        onDraftValueChange={onDraftValueChange}
      />
    );

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "h" } });
    fireEvent.change(textarea, { target: { value: "he" } });
    fireEvent.change(textarea, { target: { value: "hel" } });

    expect(onDraftValueChange).not.toHaveBeenCalled();
    vi.advanceTimersByTime(349);
    expect(onDraftValueChange).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onDraftValueChange).toHaveBeenCalledTimes(1);
    expect(onDraftValueChange).toHaveBeenLastCalledWith("hel");
  });

  it("focuses the textarea when prefill is applied", async () => {
    vi.useFakeTimers();

    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="tab-1"
        draftValue=""
        prefill="seed focus"
      />
    );

    const textarea = screen.getByPlaceholderText("Write a message…");
    expect(textarea).not.toHaveFocus();

    vi.runOnlyPendingTimers();

    await waitFor(() => {
      expect(textarea).toHaveFocus();
    });
  });

  it("flushes draft immediately on blur", () => {
    vi.useFakeTimers();
    const onDraftValueChange = vi.fn();

    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="tab-1"
        draftValue=""
        onDraftValueChange={onDraftValueChange}
      />
    );

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "draft text" } });
    vi.advanceTimersByTime(100);
    expect(onDraftValueChange).not.toHaveBeenCalled();

    fireEvent.blur(textarea);
    expect(onDraftValueChange).toHaveBeenCalledTimes(1);
    expect(onDraftValueChange).toHaveBeenLastCalledWith("draft text");

    vi.advanceTimersByTime(1000);
    expect(onDraftValueChange).toHaveBeenCalledTimes(1);
  });

  it("flushes draft on send boundaries", async () => {
    vi.useFakeTimers();
    const onDraftValueChange = vi.fn();
    const onSend = vi.fn().mockResolvedValue(undefined);

    render(
      <Composer
        onSend={onSend}
        draftScopeKey="tab-1"
        draftValue=""
        onDraftValueChange={onDraftValueChange}
      />
    );

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "hello world" } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    await waitFor(() => {
      expect(onSend).toHaveBeenCalledTimes(1);
    });
    expect(onDraftValueChange).toHaveBeenNthCalledWith(1, "hello world");
    expect(onDraftValueChange).toHaveBeenLastCalledWith("");
  });

  it("attaches slash intent metadata to onSend when composer contains a recognized slash command", async () => {
    const onSend = vi.fn().mockResolvedValue(undefined);

    render(
      <Composer
        onSend={onSend}
        draftScopeKey="tab-1"
        draftValue=""
      />
    );

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "/doc query text" } });

    await waitFor(() => {
      expect(screen.getByRole("menu", { name: "Slash commands" })).toBeInTheDocument();
    });

    fireEvent.keyDown(textarea, { key: "Enter" });

    await waitFor(() => {
      expect(textarea).toHaveValue("/doc");
    });

    expect(onSend).not.toHaveBeenCalled();
  });

  it("attaches slash intent metadata to onSend when sending a slash command after palette is dismissed", async () => {
    const onSend = vi.fn().mockResolvedValue(undefined);

    render(
      <Composer
        onSend={onSend}
        draftScopeKey="tab-1"
        draftValue=""
      />
    );

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "/doc query text" } });

    await waitFor(() => {
      expect(screen.getByRole("menu", { name: "Slash commands" })).toBeInTheDocument();
    });

    fireEvent.change(textarea, { target: { value: "hello" } });

    await waitFor(() => {
      expect(screen.queryByRole("menu", { name: "Slash commands" })).not.toBeInTheDocument();
    });

    fireEvent.keyDown(textarea, { key: "Enter" });

    await waitFor(() => {
      expect(onSend).toHaveBeenCalledTimes(1);
    });
    expect(onSend).toHaveBeenCalledWith(
      "hello",
      expect.objectContaining({
        threadIdOverride: undefined,
      })
    );
    expect(onSend.mock.calls[0][1]?.slashIntent).toBeUndefined();
  });

  it("does not attach slash intent when composer contains no recognized slash command", async () => {
    const onSend = vi.fn().mockResolvedValue(undefined);

    render(
      <Composer
        onSend={onSend}
        draftScopeKey="tab-1"
        draftValue=""
      />
    );

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "hello world" } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    await waitFor(() => {
      expect(onSend).toHaveBeenCalledTimes(1);
    });
    expect(onSend).toHaveBeenCalledWith(
      "hello world",
      expect.objectContaining({
        threadIdOverride: undefined,
      })
    );
    expect(onSend.mock.calls[0][1]?.slashIntent).toBeUndefined();
  });

  it("enables send when the draft only contains document tiles", async () => {
    const onSend = vi.fn().mockResolvedValue(undefined);

    render(
      <Composer
        onSend={onSend}
        draftScopeKey="tab-1"
        draftValue=""
        onDocumentTileRemove={vi.fn()}
        documentTiles={[
          {
            id: "doc-1",
            title: "Project Brief",
            preview: "Short excerpt",
            type: "document",
          },
        ]}
      />
    );

    expect(
      screen.getByRole("button", { name: "Remove Project Brief" })
    ).toBeInTheDocument();

    const sendButton = screen.getByRole("button", { name: "Send" });
    expect(sendButton).not.toBeDisabled();

    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(onSend).toHaveBeenCalledTimes(1);
    });
  });

  it("keeps the textarea on the content plane and gives the control row its own padding contract", () => {
    render(<Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="hello" />);

    const contentPlane = screen.getByTestId("composer-content-plane");
    const controlsRow = screen.getByTestId("composer-control-row");
    expect(contentPlane).toHaveClass("justify-end", "gap-2");
    expect(controlsRow).toHaveClass(
      "flex",
      "w-full",
      "items-center",
      "gap-3",
      "px-[var(--composer-text-pad-x,14px)]"
    );
    expect(controlsRow.className).toContain(CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS);
    expect(controlsRow).toHaveClass("px-[var(--composer-text-pad-x,14px)]");
    expect(contentPlane).toHaveClass("px-[var(--composer-pad-x,12px)]");
    expect(controlsRow.parentElement).toBe(contentPlane);
    expect(controlsRow).not.toHaveClass("mt-auto");
    expect(controlsRow).not.toHaveClass("justify-between");
    expect(controlsRow.className).not.toMatch(/\bpl-\[/);
    expect(controlsRow.className).not.toMatch(/\bmr-\[/);
    expect(controlsRow.className).not.toContain("pb-[6px]");

    const controlsStrip = screen.getByTestId("composer-controls-strip");
    expect(controlsStrip).toHaveClass(
      "min-w-0",
      "flex-none",
      "w-fit",
      "overflow-x-auto"
    );
    expect(controlsStrip.className).not.toMatch(/\bpr-/);
    expect(controlsStrip.className).not.toContain("bg-[");

    const sendSlot = screen.getByTestId("composer-send-slot");
    expect(sendSlot).toHaveClass(
      "ml-auto",
      "flex",
      "shrink-0",
      "items-center",
      "justify-center"
    );
    expect(sendSlot.className).not.toMatch(/\bpr-/);
    expect(controlsStrip.nextElementSibling).toBe(sendSlot);

    const sendButton = screen.getByRole("button", { name: "Send" });
    expect(sendButton.parentElement).toBe(sendSlot);
    expect(sendButton).toHaveAccessibleName("Send");

    const textarea = screen.getByTestId("composer-textarea");
    expect(textarea).toHaveClass("w-full", "bg-transparent", "border-none");
    expect(composerSource).not.toContain("CHAT_COMPOSER_SEND_EDGE_INSET_CLASS");
    expect(composerSource).not.toContain("pr-[48px]");
    expect(composerSource).toContain("bg-transparent");
    expect(composerSource).not.toContain("bg-[color-mix(in_oklab,var(--panel-bg)_95%,transparent)]");
    expect(composerSource).toContain("justify-end");
    expect(composerSource).toContain(
      "flex w-full items-center gap-3 px-[var(--composer-text-pad-x,14px)]"
    );
    expect(textarea.parentElement).toBe(contentPlane);
    expect(composerSource).not.toContain("mt-auto");
    expect(composerSource).not.toContain('pl-[8px]');
    expect(composerSource).not.toContain('pr-[24px]');
    expect(composerSource).toContain('from "@/contracts/slashCommands"');
    expect(composerSource).toContain("buildSlashCommandIntentPayload");
    expect(composerSource).toContain("resolveSlashCommandIntent");
    expect(composerSource).toContain("slashIntent");
    expect(composerSource).not.toContain('description: "Start or switch a conversation thread."');
    expect(composerSource).toContain("resolveSlashCommandIntent");
    expect(composerSource).not.toMatch(/\bpr-\[/);
  });

  it("switches the composer to compact phone spacing and safe-area padding on narrow widths", () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 390,
    });

    const { container } = render(
      <Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />
    );

    const composerRoot = container.querySelector("[data-composer-root]") as HTMLElement | null;
    expect(composerRoot).not.toBeNull();
    expect(composerRoot?.style.getPropertyValue("--composer-control-size")).toBe("44px");
    expect(composerRoot?.style.getPropertyValue("--composer-text-pad-x")).toBe("12px");
    expect(composerRoot?.style.getPropertyValue("--composer-text-pad-y")).toBe("8px");
    expect(composerRoot?.style.getPropertyValue("--composer-safe-area-bottom")).toBe(
      "env(safe-area-inset-bottom, 0px)"
    );

    const controlsStrip = screen.getByTestId("composer-controls-strip");
    const sourceButton = screen.getByRole("button", {
      name: "Select retrieval source",
    });

    expect(controlsStrip).toHaveClass("flex-none", "w-fit");
    expect(controlsStrip.className).not.toContain("bg-[");
    expect(controlsStrip.style.borderRadius).toBe("");
    expect(sourceButton).toHaveClass("bg-transparent", "border-0", "rounded-none");
    expect(sourceButton.style.borderRadius).toBe("");
  });

  it("stages attachments locally and uploads them only after send", async () => {
    const onSend = vi.fn().mockResolvedValue(undefined);
    const ensureThreadIdForAttachments = vi.fn().mockResolvedValue(123);
    vi.mocked(api.post).mockResolvedValue({
      data: {
        id: "doc-1",
        src_url: "/media/documents/notes.txt",
        filename: "notes.txt",
      },
    } as any);

    const { container } = render(
      <Composer
        onSend={onSend}
        ensureThreadIdForAttachments={ensureThreadIdForAttachments}
        draftScopeKey="tab-1"
        draftValue=""
      />
    );

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "hello attachments" } });

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const file = new File(["hello world"], "notes.txt", {
      type: "text/plain",
    });

    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(ensureThreadIdForAttachments).not.toHaveBeenCalled();
    expect(api.post).not.toHaveBeenCalled();

    fireEvent.keyDown(textarea, { key: "Enter" });

    await waitFor(() => {
      expect(onSend).toHaveBeenCalledTimes(1);
    });

    expect(ensureThreadIdForAttachments).toHaveBeenCalledWith(
      "hello attachments"
    );
    expect(api.post).toHaveBeenCalledTimes(1);
    expect(api.post).toHaveBeenCalledWith(
      "/api/media/upload/document",
      expect.any(FormData),
      {
        headers: { "Content-Type": "multipart/form-data" },
      }
    );
    expect(onSend.mock.calls[0][0]).toContain("cfy-media:document:doc-1");
    expect(onSend.mock.calls[0][0]).toContain("cfy-media-name:notes.txt");
    expect(onSend.mock.calls[0][0]).toContain("hello attachments");
    expect(onSend.mock.calls[0][1]).toEqual({
      threadIdOverride: 123,
    });
  });

  it("omits invalid project_id values when uploading attachments", async () => {
    window.localStorage.setItem("cfy.projectId", "0");
    const onSend = vi.fn().mockResolvedValue(undefined);
    vi.mocked(api.post).mockResolvedValue({
      data: {
        id: "doc-2",
        src_url: "/media/documents/notes.txt",
        filename: "notes.txt",
      },
    } as any);

    const { container } = render(
      <Composer
        onSend={onSend}
        threadId={123}
        draftScopeKey="tab-1"
        draftValue=""
      />
    );

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "hello attachments" } });

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const file = new File(["hello world"], "notes.txt", {
      type: "text/plain",
    });

    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledTimes(1);
    });

    const form = vi.mocked(api.post).mock.calls[0][1] as FormData;
    expect(form.get("project_id")).toBeNull();
    expect(form.get("thread_id")).toBe("123");
  });

  it("sanitizes raw backend upload errors before showing a toast", async () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    const onSend = vi.fn().mockResolvedValue(undefined);
    vi.mocked(api.post).mockRejectedValue({
      response: {
        data: {
          detail:
            "psycopg.errors.ForeignKeyViolation: insert into media_assets (project_id) values (0)",
        },
      },
    });

    const { container } = render(
      <Composer
        onSend={onSend}
        threadId={123}
        draftScopeKey="tab-1"
        draftValue=""
      />
    );

    const textarea = screen.getByPlaceholderText("Write a message…");
    fireEvent.change(textarea, { target: { value: "hello attachments" } });

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const file = new File(["hello world"], "notes.txt", {
      type: "text/plain",
    });

    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    await waitFor(() => {
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "cfy:toast",
          detail: expect.objectContaining({
            message: "Upload failed. Please try again.",
          }),
        })
      );
    });
  });

  it("flushes previous tab draft and loads next tab initial draft on scope switch", () => {
    vi.useFakeTimers();
    const onDraftValueChange = vi.fn();

    const { rerender } = render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="tab-1"
        draftValue="seed-a"
        onDraftValueChange={onDraftValueChange}
      />
    );

    const textarea = screen.getByPlaceholderText(
      "Write a message…"
    ) as HTMLTextAreaElement;
    expect(textarea.value).toBe("seed-a");

    fireEvent.change(textarea, { target: { value: "edited-a" } });
    vi.advanceTimersByTime(100);
    expect(onDraftValueChange).not.toHaveBeenCalled();

    rerender(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="tab-2"
        draftValue="seed-b"
        onDraftValueChange={onDraftValueChange}
      />
    );

    expect(onDraftValueChange).toHaveBeenCalledWith("edited-a");
    expect(
      (screen.getByPlaceholderText("Write a message…") as HTMLTextAreaElement)
        .value
    ).toBe("seed-b");
  });

  it("locks the composer while dispatching a request", () => {
    const onSend = vi.fn();

    render(
      <Composer
        onSend={onSend}
        draftScopeKey="tab-1"
        draftValue="next thought"
        currentRequestState="dispatching"
        providerRuntimeState="degraded"
        activeProviderId="local"
        providerOptions={[{ value: "local", label: "Local" }]}
        activeModelId="model-a"
        modelOptions={[{ value: "model-a", label: "Model A" }]}
        activeInferenceMode="think"
        inferenceModeOptions={[
          { value: "default", label: "Auto" },
          { value: "think", label: "Think" },
        ]}
      />
    );

    const textarea = screen.getByPlaceholderText(
      "Write a message…"
    ) as HTMLTextAreaElement;
    expect(textarea).toBeDisabled();

    expect(
      screen.getByRole("button", { name: "Sending…" })
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Select provider" })
    ).not.toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Select model" })
    ).not.toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Select inference mode" })
    ).not.toBeDisabled();
  });

  it("shows streaming as a live state without disabling the composer", () => {
    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="tab-1"
        draftValue="follow up"
        currentRequestState="streaming"
        providerRuntimeState="online"
      />
    );

    const textarea = screen.getByPlaceholderText(
      "Write a message…"
    ) as HTMLTextAreaElement;
    expect(textarea).not.toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Streaming…" })
    ).not.toBeDisabled();
  });

  it("shows warming while waiting for the model", () => {
    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="tab-1"
        draftValue="hold"
        currentRequestState="awaiting_model"
      />
    );

    const textarea = screen.getByPlaceholderText(
      "Write a message…"
    ) as HTMLTextAreaElement;
    expect(textarea).toBeDisabled();
    expect(textarea).toHaveClass("opacity-60", "cursor-not-allowed");
    expect(
      screen.getByRole("button", { name: "Warming…" })
    ).toBeDisabled();
  });

  it("keeps voice-turn submission unavailable while dispatching", () => {
    const onVoiceTurn = vi.fn();

    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="tab-1"
        draftValue=""
        currentRequestState="dispatching"
        onVoiceTurn={onVoiceTurn}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Open composer actions" }));

    const voiceTurnButton = screen
      .getByText("Upload voice turn")
      .closest("button") as HTMLButtonElement;
    expect(voiceTurnButton).toBeDisabled();

    fireEvent.click(voiceTurnButton);
    expect(onVoiceTurn).not.toHaveBeenCalled();
  });

  it("pins controls row using the shared bottom-gap contract", () => {
    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="tab-1"
        draftValue=""
      />
    );

    const controlsRow = screen.getByTestId("composer-control-row");
    expect(controlsRow.className).not.toContain("mt-auto");
    expect(controlsRow.className).toContain(
      CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS
    );
    expect(controlsRow.className).not.toContain("pb-[6px]");
  });
});
