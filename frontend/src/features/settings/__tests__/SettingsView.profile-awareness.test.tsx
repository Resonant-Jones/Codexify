import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SettingsView from "@/features/settings/SettingsView";
import type { ExtColors } from "@/types/ui";
import { SUPPORTED_PROFILE_ROUTE_LABELS } from "@/contracts/supportedProfileRoutes";
import {
  ensureRuntimeRouteCapabilitiesLoaded,
  getRuntimeRouteCapabilityState,
  markRuntimeRouteUnavailableIfNotFound,
} from "@/lib/runtimeRouteCapabilities";

vi.mock("@/features/connectors/useConnectors", () => ({
  useConnectors: () => ({
    connectors: [],
    loading: false,
    error: null,
    refresh: vi.fn(),
    updateConnector: vi.fn(),
    authorizeOAuth: vi.fn(),
    testConnector: vi.fn(),
    syncConnector: vi.fn(),
  }),
}));

vi.mock("@/features/connectors/ConnectorCard", () => ({
  ConnectorCard: () => null,
}));

vi.mock("@/components/modals/ChatGPTImportModal", () => ({
  ChatGPTImportModal: () => null,
}));


const routeCapabilityState = {
  ready: true,
  states: {
    [SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT]: "unavailable",
    [SUPPORTED_PROFILE_ROUTE_LABELS.CONNECTORS]: "unavailable",
  } as Record<string, "available" | "unavailable" | "unknown">,
  markNotFound: false,
};

vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  useRuntimeRouteCapabilities: (labels: string[]) => {
    const states: Record<string, "available" | "unavailable" | "unknown"> =
      {};
    for (const label of labels) {
      states[label] = routeCapabilityState.states[label] ?? "unknown";
    }
    return {
      ready: routeCapabilityState.ready,
      states,
      mounted: [],
      declared: {},
    };
  },
  ensureRuntimeRouteCapabilitiesLoaded: vi.fn(async () => undefined),
  getRuntimeRouteCapabilityState: vi.fn(
    (label: string) => routeCapabilityState.states[label] ?? "unknown"
  ),
  markRuntimeRouteUnavailableIfNotFound: vi.fn(
    () => routeCapabilityState.markNotFound
  ),
}));

vi.mock("@/lib/runtimeConfig", () => ({
  getDesktopConnectionSettings: vi.fn(() => ({
    backendBaseUrl: "",
    sharePublicBaseUrl: "",
  })),
  initRuntimeConfig: vi.fn(async () => ({
    mode: "web",
    backendBaseUrl: "",
    apiBaseUrl: "/api",
    sseUrl: "/api/events",
    sharePublicBaseUrl: "",
    authMode: "local",
  })),
  invokeTauriCommand: vi.fn(),
  isTauriRuntime: vi.fn(() => false),
  openExternalUrl: vi.fn(async () => false),
  resolveBackendUrl: vi.fn((path: string) => path),
  saveDesktopConnectionSettings: vi.fn(async () => ({
    mode: "web",
    backendBaseUrl: "",
    apiBaseUrl: "/api",
    sseUrl: "/api/events",
    sharePublicBaseUrl: "",
    authMode: "local",
  })),
}));

vi.mock("@/lib/api", () => ({
  default: {
    interceptors: {
      request: { use: vi.fn(() => 1), eject: vi.fn() },
      response: { use: vi.fn(() => 2), eject: vi.fn() },
    },
  },
  clearRuntimeApiKey: vi.fn(),
  getAuthToken: vi.fn(() => null),
  getDevApiKey: vi.fn(() => ""),
  readRuntimeApiKey: vi.fn(() => null),
  refreshApiBaseUrl: vi.fn(),
  setRuntimeApiKey: vi.fn(),
}));

const ensureCapabilitiesLoadedMock = vi.mocked(
  ensureRuntimeRouteCapabilitiesLoaded
);
const getRuntimeRouteCapabilityStateMock = vi.mocked(
  getRuntimeRouteCapabilityState
);
const markRuntimeRouteUnavailableIfNotFoundMock = vi.mocked(
  markRuntimeRouteUnavailableIfNotFound
);

const EXT_COLORS: ExtColors = {
  pdf: "#111111",
  doc: "#222222",
  md: "#333333",
  png: "#444444",
  sketch: "#555555",
  txt: "#666666",
  docx: "#777777",
  jpeg: "#888888",
  codex: "#999999",
};

function renderSettingsView(overrides: Partial<ComponentProps<typeof SettingsView>> = {}) {
  const props: ComponentProps<typeof SettingsView> = {
    mode: "light",
    setMode: vi.fn(),
    guardianName: "Guardian",
    setGuardianName: vi.fn(),
    userName: "User",
    setUserName: vi.fn(),
    role: "Builder",
    setRole: vi.fn(),
    notes: "Existing notes",
    setNotes: vi.fn(),
    baseColor: "#101010",
    setBaseColor: vi.fn(),
    depth: 0.5,
    setDepth: vi.fn(),
    fade: 0.5,
    setFade: vi.fn(),
    resolved: "light",
    systemPrompt: "Current system prompt.",
    setSystemPrompt: vi.fn(),
    wallpaper: null,
    setWallpaper: vi.fn(),
    extColors: EXT_COLORS,
    setExtColors: vi.fn(),
    dashboardThreadRows: 2,
    setDashboardThreadRows: vi.fn(),
    surfaceDepth: 50,
    setSurfaceDepth: vi.fn(),
    surfaceWarmth: 0,
    setSurfaceWarmth: vi.fn(),
    ...overrides,
  };

  render(<SettingsView {...props} />);
  return props;
}

describe("SettingsView restricted profile behavior", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    routeCapabilityState.ready = true;
    routeCapabilityState.states[SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT] =
      "unavailable";
    routeCapabilityState.states[SUPPORTED_PROFILE_ROUTE_LABELS.CONNECTORS] =
      "unavailable";
    routeCapabilityState.markNotFound = false;
  });

  it.each(["unavailable", "unknown", "available"] as const)(
    "offers no Persona prompt editing when Imprint is %s",
    async (capability) => {
      const user = userEvent.setup();
      routeCapabilityState.states[SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT] = capability;
      const props = renderSettingsView();
      await user.click(screen.getByRole("tab", { name: "Imprint" }));
      expect(screen.queryByText("Preview Prompt")).not.toBeInTheDocument();
      expect(screen.queryByDisplayValue("Current system prompt.")).not.toBeInTheDocument();
      const notes = screen.getByDisplayValue("Existing notes");
      await user.clear(notes);
      await user.type(notes, "Updated notes");
      await user.click(screen.getByRole("button", { name: "Save" }));
      expect(props.setNotes).toHaveBeenCalledWith("Updated notes");
      expect(props.setSystemPrompt).not.toHaveBeenCalled();
      expect(await screen.findByText("Saved locally.")).toBeInTheDocument();
      expect(ensureCapabilitiesLoadedMock).not.toHaveBeenCalled();
      expect(getRuntimeRouteCapabilityStateMock).not.toHaveBeenCalled();
      expect(markRuntimeRouteUnavailableIfNotFoundMock).not.toHaveBeenCalled();
    }
  );
});
