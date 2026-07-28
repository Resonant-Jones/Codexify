import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChatWithSidebar, {
  type GuardianApplicationDestination,
} from "../GuardianChatWithSidebar";

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

const APPLICATION_DESTINATIONS = [
  { view: "guardian", label: "Guardian", priority: "primary" },
  { view: "documents", label: "Documents", priority: "primary" },
  { view: "gallery", label: "Gallery", priority: "primary" },
  { view: "dashboard", label: "Dashboard", priority: "secondary" },
  { view: "settings", label: "Settings", priority: "secondary" },
] as const satisfies readonly GuardianApplicationDestination[];

vi.mock("@/features/chat/GuardianChat", () => ({
  default: (props: any) => {
    guardianPropsSpy(props);
    return (
      <button
        type="button"
        aria-label={props.isSidebarVisible ? "Hide sidebar" : "Show sidebar"}
        onClick={props.onSidebarToggle}
      >
        Toggle sidebar
      </button>
    );
  },
}));

vi.mock("@/components/sidebar/SidebarRoot", () => ({
  default: (props: any) => {
    sidebarPropsSpy(props);
    return (
      <div data-testid="sidebar-root-mock">
        {(props.threads ?? []).map((thread: any) => (
          <button
            key={String(thread.id)}
            type="button"
            data-testid={`thread-${String(thread.id)}`}
            onClick={() => props.onSelect(String(thread.id))}
          >
            {String(thread.title)}
          </button>
        ))}
        <button type="button" onClick={props.onNewChat}>
          New Chat
        </button>
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

vi.mock("@/lib/api", () => ({ default: apiSpies }));

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
}

function renderGuardian(
  onNavigateApplicationView = vi.fn(),
  activeApplicationView: GuardianApplicationDestination["view"] = "guardian"
) {
  return {
    onNavigateApplicationView,
    ...render(
      <GuardianChatWithSidebar
        guardianName="Guardian"
        userName="User"
        activeApplicationView={activeApplicationView}
        applicationDestinations={APPLICATION_DESTINATIONS}
        onNavigateApplicationView={onNavigateApplicationView}
        frameFirstMobile
      />
    ),
  };
}

async function openMobileSidebar(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Show sidebar" }));
  return screen.findByRole("dialog", {
    name: "Guardian navigation and threads",
  });
}

describe("Guardian mobile application navigation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionSpineInstances.length = 0;
    localStorage.clear();
    window.history.pushState({}, "", "/chat");
    setViewportWidth(430);
    apiSpies.get.mockImplementation(async (url: string) => {
      if (url === "/chat/threads") {
        return {
          data: {
            ok: true,
            threads: [{ id: 7, title: "Thread Seven", last_message: "" }],
            has_more: false,
          },
        };
      }
      return { data: {} };
    });
  });

  it("renders the identity mark and all canonical destinations only in the open mobile drawer", async () => {
    const user = userEvent.setup();
    renderGuardian();

    expect(
      screen.queryByTestId("guardian-mobile-application-navigation")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("guardian-mobile-codexify-mark")
    ).not.toBeInTheDocument();

    await openMobileSidebar(user);

    expect(
      screen.getByTestId("guardian-primary-frame").parentElement
    ).toHaveAttribute("data-guardian-frame-shell", "frame-first");
    const mark = screen.getByTestId("guardian-mobile-codexify-mark");
    expect(mark).toHaveAttribute("alt", "");
    expect(mark).toHaveAttribute("aria-hidden", "true");
    expect(
      screen.getByTestId("guardian-mobile-application-navigation")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("guardian-mobile-destination-guardian")
    ).toHaveAttribute("aria-current", "page");

    for (const destination of APPLICATION_DESTINATIONS) {
      expect(
        screen.getByRole("button", { name: destination.label })
      ).toBeInTheDocument();
    }
  });

  it("uses canonical destination identifiers and closes after every selection", async () => {
    const user = userEvent.setup();
    const navigate = vi.fn();
    renderGuardian(navigate);

    for (const destination of APPLICATION_DESTINATIONS) {
      await openMobileSidebar(user);
      await user.click(
        screen.getByTestId(
          `guardian-mobile-destination-${destination.view}`
        )
      );
      expect(navigate).toHaveBeenLastCalledWith(destination.view);
      await waitFor(() => {
        expect(
          screen.queryByTestId("mobile-sidebar-overlay")
        ).not.toBeInTheDocument();
      });
      expect(
        screen.getByTestId("guardian-primary-frame").parentElement
      ).toHaveAttribute("data-guardian-frame-shell", "frame-first");
    }
  });

  it("closes on Escape and restores focus to the existing opener", async () => {
    const user = userEvent.setup();
    renderGuardian();

    const opener = screen.getByRole("button", { name: "Show sidebar" });
    await openMobileSidebar(user);
    expect(
      screen.getByRole("button", {
        name: "Close navigation and threads sidebar",
      })
    ).toHaveFocus();

    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(
      screen.getByRole("dialog", {
        name: "Guardian navigation and threads",
      })
    ).toContainElement(document.activeElement as HTMLElement);

    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(screen.queryByTestId("mobile-sidebar-overlay")).not.toBeInTheDocument();
    });
    expect(opener).toHaveFocus();
  });

  it("keeps thread selection on the SessionSpine seam and closes the mobile drawer", async () => {
    const user = userEvent.setup();
    renderGuardian();

    await openMobileSidebar(user);
    await user.click(await screen.findByTestId("thread-7"));

    expect(sessionSpineInstances).toHaveLength(1);
    expect(sessionSpineInstances[0].tabSetThread).toHaveBeenCalledWith(
      "tab-1",
      "7",
      "Thread Seven"
    );
    await waitFor(() => {
      expect(screen.queryByTestId("mobile-sidebar-overlay")).not.toBeInTheDocument();
    });
  });

  it("does not render or expose mobile destination controls in the desktop sidebar contract", async () => {
    setViewportWidth(1440);
    renderGuardian();

    await screen.findByTestId("sidebar-root-mock");

    expect(
      screen.queryByTestId("guardian-mobile-application-navigation")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("guardian-mobile-codexify-mark")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("guardian-mobile-destination-documents")
    ).not.toBeInTheDocument();
  });
});
