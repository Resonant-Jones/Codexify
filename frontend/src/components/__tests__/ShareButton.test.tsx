import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ShareButton } from "../ShareButton";

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

vi.mock("@/lib/share-links", () => ({
  createShareLink: vi.fn(() =>
    Promise.resolve({
      ok: true,
      token: "test_token",
      url: "/share/test_token",
      expires_at: null,
    })
  ),
  copyTextWithFallback: vi.fn(() => Promise.resolve("clipboard")),
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

vi.mock("@/lib/runtimeConfig", () => ({
  resolveSharePublicUrl: (url: string) => `https://public.test${url}`,
}));

describe("ShareButton", () => {
  beforeEach(() => {
    delete (window as { location?: unknown }).location;
    (window as { location?: unknown }).location = {
      origin: "http://localhost:3000",
    };
    document.body.innerHTML = "";
    const portal = document.createElement("div");
    portal.id = "cfy-portal-root";
    document.body.appendChild(portal);
    vi.clearAllMocks();
  });

  it("renders the share button", () => {
    render(<ShareButton targetType="thread" targetId={1} />);
    const button = screen.getByRole("button", { name: /share/i });
    expect(button).toBeInTheDocument();
    expect(button).not.toBeDisabled();
  });

  it("opens the Share Sheet instead of creating a link immediately", async () => {
    const { createShareLink } = await import("@/lib/share-links");
    render(<ShareButton targetType="thread" targetId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /share/i }));
    expect(await screen.findByTestId("share-sheet")).toBeInTheDocument();
    // Opening must not create anything.
    expect(createShareLink).not.toHaveBeenCalled();
  });

  it("creates nothing when the sheet is opened and closed without an action", async () => {
    const user = userEvent.setup();
    const { createShareLink } = await import("@/lib/share-links");
    render(<ShareButton targetType="thread" targetId={1} />);
    await user.click(screen.getByRole("button", { name: /share/i }));
    await screen.findByTestId("share-sheet");
    await user.click(screen.getByLabelText("Close Share"));
    expect(screen.queryByTestId("share-sheet")).not.toBeInTheDocument();
    expect(createShareLink).not.toHaveBeenCalled();
  });

  it("Copy Link creates exactly one share token and copies the URL", async () => {
    const user = userEvent.setup();
    const { createShareLink, copyTextWithFallback } = await import(
      "@/lib/share-links"
    );
    render(<ShareButton targetType="thread" targetId={42} />);
    await user.click(screen.getByRole("button", { name: /share/i }));
    await user.click(await screen.findByTestId("share-action-copy"));
    await waitFor(() => {
      expect(createShareLink).toHaveBeenCalledTimes(1);
    });
    expect(createShareLink).toHaveBeenCalledWith("thread", 42);
    await waitFor(() => {
      expect(copyTextWithFallback).toHaveBeenCalledWith(
        "https://public.test/share/test_token"
      );
    });
  });

  it("surfaces Copy Link failure honestly", async () => {
    const user = userEvent.setup();
    const { createShareLink } = await import("@/lib/share-links");
    vi.mocked(createShareLink).mockRejectedValueOnce(
      new Error("Failed to create share link: 404")
    );
    render(<ShareButton targetType="thread" targetId={999} />);
    await user.click(screen.getByRole("button", { name: /share/i }));
    await user.click(await screen.findByTestId("share-action-copy"));
    expect(
      await screen.findByText(/Failed to create share link/)
    ).toBeInTheDocument();
  });
});
