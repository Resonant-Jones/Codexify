import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChatWithSidebar from "@/components/persona/layout/GuardianChatWithSidebar";
import ChatView from "@/features/chat/ChatView";
import { Composer } from "@/features/chat/components/Composer";
import type {
  ChatMessage,
  CompletionState,
} from "@/features/chat/useChat";

const guardianPropsSpy = vi.hoisted(() => vi.fn());
const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: apiMocks,
}));

vi.mock("@/features/chat/GuardianChat", () => ({
  default: (props: any) => {
    guardianPropsSpy(props);
    return (
      <div data-testid="guardian-content">
        <div
          data-testid="guardian-transcript-stub"
          className="overflow-y-auto"
        >
          Transcript
        </div>
        <form data-testid="guardian-composer-stub">
          <textarea aria-label="Message" />
        </form>
      </div>
    );
  },
}));

vi.mock("@/components/sidebar/SidebarRoot", () => ({
  default: () => <div data-testid="sidebar-root-stub">Threads</div>,
}));

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({ subscribe: () => () => {} }),
}));

vi.mock("@/hooks/useWallpaperUrl", () => ({
  useWallpaperUrl: () => ({ wallpaperUrl: null }),
}));

vi.mock("@/features/chat/hooks/useProviderState", () => ({
  useProviderState: () => ({ data: null, error: null, isLoading: false }),
}));

vi.mock("@/imprint/useImprintZero", () => ({
  default: () => ({
    proposal: null,
    status: null,
    accept: vi.fn(),
    reject: vi.fn(),
  }),
}));

vi.mock("@/imprint/ImprintZeroToast", () => ({ default: () => null }));

vi.mock("@/features/chat/components/PromptCostIndicator", () => ({
  default: () => null,
}));

vi.mock("@/features/workspace/WorkspacePane", () => ({
  default: () => null,
}));

vi.mock("@/components/ui/RefractiveGlassCard", () => ({
  default: ({ children }: { children?: ReactNode }) => <>{children ?? null}</>,
}));

vi.mock("@/components/surface/FrameCard", () => ({
  default: ({ children }: { children?: ReactNode }) => <>{children ?? null}</>,
}));

vi.mock("@/lib/authState", () => ({
  useAuthState: () => ({
    ready: true,
    status: "authenticated",
    token: "test-token",
  }),
  checkAuthGate: () => true,
  requireAuthReady: () => true,
}));

vi.mock("@/lib/runtimeConfig", () => ({
  isTauriRuntime: () => false,
  getDesktopRuntimeAuthConfig: () => null,
}));

vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  useRuntimeRouteCapabilities: (labels: string[]) => ({
    ready: true,
    states: Object.fromEntries(labels.map((label) => [label, "available"])),
    mounted: [],
    declared: {},
  }),
}));

vi.mock("@/state/session/SessionStateStore", () => ({
  InMemorySessionStateStore: class {},
  RedisSessionStateStore: class {},
}));

vi.mock("@/state/session/SessionSpine", () => ({
  SessionSpine: class {
    hydrate = vi.fn(async () => null);
    getActiveCompletion = vi.fn(() => null);
    isComposerBlocked = vi.fn(() => false);
    cancelActiveCompletion = vi.fn();
    tabOpen = vi.fn();
    tabSetThread = vi.fn();
    tabActivate = vi.fn();
    tabClose = vi.fn();
    tabSetProvider = vi.fn();
    tabSetModel = vi.fn();
    tabSetInferenceMode = vi.fn();
    tabSetDraft = vi.fn();
  },
}));

