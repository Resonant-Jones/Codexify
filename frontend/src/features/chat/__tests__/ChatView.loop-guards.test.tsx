import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ChatView from "@/features/chat/ChatView";
import { CHAT_LANE_MAX_WIDTH } from "@/features/chat/chatLane";
import type { ChatMessage, CompletionState } from "@/features/chat/useChat";

vi.mock("@/features/chat/hooks/useChatAutoScroll", async () => {
  const React = await vi.importActual<typeof import("react")>("react");
  return {
    useChatAutoScroll: () => ({
      containerRef: React.useRef<HTMLDivElement | null>(null),
      endRef: React.useRef<HTMLDivElement | null>(null),
    }),
  };
});

vi.mock("@/components/ui/ContextMenu", () => ({
  default: () => null,
}));

vi.mock("@/features/chat/components/InferenceStatusBanner", () => ({
  default: () => <div data-testid="inference-banner">Thinking…</div>,
}));

vi.mock("@/features/chat/components/ChatBubble", () => ({
  default: ({
    message,
    showPlay,
    onPlay,
    playState,
  }: {
    message: { id: string; content: string };
    showPlay?: boolean;
    onPlay?: () => void;
    playState?: "idle" | "playing" | "pending" | "unavailable" | "disabled";
  }) => {
    const label =
      playState === "pending"
        ? "Generating audio"
        : playState === "unavailable"
          ? "Audio unavailable"
          : playState === "playing"
            ? "Playing..."
            : "Read Aloud";
    const disabled = playState === "pending" || playState === "unavailable";
    return (
      <div data-testid={`bubble-${message.id}`}>
        <div>{message.content}</div>
        {showPlay ? (
          <button
            type="button"
            disabled={disabled}
            onClick={onPlay}
            aria-label={label}
          >
            {label}
          </button>
        ) : null}
      </div>
    );
  },
}));

const baseCompletion: CompletionState = {
  isCompleting: false,
  activeTaskId: null,
  activeThreadId: null,
  startedAt: null,
};

function buildMessage(
  id: number,
  role: "user" | "assistant",
  overrides: Partial<ChatMessage> = {}
): ChatMessage {
  return {
    id,
    thread_id: 7,
    role,
    content: `${role}-${id}`,
    created_at: `2026-03-13T00:00:${String(id).padStart(2, "0")}.000Z`,
    ...overrides,
  };
}

describe("ChatView loop guards", () => {
  const audioPlayMock = vi.fn().mockResolvedValue(undefined);
  const audioPauseMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    function MockAudio(this: any) {
      this.play = audioPlayMock;
      this.pause = audioPauseMock;
      this.onended = null;
      this.onerror = null;
    }
    Object.defineProperty(globalThis, "Audio", {
      configurable: true,
      writable: true,
      value: MockAudio,
    });
  });

  it("renders audio state controls from props without owning fetch loops", () => {
    render(
      <ChatView
        threadId={7}
        guardianName="Guardian"
        messages={[
          buildMessage(1, "assistant", { audio_status: "pending" }),
          buildMessage(2, "assistant", {
            audio_status: "failed",
            audio_error: "boom",
          }),
          buildMessage(3, "assistant", {
            audio_status: "ready",
            audio_url: "/audio/3.wav",
          }),
        ]}
        loading={false}
        error={null}
        hasMore={false}
        completionState={baseCompletion}
        endCompletion={vi.fn()}
        voiceReadAloudEnabled
      />
    );

    expect(screen.getByRole("button", { name: "Generating audio" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Audio unavailable" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Read Aloud" })).toBeEnabled();
  });

  it("loads older messages through the provided callback when scrolled to the top", async () => {
    const onLoadOlderMessages = vi.fn().mockResolvedValue(undefined);

    render(
      <ChatView
        threadId={7}
        guardianName="Guardian"
        messages={[buildMessage(1, "user"), buildMessage(2, "assistant")]}
        loading={false}
        error={null}
        hasMore
        onLoadOlderMessages={onLoadOlderMessages}
        completionState={baseCompletion}
        endCompletion={vi.fn()}
      />
    );

    const container = screen.getByTestId("chat-container");
    Object.defineProperty(container, "scrollTop", {
      configurable: true,
      writable: true,
      value: 0,
    });
    Object.defineProperty(container, "scrollHeight", {
      configurable: true,
      writable: true,
      value: 400,
    });

    fireEvent.scroll(container);

    await waitFor(() => {
      expect(onLoadOlderMessages).toHaveBeenCalledTimes(1);
    });
  });

  it("shows the shared inference banner for an active completion on the current thread", () => {
    render(
      <ChatView
        threadId={7}
        guardianName="Guardian"
        messages={[buildMessage(1, "user")]}
        loading={false}
        error={null}
        hasMore={false}
        completionState={{
          isCompleting: true,
          activeTaskId: "task-7",
          activeThreadId: 7,
          startedAt: Date.now(),
        }}
        endCompletion={vi.fn()}
      />
    );

    expect(screen.getByTestId("chat-completing-indicator")).toBeInTheDocument();
    expect(screen.getByTestId("inference-banner")).toBeInTheDocument();
  });

  it("centers the message lane at the shared max width", () => {
    render(
      <ChatView
        threadId={7}
        guardianName="Guardian"
        messages={[buildMessage(1, "user"), buildMessage(2, "assistant")]}
        loading={false}
        error={null}
        hasMore={false}
        completionState={baseCompletion}
        endCompletion={vi.fn()}
      />
    );

    const lane = screen.getByTestId("chat-conversation-lane");
    expect(lane).toHaveStyle({ maxWidth: `${CHAT_LANE_MAX_WIDTH}px` });
    expect(lane.className).toContain("md:max-w-[880px]");
  });
});
