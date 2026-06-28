import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

import AppShell from "@/components/persona/layout/AppShell";
import {
  LIVE_EVENT_CONNECTION_STATES,
  RUNTIME_HEALTH_STATUSES,
} from "@/contracts/runtimeTokens";
import {
  personaStudioApiMock,
  resetPersonaStudioApiMock,
} from "./personaStudioApiMock";

vi.mock("@/lib/authState", () => ({
  checkAuthGate: () => true,
  useAuthState: () => ({ user: null, token: null, loading: false }),
}));

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({ connected: false, lastEvent: null }),
}));

vi.mock("@/hooks/useRuntimeHealth", () => ({
  default: () => ({
    status: RUNTIME_HEALTH_STATUSES.UNAVAILABLE,
    failureKind: null,
    llmDetail: null,
    lastSuccessAt: null,
    backendReachable: null,
    chatHealthy: null,
    llmHealthy: null,
    liveEventsStatus: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
    lastCheckedAt: null,
    lastFailedAt: null,
    stale: false,
    diagnostics: {
      resolvedApiBaseUrl: null,
      resolvedApiBaseUrlSource: "unknown",
      apiKeyPresent: false,
      apiKeySource: "unknown",
      hydrationState: "ready",
      nativeCommandStatus: null,
      authSource: "unknown",
      chat: {
        endpoint: "/health/chat",
        httpStatus: null,
        transportErrorClass: null,
        parsedStatus: null,
        parsedOk: null,
        detailsStatus: null,
        detailsOk: null,
        providerRuntimeAvailable: null,
        endpointResolutionState: null,
        failureReason: null,
      },
      llm: {
        endpoint: "/api/health/llm",
        httpStatus: null,
        transportErrorClass: null,
        parsedStatus: null,
        parsedOk: null,
        detailsStatus: null,
        detailsOk: null,
        providerRuntimeAvailable: null,
        endpointResolutionState: null,
        failureReason: null,
      },
      liveEvents: {
        connectionState: LIVE_EVENT_CONNECTION_STATES.CONNECTED,
        connected: true,
        statusUpdatedAt: null,
      },
      failureKind: null,
      lastSuccessAt: null,
      lastFailedAt: null,
      lastCheckedAt: null,
      currentComputedStateSource: "fallback",
    },
  }),
}));

vi.mock("@/hooks/useWallpaperUrl", () => ({
  useWallpaperUrl: () => null,
}));

vi.mock("@/features/personaStudio/personaStudioApi", async () =>
  (await import("./personaStudioApiMock")).personaStudioApiMock
);

vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  useRuntimeRouteCapability: () => ({ ready: true, state: "available" }),
  SUPPORTED_PROFILE_ROUTE_LABELS: { CODEX: "codex", IMPRINT: "imprint", CONNECTORS: "connectors" },
}));

vi.mock("@/state/session/SessionSpine", () => ({
  SessionSpine: {
    getRegisteredSpine: () => null,
    subscribeActiveSpine: () => () => {},
  },
}));

beforeEach(() => {
  window.localStorage.clear();
  window.history.pushState({}, "", "/persona-studio");
  resetPersonaStudioApiMock();
});

function renderAppShell() {
  return render(
    <AppShell startupLocked={false} startupOverlay={null} />
  );
}

