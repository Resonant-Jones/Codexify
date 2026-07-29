import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChatWithSidebar, {
  type GuardianApplicationDestination,
} from "../GuardianChatWithSidebar";

const guardianPropsSpy = vi.hoisted(() => vi.fn());
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
      <>
        {!props.compactMobileHeader && (
          <button
            type="button"
            aria-label={props.isSidebarVisible ? "Hide sidebar" : "Show sidebar"}
            onClick={props.onSidebarToggle}
          >
            Toggle sidebar
          </button>
        )}
      </>
    );
  },
}));

vi.mock("@/components/sidebar/SidebarRoot", () => ({
  default: (props: any) => {
    const [tab, setTab] = React.useState<"threads" | "projects">("threads");
    const [search, setSearch] = React.useState("");
    return (
      <section data-testid="sidebar-root-mock">
        <div role="tablist" aria-label="Sidebar tabs">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "threads"}
            onClick={() => setTab("threads")}
          >
            Threads
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "projects"}
            onClick={() => setTab("projects")}
          >
            Projects
          </button>
        </div>
        <input
          aria-label="Workspace search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <button type="button" onClick={props.onNewChat}>
          New Chat
        </button>
      </section>
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
vi.mock("@/features/workspace/WorkspacePane", () => ({ default: () => null }));
vi.mock("@/components/ui/RefractiveGlassCard", () => ({
  default: ({ children }: { children?: React.ReactNode }) => <>{children ?? null}</>,
}));
vi.mock("@/components/surface/FrameCard", () => ({
  default: ({ children }: { children?: React.ReactNode }) => <>{children ?? null}</>,
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
    tabs: [{ tabId: "tab-1", title: "New Thread", pendingThread: true }],
    activeTabId: "tab-1",
  }),
  useSessionActiveTab: () => ({
    tabId: "tab-1",
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
  const rendered = render(
    <GuardianChatWithSidebar
      guardianName="Guardian"
      userName="User"
      activeApplicationView={activeApplicationView}
      applicationDestinations={APPLICATION_DESTINATIONS}
      onNavigateApplicationView={onNavigateApplicationView}
      frameFirstMobile
    />
  );
  return { ...rendered, onNavigateApplicationView };
}

async function openDrawer(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Show sidebar" }));
  return screen.findByRole("dialog", {
    name: "Guardian navigation and threads",
  });
}

describe("Guardian mobile sidebar application menu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionSpineInstances.length = 0;
    localStorage.clear();
    window.history.pushState({}, "", "/chat");
    setViewportWidth(430);
    apiSpies.get.mockResolvedValue({
      data: { ok: true, threads: [], projects: [], has_more: false },
    });
  });

  it("defaults to a workspace-first drawer and expands destinations above the stable workspace", async () => {
    const user = userEvent.setup();
    renderGuardian();
    const drawer = await openDrawer(user);
    const trigger = within(drawer).getByRole("button", {
      name: "Open Codexify navigation",
    });
    const workspace = within(drawer).getByTestId("sidebar-root-mock");

    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(trigger).toHaveAttribute(
      "aria-controls",
      "guardian-mobile-application-navigation"
    );
    expect(
      within(drawer).queryByRole("navigation", {
        name: "Application destinations",
      })
    ).not.toBeInTheDocument();
    expect(within(drawer).getByRole("tab", { name: "Threads" })).toHaveAttribute(
      "aria-selected",
      "true"
    );

    await user.type(
      within(drawer).getByRole("textbox", { name: "Workspace search" }),
      "retained"
    );
    await user.click(trigger);

    const navigation = within(drawer).getByRole("navigation", {
      name: "Application destinations",
    });
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(
      within(navigation)
        .getAllByRole("button")
        .map((button) => button.textContent)
    ).toEqual(["Guardian", "Documents", "Gallery", "Dashboard", "Settings"]);
    expect(
      navigation.compareDocumentPosition(workspace) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
    expect(within(drawer).getByTestId("sidebar-root-mock")).toBe(workspace);
    expect(
      within(drawer).getByRole("textbox", { name: "Workspace search" })
    ).toHaveValue("retained");

    await user.click(trigger);
    expect(
      within(drawer).queryByRole("navigation", {
        name: "Application destinations",
      })
    ).not.toBeInTheDocument();
    expect(
      within(drawer).getByRole("textbox", { name: "Workspace search" })
    ).toHaveValue("retained");
  });

  it("layers Escape dismissal and restores focus to the mark before closing the drawer", async () => {
    const user = userEvent.setup();
    renderGuardian();
    const opener = screen.getByRole("button", { name: "Show sidebar" });
    const drawer = await openDrawer(user);
    const trigger = within(drawer).getByRole("button", {
      name: "Open Codexify navigation",
    });

    await user.click(trigger);
    await user.keyboard("{Escape}");

    expect(
      screen.getByRole("dialog", { name: "Guardian navigation and threads" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open Codexify navigation" })
    ).toHaveFocus();
    expect(
      screen.queryByRole("navigation", { name: "Application destinations" })
    ).not.toBeInTheDocument();

    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(
        screen.queryByRole("dialog", {
          name: "Guardian navigation and threads",
        })
      ).not.toBeInTheDocument();
    });
    expect(opener).toHaveFocus();
  });

  it.each(APPLICATION_DESTINATIONS)(
    "routes $label through the supplied callback and resets the disclosure",
    async (destination) => {
      const user = userEvent.setup();
      const navigate = vi.fn();
      renderGuardian(navigate);
      const drawer = await openDrawer(user);
      await user.click(
        within(drawer).getByRole("button", {
          name: "Open Codexify navigation",
        })
      );
      await user.click(within(drawer).getByRole("button", { name: destination.label }));

      expect(navigate).toHaveBeenCalledWith(destination.view);
      await waitFor(() => {
        expect(
          screen.queryByRole("dialog", {
            name: "Guardian navigation and threads",
          })
        ).not.toBeInTheDocument();
      });

      await openDrawer(user);
      expect(
        screen.getByRole("button", { name: "Open Codexify navigation" })
      ).toHaveAttribute("aria-expanded", "false");
      expect(
        screen.queryByRole("navigation", {
          name: "Application destinations",
        })
      ).not.toBeInTheDocument();
    }
  );

  it("does not refetch workspace data when the local menu toggles", async () => {
    const user = userEvent.setup();
    renderGuardian();
    const drawer = await openDrawer(user);
    await waitFor(() =>
      expect(
        apiSpies.get.mock.calls.filter(([url]) => url === "/api/projects")
      ).toHaveLength(1)
    );
    const trigger = within(drawer).getByRole("button", {
      name: "Open Codexify navigation",
    });

    await user.click(trigger);
    await user.click(trigger);

    expect(
      apiSpies.get.mock.calls.filter(([url]) => url === "/api/projects")
    ).toHaveLength(1);
  });

  it("does not render the mobile disclosure in the desktop contract", async () => {
    setViewportWidth(1440);
    renderGuardian();

    await screen.findByTestId("sidebar-root-mock");
    expect(
      screen.queryByRole("button", { name: "Open Codexify navigation" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "Application destinations" })
    ).not.toBeInTheDocument();
  });
});
