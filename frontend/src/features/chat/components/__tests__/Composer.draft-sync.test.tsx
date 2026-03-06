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
});