describe("Persona Studio Shell Integration", () => {
  it("renders the Persona Studio route in the app shell", async () => {
    renderAppShell();

    expect(screen.getByRole("heading", { name: "Persona Studio" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /persona studio editor/i })).toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-rail")).toBeInTheDocument();
    expect(screen.getByTestId("persona-preview-panel")).toBeInTheDocument();
  });

  it("renders Persona Studio hierarchy directly from the route", () => {
    renderAppShell();

    expect(screen.getByRole("heading", { name: "Persona Studio" })).toBeInTheDocument();
    expect(screen.getByText(/configure reusable agent profiles\./i)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /persona studio editor/i })).toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-rail")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /identity/i })).toHaveAttribute(
      "data-state",
      "active"
    );
    // Profile selector is present
    expect(screen.getByTestId("persona-studio-profile-selector")).toBeInTheDocument();
    expect(screen.queryByTestId("composer-shell")).not.toBeInTheDocument();
    expect(screen.queryByTestId("chat-conversation-lane")).not.toBeInTheDocument();
    expect(screen.queryByTestId("composer-input")).not.toBeInTheDocument();
  });

  it("renders the right rail with the Preview tab default", () => {
    renderAppShell();

    expect(screen.getByTestId("persona-studio-rail")).toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-rail-tabs")).toBeInTheDocument();
    const previewTab = screen.getByRole("tab", { name: /^preview$/i });
    expect(previewTab).toHaveAttribute("aria-selected", "true");
    expect(previewTab).toHaveAttribute(
      "aria-controls",
      "persona-studio-rail-panel-preview"
    );

    const diagnosticsTab = screen.getByRole("tab", { name: /^diagnostics$/i });
    expect(diagnosticsTab).toHaveAttribute("aria-selected", "false");

    // Profiles tab no longer exists on the rail
    expect(screen.queryByRole("tab", { name: /^profiles$/i })).not.toBeInTheDocument();
  });

  it("renders the editor tabs when Persona Studio is active", () => {
    renderAppShell();

    expect(screen.getByRole("button", { name: /identity/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /model/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /voice/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /prompt/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /tools/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retrieval/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /truth matrix/i })).toBeInTheDocument();
  });

  it("renders diagnostics panel when Persona Studio is active", async () => {
    const user = userEvent.setup();
    renderAppShell();

    await user.click(screen.getByRole("tab", { name: /diagnostics/i }));
    const diagnosticsPanel = screen.getByTestId("persona-studio-rail-diagnostics-panel");
    expect(diagnosticsPanel).toHaveAttribute("role", "tabpanel");
    expect(diagnosticsPanel).toHaveAttribute(
      "aria-labelledby",
      "persona-studio-rail-tab-diagnostics"
    );
    expect(screen.getByText("Save Status")).toBeInTheDocument();
    expect(screen.getByText("Effective Config")).toBeInTheDocument();
    expect(screen.getByText("Debug Log")).toBeInTheDocument();
  });

  it("does not render chat composer or thread UI in Persona Studio", () => {
    renderAppShell();

    expect(screen.getByRole("region", { name: /persona studio editor/i })).toBeInTheDocument();
    expect(screen.queryByTestId("composer-input")).not.toBeInTheDocument();
    expect(screen.queryByTestId("composer-shell")).not.toBeInTheDocument();
    expect(screen.queryByTestId("chat-conversation-lane")).not.toBeInTheDocument();
  });

  it("renders Generation Top K and Retrieval Top K as separate fields", async () => {
    const user = userEvent.setup();
    renderAppShell();

    await user.click(screen.getByRole("button", { name: /model/i }));

    expect(screen.getByText("Generation Top K", { selector: "label" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /retrieval/i }));

    expect(screen.getByText("Retrieval Top K", { selector: "label" })).toBeInTheDocument();
    expect(screen.getByText(/distinct from generation top k/i)).toBeInTheDocument();
  });

  it("can select a profile from the profile selector", async () => {
    const user = userEvent.setup();
    renderAppShell();

    // Open profile selector
    const trigger = screen.getByTestId("persona-studio-profile-selector-trigger");
    await user.click(trigger);

    // Select Code Assistant
    const codeAssistantOption = screen.getByTestId("persona-studio-profile-option-profile-2");
    await user.click(codeAssistantOption);

    expect(screen.getByTestId("persona-studio-profile-selector-trigger")).toHaveTextContent(/code assistant/i);
  });

  it("renders the profile selector as a compact inline text trigger (no square tile)", () => {
    renderAppShell();

    const trigger = screen.getByTestId("persona-studio-profile-selector-trigger");
    const save = screen.getByTestId("persona-studio-action-save");

    // Visible profile name text — not icon-only
    expect(trigger).toHaveTextContent(/guardian default/i);
    expect(
      screen.getByTestId("persona-studio-profile-selector-trigger-name")
    ).toHaveTextContent(/guardian default/i);

    // Accessible label/title for selecting profile
    expect(trigger).toHaveAttribute("aria-label", expect.stringMatching(/profile:/i));
    expect(trigger).toHaveAttribute("title", expect.stringMatching(/profile:/i));

    // The trigger must not be the old oversized icon element — no SVG chevron block
    expect(trigger.querySelector("svg")).toBeNull();

    // The selector must not render a tile/card test id
    expect(
      screen.queryByTestId("persona-studio-profile-selector-tile")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("persona-studio-profile-selector-card")
    ).not.toBeInTheDocument();

    // Compact: trigger height matches action button height (no taller, no min-height override)
    const triggerRect = trigger.getBoundingClientRect();
    const saveRect = save.getBoundingClientRect();
    expect(triggerRect.height).toBeLessThanOrEqual(saveRect.height + 1);
    expect(triggerRect.height).toBeLessThan(40); // never a square tile
  });

  it("renders profile actions in the selector dropdown", async () => {
    const user = userEvent.setup();
    renderAppShell();

    // Open profile selector
    await user.click(screen.getByTestId("persona-studio-profile-selector-trigger"));

    // Profile actions are inside the dropdown
    expect(screen.getByTestId("persona-studio-action-save")).toBeVisible();
    expect(screen.getByTestId("persona-studio-action-save-as-new")).toBeVisible();
    expect(screen.getByTestId("persona-studio-action-reset")).toBeVisible();
    expect(screen.getByTestId("persona-studio-action-reset-all")).toBeVisible();
  });

  it("renders profile-level actions and the Studio reset exactly once, and not the old 'Reset All Data'", () => {
    renderAppShell();

    expect(screen.getByRole("button", { name: /^save profile$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^save as new profile$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^reset profile changes$/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^reset local studio data$/i })
    ).toBeInTheDocument();

    // Reset local Studio data must appear exactly once
    expect(
      screen.getAllByRole("button", { name: /^reset local studio data$/i })
    ).toHaveLength(1);

    // Old "Reset All Data" wording must not appear anywhere
    expect(
      screen.queryByRole("button", { name: /^reset all data$/i })
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/reset all data/i)).not.toBeInTheDocument();
  });

  it("opens a bounded scrollable profile list when the compact selector is clicked", async () => {
    const user = userEvent.setup();
    renderAppShell();

    await user.click(screen.getByTestId("persona-studio-profile-selector-trigger"));

    const list = screen.getByTestId("persona-studio-profile-selector-list");
    expect(list).toBeInTheDocument();

    // Bounded scroll container — explicit test id + overflow utility
    expect(list.className).toMatch(/overflow-y-auto/);
    expect(list.className).toMatch(/max-h-/);

    // Dropdown exposes the same available profiles
    expect(
      screen.getByTestId("persona-studio-profile-option-profile-1")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("persona-studio-profile-option-profile-2")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("persona-studio-profile-option-profile-3")
    ).toBeInTheDocument();
  });

  it("applies Persona Studio action material markers under the shell", () => {
    renderAppShell();

    const trigger = screen.getByTestId("persona-studio-profile-selector-trigger");
    const save = screen.getByTestId("persona-studio-action-save");
    const saveAsNew = screen.getByTestId("persona-studio-action-save-as-new");
    const reset = screen.getByTestId("persona-studio-action-reset");
    const resetAll = screen.getByTestId("persona-studio-action-reset-all");
    const send = screen.getByRole("button", { name: /^send$/i });
    const clear = screen.getByRole("button", { name: /clear preview session/i });

    expect(trigger).toHaveClass("ps-action-chip");
    expect(trigger).toHaveAttribute("data-ps-material", "selector");

    expect(save).toHaveAttribute("data-ps-material", "primary");
    expect(send).toHaveAttribute("data-ps-material", "primary");

    expect(saveAsNew).toHaveAttribute("data-ps-material", "secondary");
    expect(clear).toHaveAttribute("data-ps-material", "secondary");

    expect(reset).toHaveAttribute("data-ps-material", "reset");
    expect(resetAll).toHaveAttribute("data-ps-material", "reset");

    // No decorative SVGs introduced onto any action chip via the shell path
    [trigger, save, saveAsNew, reset, resetAll, send, clear].forEach((chip) => {
      expect(chip.querySelector("svg")).toBeNull();
    });
  });

  it("renders a truthful matrix for current Persona Studio controls", async () => {
    const user = userEvent.setup();
    renderAppShell();

    await user.click(screen.getByRole("button", { name: /truth matrix/i }));

    const matrix = screen.getByRole("table", { name: /persona studio truth matrix/i });

    expect(within(matrix).getByRole("columnheader", { name: /control/i })).toBeInTheDocument();
    expect(within(matrix).getByRole("columnheader", { name: /ui present/i })).toBeInTheDocument();
    expect(
      within(matrix).getByRole("columnheader", { name: /local draft state/i })
    ).toBeInTheDocument();
    expect(within(matrix).getByRole("columnheader", { name: /saved locally/i })).toBeInTheDocument();
    expect(
      within(matrix).getByRole("columnheader", { name: /backend persisted/i })
    ).toBeInTheDocument();
    expect(
      within(matrix).getByRole("columnheader", { name: /applied to runtime/i })
    ).toBeInTheDocument();

    const getRowValues = (label: string) => {
      const rowHeader = within(matrix).getByRole("rowheader", { name: label });
      const row = rowHeader.closest("tr");
      expect(row).not.toBeNull();
      return within(row as HTMLElement)
        .getAllByRole("cell")
        .map((cell) => cell.textContent?.trim());
    };

    expect(getRowValues("Persona Name")).toEqual(["Yes", "Yes", "Yes", "Yes", "Yes"]);
    expect(getRowValues("System Prompt")).toEqual(["Yes", "Yes", "Yes", "Yes", "Yes"]);
    expect(getRowValues("Model Provider")).toEqual(["Yes", "Yes", "Yes", "Yes", "Yes"]);
    expect(getRowValues("Model ID")).toEqual(["Yes", "Yes", "Yes", "Yes", "Yes"]);
    expect(getRowValues("Temperature")).toEqual(["Yes", "Yes", "Yes", "Yes", "Yes"]);
    expect(getRowValues("Generation Top K")).toEqual(["Yes", "Yes", "Yes", "No", "No"]);
    expect(getRowValues("Retrieval Top K")).toEqual(["Yes", "Yes", "Yes", "No", "No"]);
    expect(getRowValues("Voice Enabled")).toEqual(["Yes", "Yes", "Yes", "No", "No"]);
  });
});