vi.mock("@/state/session/hooks", () => ({
  useSessionRailSlice: () => ({
    tabs: [
      {
        tabId: "tab-1",
        threadId: undefined,
        title: "New Thread",
        pendingThread: true,
      },
    ],
    activeTabId: "tab-1",
  }),
  useSessionActiveTab: () => ({
    tabId: "tab-1",
    threadId: undefined,
    title: "New Thread",
    pendingThread: true,
  }),
  useSessionActiveDraft: () => "",
  useSessionActiveProviderId: () => "local",
  useSessionActiveModelId: () => "default",
  useSessionActiveInferenceMode: () => "default",
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

vi.mock("@/components/persona/layout/mobileShellProfile", async () => {
  const actual = await vi.importActual<
    typeof import("@/components/persona/layout/mobileShellProfile")
  >("@/components/persona/layout/mobileShellProfile");
  return {
    ...actual,
    useMobileShellProfile: () => ({
      ...actual.getMobileShellProfile({ viewportClass: "phone" }),
      active: true,
    }),
  };
});

vi.mock("@/hooks/useViewportInsets", () => ({
  useViewportInsets: () => ({
    layoutViewportHeight: 844,
    visualViewportHeight: 520,
    visualViewportOffsetTop: 0,
    keyboardInset: 324,
    isKeyboardOpen: true,
  }),
}));

vi.mock("@/components/ui/ContextMenu", () => ({
  default: () => null,
}));

vi.mock("@/features/chat/components/InferenceStatusBanner", () => ({
  default: () => null,
}));

vi.mock("@/features/chat/components/ChatBubble", () => ({
  default: ({ message }: { message: ChatMessage }) => (
    <div data-testid={`message-${message.id}`}>{message.content}</div>
  ),
}));

const completionState: CompletionState = {
  isCompleting: false,
  activeTaskId: null,
  activeThreadId: null,
  startedAt: null,
};

const messages: ChatMessage[] = [
  {
    id: 1,
    thread_id: 7,
    role: "user",
    content: "Recorded turn",
    created_at: "2026-07-28T00:00:00.000Z",
  },
];

function renderChatView(composerProjected: boolean) {
  return render(
    <ChatView
      threadId={7}
      messages={messages}
      loading={false}
      error={null}
      hasMore={false}
      completionState={completionState}
      endCompletion={vi.fn()}
      bottomPadding={180}
      composerProjected={composerProjected}
    />
  );
}

function setScrollGeometry(
  element: HTMLElement,
  geometry: { clientHeight: number; scrollHeight: number; scrollTop: number }
) {
  Object.defineProperties(element, {
    clientHeight: {
      configurable: true,
      value: geometry.clientHeight,
    },
    scrollHeight: {
      configurable: true,
      value: geometry.scrollHeight,
    },
    scrollTop: {
      configurable: true,
      writable: true,
      value: geometry.scrollTop,
    },
  });
}

describe("Guardian mobile composer projection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 430,
    });
    apiMocks.get.mockResolvedValue({
      data: { ok: true, threads: [], has_more: false },
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("keeps the frame, compact header, transcript, and composer under one narrow Guardian owner", () => {
    render(
      <GuardianChatWithSidebar
        guardianName="Guardian"
        userName="User"
        frameFirstMobile
      />
    );

    const frame = screen.getByTestId("guardian-primary-frame");
    expect(frame).toHaveAttribute("data-frame-owner", "mobile-guardian");
    expect(frame.parentElement).toHaveAttribute(
      "data-guardian-frame-shell",
      "frame-first"
    );
    expect(
      frame.querySelector('[data-testid="guardian-mobile-compact-header"]')
    ).toBeInTheDocument();
    expect(
      frame.querySelector('[data-testid="guardian-transcript-stub"]')
    ).toHaveClass("overflow-y-auto");
    expect(
      frame.querySelector('[data-testid="guardian-composer-stub"]')
    ).toBeInTheDocument();
    expect(guardianPropsSpy.mock.calls.at(-1)?.[0]).toMatchObject({
      compactMobileHeader: true,
      mobileComposerProjectionEnabled: true,
      mobileComposerProjectionSuspended: false,
    });
  });

  it("does not enable the mobile projection seam outside frame-first Guardian", () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 1440,
    });

    render(
      <GuardianChatWithSidebar
        guardianName="Guardian"
        userName="User"
        frameFirstMobile={false}
      />
    );

    expect(guardianPropsSpy.mock.calls.at(-1)?.[0]).toMatchObject({
      compactMobileHeader: false,
      mobileComposerProjectionEnabled: false,
      mobileComposerProjectionSuspended: false,
    });
  });

  it("activates projection on narrow focus and exits it on blur", async () => {
    const onProjectionChange = vi.fn();

    render(
      <Composer
        onSend={vi.fn()}
        draftValue=""
        mobileProjectionEnabled
        onMobileProjectionChange={onProjectionChange}
      />
    );

    const textarea = screen.getByTestId("composer-textarea");
    act(() => textarea.focus());

    await waitFor(() => {
      expect(screen.getByTestId("composer-textarea").closest("[data-composer-root]"))
        .toHaveAttribute("data-mobile-projected", "true");
    });
    expect(onProjectionChange).toHaveBeenLastCalledWith(true);

    fireEvent.blur(textarea);

    await waitFor(() => {
      expect(onProjectionChange).toHaveBeenLastCalledWith(false);
    });
  });

  it("does not activate projection in the desktop contract", async () => {
    const onProjectionChange = vi.fn();

    render(
      <Composer
        onSend={vi.fn()}
        draftValue=""
        mobileProjectionEnabled={false}
        onMobileProjectionChange={onProjectionChange}
      />
    );

    act(() => screen.getByTestId("composer-textarea").focus());

    await waitFor(() => {
      expect(onProjectionChange).toHaveBeenLastCalledWith(false);
    });
    expect(
      screen.getByTestId("composer-textarea").closest("[data-composer-root]")
    ).toHaveAttribute("data-mobile-projected", "false");
  });

  it("uses the canonical mobile minimum-size token and retains the control strip", () => {
    render(
      <Composer
        onSend={vi.fn()}
        draftValue=""
        mobileProjectionEnabled
        activeProviderId="local"
        providerOptions={[{ value: "local", label: "Local" }]}
        activeModelId="guardian-model"
        modelOptions={[{ value: "guardian-model", label: "Guardian model" }]}
        inferenceModeOptions={[{ value: "auto", label: "Auto" }]}
        sourceOptions={[{ value: "project", label: "Project" }]}
      />
    );

    expect(screen.getByTestId("composer-textarea")).toHaveStyle({
      fontSize: "var(--guardian-composer-mobile-input-size)",
    });
    expect(screen.getByTestId("composer-controls-strip")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open composer actions" })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();
    expect(screen.getByText("Local")).toBeInTheDocument();
    expect(screen.getByText("Guardian model")).toBeInTheDocument();
    expect(screen.getByText("Auto")).toBeInTheDocument();
    expect(screen.getByText("Project")).toBeInTheDocument();
  });

  it("blurs and exits projection only after successful user-message submission", async () => {
    let resolveSend: (() => void) | null = null;
    const onSend = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveSend = resolve;
        })
    );
    const onProjectionChange = vi.fn();

    render(
      <Composer
        onSend={onSend}
        draftValue=""
        mobileProjectionEnabled
        onMobileProjectionChange={onProjectionChange}
      />
    );

    const textarea = screen.getByTestId("composer-textarea");
    act(() => textarea.focus());
    fireEvent.change(textarea, { target: { value: "Persist this turn" } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    await waitFor(() => expect(onSend).toHaveBeenCalledTimes(1));
    expect(textarea).toHaveFocus();
    expect(textarea).toHaveValue("Persist this turn");

    await act(async () => {
      resolveSend?.();
    });

    await waitFor(() => {
      expect(textarea).not.toHaveFocus();
      expect(textarea).toHaveValue("");
      expect(onProjectionChange).toHaveBeenLastCalledWith(false);
    });
  });

  it("preserves the draft and focus availability when submission fails", async () => {
    const onSend = vi.fn().mockRejectedValue(new Error("transport failed"));
    const onProjectionChange = vi.fn();

    render(
      <Composer
        onSend={onSend}
        draftValue=""
        mobileProjectionEnabled
        onMobileProjectionChange={onProjectionChange}
      />
    );

    const textarea = screen.getByTestId("composer-textarea");
    act(() => textarea.focus());
    fireEvent.change(textarea, { target: { value: "Keep this draft" } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    await waitFor(() => expect(onSend).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(textarea).toHaveValue("Keep this draft"));
    expect(textarea).toHaveFocus();
    expect(onProjectionChange).toHaveBeenLastCalledWith(true);
  });

  it("suspends projection for overlays without discarding the draft", async () => {
    const onProjectionChange = vi.fn();
    const view = render(
      <Composer
        onSend={vi.fn()}
        draftValue=""
        mobileProjectionEnabled
        projectionSuspended={false}
        onMobileProjectionChange={onProjectionChange}
      />
    );

    const textarea = screen.getByTestId("composer-textarea");
    act(() => textarea.focus());
    fireEvent.change(textarea, { target: { value: "Overlay-safe draft" } });

    view.rerender(
      <Composer
        onSend={vi.fn()}
        draftValue=""
        mobileProjectionEnabled
        projectionSuspended
        onMobileProjectionChange={onProjectionChange}
      />
    );

    await waitFor(() => {
      expect(textarea).not.toHaveFocus();
      expect(onProjectionChange).toHaveBeenLastCalledWith(false);
    });
    expect(textarea).toHaveValue("Overlay-safe draft");
  });

  it("keeps near-bottom subject lock within the transcript scroll owner", () => {
    const windowScroll = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const view = renderChatView(false);
    const transcript = screen.getByTestId("chat-container");
    setScrollGeometry(transcript, {
      clientHeight: 400,
      scrollHeight: 1000,
      scrollTop: 550,
    });
    fireEvent.scroll(transcript);

    view.rerender(
      <ChatView
        threadId={7}
        messages={messages}
        loading={false}
        error={null}
        hasMore={false}
        completionState={completionState}
        endCompletion={vi.fn()}
        bottomPadding={180}
        composerProjected
      />
    );

    expect(transcript).toHaveClass("overflow-y-auto");
    return waitFor(() => {
      expect(transcript.scrollTop).toBe(600);
      expect(windowScroll).not.toHaveBeenCalled();
    });
  });

  it("preserves a meaningfully scrolled-up transcript position", () => {
    const view = renderChatView(false);
    const transcript = screen.getByTestId("chat-container");
    setScrollGeometry(transcript, {
      clientHeight: 400,
      scrollHeight: 1000,
      scrollTop: 100,
    });
    fireEvent.scroll(transcript);

    view.rerender(
      <ChatView
        threadId={7}
        messages={messages}
        loading={false}
        error={null}
        hasMore={false}
        completionState={completionState}
        endCompletion={vi.fn()}
        bottomPadding={180}
        composerProjected
      />
    );

    expect(transcript.scrollTop).toBe(100);
  });
});
