import { beforeEach, describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

import AppShell from "@/components/persona/layout/AppShell";

vi.mock("@/lib/authState", () => ({
  checkAuthGate: () => true,
  useAuthState: () => ({ user: null, token: null, loading: false }),
}));

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({ connected: false, lastEvent: null }),
}));

vi.mock("@/hooks/useRuntimeHealth", () => ({
  default: () => ({ healthy: false, checkedAt: null }),
}));

vi.mock("@/hooks/useWallpaperUrl", () => ({
  useWallpaperUrl: () => null,
}));

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
  window.history.pushState({}, "", "/");
});

function renderAppShell() {
  return render(
    <AppShell startupLocked={false} startupOverlay={null} />
  );
}

describe("Persona Studio Shell Integration", () => {
  it("renders Persona Studio navigation pill in the app shell", async () => {
    renderAppShell();

    const personaStudioPill = screen.getByRole("button", { name: /persona studio/i });
    expect(personaStudioPill).toBeInTheDocument();
  });

  it("renders Persona Studio page content when navigating to it", async () => {
    const user = userEvent.setup();
    renderAppShell();

    const personaStudioPill = screen.getByRole("button", { name: /persona studio/i });
    await user.click(personaStudioPill);

    expect(screen.getByText(/configure runtime persona profiles/i)).toBeInTheDocument();
  });

  it("renders the profile list panel when Persona Studio is active", async () => {
    const user = userEvent.setup();
    renderAppShell();

    await user.click(screen.getByRole("button", { name: /persona studio/i }));

    expect(screen.getByText("Profiles")).toBeInTheDocument();
  });

  it("renders the editor tabs when Persona Studio is active", async () => {
    const user = userEvent.setup();
    renderAppShell();

    await user.click(screen.getByRole("button", { name: /persona studio/i }));

    expect(screen.getByRole("button", { name: /identity/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /model/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /voice/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /prompt/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /tools/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retrieval/i })).toBeInTheDocument();
  });

  it("renders diagnostics panel when Persona Studio is active", async () => {
    const user = userEvent.setup();
    renderAppShell();

    await user.click(screen.getByRole("button", { name: /persona studio/i }));

    expect(screen.getByText("Diagnostics")).toBeInTheDocument();
    expect(screen.getByText("Save Status")).toBeInTheDocument();
    expect(screen.getByText("Unsaved Changes")).toBeInTheDocument();
    expect(screen.getByText("Effective Config")).toBeInTheDocument();
    expect(screen.getByText("Debug Log")).toBeInTheDocument();
  });

  it("does not render chat composer elements in Persona Studio", async () => {
    const user = userEvent.setup();
    renderAppShell();

    await user.click(screen.getByRole("button", { name: /persona studio/i }));

    expect(screen.getByTestId("persona-studio-framecard")).toBeInTheDocument();
    expect(screen.queryByTestId("composer-input")).not.toBeInTheDocument();
  });

  it("renders Generation Top K and Retrieval Top K as separate fields", async () => {
    const user = userEvent.setup();
    renderAppShell();

    await user.click(screen.getByRole("button", { name: /persona studio/i }));
    await user.click(screen.getByRole("button", { name: /model/i }));

    expect(screen.getByText("Generation Top K", { selector: "label" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /retrieval/i }));

    expect(screen.getByText("Retrieval Top K", { selector: "label" })).toBeInTheDocument();
    expect(screen.getByText(/distinct from generation top k/i)).toBeInTheDocument();
  });

  it("can switch between profile tabs", async () => {
    const user = userEvent.setup();
    renderAppShell();

    await user.click(screen.getByRole("button", { name: /persona studio/i }));

    const codeAssistantCard = screen.getAllByText("Code Assistant")[0]?.closest("button");
    if (codeAssistantCard) {
      await user.click(codeAssistantCard);
    }
    expect(screen.getByTestId("persona-studio-framecard")).toBeInTheDocument();
  });

  it("renders Save, Save As New, and Reset controls", async () => {
    const user = userEvent.setup();
    renderAppShell();

    await user.click(screen.getByRole("button", { name: /persona studio/i }));

    expect(screen.getByRole("button", { name: /save as new/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^reset$/i })).toBeInTheDocument();
  });

  it("renders a truthful matrix for current Persona Studio controls", async () => {
    const user = userEvent.setup();
    renderAppShell();

    await user.click(screen.getByRole("button", { name: /persona studio/i }));

    expect(screen.getByText("Truth Matrix")).toBeInTheDocument();

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

    expect(getRowValues("Persona Name")).toEqual(["Yes", "Yes", "Yes", "No", "No"]);
    expect(getRowValues("Generation Top K")).toEqual(["Yes", "Yes", "Yes", "No", "No"]);
    expect(getRowValues("Retrieval Top K")).toEqual(["Yes", "Yes", "Yes", "No", "No"]);
    expect(getRowValues("Voice Enabled")).toEqual(["Yes", "Yes", "Yes", "No", "No"]);
  });
});
