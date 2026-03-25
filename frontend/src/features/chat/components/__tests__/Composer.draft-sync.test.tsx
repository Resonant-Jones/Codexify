import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Composer } from "@/features/chat/components/Composer";
import api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  default: {
    post: vi.fn(),
  },
}));

describe("Composer draft sync", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
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

  it("shows a vision capability notice when image attachments are staged", async () => {
    const createObjectURLMock = vi.fn(() => "blob:preview");
    const revokeObjectURLMock = vi.fn();
    if (typeof window.URL.createObjectURL !== "function") {
      Object.defineProperty(window.URL, "createObjectURL", {
        configurable: true,
        value: createObjectURLMock,
      });
    } else {
      vi.spyOn(window.URL, "createObjectURL").mockImplementation(createObjectURLMock);
    }
    if (typeof window.URL.revokeObjectURL !== "function") {
      Object.defineProperty(window.URL, "revokeObjectURL", {
        configurable: true,
        value: revokeObjectURLMock,
      });
    } else {
      vi.spyOn(window.URL, "revokeObjectURL").mockImplementation(revokeObjectURLMock);
    }

    const { container } = render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="tab-1"
        draftValue=""
        activeModelId="vision-chat"
        modelOptions={[
          {
            value: "text-chat",
            label: "Text Chat",
            supportsChat: true,
            supportsVision: false,
            modelKind: "chat",
          },
          {
            value: "vision-chat",
            label: "Vision Chat",
            supportsChat: true,
            supportsVision: true,
            modelKind: "vision_chat",
          },
        ]}
      />
    );

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const file = new File(["image"], "photo.png", {
      type: "image/png",
    });

    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(
      screen.getByText(
        "Image attached. Vision-capable chat models can inspect it; text-only chat models will not see it natively."
      )
    ).toBeInTheDocument();
    expect(createObjectURLMock).toHaveBeenCalledTimes(1);
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
});
