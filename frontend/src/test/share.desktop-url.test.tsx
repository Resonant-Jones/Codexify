import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ShareButton } from "@/components/ShareButton";
import { initRuntimeConfig } from "@/lib/runtimeConfig";

vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  useRuntimeRouteCapability: () => ({
    mounted: ["direct_messages"],
    declared: {},
    ready: true,
    state: "available",
  }),
  useRuntimeRouteCapabilities: () => ({ states: {} }),
  ensureRuntimeRouteCapabilitiesLoaded: () => Promise.resolve(),
  getRuntimeRouteCapabilityState: () => "available",
  markRuntimeRouteUnavailable: () => {},
  markRuntimeRouteUnavailableIfNotFound: () => false,
  __resetRuntimeRouteCapabilitiesForTests: () => {},
}));

vi.mock("@/lib/direct-messages", () => ({
  searchDirectMessageProfiles: vi.fn(),
  resolveDirectMessageRelationship: vi.fn(),
  fetchRelationshipConversations: vi.fn(),
  createDirectMessageConversation: vi.fn(),
  sendDirectMessage: vi.fn(),
  fetchThreadProjectScope: vi.fn(),
  peerPresentationLabel: vi.fn(),
}));

vi.mock("@/lib/share-links", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/share-links")>();
  return {
    ...actual,
    createShareLink: vi.fn(async () => ({
      ok: true,
      token: "abc123",
      url: "/share/abc123",
      expires_at: null,
    })),
    copyTextWithFallback: vi.fn(async () => "clipboard"),
  };
});

const invokeMock = vi.fn();

describe("ShareButton desktop public URL", () => {
  beforeEach(async () => {
    localStorage.clear();
    delete (window as any).__TAURI_INTERNALS__;
    (window as any).__TAURI_IPC__ = {};
    (window as any).__CFY_TAURI_CORE__ = { invoke: invokeMock };
    localStorage.setItem("cfy.desktop.sharePublicBaseUrl", "https://public.codexify.test");
    localStorage.setItem("cfy.desktop.backendBaseUrl", "http://127.0.0.1:8888");

    invokeMock.mockResolvedValue({
      mode: "tauri",
      backendBaseUrl: "http://127.0.0.1:8888",
      apiBaseUrl: "http://127.0.0.1:8888/api",
      sseUrl: "http://127.0.0.1:8888/api/events",
      sharePublicBaseUrl: "https://public.codexify.test",
      authMode: "local",
    });

    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });

    document.body.innerHTML = "";
    const portal = document.createElement("div");
    portal.id = "cfy-portal-root";
    document.body.appendChild(portal);

    await initRuntimeConfig({ force: true });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    delete (window as any).__CFY_TAURI_CORE__;
  });

  it("copies the share URL using the configured public base URL via the sheet", async () => {
    const user = userEvent.setup();
    const { copyTextWithFallback } = await import("@/lib/share-links");
    render(<ShareButton targetType="thread" targetId={12} />);

    await user.click(screen.getByRole("button", { name: /share/i }));
    await user.click(await screen.findByTestId("share-action-copy"));

    await waitFor(() => {
      expect(copyTextWithFallback).toHaveBeenCalledWith(
        "https://public.codexify.test/share/abc123"
      );
    });
  });
});
