import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { SettingsView } from "@/features/settings/SettingsView";
import { SETTINGS_DENSITY } from "@/features/settings/settingsDensityContract";
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
    setSurfaceDepth: vi.fn(),
    setSurfaceWarmth: vi.fn(),
    setUserName: vi.fn(),
    setWallpaper: vi.fn(),
    surfaceDepth: 50,
    surfaceWarmth: 0,
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
    expect(
      screen.queryByTestId("mock-persona-settings")
    ).not.toBeInTheDocument();
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
    const appearanceSurface = screen.getByTestId(
      "settings-appearance-surface"
    );

    expect(
      screen.queryByRole("button", { name: "Import ChatGPT history" })
    ).not.toBeInTheDocument();
    expect(scrollBody).toHaveClass("overflow-auto", "justify-center");
    expect(scrollBody.parentElement).toHaveStyle({
      gap: SETTINGS_DENSITY.dockContentGap,
    });
    expect(content).toHaveClass("w-full", "min-w-0");
    expect(content).toHaveClass("min-h-full");
    expect(content).toHaveAttribute("data-layout", "settings-content-grid");
    expect(content).toHaveStyle({ maxWidth: "72rem" });
    expect(appearanceSurface).toHaveClass(
      "flex",
      "flex-1",
      "flex-col",
      "justify-start",
      "min-w-0"
    );
    for (const tabButton of screen.getAllByRole("tab")) {
      expect(tabButton).toHaveClass("pill-tab", "min-w-max", "shrink-0");
      expect(tabButton).not.toHaveClass("lg:flex-1", "lg:min-w-0");
      expect(tabButton).toHaveStyle({ minWidth: "7.5rem" });
    }

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

  test("shows the System Docs boundary copy without turning Data into a project corpus lane", async () => {
    const user = userEvent.setup();
    const props = createSettingsViewProps();

    render(<SettingsView {...props} />);

    await user.click(screen.getByRole("tab", { name: "Data" }));

    expect(
      screen.getByTestId("settings-system-docs-surface")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/constitutional overlays for the assistant prompt/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/cloud-backed usage/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Project Knowledge Base surface in the project menu/i)
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/project corpus lane/i)
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Import ChatGPT history" })
    ).toBeInTheDocument();
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

  test("exposes the Material Controls section with both surface sliders", () => {
    const props = createSettingsViewProps();
    render(<SettingsView {...props} />);

    const materialSection = screen.getByTestId("material-controls-section");
    expect(materialSection).toBeInTheDocument();
    expect(
      within(materialSection).getByText("Material Controls")
    ).toBeInTheDocument();

    const depthSlider = screen.getByTestId("surface-depth-slider");
    const warmthSlider = screen.getByTestId("surface-warmth-slider");
    expect(depthSlider).toBeInTheDocument();
    expect(depthSlider).toHaveAttribute("type", "range");
    expect(depthSlider.style.accentColor).toBe("var(--accent)");
    expect(warmthSlider).toBeInTheDocument();
    expect(warmthSlider).toHaveAttribute("type", "range");
    expect(warmthSlider.style.accentColor).toBe("var(--accent)");
  });

  test("exposes the responsive Appearance grid and preserves full-width wide panels", async () => {
    const user = userEvent.setup();
    const props = createSettingsViewProps();
    render(<SettingsView {...props} />);

    const appearanceGrid = screen.getByTestId("settings-appearance-grid");
    expect(appearanceGrid).toHaveClass("grid", "grid-cols-1", "lg:grid-cols-2");
    expect(appearanceGrid).toHaveAttribute(
      "data-layout-columns",
      "responsive-two-column"
    );
    expect(
      Array.from(document.querySelectorAll("style")).some((style) =>
        style.textContent?.includes(
          '#settings-panel-appearance [data-layout-columns="responsive-two-column"]'
        ) && style.textContent?.includes("@media (min-width: 64rem)")
      )
    ).toBe(true);

    expect(
      screen.getByTestId("settings-appearance-content-column")
    ).toHaveAttribute("data-layout-span", "column");
    expect(
      screen.getByTestId("settings-appearance-controls-column")
    ).toHaveAttribute("data-layout-span", "column");

    await user.click(screen.getByRole("tab", { name: "Imprint" }));
    expect(screen.getByTestId("imprint-workspace")).toHaveAttribute(
      "data-layout-span",
      "full"
    );

    await user.click(screen.getByRole("tab", { name: "Data" }));
    expect(screen.getByTestId("settings-data-surface")).toHaveAttribute(
      "data-layout-span",
      "full"
    );
  });

  test("orders Material Controls between File Type Colors and Dashboard Layout", () => {
    const props = createSettingsViewProps();
    const { container } = render(<SettingsView {...props} />);

    const surface = container.querySelector(
      '[data-testid="settings-appearance-surface"]'
    );
    expect(surface).not.toBeNull();
    if (!surface) return;

    const fileTypeTitle = screen.getByText("File Type Colors");
    const materialTitle = screen.getByText("Material Controls");
    const dashboardTitle = screen.getByText("Dashboard Layout");

    const fileTypeSection = fileTypeTitle.closest("div[class*='space-y']");
    const materialSection = materialTitle.closest(
      '[data-testid="material-controls-section"]'
    );
    const dashboardSection = dashboardTitle.closest("div[class*='space-y']");

    expect(fileTypeSection).not.toBeNull();
    expect(materialSection).not.toBeNull();
    expect(dashboardSection).not.toBeNull();
    if (!fileTypeSection || !materialSection || !dashboardSection) return;

    const position =
      fileTypeSection.compareDocumentPosition(materialSection) &
      Node.DOCUMENT_POSITION_FOLLOWING;
    const materialFollowsDashboard =
      materialSection.compareDocumentPosition(dashboardSection) &
      Node.DOCUMENT_POSITION_FOLLOWING;
    expect(position).toBeTruthy();
    expect(materialFollowsDashboard).toBeTruthy();
  });

  test("does not retain the legacy Surface Tuning heading", () => {
    const props = createSettingsViewProps();
    render(<SettingsView {...props} />);

    expect(screen.queryByText("Surface Tuning")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("surface-tuning-section")
    ).not.toBeInTheDocument();
  });

  test("renders the Appearance canvas as visually borderless while retaining structural classes", () => {
    const props = createSettingsViewProps();
    render(<SettingsView {...props} />);

    const appearanceSurface = screen.getByTestId(
      "settings-appearance-surface"
    );

    expect(appearanceSurface).toHaveAttribute("data-variant", "canvas");

    // Inline style assertions (bypass jsdom computed-style normalization)
    expect(appearanceSurface.style.borderColor).toBe("transparent");
    expect(appearanceSurface.style.background).toBe("transparent");
    expect(appearanceSurface.style.boxShadow).toBe("none");

    expect(appearanceSurface).toHaveClass(
      "flex",
      "flex-1",
      "flex-col",
      "justify-start",
      "min-w-0"
    );

    // Appearance controls remain present
    expect(screen.getByText("Theme")).toBeInTheDocument();
    expect(screen.getByText("Material Controls")).toBeInTheDocument();
    expect(screen.getByText("Dashboard Layout")).toBeInTheDocument();
  });

  test("retains card treatment on Imprint and other non-Appearance tabs", async () => {
    const user = userEvent.setup();
    const props = createSettingsViewProps();
    render(<SettingsView {...props} />);

    // Imprint tab
    await user.click(screen.getByRole("tab", { name: "Imprint" }));

    const imprintSurface = screen.getByTestId("settings-system-surface");
    expect(imprintSurface).toHaveAttribute("data-variant", "card");
    expect(imprintSurface).not.toHaveStyle({ borderColor: "transparent" });
    expect(imprintSurface).not.toHaveStyle({ background: "transparent" });

    // Nested imprint workspace also retains card default
    const imprintWorkspace = screen.getByTestId("imprint-workspace");
    expect(imprintWorkspace).toHaveAttribute("data-variant", "card");

    // Data tab
    await user.click(screen.getByRole("tab", { name: "Data" }));
    const dataSurface = screen.getByTestId("settings-data-surface");
    expect(dataSurface).toHaveAttribute("data-variant", "card");
    expect(dataSurface).not.toHaveStyle({ borderColor: "transparent" });
  });

  test("preserves Data-tab import scoping with canvas variant active", async () => {
    const user = userEvent.setup();
    const props = createSettingsViewProps();

    render(<SettingsView {...props} />);

    // Start on Appearance (canvas variant) — verify import button not present
    expect(
      screen.queryByRole("button", { name: "Import ChatGPT history" })
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Data" }));
    expect(
      screen.getByRole("button", { name: "Import ChatGPT history" })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Appearance" }));
    expect(
      screen.queryByRole("button", { name: "Import ChatGPT history" })
    ).not.toBeInTheDocument();
  });

  test("all five Appearance sliders use the canonical SettingsRangeControl with var(--accent)", () => {
    const props = createSettingsViewProps();
    render(<SettingsView {...props} />);

    const sliderTestIds = [
      "surface-depth-slider",
      "surface-warmth-slider",
      "dashboard-thread-rows-slider",
      "depth-slider",
      "fade-slider",
    ];

    for (const testId of sliderTestIds) {
      const slider = screen.getByTestId(testId);
      expect(slider).toHaveAttribute("type", "range");
      expect(slider.style.accentColor).toBe("var(--accent)");
      expect(slider.style.accentColor).not.toContain("blue");
      expect(slider.style.accentColor).not.toContain("#");
    }
  });

  test("groups Depth and Fade under Background Treatment", () => {
    const props = createSettingsViewProps();
    render(<SettingsView {...props} />);

    const bgSection = screen.getByTestId("background-treatment-section");
    expect(bgSection).toBeInTheDocument();
    expect(
      within(bgSection).getByText("Background Treatment")
    ).toBeInTheDocument();

    const depthSlider = screen.getByTestId("depth-slider");
    const fadeSlider = screen.getByTestId("fade-slider");
    expect(bgSection).toContainElement(depthSlider);
    expect(bgSection).toContainElement(fadeSlider);

    // Values remain present
    expect(bgSection.textContent).toContain("0.4");
    expect(bgSection.textContent).toContain("0.2");
  });

  test("retains existing labels and hierarchy for Material Controls and Dashboard Layout", () => {
    const props = createSettingsViewProps();
    render(<SettingsView {...props} />);

    expect(screen.getByText("Material Controls")).toBeInTheDocument();
    expect(screen.getByText("Dashboard Layout")).toBeInTheDocument();
    expect(screen.getByText("Surface Depth")).toBeInTheDocument();
    expect(screen.getByText("Surface Warmth")).toBeInTheDocument();
    expect(screen.getByText(/Recent thread rows/)).toBeInTheDocument();

    // Dashboard Layout slider uses canonical accent
    const rowsSlider = screen.getByTestId("dashboard-thread-rows-slider");
    expect(rowsSlider.style.accentColor).toBe("var(--accent)");
  });
});
