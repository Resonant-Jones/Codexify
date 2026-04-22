import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { SettingsView } from "@/features/settings/SettingsView";
import type { ExtColors, ThemeMode } from "@/types/ui";

const useConnectorsMock = vi.fn();

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

vi.mock("@/features/settings/components/SettingsPanelShell", () => ({
  default: ({ children }: { children: ReactNode }) => (
    <div data-testid="settings-panel-shell">{children}</div>
  ),
}));

vi.mock("@/components/modals/ChatGPTImportModal", () => ({
  ChatGPTImportModal: ({ open }: { open: boolean }) =>
    open ? <section data-testid="chatgpt-import-modal">ChatGPT Import</section> : null,
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

  test("renders the Personal Facts tab and panel without breaking the Imprint workspace", async () => {
    const user = userEvent.setup();
    const props = createSettingsViewProps();

    render(<SettingsView {...props} />);

    expect(
      screen.getByRole("tablist", { name: "Settings tabs" })
    ).toBeInTheDocument();
    expect(screen.getByRole("tablist", { name: "Settings tabs" })).toHaveStyle({
      position: "sticky",
      top: "calc(var(--radius-micro) * 0.75)",
      paddingInline: "calc(var(--radius-micro) * 0.75)",
    });
    expect(screen.getByRole("tab", { name: "Personal Facts" })).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Imprint" }));

    expect(screen.getByText("Imprint Workspace")).toBeInTheDocument();
    expect(screen.getByTestId("imprint-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("mock-imprint-review")).toBeInTheDocument();
    expect(screen.getByTestId("mock-system-prompt-inspector")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Imprint" })).toHaveAttribute(
      "aria-selected",
      "true"
    );

    await user.click(screen.getByRole("tab", { name: "Personal Facts" }));

    expect(
      screen.getByRole("tabpanel", { name: "Personal Facts" })
    ).toBeInTheDocument();
    expect(screen.getByTestId("mock-persona-settings")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Personal Facts" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
  });

  test("restores the Personal Facts tab after remounting when it was last active", async () => {
    const user = userEvent.setup();
    const props = createSettingsViewProps();
    const { unmount } = render(<SettingsView {...props} />);

    await user.click(screen.getByRole("tab", { name: "Personal Facts" }));

    await waitFor(() => {
      expect(window.sessionStorage.getItem("cfy.settingsTab")).toBe(
        "personalFacts"
      );
    });

    unmount();
    render(<SettingsView {...props} />);

    expect(screen.getByRole("tab", { name: "Personal Facts" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(
      screen.getByRole("tabpanel", { name: "Personal Facts" })
    ).toBeInTheDocument();
  });

  test("keeps the import surface scoped to the Data tab and isolates the scroll body", async () => {
    const user = userEvent.setup();
    const props = createSettingsViewProps();

    render(<SettingsView {...props} />);

    const scrollBody = screen.getByTestId(
      "settings-panel-scroll-body"
    ) as HTMLDivElement;
    const content = screen.getByTestId(
      "settings-panel-content"
    ) as HTMLDivElement;

    expect(
      screen.queryByRole("button", { name: "Import ChatGPT history" })
    ).not.toBeInTheDocument();
    expect(scrollBody).toHaveClass("overflow-auto", "justify-center");
    expect(content).toHaveClass("max-w-[72rem]", "w-full", "min-w-0");

    await user.click(screen.getByRole("tab", { name: "Data" }));
    expect(
      screen.getByRole("button", { name: "Import ChatGPT history" })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Appearance" }));

    expect(
      screen.queryByRole("button", { name: "Import ChatGPT history" })
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Data" }));
    expect(
      screen.getByRole("button", { name: "Import ChatGPT history" })
    ).toBeInTheDocument();

    for (const tabName of ["Appearance", "Imprint", "Connectors", "Personal Facts"]) {
      await user.click(screen.getByRole("tab", { name: tabName }));
      expect(scrollBody).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: "Import ChatGPT history" })
      ).not.toBeInTheDocument();
    }
  });

  test("falls back safely when the persisted tab is invalid", () => {
    window.sessionStorage.setItem("cfy.settingsTab", "definitely-not-a-tab");

    const props = createSettingsViewProps();
    render(<SettingsView {...props} />);

    expect(screen.getByRole("tab", { name: "Appearance" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
  });
});
