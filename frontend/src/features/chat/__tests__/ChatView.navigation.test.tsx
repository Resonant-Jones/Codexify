import { act, fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChatView from "@/features/chat/ChatView";
import type { ChatMessage, CompletionState } from "@/features/chat/useChat";

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: apiMocks,
}));

vi.mock("@/components/ui/ContextMenu", () => ({
  default: () => null,
}));

vi.mock("@/features/chat/components/InferenceStatusBanner", () => ({
  default: () => <div data-testid="inference-banner">Thinking…</div>,
}));

vi.mock("@/features/chat/components/ChatBubble", () => ({
  default: ({ message }: { message: { id: string; content: string } }) => (
    <div data-testid={`bubble-${message.id}`}>{message.content}</div>
  ),
}));

const idleCompletion: CompletionState = {
  isCompleting: false,
  activeTaskId: null,
  activeThreadId: null,
  startedAt: null,
};

/**
 * jsdom has no ResizeObserver. Real browsers fire an initial callback once an
 * element is observed, and ChatView relies on that callback to re-measure the
 * transcript after its mount effect resets the overflow state.
 */
class ResizeObserverStub {
  constructor(private readonly callback: () => void) {}

  observe(): void {
    this.callback();
  }

  unobserve(): void {}

  disconnect(): void {}
}

/**
 * jsdom performs no layout, so the transcript geometry is provided by
 * prototype overrides. Anchor positions are derived from the message order so
 * the projection stays deterministic.
 */
let scrollTopValue = 0;
let viewportHeight = 500;
let contentHeight = 2000;
let viewportWidth = 1200;
const anchorOffsets = new Map<string, number>();

const originalDescriptors = {
  clientHeight: Object.getOwnPropertyDescriptor(
    HTMLElement.prototype,
    "clientHeight"
  ),
  clientWidth: Object.getOwnPropertyDescriptor(
    HTMLElement.prototype,
    "clientWidth"
  ),
  scrollHeight: Object.getOwnPropertyDescriptor(
    HTMLElement.prototype,
    "scrollHeight"
  ),
  scrollTop: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollTop"),
  getBoundingClientRect: Object.getOwnPropertyDescriptor(
    Element.prototype,
    "getBoundingClientRect"
  ),
  innerWidth: Object.getOwnPropertyDescriptor(window, "innerWidth"),
  scrollIntoView: Object.getOwnPropertyDescriptor(
    Element.prototype,
    "scrollIntoView"
  ),
};

function primeAnchorOffsets(messages: ChatMessage[]): void {
  anchorOffsets.clear();
  let index = 0;
  for (const message of messages) {
    if (message.role === "user") {
      anchorOffsets.set(`conversation-section-${message.id}`, index * 100);
      index += 1;
    }
  }
}

function installLayout(): void {
  Object.defineProperty(HTMLElement.prototype, "clientHeight", {
    configurable: true,
    get: () => viewportHeight,
  });
  Object.defineProperty(HTMLElement.prototype, "clientWidth", {
    configurable: true,
    get: () => viewportWidth,
  });
  Object.defineProperty(HTMLElement.prototype, "scrollHeight", {
    configurable: true,
    get: () => contentHeight,
  });
  Object.defineProperty(HTMLElement.prototype, "scrollTop", {
    configurable: true,
    get: () => scrollTopValue,
    set: (value: number) => {
      scrollTopValue = Number(value);
    },
  });
  Element.prototype.getBoundingClientRect = function getBoundingClientRect() {
    const anchor = this.getAttribute?.("data-conversation-anchor") ?? null;
    const isContainer =
      this.getAttribute?.("data-testid") === "chat-container";
    const contentTop = anchor ? (anchorOffsets.get(anchor) ?? 0) : 0;
    const top = isContainer ? 0 : contentTop - scrollTopValue;
    return {
      top,
      bottom: top + 40,
      left: 0,
      right: viewportWidth,
      width: viewportWidth,
      height: 40,
      x: 0,
      y: top,
      toJSON: () => ({}),
    } as DOMRect;
  };
}

