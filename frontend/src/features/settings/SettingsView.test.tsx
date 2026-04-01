import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SettingsView from "./SettingsView";

const mockedApi = vi.hoisted(() => ({
  get: vi.fn(async () => ({ data: {} })),
  post: vi.fn(async () => ({ data: {} })),
  delete: vi.fn(async () => ({ data: {} })),
  interceptors: {
    request: { use: vi.fn(() => 1), eject: vi.fn() },
    response: { use: vi.fn(() => 2), eject: vi.fn() },
  },
}));

const mockedUpdatePersonaSettings = vi.hoisted(() => vi.fn());
const fetchLatestRagTraceMock = vi.hoisted(() => vi.fn());
const mockedUseContextTrace = vi.hoisted(() => vi.fn());

vi.mock("@/components/ui/button", () => ({
  Button: (props: Record<string, unknown>) => (
    <button {...props}>{props.children as string}</button>
  ),
}));

vi.mock("@/components/ui/input", () => ({
  Input: (props: Record<string, unknown>) => <input {...props} />,
}));

vi.mock("@/components/ui/textarea", () => ({
  Textarea: (props: Record<string, unknown>) => <textarea {...props} />,
}));

vi.mock("@/components/controls/SegmentedThemeControl", () => ({
  default: () => <div data-testid="segmented-theme-control" />,
}));

vi.mock("@/features/connectors/useConnectors", () => ({
  useConnectors: () => ({
    connectors: [],
    updateConnector: vi.fn(),
    loading: false,
    error: null,
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
  openExternalUrl: vi.fn(async () => true),
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
  default: mockedApi,
  clearRuntimeApiKey: vi.fn(),
  fetchLatestRagTrace: fetchLatestRagTraceMock,
  getAuthToken: vi.fn(() => null),
  getDevApiKey: vi.fn(() => ""),
  readRuntimeApiKey: vi.fn(() => ""),
  refreshApiBaseUrl: vi.fn(),
  setRuntimeApiKey: vi.fn(),
}));

vi.mock("@/features/settings/api/persona", () => ({
  updatePersonaSettings: mockedUpdatePersonaSettings,
}));

vi.mock("@/lib/guardianEventSource", () => ({
  GuardianEventSource: class {
    onopen: (() => void) | null = null;
    onerror: (() => void) | null = null;
    addEventListener() {}
    removeEventListener() {}
    close() {}
  },
}));

vi.mock("@/state/contextTrace", () => ({
  useContextTrace: mockedUseContextTrace,
}));

function renderSettingsView(
  overrides: Partial<Parameters<typeof SettingsView>[0]> = {}
) {
  return render(
    <SettingsView
      mode="light"
      setMode={vi.fn()}
      guardianName="Guardian"
      setGuardianName={vi.fn()}
      userName="User"
      setUserName={vi.fn()}
      role="Builder"
      setRole={vi.fn()}
      notes="Notes"
      setNotes={vi.fn()}
      baseColor="#111827"
      setBaseColor={vi.fn()}
      depth={0.3}
      setDepth={vi.fn()}
      fade={0.2}
      setFade={vi.fn()}
      resolved="light"
      systemPrompt="Original system prompt"
      setSystemPrompt={vi.fn()}
      wallpaper={null}
      setWallpaper={vi.fn()}
      extColors={{} as any}
      setExtColors={vi.fn()}
      dashboardThreadRows={2}
      setDashboardThreadRows={vi.fn()}
      {...overrides}
    />
  );
}

describe("SettingsView save flow", () => {
  beforeEach(() => {
    mockedUpdatePersonaSettings.mockReset();
    mockedApi.get.mockClear();
    mockedApi.post.mockClear();
    mockedApi.delete.mockClear();
    fetchLatestRagTraceMock.mockReset();
    mockedUseContextTrace.mockReturnValue({
      lastDepth: "normal",
      lastMemory: [],
      lastSemantic: [],
      lastThreadId: null,
      lastTimestamp: null,
    });
    window.localStorage.clear();
    window.history.pushState({}, "", "/chat/42");
  });

  it("shows success after the system prompt save resolves", async () => {
    const setSystemPrompt = vi.fn();
    mockedUpdatePersonaSettings.mockResolvedValue({
      id: 42,
      text: "Updated system prompt",
      source: "user",
      createdAt: "2026-03-30T12:00:00Z",
      canClear: false,
    });

    renderSettingsView({ setSystemPrompt });

    fireEvent.click(screen.getByRole("button", { name: /^system prompt$/i }));
    fireEvent.change(screen.getByDisplayValue("Original system prompt"), {
      target: { value: "Updated system prompt" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      expect(mockedUpdatePersonaSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          text: "Updated system prompt",
          persona_prompt: "Updated system prompt",
          system_prompt: "Updated system prompt",
        })
      );
    });

    expect(
      await screen.findByText("Saved locally and synced to runtime persona layer.")
    ).toBeInTheDocument();
    expect(setSystemPrompt).toHaveBeenCalledWith("Updated system prompt");
  });

  it("binds diagnostics to the active route thread and refreshes when the active thread changes", async () => {
    fetchLatestRagTraceMock.mockResolvedValue({ documents: [], graph: [] });

    renderSettingsView();

    fireEvent.click(screen.getByRole("button", { name: /^diagnostics$/i }));

    await waitFor(() => {
      expect(fetchLatestRagTraceMock).toHaveBeenCalledWith(42);
    });

    expect(
      screen.getAllByText(
        (_, element) =>
          element?.textContent?.trim() === "Depth: normal • Thread: 42"
      )
    ).not.toHaveLength(0);
    expect(
      screen.queryByText((_, element) =>
        Boolean(element?.textContent?.includes("Thread: n/a"))
      )
    ).not.toBeInTheDocument();

    act(() => {
      window.history.pushState({}, "", "/chat/84");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    await waitFor(() => {
      expect(fetchLatestRagTraceMock).toHaveBeenLastCalledWith(84);
    });

    expect(
      screen.getAllByText(
        (_, element) =>
          element?.textContent?.trim() === "Depth: normal • Thread: 84"
      )
    ).not.toHaveLength(0);
  });
});
