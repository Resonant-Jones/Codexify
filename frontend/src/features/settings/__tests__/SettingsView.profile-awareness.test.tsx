import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SettingsView from "@/features/settings/SettingsView";
import type { ExtColors } from "@/types/ui";
import { updatePersonaSettings } from "@/features/settings/api/persona";
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

vi.mock("@/features/settings/diagnostics", () => ({
  MemoryBrowser: () => null,
}));

vi.mock("@/components/modals/ChatGPTImportModal", () => ({
  ChatGPTImportModal: () => null,
}));

vi.mock("@/features/settings/api/persona", () => ({
  updatePersonaSettings: vi.fn(),
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

const updatePersonaSettingsMock = vi.mocked(updatePersonaSettings);
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
    updatePersonaSettingsMock.mockResolvedValue({
      id: 9,
      text: "Updated runtime persona.",
      source: "user",
      createdAt: "2026-03-30T10:00:00Z",
      canClear: false,
    });
  });

  it("saves locally and skips persona sync when imprint is unavailable", async () => {
    const user = userEvent.setup();
    const props = renderSettingsView();

    await user.click(screen.getByRole("button", { name: "System Prompt" }));
    const promptField = screen.getByDisplayValue("Current system prompt.");
    await user.clear(promptField);
    await user.type(promptField, "Local-only prompt update.");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(props.setSystemPrompt).toHaveBeenCalledWith("Local-only prompt update.");
    expect(updatePersonaSettingsMock).not.toHaveBeenCalled();
    expect(
      await screen.findByText(
        "Saved locally. Not synced to runtime persona layer in this profile."
      )
    ).toBeInTheDocument();
  });

  it("attempts sync once in unknown state and downgrades 404 to local-only success", async () => {
    const user = userEvent.setup();
    routeCapabilityState.states[SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT] =
      "unknown";
    routeCapabilityState.markNotFound = true;
    updatePersonaSettingsMock.mockRejectedValue({
      response: { status: 404, data: { detail: "Not Found" } },
    });

    const props = renderSettingsView();

    await user.click(screen.getByRole("button", { name: "System Prompt" }));
    const promptField = screen.getByDisplayValue("Current system prompt.");
    await user.clear(promptField);
    await user.type(promptField, "Unknown route prompt update.");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(ensureCapabilitiesLoadedMock).toHaveBeenCalled();
      expect(getRuntimeRouteCapabilityStateMock).toHaveBeenCalledWith(
        SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT
      );
      expect(updatePersonaSettingsMock).toHaveBeenCalledTimes(1);
      expect(markRuntimeRouteUnavailableIfNotFoundMock).toHaveBeenCalled();
    });

    expect(props.setSystemPrompt).toHaveBeenCalledWith(
      "Unknown route prompt update."
    );
    expect(
      await screen.findByText(
        "Saved locally. Not synced to runtime persona layer in this profile."
      )
    ).toBeInTheDocument();
  });

  it("preserves local save when persona sync fails for non-404 reasons", async () => {
    const user = userEvent.setup();
    routeCapabilityState.states[SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT] =
      "available";
    updatePersonaSettingsMock.mockRejectedValue({
      response: { status: 500, data: { detail: "backend sync broke" } },
    });

    const props = renderSettingsView();

    await user.click(screen.getByRole("button", { name: "System Prompt" }));
    const promptField = screen.getByDisplayValue("Current system prompt.");
    await user.clear(promptField);
    await user.type(promptField, "Retryable prompt update.");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(updatePersonaSettingsMock).toHaveBeenCalledTimes(1);
    });

    expect(props.setSystemPrompt).toHaveBeenCalledWith(
      "Retryable prompt update."
    );
    expect(
      await screen.findByText("Saved locally. Persona sync failed.")
    ).toBeInTheDocument();
    expect(screen.getByText("backend sync broke")).toBeInTheDocument();
  });
});