function restoreLayout(): void {
  for (const [key, descriptor] of Object.entries({
    clientHeight: originalDescriptors.clientHeight,
    clientWidth: originalDescriptors.clientWidth,
    scrollHeight: originalDescriptors.scrollHeight,
    scrollTop: originalDescriptors.scrollTop,
  })) {
    if (descriptor) {
      Object.defineProperty(HTMLElement.prototype, key, descriptor);
    } else {
      delete (HTMLElement.prototype as unknown as Record<string, unknown>)[key];
    }
  }
  if (originalDescriptors.getBoundingClientRect) {
    Object.defineProperty(
      Element.prototype,
      "getBoundingClientRect",
      originalDescriptors.getBoundingClientRect
    );
  }
  if (originalDescriptors.scrollIntoView) {
    Object.defineProperty(
      Element.prototype,
      "scrollIntoView",
      originalDescriptors.scrollIntoView
    );
  }
  if (originalDescriptors.innerWidth) {
    Object.defineProperty(window, "innerWidth", originalDescriptors.innerWidth);
  }
}

function buildMessage(
  id: number,
  role: "user" | "assistant",
  content = `${role} ${id}`
): ChatMessage {
  return {
    id,
    thread_id: 7,
    role,
    content,
    created_at: `2026-03-13T00:00:${String(id % 60).padStart(2, "0")}.000Z`,
  };
}

async function flushFrames(): Promise<void> {
  await act(async () => {
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => resolve());
    });
  });
}

/**
 * Move the transcript to a reading position. Browsers emit a scroll event
 * after a programmatic scroll; jsdom does not, so the event is dispatched here
 * to keep ChatView's own scroll handling in step with the geometry.
 */
function scrollToPosition(position: number): void {
  scrollTopValue = position;
  fireEvent.scroll(screen.getByTestId("chat-container"));
}

function clickMark(index: number): void {
  const marks = screen.getAllByTestId("conversation-minimap-mark");
  fireEvent.click(marks[index]);
  scrollToPosition(scrollTopValue);
}

function renderChatView(
  messages: ChatMessage[],
  overrides: {
    threadId?: number;
    hasMore?: boolean;
    onLoadOlderMessages?: () => Promise<void>;
    streamingDraft?: {
      threadId: number | null;
      content: string;
      updatedAt: number;
    } | null;
  } = {}
) {
  const threadId = overrides.threadId ?? 7;
  primeAnchorOffsets(messages);

  return render(
    <ChatView
      threadId={threadId}
      guardianName="Guardian"
      messages={messages}
      loading={false}
      error={null}
      hasMore={overrides.hasMore ?? false}
      onLoadOlderMessages={overrides.onLoadOlderMessages}
      completionState={idleCompletion}
      endCompletion={vi.fn()}
      streamingDraft={overrides.streamingDraft ?? null}
    />
  );
}

const threeTurns = [
  buildMessage(1, "user"),
  buildMessage(2, "assistant"),
  buildMessage(3, "user"),
  buildMessage(4, "assistant"),
  buildMessage(5, "user"),
];

