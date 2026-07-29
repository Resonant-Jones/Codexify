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

import { CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS, CHAT_COMPOSER_SEND_EDGE_INSET_CLASS, CHAT_COMPOSER_SEND_SLOT_BALANCE_CLASS } from "@/features/chat/chatLane";
import GuardianChatWithSidebar from "@/components/persona/layout/GuardianChatWithSidebar";
import ChatView from "@/features/chat/ChatView";
import { Composer } from "@/features/chat/components/Composer";
import type {
  ChatMessage,
  CompletionState,
} from "@/features/chat/useChat";

const guardianPropsSpy = vi.hoisted(() => vi.fn());
const projectCacheMock = vi.hoisted(() => ({
  projectList: [{ id: 7, name: "Canonical project" }],
  setProjectList: vi.fn(),
  refreshProjectsFromServer: vi.fn(),
  looseCount: 0,
}));
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

vi.mock("@/components/sidebar/useProjectsCache", () => ({
  useProjectsCache: () => projectCacheMock,
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

  it("projects the canonical project cache options into Guardian", async () => {
    render(
      <GuardianChatWithSidebar
        guardianName="Guardian"
        userName="User"
        frameFirstMobile
      />
    );

    await waitFor(() => {
      expect(guardianPropsSpy.mock.calls.at(-1)?.[0]).toMatchObject({
        projectOptions: [{ id: 7, name: "Canonical project" }],
      });
    });
  });

  it("mounts separate base and projection surfaces on narrow focus and tears down on blur", async () => {
    const onProjectionChange = vi.fn();

    render(
      <Composer
        onSend={vi.fn()}
        draftValue=""
        mobileProjectionEnabled
        onMobileProjectionChange={onProjectionChange}
      />
    );

    // Before focus: only base surface is present
    expect(
      document.querySelector('[data-composer-surface="projection"]')
    ).toBeNull();
    const baseRoot = document.querySelector('[data-composer-surface="base"]');
    expect(baseRoot).toBeInTheDocument();
    expect(baseRoot).not.toHaveAttribute("inert");

    const textarea = screen.getByTestId("composer-textarea");
    act(() => textarea.focus());

    // After focus: both surfaces exist
    await waitFor(() => {
      expect(
        document.querySelector('[data-composer-surface="projection"]')
      ).toBeInTheDocument();
      expect(
        document.querySelector('[data-composer-surface="base"]')
      ).toBeInTheDocument();
    });

    // Base surface becomes inert when projection is active
    expect(baseRoot).toHaveAttribute("inert");
    expect(onProjectionChange).toHaveBeenLastCalledWith(true);

    // Textarea lives in the projection surface
    const projectedTextarea = document.querySelector(
      '[data-composer-surface="projection"] [data-testid="composer-textarea"]'
    );
    expect(projectedTextarea).toBeInTheDocument();

    // Only one interactive textarea
    const allTextareas = document.querySelectorAll(
      '[data-testid="composer-textarea"]'
    );
    expect(allTextareas.length).toBe(1);

    fireEvent.blur(projectedTextarea!);

    await waitFor(() => {
      expect(onProjectionChange).toHaveBeenLastCalledWith(false);
      // Projection surface removed after blur
      expect(
        document.querySelector('[data-composer-surface="projection"]')
      ).toBeNull();
      // Base surface no longer inert
      expect(baseRoot).not.toHaveAttribute("inert");
    });
  });

  it("does not mount a projection surface in the desktop contract", async () => {
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
      document.querySelector('[data-composer-surface="projection"]')
    ).toBeNull();
    expect(
      screen.getByTestId("composer-textarea").closest("[data-composer-root]")
    ).toHaveAttribute("data-mobile-projected", "false");
  });

  it("renders compact mobile composer without provider/model summary chip", () => {
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

    // Base surface renders with data-composer-surface="base"
    const baseRoot = screen
      .getByTestId("composer-textarea")
      .closest("[data-composer-surface]");
    expect(baseRoot).toHaveAttribute("data-composer-surface", "base");

    // Compact mobile properties
    expect(screen.getByTestId("composer-textarea")).toHaveStyle({
      fontSize: "var(--guardian-composer-mobile-input-size)",
    });
    expect(screen.getByTestId("composer-controls-strip")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open composer actions" })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();

    // Send button uses token-backed right inset
    const sendSlot = screen.getByTestId("composer-send-slot");
    expect(sendSlot).toHaveClass("mr-[var(--composer-text-pad-x,14px)]");
    const sendButton = screen.getByRole("button", { name: "Send" });
    expect(sendButton.className).not.toMatch(/\b-mr-\[/);
    expect(sendButton.className).not.toMatch(/\btranslate[Xx]\b/);

    // Mobile control row does not use the desktop send-edge-inset.
    const controlRow = screen.getByTestId("composer-control-row");
    expect(controlRow.className).not.toContain(CHAT_COMPOSER_SEND_EDGE_INSET_CLASS);

    // Provider/model summary chip is NOT present on mobile
    expect(
      screen.queryByTestId("composer-mobile-context-summary")
    ).toBeNull();

    // Desktop selectors are absent on mobile
    expect(screen.queryByRole("button", { name: "Select provider" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Select model" })).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Select inference mode" })
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Select retrieval source" })
    ).toBeNull();
  });

  it("blurs and tears down projection only after successful user-message submission", async () => {
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

    // Focus to activate projection
    act(() => screen.getByTestId("composer-textarea").focus());

    await waitFor(() => {
      expect(
        document.querySelector('[data-composer-surface="projection"]')
      ).toBeInTheDocument();
    });

    const projectedTextarea = screen.getByTestId("composer-textarea");
    fireEvent.change(projectedTextarea, { target: { value: "Persist this turn" } });
    fireEvent.keyDown(projectedTextarea, { key: "Enter" });

    await waitFor(() => expect(onSend).toHaveBeenCalledTimes(1));
    // Textarea is in projection during submission
    expect(
      document.querySelector('[data-composer-surface="projection"]')
    ).toBeInTheDocument();
    expect(projectedTextarea).toHaveFocus();
    expect(projectedTextarea).toHaveValue("Persist this turn");

    await act(async () => {
      resolveSend?.();
    });

    await waitFor(() => {
      // After send completes, projection is removed and textarea returns to base
      expect(
        document.querySelector('[data-composer-surface="projection"]')
      ).toBeNull();
      expect(onProjectionChange).toHaveBeenLastCalledWith(false);
    });

    // Re-query the textarea (now in base surface)
    const baseTextarea = screen.getByTestId("composer-textarea");
    expect(baseTextarea.closest('[data-composer-surface="base"]')).toBeInTheDocument();
    expect(baseTextarea).not.toHaveFocus();
    expect(baseTextarea).toHaveValue("");
  });

  it("preserves the draft, focus, and projection surface when submission fails", async () => {
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

    // Focus to activate projection, then re-query for the projected textarea
    act(() => screen.getByTestId("composer-textarea").focus());

    await waitFor(() => {
      expect(
        document.querySelector('[data-composer-surface="projection"]')
      ).toBeInTheDocument();
    });

    const projectedTextarea = screen.getByTestId("composer-textarea");
    fireEvent.change(projectedTextarea, { target: { value: "Keep this draft" } });
    fireEvent.keyDown(projectedTextarea, { key: "Enter" });

    await waitFor(() => expect(onSend).toHaveBeenCalledTimes(1));
    expect(projectedTextarea).toHaveValue("Keep this draft");
    expect(projectedTextarea).toHaveFocus();
    expect(onProjectionChange).toHaveBeenLastCalledWith(true);
    // Projection surface remains after failed send
    expect(
      document.querySelector('[data-composer-surface="projection"]')
    ).toBeInTheDocument();
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

    // Confirm projection is active
    expect(
      document.querySelector('[data-composer-surface="projection"]')
    ).toBeInTheDocument();

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
      // Projection surface removed after suspension
      expect(
        document.querySelector('[data-composer-surface="projection"]')
      ).toBeNull();
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

  it("keeps base composer shell in normal flow while projection surface is portal'd", async () => {
    const onProjectionChange = vi.fn();

    render(
      <Composer
        onSend={vi.fn()}
        draftValue=""
        mobileProjectionEnabled
        onMobileProjectionChange={onProjectionChange}
      />
    );

    // Before projection: base surface is in normal flow, not inert
    const baseRoot = document.querySelector('[data-composer-surface="base"]');
    expect(baseRoot).toBeInTheDocument();
    expect(baseRoot).not.toHaveAttribute("inert");

    // Focus to activate projection
    const textarea = screen.getByTestId("composer-textarea");
    act(() => textarea.focus());

    await waitFor(() => {
      expect(
        document.querySelector('[data-composer-surface="projection"]')
      ).toBeInTheDocument();
    });

    // Base surface becomes inert but remains in the DOM (flow-owned)
    expect(baseRoot).toHaveAttribute("inert");
    expect(baseRoot).toHaveAttribute("data-mobile-compact", "true");

    // Projection surface is rendered outside base root
    const projectionRoot = document.querySelector(
      '[data-composer-surface="projection"]'
    );
    expect(projectionRoot).toBeInTheDocument();
    expect(projectionRoot?.parentElement).toBe(document.body);

    // Textarea lives in the projection surface
    const projectedTextarea =
      projectionRoot!.querySelector('[data-testid="composer-textarea"]');
    expect(projectedTextarea).toBeInTheDocument();

    // Send button appears in both base (inert) and projection (active)
    const sendButtons = screen.getAllByRole("button", { name: "Send" });
    expect(sendButtons.length).toBeGreaterThanOrEqual(1);

    // Base composer-root does not switch to absolute positioning
    expect(baseRoot?.className).not.toContain("absolute");
    expect(onProjectionChange).toHaveBeenLastCalledWith(true);
  });
});
