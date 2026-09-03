import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChatWithSidebar from "../GuardianChatWithSidebar";

const guardianPropsSpy = vi.hoisted(() => vi.fn());
const sidebarPropsSpy = vi.hoisted(() => vi.fn());
const sessionSpineInstances = vi.hoisted(() => [] as any[]);
const apiSpies = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}));

vi.mock("@/features/chat/GuardianChat", () => ({
  default: (props: any) => {
    guardianPropsSpy(props);
    const hideHeader = props.compactMobileHeader === true;
    return (
      <div data-testid="guardian-current-content">
        {!hideHeader && (
          <button
            type="button"
            aria-label={props.isSidebarVisible ? "Hide sidebar" : "Show sidebar"}
            onClick={props.onSidebarToggle}
          >
            Toggle sidebar
          </button>
        )}
        <div data-testid="guardian-session-rail">SessionRail</div>
        <div data-testid="guardian-transcript">Transcript</div>
        <form data-testid="guardian-composer">
          <textarea data-testid="composer-textarea" aria-label="Message" />
        </form>
      </div>
    );
  },
}));

vi.mock("@/components/sidebar/SidebarRoot", () => ({
  default: (props: any) => {
    sidebarPropsSpy(props);
    return (
      <div data-testid="sidebar-root-mock">
        {props.onNewChat && (
          <button type="button" onClick={props.onNewChat}>
            New Chat
          </button>
        )}
      </div>
    );
  },
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

    constructor() {
      sessionSpineInstances.push(this);
    }
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

vi.mock("@/lib/api", () => ({
  default: apiSpies,
  buildChatThreadsPath: () => "/api/chat/threads",
  fetchChatThread: vi.fn(),
  moveChatThread: vi.fn(),
}));

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
}

function renderGuardianFrameFirst(overrides: Record<string, unknown> = {}) {
  return render(
    <GuardianChatWithSidebar
      guardianName="Guardian"
      userName="User"
      frameFirstMobile
      mobileFramePrelude={
        <div data-testid="guardian-mobile-frame-prelude">
          <div role="toolbar" data-testid="guardian-mobile-frame-utilities">
            <button type="button" data-testid="prelude-workspace-btn">
              Open Workspace
            </button>
            <button type="button" data-testid="prelude-settings-btn">
              Settings
            </button>
            <button type="button" data-testid="prelude-voice-btn">
              Voice
            </button>
          </div>
          <div data-testid="runtime-status-notice">
            Provider degraded
          </div>
        </div>
      }
      {...overrides}
    />
  );
}

function renderGuardianDesktop() {
  setViewportWidth(1440);
  return render(
    <GuardianChatWithSidebar
      guardianName="Guardian"
      userName="User"
      frameFirstMobile={false}
    />
  );
}

describe("Guardian mobile header tools", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionSpineInstances.length = 0;
    localStorage.clear();
    window.history.pushState({}, "", "/chat");
    setViewportWidth(430);
    apiSpies.get.mockResolvedValue({
      data: { ok: true, threads: [], has_more: false },
    });
  });

  afterEach(() => {
    cleanup();
  });

  describe("compact header structure", () => {
    it("renders the compact header only under the frame-first Guardian condition", () => {
      renderGuardianFrameFirst();

      expect(
        screen.getByTestId("guardian-mobile-compact-header")
      ).toBeInTheDocument();
    });

    it("does not render the compact header on desktop", () => {
      renderGuardianDesktop();

      expect(
        screen.queryByTestId("guardian-mobile-compact-header")
      ).not.toBeInTheDocument();
    });

    it("retains the left sidebar control", () => {
      renderGuardianFrameFirst();

      const compactHeader = screen.getByTestId("guardian-mobile-compact-header");
      expect(
        within(compactHeader).getByRole("button", { name: "Show sidebar" })
      ).toBeInTheDocument();
    });

    it("renders the right Guardian tools menu trigger", () => {
      renderGuardianFrameFirst();

      const toolsTrigger = screen.getByTestId("guardian-mobile-tools-trigger");
      expect(toolsTrigger).toBeInTheDocument();
      expect(toolsTrigger).toHaveAttribute("aria-label", "Open Guardian tools");
      expect(toolsTrigger).toHaveAttribute("aria-haspopup", "menu");
      expect(toolsTrigger).toHaveAttribute("aria-expanded", "false");
    });
  });

  describe("displaced persistent tool rows", () => {
    it("does not render the persistent Open Workspace row", () => {
      renderGuardianFrameFirst();

      // The prelude toolbar is not rendered persistently
      expect(
        screen.queryByTestId("guardian-mobile-frame-utilities")
      ).not.toBeInTheDocument();
    });

    it("does not render the persistent prelude buttons outside the menu", () => {
      renderGuardianFrameFirst();

      // The prelude toolbar buttons should not be visible in the DOM outside the menu
      // (they are inside the dropdown which is portal-rendered when closed)
      expect(
        screen.queryByTestId("prelude-workspace-btn")
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("prelude-settings-btn")
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("prelude-voice-btn")
      ).not.toBeInTheDocument();
    });
  });

  describe("utility menu content", () => {
    it("exposes displaced actions when the menu is opened", async () => {
      const user = userEvent.setup();
      renderGuardianFrameFirst();

      const trigger = screen.getByTestId("guardian-mobile-tools-trigger");
      await user.click(trigger);

      // The menu should now be open and the toolbar buttons visible
      const menu = screen.getByRole("menu");
      expect(menu).toBeInTheDocument();

      // New thread action
      expect(
        within(menu).getByTestId("guardian-mobile-tools-new-thread")
      ).toBeInTheDocument();

      // Prelude toolbar buttons are rendered inside the menu
      expect(
        within(menu).getByTestId("prelude-workspace-btn")
      ).toBeInTheDocument();
      expect(
        within(menu).getByTestId("prelude-settings-btn")
      ).toBeInTheDocument();
    });

    it("closes the menu on Escape", async () => {
      const user = userEvent.setup();
      renderGuardianFrameFirst();

      const trigger = screen.getByTestId("guardian-mobile-tools-trigger");
      await user.click(trigger);

      expect(screen.getByRole("menu")).toBeInTheDocument();

      await user.keyboard("{Escape}");

      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });

    it("has the 'New thread' action in the menu", async () => {
      const user = userEvent.setup();
      renderGuardianFrameFirst();

      const trigger = screen.getByTestId("guardian-mobile-tools-trigger");
      await user.click(trigger);

      const newThreadItem = screen.getByTestId(
        "guardian-mobile-tools-new-thread"
      );
      expect(newThreadItem).toBeInTheDocument();
      expect(newThreadItem).toHaveTextContent("New thread");
    });
  });

  describe("runtime and auth truth preservation", () => {
    it("keeps runtime-health notice outside the utility menu", () => {
      renderGuardianFrameFirst();

      // The runtime status notice is visible outside the menu
      expect(
        screen.getByTestId("runtime-status-notice")
      ).toBeInTheDocument();
      expect(screen.getByText("Provider degraded")).toBeInTheDocument();
    });

    it("does not place runtime notice inside the closed menu", () => {
      renderGuardianFrameFirst();

      // When menu is closed, runtime notice is visible in the main content
      const compactHeader = screen.getByTestId("guardian-mobile-compact-header");
      // The runtime notice should NOT be a child of the compact header
      expect(
        within(compactHeader).queryByText("Provider degraded")
      ).not.toBeInTheDocument();
    });
  });

  describe("desktop preservation", () => {
    it("does not render the mobile tools trigger on desktop", () => {
      renderGuardianDesktop();

      expect(
        screen.queryByTestId("guardian-mobile-tools-trigger")
      ).not.toBeInTheDocument();
    });

    it("retains the Guardian sidebar on desktop", async () => {
      renderGuardianDesktop();

      // Desktop layout should have the persistent sidebar
      await screen.findByTestId("sidebar-root-mock");
    });
  });

  describe("non-Guardian mobile views are unchanged", () => {
    it("does not render the compact header when frameFirstMobile is false", () => {
      setViewportWidth(430);
      render(
        <GuardianChatWithSidebar
          guardianName="Guardian"
          userName="User"
          frameFirstMobile={false}
        />
      );

      expect(
        screen.queryByTestId("guardian-mobile-compact-header")
      ).not.toBeInTheDocument();
    });
  });

  describe("frame and composer integrity", () => {
    it("keeps the composer inside the primary frame", () => {
      renderGuardianFrameFirst();

      const primaryFrame = screen.getByTestId("guardian-primary-frame");
      expect(
        within(primaryFrame).getByTestId("composer-textarea")
      ).toBeInTheDocument();
    });

    it("keeps frame geometry unchanged", () => {
      renderGuardianFrameFirst();

      const frameShell = screen.getByTestId("guardian-primary-frame").parentElement;
      expect(frameShell).toHaveAttribute(
        "data-guardian-frame-shell",
        "frame-first"
      );
    });

    it("keeps compact mobile layout while Guardian tools are open", async () => {
      const user = userEvent.setup();
      renderGuardianFrameFirst();

      await user.click(screen.getByTestId("guardian-mobile-tools-trigger"));

      expect(guardianPropsSpy.mock.calls.at(-1)?.[0]).toMatchObject({
        compactMobile: true,
      });
    });
  });

  describe("sidebar independence", () => {
    it("keeps sidebar opening independent from the right utility menu", async () => {
      const user = userEvent.setup();
      renderGuardianFrameFirst();

      // Open sidebar
      const sidebarBtn = within(
        screen.getByTestId("guardian-mobile-compact-header")
      ).getByRole("button", { name: "Show sidebar" });
      await user.click(sidebarBtn);

      // Sidebar drawer should open
      expect(
        screen.getByRole("dialog", {
          name: "Application navigation and workspace",
        })
      ).toBeInTheDocument();
      expect(guardianPropsSpy.mock.calls.at(-1)?.[0]).toMatchObject({
        compactMobile: true,
      });
    });
  });
});
