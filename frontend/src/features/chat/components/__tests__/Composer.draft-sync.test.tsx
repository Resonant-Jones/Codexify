import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Composer } from "@/features/chat/components/Composer";

describe("Composer draft sync", () => {
  afterEach(() => {
    vi.useRealTimers();
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
