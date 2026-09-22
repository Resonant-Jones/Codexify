import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  PROVIDER_RUNTIME_STATES,
  type ProviderRuntimeState,
} from "@/contracts/runtimeTokens";

import GuardianChatWithSidebar, {
  __resetThreadRefreshGuardForTests,
} from "../GuardianChatWithSidebar";

const apiSpies = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}));
const sessionState = vi.hoisted(() => ({
  activeThreadId: null as string | null,
}));

vi.mock("@/features/chat/GuardianChat", () => ({
  default: (props: {
    activeThread?: { id?: string } | null;
    providerRuntimeState?: string | null;
  }) => (
    <div
      data-testid="guardian-chat-mock"
      data-provider-runtime-state={props.providerRuntimeState ?? "unknown"}
    >
      {props.activeThread?.id === "7" ? (
        <article aria-label="Completed assistant response">
          Durable assistant output
        </article>
      ) : null}
    </div>
  ),
}));

vi.mock("@/components/sidebar/SidebarRoot", () => ({
  default: () => <aside data-testid="sidebar-root-mock" />,
}));

vi.mock("@/components/sidebar/useProjectsCache", () => ({
  useProjectsCache: () => ({ projectList: [] }),
}));

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({ subscribe: () => () => {} }),
}));

vi.mock("@/hooks/useWallpaperUrl", () => ({
  useWallpaperUrl: () => ({ wallpaperUrl: null }),
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
vi.mock("../MobileAppSidebarDrawer", () => ({ default: () => null }));

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

vi.mock("@/lib/providerPref", () => ({
  getPreferredProviderSelection: () => ({ provider: "local", model: "local-chat" }),
}));

vi.mock("@/state/session/SessionStateStore", () => ({
  InMemorySessionStateStore: class {
    getSessionState = vi.fn(async () => null);
  },
  RedisSessionStateStore: class {
    getSessionState = vi.fn(async () => null);
  },
}));

vi.mock("@/state/session/SessionSpine", () => ({
  SessionSpine: class {
    hydrate = vi.fn(async () => null);
    getDraft = vi.fn(() => "");
    getActiveTab = vi.fn(() =>
      sessionState.activeThreadId
        ? {
            tabId: "tab-1",
            threadId: sessionState.activeThreadId,
            title: "Completed thread",
          }
        : null
    );
    getActiveCompletion = vi.fn(() => null);
    isComposerBlocked = vi.fn(() => false);
    cancelActiveCompletion = vi.fn(() => null);
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
    tabs: sessionState.activeThreadId
      ? [
          {
            tabId: "tab-1",
            threadId: sessionState.activeThreadId,
            title: "Completed thread",
          },
        ]
      : [],
    activeTabId: sessionState.activeThreadId ? "tab-1" : null,
  }),
  useSessionActiveTab: () =>
    sessionState.activeThreadId
      ? {
          tabId: "tab-1",
          threadId: sessionState.activeThreadId,
          title: "Completed thread",
        }
      : null,
  useSessionActiveDraft: () => "",
  useSessionActiveProviderId: () => "local",
  useSessionActiveModelId: () => "local-chat",
  useSessionActiveInferenceMode: () => "default",
}));

vi.mock("@/lib/api", () => ({
  default: apiSpies,
  buildChatThreadsPath: () => "/api/chat/threads",
  fetchChatThread: vi.fn(async () => null),
  moveChatThread: vi.fn(async () => null),
}));

function renderShell(providerRuntimeState: ProviderRuntimeState) {
  return render(
    <GuardianChatWithSidebar
      guardianName="Guardian"
      userName="User"
      providerRuntimeState={providerRuntimeState}
    />
  );
}

function expectProviderStatusHidden(state: string) {
  expect(
    screen.queryByRole("status", { name: /^Provider runtime:/ })
  ).not.toBeInTheDocument();
  expect(screen.getByTestId("guardian-chat-mock")).toHaveAttribute(
    "data-provider-runtime-state",
    state
  );
  expect(screen.queryByText("Queued")).not.toBeInTheDocument();
}

describe("GuardianChatWithSidebar terminal projection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    __resetThreadRefreshGuardForTests();
    sessionState.activeThreadId = null;
    window.history.replaceState({}, "", "/chat");
    window.localStorage.clear();
    window.sessionStorage.clear();
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 1440,
    });
    apiSpies.get.mockImplementation((url: string) => {
      if (url === "/api/chat/threads") {
        return Promise.resolve({
          data: {
            threads: sessionState.activeThreadId
              ? [
                  {
                    id: Number(sessionState.activeThreadId),
                    title: "Completed thread",
                    last_message: "Durable assistant output",
                  },
                ]
              : [],
            has_more: false,
          },
        });
      }
      return Promise.resolve({ data: {} });
    });
  });

  it("keeps healthy idle provider state out of the shell status UI", () => {
    renderShell(PROVIDER_RUNTIME_STATES.READY);

    expectProviderStatusHidden(PROVIDER_RUNTIME_STATES.READY);
  });

  it("keeps a completed conversation visible without projecting Queued", async () => {
    sessionState.activeThreadId = "7";
    window.history.replaceState({}, "", "/chat/7");

    renderShell(PROVIDER_RUNTIME_STATES.READY);

    expect(await screen.findByLabelText("Completed assistant response")).toHaveTextContent(
      "Durable assistant output"
    );
    expectProviderStatusHidden(PROVIDER_RUNTIME_STATES.READY);
  });

  it("stays non-queued when an idle completed thread is remounted", async () => {
    sessionState.activeThreadId = "7";
    window.history.replaceState({}, "", "/chat/7");
    const firstRender = renderShell(PROVIDER_RUNTIME_STATES.READY);
    await screen.findByLabelText("Completed assistant response");
    firstRender.unmount();

    renderShell(PROVIDER_RUNTIME_STATES.READY);

    await waitFor(() => {
      expect(screen.getByLabelText("Completed assistant response")).toBeInTheDocument();
    });
    expectProviderStatusHidden(PROVIDER_RUNTIME_STATES.READY);
  });

  it("keeps model-warming state out of shell status UI while passing it to chat", () => {
    renderShell(PROVIDER_RUNTIME_STATES.MODEL_WARMING);

    expectProviderStatusHidden(PROVIDER_RUNTIME_STATES.MODEL_WARMING);
  });

  it.each([
    PROVIDER_RUNTIME_STATES.DEGRADED,
    PROVIDER_RUNTIME_STATES.OFFLINE,
  ])("keeps %s state out of shell status UI while passing it to chat", (state) => {
    renderShell(state);

    expectProviderStatusHidden(state);
  });
});
