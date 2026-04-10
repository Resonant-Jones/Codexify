import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { SettingsView } from "@/features/settings/SettingsView";
import type { ExtColors, ThemeMode } from "@/types/ui";

const useConnectorsMock = vi.fn();
const SETTINGS_TAB_STORAGE_KEY = "cfy.settings.activeTab";

vi.mock("@/features/connectors/useConnectors", () => ({
  useConnectors: () => useConnectorsMock(),
}));

vi.mock("@/features/settings/components/ImprintReviewPanel", () => ({
  default: () => (
    <section data-testid="mock-imprint-review">Imprint Review</section>
  ),
}));

vi.mock("@/features/settings/components/PersonalFactsPanel", () => ({
  default: () => (
    <section data-testid="mock-persona-settings">Persona Settings</section>
  ),
}));

vi.mock("@/features/settings/components/SystemPromptInspector", () => ({
  default: () => (
    <section data-testid="mock-system-prompt-inspector">
      System Prompt Inspector
    </section>
  ),
}));

vi.mock("@/components/modals/ChatGPTImportModal", () => ({
  ChatGPTImportModal: () => null,
}));

vi.mock("@/lib/runtimeConfig", () => ({
  getDesktopConnectionSettings: () => ({
    backendBaseUrl: "",
    sharePublicBaseUrl: "",
  }),
  getRuntimeConfigSync: () => ({
    apiBaseUrl: "",
    backendBaseUrl: "",
    sharePublicBaseUrl: "",
  }),
  initRuntimeConfig: vi.fn(),
  invokeTauriCommand: vi.fn(),
  isTauriRuntime: () => false,
  openExternalUrl: vi.fn(),
  resolveBackendUrl: (path: string) => path,
  saveDesktopConnectionSettings: vi.fn(),
}));

function createSettingsViewProps() {
  return {
    baseColor: "#111111",
    dashboardThreadRows: 2,
    depth: 0.4,
    extColors: {
      codex: "#000000",
      doc: "#000000",
      docx: "#000000",
      jpeg: "#000000",
      md: "#000000",
      pdf: "#000000",
      png: "#000000",
      sketch: "#000000",
      txt: "#000000",
    } satisfies ExtColors,
    fade: 0.2,
    guardianName: "Harbor",
    mode: "light" as ThemeMode,
    notes: "Local notes",
    resolved: "light" as const,
    role: "Researcher",
    setBaseColor: vi.fn(),
    setDashboardThreadRows: vi.fn(),
    setDepth: vi.fn(),
    setExtColors: vi.fn(),
    setFade: vi.fn(),
    setGuardianName: vi.fn(),
    setMode: vi.fn(),
    setNotes: vi.fn(),
    setRole: vi.fn(),
    setSystemPrompt: vi.fn(),
    setUserName: vi.fn(),
    setWallpaper: vi.fn(),
    systemPrompt: "Local preview prompt",
    userName: "Ari",
    wallpaper: null,
  };
}

describe("SettingsView", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    useConnectorsMock.mockReturnValue({
      connectors: [],
      error: null,
      loading: false,
      updateConnector: vi.fn(),
      authorizeOAuth: vi.fn(),
      testConnector: vi.fn(),
      syncConnector: vi.fn(),
    });
  });

  test("mounts the Imprint workspace as one consumer flow", async () => {
    const user = userEvent.setup();
    const props = createSettingsViewProps();

    render(<SettingsView {...props} />);

    expect(
      screen.getByRole("tablist", { name: "Settings tabs" })
    ).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Imprint" }));

    expect(screen.getByText("Local Preview")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Imprint" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByTestId("imprint-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("mock-imprint-review")).toBeInTheDocument();
    expect(screen.getByTestId("mock-system-prompt-inspector")).toBeInTheDocument();
  });

  test("scopes the import controls to the Data tab", async () => {
    const user = userEvent.setup();
    const props = createSettingsViewProps();

    render(<SettingsView {...props} />);

    expect(
      screen.queryByRole("button", { name: "Import ChatGPT history" })
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Data" }));

    expect(
      screen.getByRole("button", { name: "Import ChatGPT history" })
    ).toBeInTheDocument();
  });

  test("persists the Personal Facts tab and restores it on remount", async () => {
    const user = userEvent.setup();
    const props = createSettingsViewProps();
    const { unmount } = render(<SettingsView {...props} />);

    await user.click(screen.getByRole("tab", { name: "Personal Facts" }));

    expect(screen.getByRole("tab", { name: "Personal Facts" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByTestId("mock-persona-settings")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Import ChatGPT history" })
    ).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem(SETTINGS_TAB_STORAGE_KEY)).toBe(
      "personalFacts"
    );

    unmount();
    render(<SettingsView {...props} />);

    expect(screen.getByRole("tab", { name: "Personal Facts" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByTestId("mock-persona-settings")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Import ChatGPT history" })
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Appearance" }));

    expect(window.sessionStorage.getItem(SETTINGS_TAB_STORAGE_KEY)).toBe(
      "appearance"
    );
  });

  test("falls back safely when persisted tab state is invalid", async () => {
    window.sessionStorage.setItem(SETTINGS_TAB_STORAGE_KEY, "broken-tab");

    render(<SettingsView {...createSettingsViewProps()} />);

    expect(screen.getByRole("tab", { name: "Appearance" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(
      screen.queryByRole("button", { name: "Import ChatGPT history" })
    ).not.toBeInTheDocument();

    await waitFor(() => {
      expect(window.sessionStorage.getItem(SETTINGS_TAB_STORAGE_KEY)).toBe(
        "appearance"
      );
    });
  });

  test("keeps per-tab scroll memory intact while switching between tabs", async () => {
    const user = userEvent.setup();
    render(<SettingsView {...createSettingsViewProps()} />);

    const shell = screen.getByTestId("settings-panel-shell") as HTMLElement;

    await user.click(screen.getByRole("tab", { name: "Data" }));
    shell.scrollTop = 180;

    await user.click(screen.getByRole("tab", { name: "Appearance" }));
    await user.click(screen.getByRole("tab", { name: "Data" }));

    expect(shell.scrollTop).toBe(180);
    expect(
      screen.getByRole("button", { name: "Import ChatGPT history" })
    ).toBeInTheDocument();
  });
});