describe("ChatView conversation minimap", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    scrollTopValue = 0;
    viewportHeight = 500;
    contentHeight = 2000;
    viewportWidth = 1200;
    anchorOffsets.clear();
    installLayout();
    Element.prototype.scrollIntoView = vi.fn();
    (globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver =
      ResizeObserverStub;
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 1440,
    });
  });

  afterEach(() => {
    restoreLayout();
  });

  it("shows the rail when the transcript overflows and has several sections", async () => {
    renderChatView(threeTurns.slice(0, 3));

    await flushFrames();

    expect(screen.getByTestId("conversation-minimap")).toBeInTheDocument();
    expect(screen.getAllByTestId("conversation-minimap-mark")).toHaveLength(2);
  });

  it("does not show the rail for a single navigable section", async () => {
    renderChatView([buildMessage(1, "user"), buildMessage(2, "assistant")]);

    await flushFrames();

    expect(
      screen.queryByTestId("conversation-minimap")
    ).not.toBeInTheDocument();
  });

  it("does not show the rail when the transcript does not overflow", async () => {
    contentHeight = 400;
    renderChatView([buildMessage(1, "user"), buildMessage(3, "user")]);

    await flushFrames();

    expect(
      screen.queryByTestId("conversation-minimap")
    ).not.toBeInTheDocument();
  });

  it("does not show the rail on a phone viewport", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 390,
    });
    viewportWidth = 390;

    renderChatView([buildMessage(1, "user"), buildMessage(3, "user")]);

    await flushFrames();

    expect(
      screen.queryByTestId("conversation-minimap")
    ).not.toBeInTheDocument();
    // No hidden focusable replacement control is left behind.
    expect(
      document.querySelectorAll("[data-testid^='conversation-minimap']")
    ).toHaveLength(0);
  });

  it("keeps the scroll position unchanged while previewing a destination", async () => {
    renderChatView(threeTurns);

    await flushFrames();
    scrollToPosition(150);

    fireEvent.mouseEnter(screen.getAllByTestId("conversation-minimap-mark")[1]);
    await flushFrames();

    expect(screen.getByTestId("conversation-minimap-preview")).toBeInTheDocument();
    expect(scrollTopValue).toBe(150);
  });

  it("commits navigation to the correct stable message", async () => {
    renderChatView(threeTurns);

    await flushFrames();
    scrollToPosition(250);

    // The first section anchors at content offset 0.
    clickMark(0);
    await flushFrames();
    expect(scrollTopValue).toBe(0);

    // The third section anchors at content offset 200.
    clickMark(2);
    await flushFrames();
    expect(scrollTopValue).toBe(192);
  });

  it("restores the prior reading position with the back action", async () => {
    renderChatView(threeTurns);

    await flushFrames();
    scrollToPosition(250);

    clickMark(0);
    await flushFrames();
    expect(scrollTopValue).not.toBe(250);

    fireEvent.click(screen.getByTestId("conversation-minimap-back"));
    await flushFrames();

    expect(scrollTopValue).toBe(250);
  });

  it("does not replace the original return point across repeated jumps", async () => {
    renderChatView(threeTurns);

    await flushFrames();
    scrollToPosition(250);

    clickMark(0);
    await flushFrames();
    clickMark(2);
    await flushFrames();

    fireEvent.click(screen.getByTestId("conversation-minimap-back"));
    await flushFrames();

    // The original reading position is restored, not the intermediate jump.
    expect(scrollTopValue).toBe(250);
  });

  it("preserves the return anchor when older messages are prepended", async () => {
    const initial = [
      buildMessage(11, "user"),
      buildMessage(12, "assistant"),
      buildMessage(13, "user"),
      buildMessage(14, "assistant"),
    ];
    const { rerender } = renderChatView(initial);

    await flushFrames();
    scrollToPosition(250);

    clickMark(0);
    await flushFrames();

    // Older history is prepended above the anchored message.
    const prepended = [buildMessage(9, "user"), ...initial];
    primeAnchorOffsets(prepended);
    rerender(
      <ChatView
        threadId={7}
        guardianName="Guardian"
        messages={prepended}
        loading={false}
        error={null}
        hasMore={false}
        completionState={idleCompletion}
        endCompletion={vi.fn()}
      />
    );

    await flushFrames();

    fireEvent.click(screen.getByTestId("conversation-minimap-back"));
    await flushFrames();

    // The anchored message keeps its viewport relationship even though the
    // history above it grew by one turn, so the reader lands back on the same
    // content they were reading.
    expect(scrollTopValue).toBe(350);
  });

  it("tracks the active section from ordinary scrolling", async () => {
    renderChatView(threeTurns);

    await flushFrames();

    const marks = screen.getAllByTestId("conversation-minimap-mark");
    expect(marks[0]).toHaveAttribute("data-active", "true");

    scrollToPosition(150);
    await flushFrames();

    expect(marks[1]).toHaveAttribute("data-active", "true");
    expect(marks[0]).toHaveAttribute("data-active", "false");
  });

  it("does not pull the reader down when a new message arrives", async () => {
    const { rerender } = renderChatView(threeTurns.slice(0, 4));

    await flushFrames();
    scrollToPosition(250);

    clickMark(0);
    await flushFrames();

    const scrollIntoView = Element.prototype.scrollIntoView as ReturnType<
      typeof vi.fn
    >;
    scrollIntoView.mockClear();

    const withNewMessage = [...threeTurns.slice(0, 4), buildMessage(5, "user")];
    primeAnchorOffsets(withNewMessage);
    rerender(
      <ChatView
        threadId={7}
        guardianName="Guardian"
        messages={withNewMessage}
        loading={false}
        error={null}
        hasMore={false}
        completionState={idleCompletion}
        endCompletion={vi.fn()}
      />
    );

    await flushFrames();

    expect(scrollIntoView).not.toHaveBeenCalled();
    expect(scrollTopValue).toBe(0);
  });

  it("does not pull the reader down when a stream updates", async () => {
    const messages = threeTurns.slice(0, 4);
    const { rerender } = renderChatView(messages);

    await flushFrames();
    scrollToPosition(250);

    clickMark(0);
    await flushFrames();

    const scrollIntoView = Element.prototype.scrollIntoView as ReturnType<
      typeof vi.fn
    >;
    scrollIntoView.mockClear();

    rerender(
      <ChatView
        threadId={7}
        guardianName="Guardian"
        messages={messages}
        loading={false}
        error={null}
        hasMore={false}
        completionState={idleCompletion}
        endCompletion={vi.fn()}
        streamingDraft={{
          threadId: 7,
          content: "streaming…",
          updatedAt: 1_800_000_000_000,
        }}
      />
    );

    await flushFrames();

    expect(scrollIntoView).not.toHaveBeenCalled();
    expect(scrollTopValue).toBe(0);
  });

  it("restores latest-follow behavior through the existing Latest action", async () => {
    const initial = threeTurns.slice(0, 4);
    const { rerender } = renderChatView(initial);

    await flushFrames();
    scrollToPosition(250);

    clickMark(0);
    await flushFrames();

    const scrollIntoView = Element.prototype.scrollIntoView as ReturnType<
      typeof vi.fn
    >;
    scrollIntoView.mockClear();

    fireEvent.click(screen.getByTestId("jump-to-latest-button"));
    await flushFrames();

    const withNewMessage = [...initial, buildMessage(5, "user")];
    primeAnchorOffsets(withNewMessage);
    rerender(
      <ChatView
        threadId={7}
        guardianName="Guardian"
        messages={withNewMessage}
        loading={false}
        error={null}
        hasMore={false}
        completionState={idleCompletion}
        endCompletion={vi.fn()}
      />
    );

    await flushFrames();

    expect(scrollIntoView).toHaveBeenCalled();
  });

  it("fails safely when a destination is missing", async () => {
    renderChatView(threeTurns.slice(0, 3));

    await flushFrames();
    scrollToPosition(150);

    const container = screen.getByTestId("chat-container");
    const anchors = container.querySelectorAll("[data-conversation-anchor]");
    anchors[0].removeAttribute("data-conversation-anchor");

    clickMark(0);
    await flushFrames();

    // No unrelated message is navigated to.
    expect(scrollTopValue).toBe(150);
  });

  it("never displays another thread's stale preview after a thread switch", async () => {
    const { rerender } = renderChatView(threeTurns.slice(0, 3));

    await flushFrames();

    fireEvent.mouseEnter(screen.getAllByTestId("conversation-minimap-mark")[0]);
    expect(screen.getByTestId("conversation-minimap-preview")).toBeInTheDocument();

    const otherThread = [
      buildMessage(11, "user"),
      buildMessage(12, "assistant"),
      buildMessage(13, "user"),
    ];
    primeAnchorOffsets(otherThread);
    rerender(
      <ChatView
        threadId={8}
        guardianName="Guardian"
        messages={otherThread}
        loading={false}
        error={null}
        hasMore={false}
        completionState={idleCompletion}
        endCompletion={vi.fn()}
      />
    );

    await flushFrames();

    expect(
      screen.queryByTestId("conversation-minimap-preview")
    ).not.toBeInTheDocument();
  });

  it("adds no API calls and no new persistent state for navigation", async () => {
    renderChatView(threeTurns.slice(0, 3));

    await flushFrames();
    scrollToPosition(150);

    const sessionKeysBefore = Object.keys(window.sessionStorage);
    const localKeysBefore = Object.keys(window.localStorage);

    clickMark(0);
    await flushFrames();

    expect(apiMocks.get).not.toHaveBeenCalled();
    expect(apiMocks.post).not.toHaveBeenCalled();

    expect(Object.keys(window.sessionStorage)).toEqual(sessionKeysBefore);
    expect(Object.keys(window.localStorage)).toEqual(localKeysBefore);
  });

  it("keeps the existing pagination control available", async () => {
    const onLoadOlderMessages = vi.fn().mockResolvedValue(undefined);
    renderChatView([buildMessage(1, "user"), buildMessage(3, "user")], {
      hasMore: true,
      onLoadOlderMessages,
    });

    await flushFrames();

    expect(screen.getByTestId("load-older-messages")).toBeInTheDocument();
    expect(screen.getByTestId("conversation-minimap")).toBeInTheDocument();
  });

  it("keeps the ordinary transcript scroll container as the scroll owner", async () => {
    renderChatView(threeTurns.slice(0, 3));

    await flushFrames();
    scrollToPosition(150);

    const windowScrollTo = vi
      .spyOn(window, "scrollTo")
      .mockImplementation(() => {});

    clickMark(0);
    await flushFrames();

    expect(windowScrollTo).not.toHaveBeenCalled();
    expect(window.scrollY).toBe(0);

    windowScrollTo.mockRestore();
  });
});
