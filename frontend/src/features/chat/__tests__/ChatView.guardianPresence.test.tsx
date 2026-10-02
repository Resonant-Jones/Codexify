import { render, screen, within } from "@testing-library/react";
import "@testing-library/jest-dom";
import { describe, expect, it, vi } from "vitest";

import type { ProviderRuntimeState } from "@/contracts/runtimeTokens";
import ChatView from "@/features/chat/ChatView";
import type { ChatMessage, CompletionState } from "@/features/chat/useChat";

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: {
    get: apiMocks.get,
    post: apiMocks.post,
  },
}));

vi.mock("@/components/ui/ContextMenu", () => ({ default: () => null }));

vi.mock("@/features/chat/hooks/useChatAutoScroll", async () => {
  const React = await vi.importActual<typeof import("react")>("react");
  return {
    useChatAutoScroll: () => ({
      containerRef: React.useRef<HTMLDivElement | null>(null),
      endRef: React.useRef<HTMLDivElement | null>(null),
    }),
  };
});

vi.mock("@/features/chat/components/ChatBubble", () => ({
  default: ({ message }: { message: { id: string; authorName: string; content: string } }) => (
    <div data-testid={`chat-bubble-${message.id}`}>
      <span>{message.authorName}</span>
      <span>{message.content}</span>
    </div>
  ),
}));

const idleCompletion: CompletionState = {
  isCompleting: false,
  activeTaskId: null,
  activeThreadId: null,
  startedAt: null,
  requestState: null,
};

function message(id: number, role: "user" | "assistant"): ChatMessage {
  return {
    id,
    thread_id: 7,
    role,
    content: `${role}-${id}`,
    created_at: `2026-09-27T12:00:0${id}.000Z`,
  };
}

function renderChat(overrides: {
  messages?: ChatMessage[];
  completionState?: CompletionState;
  providerRuntimeState?: ProviderRuntimeState;
  streamingDraft?: { threadId: number | null; content: string; updatedAt: number | null } | null;
} = {}) {
  return render(
    <ChatView
      threadId={7}
      guardianName="Aster"
      messages={overrides.messages ?? []}
      loading={false}
      error={null}
      hasMore={false}
      completionState={overrides.completionState ?? idleCompletion}
      providerRuntimeState={overrides.providerRuntimeState}
      endCompletion={vi.fn()}
      streamingDraft={overrides.streamingDraft}
    />
  );
}

describe("ChatView Guardian runtime presence", () => {
  it("renders exactly one neutral presence bubble for each persisted assistant message", () => {
    renderChat({ messages: [message(1, "assistant")] });

    const presences = screen.getAllByTestId("guardian-presence");
    expect(presences).toHaveLength(1);
    expect(presences[0]).toHaveAttribute("data-presence-state", "idle");
  });

  it("does not render Guardian presence for a user-authored message", () => {
    renderChat({ messages: [message(1, "user")] });

    expect(screen.queryByTestId("guardian-presence")).not.toBeInTheDocument();
  });

  it("shows one live presence bubble beside an active completion without a streaming draft", () => {
    renderChat({
      messages: [message(1, "assistant")],
      completionState: {
        isCompleting: true,
        activeTaskId: "task-1",
        activeThreadId: 7,
        startedAt: 100,
        requestState: "awaiting_first_token",
      },
      providerRuntimeState: "ready",
    });

    const presences = screen.getAllByTestId("guardian-presence");
    expect(presences).toHaveLength(2);
    expect(presences[0]).toHaveAttribute("data-presence-state", "idle");
    expect(presences[1]).toHaveAttribute("data-presence-state", "starting");

    const status = screen.getByTestId("chat-completing-indicator");
    expect(within(status).getByTestId("guardian-presence")).toHaveAttribute(
      "data-presence-state",
      "starting"
    );
    expect(within(status).getByText("Thinking…")).toBeInTheDocument();
  });

  it("uses the shared mapper for warming and keeps historical presence neutral", () => {
    renderChat({
      messages: [message(1, "assistant")],
      completionState: {
        isCompleting: true,
        activeTaskId: "task-1",
        activeThreadId: 7,
        startedAt: 100,
        requestState: "awaiting_model",
      },
      providerRuntimeState: "model_warming",
    });

    const presences = screen.getAllByTestId("guardian-presence");
    expect(presences[0]).toHaveAttribute("data-presence-state", "idle");
    expect(presences[1]).toHaveAttribute("data-presence-state", "warming");
    expect(presences[1]).not.toHaveAttribute("data-presence-state", "error");
    expect(screen.getByText("Thinking…")).toBeInTheDocument();
  });

  it("puts the only live bubble beside the streaming draft and does not recolor history", () => {
    renderChat({
      messages: [message(1, "assistant")],
      completionState: {
        isCompleting: true,
        activeTaskId: "task-1",
        activeThreadId: 7,
        startedAt: 100,
        requestState: "streaming",
      },
      providerRuntimeState: "generating",
      streamingDraft: { threadId: 7, content: "partial response", updatedAt: 101 },
    });

    const presences = screen.getAllByTestId("guardian-presence");
    expect(presences).toHaveLength(2);
    expect(presences[0]).toHaveAttribute("data-presence-state", "idle");
    expect(presences[1]).toHaveAttribute("data-presence-state", "generating");

    const draft = screen.getByTestId("chat-streaming-draft");
    expect(within(draft).getByTestId("guardian-presence")).toHaveAttribute(
      "data-presence-state",
      "generating"
    );
    expect(
      within(screen.getByTestId("chat-completing-indicator")).queryByTestId(
        "guardian-presence"
      )
    ).not.toBeInTheDocument();
    expect(screen.getByText("Thinking…")).toBeInTheDocument();
  });
});
