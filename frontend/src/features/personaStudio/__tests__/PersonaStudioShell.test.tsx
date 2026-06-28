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
    expect(screen.getByTestId("persona-studio-profile-selector")).toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-profile-selector-trigger")).toHaveTextContent(
      /guardian default/i
    );
    expect(screen.getByRole("button", { name: /^save profile$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save as new profile/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reset profile changes/i })).toBeInTheDocument();
    expect(screen.queryByTestId("composer-shell")).not.toBeInTheDocument();
    expect(screen.queryByTestId("chat-conversation-lane")).not.toBeInTheDocument();
    expect(screen.queryByTestId("composer-input")).not.toBeInTheDocument();
  });

  it("renders the right rail with the Preview tab default", () => {
    renderAppShell();

    expect(screen.getByTestId("persona-studio-rail")).toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-rail-tabs")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^preview$/i })).toHaveAttribute(
      "data-state",
      "active"
    );
    expect(screen.getByRole("button", { name: /^preview$/i })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByRole("button", { name: /^diagnostics$/i })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
    expect(screen.queryByRole("button", { name: /^profiles$/i })).not.toBeInTheDocument();
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

    await user.click(screen.getByRole("button", { name: /diagnostics/i }));
    expect(screen.getByRole("complementary", { name: /persona studio diagnostics/i })).toBeInTheDocument();
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

  it("can open and switch the profile selector", async () => {
    const user = userEvent.setup();
    renderAppShell();

    const trigger = screen.getByTestId("persona-studio-profile-selector-trigger");
    expect(trigger).toHaveTextContent(/guardian default/i);
    expect(trigger).toHaveAttribute("data-persona-studio-action-tier", "utility");
    expect(trigger.querySelector("svg")).toBeNull();

    await user.click(trigger);
    expect(screen.getByTestId("persona-studio-profile-selector-dropdown")).toBeVisible();
    expect(screen.getByTestId("persona-studio-profile-option-profile-1")).toBeVisible();
    expect(screen.getByTestId("persona-studio-profile-option-profile-2")).toBeVisible();
    expect(screen.getByTestId("persona-studio-profile-option-profile-3")).toBeVisible();

    await user.click(screen.getByTestId("persona-studio-profile-option-profile-2"));
    expect(screen.getByTestId("persona-studio-profile-selector-trigger")).toHaveTextContent(
      /code assistant/i
    );
  });

  it("renders the micro-aqua action tiers with a single reset chip", () => {
    renderAppShell();

    expect(screen.getByRole("button", { name: /^save profile$/i })).toHaveAttribute(
      "data-persona-studio-action-tier",
      "primary"
    );
    expect(screen.getByRole("button", { name: /^save as new profile$/i })).toHaveAttribute(
      "data-persona-studio-action-tier",
      "secondary"
    );
    expect(screen.getByRole("button", { name: /^reset profile changes$/i })).toHaveAttribute(
      "data-persona-studio-action-tier",
      "reset"
    );
    expect(
      screen.getByRole("button", { name: /^reset local studio data$/i })
    ).toHaveAttribute("data-persona-studio-action-tier", "reset");
    expect(
      screen.getAllByRole("button", { name: /^reset local studio data$/i })
    ).toHaveLength(1);
    expect(screen.queryByRole("button", { name: /^reset all data$/i })).not.toBeInTheDocument();
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
