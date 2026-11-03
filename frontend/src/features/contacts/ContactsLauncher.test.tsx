/**
 * The launcher's unread badge.
 *
 * The launcher is a *presentation surface*, not a second notification store:
 * it renders the same caller-local read projection the Inbox badges read,
 * out of the shared People state owner.  These tests drive the REAL state
 * owner, because a mocked projection cannot show whether the launcher can
 * load and display that projection on its own.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ContactsLauncher from "./ContactsLauncher";
import {
  fetchDirectMessageConversations,
  type DirectMessageConversation,
} from "@/lib/direct-messages";

vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  useRuntimeRouteCapability: (label: string) => ({
    mounted: ["direct_messages"],
    declared: {},
    ready: true,
    state: label === "direct_messages" ? "available" : "unavailable",
  }),
  useRuntimeRouteCapabilities: () => ({
    mounted: ["direct_messages"],
    declared: {},
    ready: true,
    states: { direct_messages: "available" },
  }),
  ensureRuntimeRouteCapabilitiesLoaded: () => Promise.resolve(),
  getRuntimeRouteCapabilityState: () => "available",
  markRuntimeRouteUnavailable: () => {},
  markRuntimeRouteUnavailableIfNotFound: () => false,
  __resetRuntimeRouteCapabilitiesForTests: () => {},
}));

vi.mock("@/lib/direct-messages", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/direct-messages")>();
  return {
    ...actual,
    fetchDirectMessageConversations: vi.fn(),
    fetchDirectMessageMessages: vi.fn(() => Promise.resolve([])),
    fetchDirectMessageConversation: vi.fn(),
    markDirectMessageConversationRead: vi.fn(),
    normalizeDirectMessageError: (error: unknown) =>
      error instanceof Error ? error : new Error("request failed"),
  };
});

function conversation(
  id: string,
  unreadCount: number,
): DirectMessageConversation {
  return {
    conversation_id: id,
    relationship_id: `rel-${id}`,
    kind: "direct",
    created_at: "2026-09-01T00:00:00Z",
    latest_activity_at: "2026-09-01T01:00:00Z",
    participants: [],
    peer: {
      node_id: "node-local",
      profile_id: "profile-bob",
      username: "bob",
      username_state: "active",
      display_name: "Bob Tester",
      avatar_url: null,
    },
    origin: {
      created_by_profile_id: "profile-bob",
      origin_project_id: null,
      origin_thread_id: null,
      created_at: "2026-09-01T00:00:00Z",
    },
    placement: { project_id: null, created_at: null, updated_at: null },
    latest_message: null,
    unread_count: unreadCount,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ContactsLauncher unread badge", () => {
  it("shows the shared projection's unread total without opening People", async () => {
    vi.mocked(fetchDirectMessageConversations).mockResolvedValue([
      conversation("c-1", 3),
      conversation("c-2", 2),
    ]);

    render(<ContactsLauncher className="pill-tab" />);

    // The badge must appear on its own: the People window is never opened
    // here, so the count can only come from the launcher's own projection
    // load through the shared state owner.
    const badge = await screen.findByTestId("contacts-launcher-unread-badge");
    expect(badge).toHaveTextContent("5");
    expect(
      screen.getByRole("button", { name: "People (5 unread messages)" }),
    ).toBeInTheDocument();
  });

  it("loads the projection once, not once per surface", async () => {
    vi.mocked(fetchDirectMessageConversations).mockResolvedValue([
      conversation("c-1", 1),
    ]);

    render(<ContactsLauncher className="pill-tab" />);

    await waitFor(() => {
      expect(fetchDirectMessageConversations).toHaveBeenCalled();
    });
    expect(fetchDirectMessageConversations).toHaveBeenCalledTimes(1);
  });

  it("shows no badge when the shared projection has nothing unread", async () => {
    vi.mocked(fetchDirectMessageConversations).mockResolvedValue([
      conversation("c-1", 0),
    ]);

    render(<ContactsLauncher className="pill-tab" />);

    await waitFor(() => {
      expect(fetchDirectMessageConversations).toHaveBeenCalled();
    });
    expect(
      screen.queryByTestId("contacts-launcher-unread-badge"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "People" }),
    ).toBeInTheDocument();
  });
});
