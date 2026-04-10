import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

describe("SettingsView", () => {
  beforeEach(() => {
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
    const props = {
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

    render(<SettingsView {...props} />);

    expect(
      screen.getByRole("tablist", { name: "Settings sections" })
    ).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Imprint" }));

    expect(screen.getByText("Local Preview")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Imprint" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByTestId("imprint-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("mock-imprint-review")).toBeInTheDocument();
    expect(screen.getByTestId("mock-persona-settings")).toBeInTheDocument();
    expect(screen.getByTestId("mock-system-prompt-inspector")).toBeInTheDocument();
  });

  test("scopes the import controls to the Data tab", async () => {
    const user = userEvent.setup();
    const props = {
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

    render(<SettingsView {...props} />);

    expect(
      screen.queryByRole("button", { name: "Import ChatGPT history" })
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Data" }));

    expect(
      screen.getByRole("button", { name: "Import ChatGPT history" })
    ).toBeInTheDocument();
  });
});
