import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Composer } from "@/features/chat/components/Composer";
import { CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS } from "@/features/chat/chatLane";
import api from "@/lib/api";
import composerSource from "@/features/chat/components/Composer.tsx?raw";

vi.mock("@/lib/api", () => ({
  default: {
    post: vi.fn(),
  },
}));

describe("Composer draft sync", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    window.localStorage.clear();
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

  it("assigns right-edge ownership to the control row and keeps the send button circular", () => {
    render(<Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />);

    const controlsRow = screen.getByTestId("composer-control-row");
    expect(controlsRow).toHaveClass("pr-[24px]");

    const sendSlot = screen.getByTestId("composer-send-slot");
    expect(sendSlot).toHaveClass("shrink-0");
    expect(sendSlot.className).not.toMatch(/\bpr-/);

    const sendButton = screen.getByRole("button", { name: "Send" });
    expect(sendButton.parentElement).toBe(sendSlot);
    expect(sendButton).toHaveClass(
      "h-8",
      "w-8",
      "min-w-0",
      "rounded-full",
      "p-0"
    );
    expect(sendButton.className).not.toMatch(/\brounded-md\b/);

    const textarea = screen.getByPlaceholderText("Write a message…");
    expect(textarea.parentElement).toHaveAttribute("data-composer-root");
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
    expect(onSend.mock.calls[0][1]).toEqual({ threadIdOverride: 123 });
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

  it("keeps the draft workspace interactive during an in-flight turn but blocks send", () => {
    const onSend = vi.fn();
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    const { container } = render(
      <Composer
        onSend={onSend}
        draftScopeKey="tab-1"
        draftValue=""
        isTurnInFlight
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
    fireEvent.change(textarea, { target: { value: "next thought" } });
    expect(textarea.value).toBe("next thought");

    expect(
      screen.getByRole("button", { name: "Select provider" })
    ).not.toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Select model" })
    ).not.toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Select inference mode" })
    ).not.toBeDisabled();

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const file = new File(["hello world"], "notes.txt", {
      type: "text/plain",
    });
    fireEvent.change(fileInput, { target: { files: [file] } });
    expect(screen.getByLabelText("Remove attachment")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(onSend).not.toHaveBeenCalled();
    expect(dispatchSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "cfy:toast",
      })
    );
  });

  it("keeps voice-turn submission unavailable while a turn is in flight", () => {
    const onVoiceTurn = vi.fn();

    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="tab-1"
        draftValue=""
        isTurnInFlight
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
    expect(controlsRow.className).toContain("mt-auto");
    expect(controlsRow.className).toContain(
      CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS
    );

    expect(composerSource).not.toContain('pb-[2px]');
  });
});
