import { cleanup, render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChatWithSidebar from "../GuardianChatWithSidebar";
import { resolveAppShellPresentationProfile } from "../AppShell";

const guardianPropsSpy = vi.hoisted(() => vi.fn());
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
        <div data-testid="guardian-current-controls">
          <button
            type="button"
            aria-label={props.isSidebarVisible ? "Hide sidebar" : "Show sidebar"}
            onClick={props.onSidebarToggle}
          >
            Toggle sidebar
          </button>
        </div>
        )}
        <div data-testid="guardian-transcript">Transcript</div>
        <form data-testid="guardian-composer">
          <textarea data-testid="composer-textarea" aria-label="Message" />
        </form>
      </div>
    );
  },
}));

vi.mock("@/components/sidebar/SidebarRoot", () => ({
  default: () => <div data-testid="sidebar-root-mock">Threads</div>,
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

vi.mock("@/lib/api", () => ({ default: apiSpies }));

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
}

describe("Guardian frame-first mobile shell", () => {
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

  it("selects the frame-first profile only for narrow Guardian", () => {
    expect(resolveAppShellPresentationProfile("guardian", true)).toBe(
      "guardian_frame_first"
    );

    for (const view of [
      "dashboard",
      "documents",
      "gallery",
      "settings",
    ] as const) {
      expect(resolveAppShellPresentationProfile(view, true)).toBe("default");
    }

    expect(resolveAppShellPresentationProfile("guardian", false)).toBe(
      "default"
    );
  });

  it("keeps the current controls, drawer opener, transcript, and composer inside one primary frame owner", () => {
    render(
      <GuardianChatWithSidebar
        guardianName="Guardian"
        userName="User"
        frameFirstMobile
        mobileFramePrelude={
          <div data-testid="guardian-mobile-frame-prelude">
            <button type="button">Current utility</button>
          </div>
        }
      />
    );

    const primaryFrame = screen.getByTestId("guardian-primary-frame");
    const frameShell = primaryFrame.parentElement;

    expect(screen.getAllByTestId("guardian-primary-frame")).toHaveLength(1);
    expect(frameShell).toHaveAttribute(
      "data-guardian-frame-shell",
      "frame-first"
    );
    expect(primaryFrame).toHaveAttribute(
      "data-frame-owner",
      "mobile-guardian"
    );
    expect(primaryFrame).toHaveStyle({
      gridColumn: "1",
      gridRow: "1",
    });
    expect(
      within(primaryFrame).getByTestId("guardian-mobile-compact-header")
    ).toBeInTheDocument();
    expect(
      within(primaryFrame).getByTestId("guardian-mobile-tools-trigger")
    ).toBeInTheDocument();
    expect(
      within(primaryFrame).getByRole("button", { name: "Show sidebar" })
    ).toBeInTheDocument();
    // The compact header removes the persistent prelude toolbar
    expect(
      within(primaryFrame).queryByTestId("guardian-mobile-frame-prelude")
    ).not.toBeInTheDocument();
    expect(
      within(primaryFrame).getByTestId("guardian-transcript")
    ).toBeInTheDocument();
    expect(
      within(primaryFrame).getByTestId("guardian-composer")
    ).toContainElement(
      within(primaryFrame).getByTestId("composer-textarea")
    );
    expect(guardianPropsSpy.mock.calls.at(-1)?.[0]).toMatchObject({
      compactMobileHeader: true,
      mobileComposerProjectionEnabled: true,
      mobileComposerProjectionSuspended: false,
    });
  });
});
