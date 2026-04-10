import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useLayoutEffect, useRef, type ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { SettingsView } from "@/features/settings/SettingsView";
import type { ExtColors, ThemeMode } from "@/types/ui";

const useConnectorsMock = vi.fn();
let settingsShellViewport: null | {
  addEventListener: (type: string, listener: () => void, options?: { passive?: boolean }) => void;
  clientHeight: number;
  currentScrollTop: number;
  dispatchScroll: () => void;
  removeEventListener: (type: string, listener: () => void) => void;
  scrollHeight: number;
  scrollWrites: number[];
  scrollTop: number;
} = null;
let lastShellTabChange: null | ((tab: string) => void) = null;

vi.mock("@/features/connectors/useConnectors", () => ({
  useConnectors: () => useConnectorsMock(),
}));

vi.mock("@/features/settings/components/ImprintReviewPanel", () => ({
  default: () => (
    <section data-testid="mock-imprint-review">Imprint Review</section>
  ),
}));

vi.mock("@/features/settings/components/PersonaSettingsPanel", () => ({
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

vi.mock("@/features/settings/components/SettingsPanelShell", () => {
  const tabs = [
    { id: "appearance", label: "Appearance" },
    { id: "system", label: "Imprint" },
    { id: "connectors", label: "Connectors" },
    { id: "data", label: "Data" },
    { id: "personalFacts", label: "Personal Facts" },
  ] as const;

  return {
    default: ({
      activeTab,
      children,
      onTabChange,
      scrollContainerRef,
    }: {
      activeTab: string;
      children: ReactNode;
      onTabChange: (tab: string) => void;
      scrollContainerRef?: { current: unknown };
      }) => {
      const viewportRef = useRef<NonNullable<typeof settingsShellViewport> | null>(
        null
      );

      if (!viewportRef.current) {
        const listeners = new Set<() => void>();
        let currentScrollTop = 0;
        viewportRef.current = {
          addEventListener: (type, listener) => {
            if (type === "scroll") {
              listeners.add(listener);
            }
          },
          clientHeight: 100,
          dispatchScroll: () => {
            for (const listener of listeners) {
              listener();
            }
          },
          removeEventListener: (type, listener) => {
            if (type === "scroll") {
              listeners.delete(listener);
            }
          },
          scrollHeight: 500,
          scrollWrites: [],
          get scrollTop() {
            return currentScrollTop;
          },
          set scrollTop(value: number) {
            currentScrollTop = Number(value) || 0;
            this.scrollWrites.push(currentScrollTop);
          },
        };
      }

      useLayoutEffect(() => {
        if (scrollContainerRef) {
          scrollContainerRef.current = viewportRef.current;
        }
        settingsShellViewport = viewportRef.current;
        lastShellTabChange = onTabChange;
        return () => {
          if (scrollContainerRef) {
            scrollContainerRef.current = null;
          }
        };
      }, [scrollContainerRef]);

      return (
        <div data-testid="settings-panel-shell">
          <div role="tablist" aria-label="Settings tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                role="tab"
                aria-selected={activeTab === tab.id}
                type="button"
                onClick={() => onTabChange(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          {children}
        </div>
      );
    },
  };
});

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
    settingsShellViewport = null;
    lastShellTabChange = null;
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

    await user.click(screen.getByRole("tab", { name: "Imprint" }));

    expect(screen.getByText("Local Preview")).toBeInTheDocument();
    expect(screen.getByTestId("imprint-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("mock-imprint-review")).toBeInTheDocument();
    expect(screen.getByTestId("mock-persona-settings")).toBeInTheDocument();
    expect(screen.getByTestId("mock-system-prompt-inspector")).toBeInTheDocument();
  });

  test("keeps the import surface scoped to the Data tab and restores tab scroll positions", async () => {
    const user = userEvent.setup();
    const props = createSettingsViewProps();

    render(<SettingsView {...props} />);
    await waitFor(() => expect(settingsShellViewport).not.toBeNull());
    expect(lastShellTabChange).not.toBeNull();

    await user.click(screen.getByRole("tab", { name: "Data" }));
    expect(
      screen.getByRole("button", { name: "Import ChatGPT history" })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Import ChatGPT history" }));
    expect(screen.getByTestId("chatgpt-import-modal")).toBeInTheDocument();

    settingsShellViewport!.scrollTop = 180;
    settingsShellViewport!.dispatchScroll();
    lastShellTabChange!("appearance");
    settingsShellViewport!.scrollTop = 12;
    settingsShellViewport!.dispatchScroll();
    lastShellTabChange!("data");

    await waitFor(() =>
      expect(
        settingsShellViewport!.scrollWrites.filter((value) => value === 180)
      ).toHaveLength(2)
    );
    expect(
      screen.getByRole("button", { name: "Import ChatGPT history" })
    ).toBeInTheDocument();
    expect(screen.getByTestId("chatgpt-import-modal")).toBeInTheDocument();

    for (const tabName of ["Appearance", "Imprint", "Connectors", "Personal Facts"]) {
      await user.click(screen.getByRole("tab", { name: tabName }));
      expect(
        screen.queryByRole("button", { name: "Import ChatGPT history" })
      ).not.toBeInTheDocument();
      expect(screen.queryByTestId("chatgpt-import-modal")).not.toBeInTheDocument();
    }
  });
});
