import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SettingsView from "./SettingsView";

const SETTINGS_TAB_STORAGE_KEY = "cfy.settingsTab";

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
  getAuthToken: vi.fn(() => null),
  getDevApiKey: vi.fn(() => ""),
  readRuntimeApiKey: vi.fn(() => ""),
  refreshApiBaseUrl: vi.fn(),
  setRuntimeApiKey: vi.fn(),
}));

vi.mock("@/features/settings/api/persona", () => ({
  updatePersonaSettings: mockedUpdatePersonaSettings,
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
    window.localStorage.clear();
    window.sessionStorage.clear();
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

    fireEvent.click(screen.getByRole("tab", { name: /^imprint$/i }));
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

    await waitFor(() => {
      expect(
        screen.getByText(/Saved locally and synced to runtime persona layer\./)
      ).toBeInTheDocument();
    });

    expect(
      screen.queryByTestId("personal-facts-panel")
    ).not.toBeInTheDocument();

    expect(setSystemPrompt).toHaveBeenCalledWith("Updated system prompt");
  });

  it("moves the settings rail with arrow keys", () => {
    renderSettingsView();

    const appearanceTab = screen.getByRole("tab", { name: /^appearance$/i });
    const imprintTab = screen.getByRole("tab", { name: /^imprint$/i });

    appearanceTab.focus();
    fireEvent.keyDown(appearanceTab, { key: "ArrowRight" });

    expect(imprintTab).toHaveFocus();
    expect(imprintTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: /^imprint$/i })).toBeInTheDocument();
  });

  it("persists the selected tab and restores it on remount", async () => {
    const { unmount } = renderSettingsView();

    fireEvent.click(screen.getByRole("tab", { name: /^data$/i }));

    await waitFor(() => {
      expect(window.sessionStorage.getItem(SETTINGS_TAB_STORAGE_KEY)).toBe(
        "data"
      );
    });

    expect(
      screen.getByRole("button", { name: /import chatgpt history/i })
    ).toBeInTheDocument();

    unmount();
    renderSettingsView();

    expect(screen.getByRole("tab", { name: /^data$/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(
      screen.getByRole("button", { name: /import chatgpt history/i })
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /^appearance$/i }));

    expect(
      screen.queryByRole("button", { name: /import chatgpt history/i })
    ).not.toBeInTheDocument();

    await waitFor(() => {
      expect(window.sessionStorage.getItem(SETTINGS_TAB_STORAGE_KEY)).toBe(
        "appearance"
      );
    });
  });

  it("frames System Docs as constitutional overlays on the Data tab", async () => {
    renderSettingsView();

    fireEvent.click(screen.getByRole("tab", { name: /^data$/i }));

    expect(
      screen.getByTestId("settings-system-docs-surface")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /System Docs are high-authority constitutional overlays for the assistant prompt\./i
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /They are not the normal place for project documents or project knowledge ingestion\./i
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Project-local working docs will live in a separate Project Knowledge Base surface in the project menu\./i
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/project document ingestion lane/i)
    ).not.toBeInTheDocument();
  });

  it("does not expose Diagnostics and falls back when it was persisted", async () => {
    window.sessionStorage.setItem(SETTINGS_TAB_STORAGE_KEY, "diagnostics");

    renderSettingsView();

    expect(
      screen.queryByRole("tab", { name: /^diagnostics$/i })
    ).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /^appearance$/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(
      screen.queryByRole("button", { name: /import chatgpt history/i })
    ).not.toBeInTheDocument();

    await waitFor(() => {
      expect(window.sessionStorage.getItem(SETTINGS_TAB_STORAGE_KEY)).toBe(
        "appearance"
      );
    });
  });

  it("keeps per-tab scroll memory intact while switching between tabs", async () => {
    const originalAddEventListener = HTMLElement.prototype.addEventListener;
    const scrollListeners: EventListener[] = [];
    const addEventListenerSpy = vi
      .spyOn(HTMLElement.prototype, "addEventListener")
      .mockImplementation(function (
        this: HTMLElement,
        type: string,
        listener: EventListenerOrEventListenerObject,
        options?: boolean | AddEventListenerOptions
      ) {
        if (
          this.getAttribute("data-testid") === "settings-panel-scroll-body" &&
          type === "scroll"
        ) {
          scrollListeners.push(listener as EventListener);
        }
        return originalAddEventListener.call(
          this,
          type,
          listener as any,
          options as any
        );
      });

    try {
      renderSettingsView();

      await act(async () => {
        fireEvent.click(screen.getByRole("tab", { name: /^data$/i }));
      });

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /import chatgpt history/i })
        ).toBeInTheDocument();
      });
      await waitFor(() => {
        expect(scrollListeners.length).toBeGreaterThanOrEqual(1);
      });

      const shell = screen.getByTestId("settings-panel-scroll-body");
      let scrollTop = 0;
      Object.defineProperty(shell, "scrollTop", {
        get: () => scrollTop,
        set: (value) => {
          scrollTop = Number(value);
        },
        configurable: true,
      });

      scrollTop = 180;
      await act(async () => {
        scrollListeners.at(-1)?.(new Event("scroll"));
      });

      await act(async () => {
        fireEvent.click(screen.getByRole("tab", { name: /^appearance$/i }));
      });
      await waitFor(() => {
        expect(screen.getByRole("tab", { name: /^appearance$/i })).toHaveAttribute(
          "aria-selected",
          "true"
        );
      });

      await act(async () => {
        fireEvent.click(screen.getByRole("tab", { name: /^data$/i }));
      });

      await waitFor(() => {
        expect(scrollTop).toBe(180);
        expect(
          screen.getByRole("button", { name: /import chatgpt history/i })
        ).toBeInTheDocument();
      });
    } finally {
      addEventListenerSpy.mockRestore();
    }
  });
});
