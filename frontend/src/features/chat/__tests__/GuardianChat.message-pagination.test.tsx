import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import React from "react";

import ChatView from "@/features/chat/ChatView";
import { CHAT_LANE_MAX_WIDTH } from "@/features/chat/chatLane";
import type { CompletionState } from "@/features/chat/useChat";

const idleCompletion: CompletionState = {
  isCompleting: false,
  activeTaskId: null,
  activeThreadId: null,
  startedAt: null,
};

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: apiMocks,
}));

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

function makeMessage(id: number, role: "user" | "assistant" = "user") {
  return {
    id,
    threadId: 1,
    role,
    content: `Message ${id}`,
    createdAt: `2026-01-01T00:${String(id).padStart(2, "0")}:00.000Z`,
    user: { name: "tester" },
    toolCalls: [],
    toolResults: [],
    attachments: [],
    translated: undefined,
    execution: null,
    metadata: null,
    turnId: null,
    extraMeta: null,
  };
}

function renderChatView(opts: {
  hasMore?: boolean;
  onLoadOlderMessages?: () => Promise<unknown>;
  messages?: any[];
  loading?: boolean;
}) {
  const {
    hasMore = false,
    onLoadOlderMessages,
    messages = [],
    loading = false,
  } = opts;

  return render(
    <ChatView
      threadId={1}
      guardianName="Guardian"
      messages={messages}
      loading={loading}
      error={null}
      hasMore={hasMore}
      onLoadOlderMessages={onLoadOlderMessages}
      completionState={idleCompletion}
      endCompletion={vi.fn()}
      autoReadEnabled={false}
    />
  );
}

describe("ChatView message pagination", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 1024,
    });
  });

  it("shows Load older messages button when hasMore is true", async () => {
    renderChatView({
      hasMore: true,
      onLoadOlderMessages: vi.fn(),
      messages: [makeMessage(1), makeMessage(2)],
    });

    const button = screen.queryByTestId("load-older-messages");
    expect(button).toBeInTheDocument();
    expect(button).not.toBeDisabled();
  });

  it("hides Load older messages button when hasMore is false", () => {
    renderChatView({
      hasMore: false,
      messages: [makeMessage(1)],
    });

    const button = screen.queryByTestId("load-older-messages");
    expect(button).not.toBeInTheDocument();
  });

  it("hides Load older messages button when onLoadOlderMessages is not provided", () => {
    renderChatView({
      hasMore: true,
      onLoadOlderMessages: undefined,
      messages: [makeMessage(1)],
    });

    const button = screen.queryByTestId("load-older-messages");
    expect(button).not.toBeInTheDocument();
  });

  it("calls onLoadOlderMessages when the button is clicked", async () => {
    const onLoadOlderMessages = vi.fn().mockResolvedValue(undefined);
    renderChatView({
      hasMore: true,
      onLoadOlderMessages,
      messages: [makeMessage(1)],
    });

    const button = screen.getByTestId("load-older-messages");
    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(onLoadOlderMessages).toHaveBeenCalledTimes(1);
    });
  });

  it("disables button while loading older messages", async () => {
    let resolveLoad: () => void;
    const onLoadOlderMessages = vi.fn().mockImplementation(
      () => new Promise<void>((resolve) => {
        resolveLoad = resolve;
      })
    );
    renderChatView({
      hasMore: true,
      onLoadOlderMessages,
      messages: [makeMessage(1)],
    });

    const button = screen.getByTestId("load-older-messages");
    fireEvent.click(button);

    await waitFor(() => {
      expect(button).toBeDisabled();
    });

    // Resolve and verify button re-enables
    await act(async () => {
      resolveLoad!();
    });

    await waitFor(() => {
      expect(button).not.toBeDisabled();
    });
  });

  it("shows loading text while fetching older messages", async () => {
    let resolveLoad: () => void;
    const onLoadOlderMessages = vi.fn().mockImplementation(
      () => new Promise<void>((resolve) => {
        resolveLoad = resolve;
      })
    );
    renderChatView({
      hasMore: true,
      onLoadOlderMessages,
      messages: [makeMessage(1)],
    });

    const button = screen.getByTestId("load-older-messages");
    fireEvent.click(button);

    await waitFor(() => {
      expect(button).toHaveTextContent(/Loading older messages/i);
    });

    await act(async () => {
      resolveLoad!();
    });

    await waitFor(() => {
      expect(button).toHaveTextContent(/Load older messages/i);
    });
  });

  it("does not crash when onLoadOlderMessages rejects", async () => {
    const onLoadOlderMessages = vi.fn().mockRejectedValue(new Error("fetch failed"));
    renderChatView({
      hasMore: true,
      onLoadOlderMessages,
      messages: [makeMessage(1)],
    });

    const button = screen.getByTestId("load-older-messages");
    await act(async () => {
      fireEvent.click(button);
    });

    // The error is swallowed in ChatView's try/finally, button should re-enable
    await waitFor(() => {
      expect(button).not.toBeDisabled();
    });
  }, 2000);  // longer timeout to allow unhandled rejection to flush
});
