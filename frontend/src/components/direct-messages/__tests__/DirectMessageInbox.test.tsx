import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DirectMessageInbox from "@/components/direct-messages/DirectMessageInbox";
import DirectMessagesUnavailable from "@/components/direct-messages/DirectMessagesUnavailable";
import {
  createGeneralDirectMessageConversation,
  fetchDirectMessageConversations,
  fetchDirectMessageMessages,
  fetchOwnSocialIdentity,
  resolveDirectMessageRelationship,
  searchDirectMessageProfiles,
  sendDirectMessage,
  type ConversationProjection,
  type MessageEnvelope,
  type SocialProfilePayload,
} from "@/lib/direct-messages";

vi.mock("@/lib/direct-messages", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/direct-messages")>();
  return {
    ...actual,
    fetchDirectMessageConversations: vi.fn(),
    fetchOwnSocialIdentity: vi.fn(),
    fetchDirectMessageMessages: vi.fn(),
    sendDirectMessage: vi.fn(),
    searchDirectMessageProfiles: vi.fn(),
    resolveDirectMessageRelationship: vi.fn(),
    createGeneralDirectMessageConversation: vi.fn(),
  };
});

const mockedFetchConversations = vi.mocked(fetchDirectMessageConversations);
const mockedFetchIdentity = vi.mocked(fetchOwnSocialIdentity);
const mockedFetchMessages = vi.mocked(fetchDirectMessageMessages);
const mockedSend = vi.mocked(sendDirectMessage);
const mockedSearch = vi.mocked(searchDirectMessageProfiles);
const mockedResolve = vi.mocked(resolveDirectMessageRelationship);
const mockedCreate = vi.mocked(createGeneralDirectMessageConversation);

const SELF = "self-profile";
const BOB = "peer-bob";
const CAROL = "peer-carol";
const REL_B = "rel-bob";
const REL_C = "rel-carol";

function profile(id: string, username: string): SocialProfilePayload {
  return {
    node_id: "node-local",
    profile_id: id,
    username,
    username_state: "active",
    display_name: null,
    avatar_url: null,
  };
}

const selfProfile = profile(SELF, "alice");

function conversation(
  id: string,
  relationshipId: string,
  peer: SocialProfilePayload,
  overrides: Partial<ConversationProjection> = {}
): ConversationProjection {
  return {
    conversation_id: id,
    relationship_id: relationshipId,
    kind: "direct",
    created_at: "2026-08-31T12:00:00Z",
    latest_activity_at: "2026-08-31T12:00:00Z",
    participants: [selfProfile, peer],
    origin: {
      created_by_profile_id: SELF,
      origin_project_id: null,
      origin_thread_id: null,
      created_at: "2026-08-31T12:00:00Z",
    },
    placement: {
      project_id: null,
      created_at: null,
      updated_at: null,
    },
    latest_message: null,
    ...overrides,
  };
}

const bob = profile(BOB, "bob");
const carol = profile(CAROL, "carol");

// Server activity order: C3 (carol) most recent, then C2, then C1.
const c1 = conversation("c1", REL_B, bob);
const c2 = conversation("c2", REL_B, bob);
const c3 = conversation("c3", REL_C, carol);

function envelope(
  id: string,
  body: string,
  senderProfileId: string,
  conversationId: string
): MessageEnvelope {
  return {
    protocol_version: "1.0",
    message_id: id,
    conversation_id: conversationId,
    source: { node_id: "node-local", profile_id: senderProfileId },
    destination: { node_id: "node-local", profile_id: SELF },
    content: { type: "text/plain", body },
    created_at: "2026-08-31T12:00:00Z",
  };
}

function mockLoadedInbox(
  conversations: ConversationProjection[] = [c3, c2, c1]
) {
  mockedFetchConversations.mockResolvedValue(conversations);
  mockedFetchIdentity.mockResolvedValue(selfProfile);
}

function visibleConversationIds(): string[] {
  const list = screen.getByTestId("inbox-conversation-list");
  const rows = Array.from(list.querySelectorAll("[data-testid^='inbox-conversation-']"));
  return rows.map((row) => row.getAttribute("data-testid")!.replace("inbox-conversation-", ""));
}

describe("DirectMessageInbox", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLoadedInbox();
    mockedFetchMessages.mockResolvedValue([]);
  });

  it("All filter lists every conversation in server order", async () => {
    render(<DirectMessageInbox />);
    await screen.findByTestId("inbox-conversation-list");
    expect(visibleConversationIds()).toEqual(["c3", "c2", "c1"]);
  });

  it("person filter for Bob shows both Bob conversations without collapsing", async () => {
    render(<DirectMessageInbox />);
    await screen.findByTestId("inbox-conversation-list");
    fireEvent.click(screen.getByTestId(`inbox-filter-${REL_B}`));
    await waitFor(() => {
      expect(visibleConversationIds()).toEqual(["c2", "c1"]);
    });
    expect(
      screen.queryByTestId("inbox-conversation-c3")
    ).not.toBeInTheDocument();
  });

  it("person filter for Carol shows only her conversation", async () => {
    render(<DirectMessageInbox />);
    await screen.findByTestId("inbox-conversation-list");
    fireEvent.click(screen.getByTestId(`inbox-filter-${REL_C}`));
    await waitFor(() => {
      expect(visibleConversationIds()).toEqual(["c3"]);
    });
  });

  it("keeps the filter keyed by relationship when the peer username changes", async () => {
    const renamedBob = profile(BOB, "bobby-renamed");
    const renamedFixture = [
      conversation("c3", REL_C, carol),
      conversation("c2", REL_B, renamedBob),
      conversation("c1", REL_B, renamedBob),
    ];
    mockLoadedInbox(renamedFixture);
    const { rerender } = render(<DirectMessageInbox />);
    await screen.findByTestId("inbox-conversation-list");
    // The relationship-scoped chip exists even though the label changed.
    fireEvent.click(screen.getByTestId(`inbox-filter-${REL_B}`));
    await waitFor(() => {
      expect(visibleConversationIds()).toEqual(["c2", "c1"]);
    });
    rerender(<DirectMessageInbox />);
  });

  it("selecting a conversation loads exactly that conversation", async () => {
    render(<DirectMessageInbox />);
    await screen.findByTestId("inbox-conversation-list");
    fireEvent.click(screen.getByTestId("inbox-conversation-c2"));
    await waitFor(() => {
      expect(mockedFetchMessages).toHaveBeenCalledWith("c2", expect.anything());
    });
    expect(mockedFetchMessages).not.toHaveBeenCalledWith(
      "c1",
      expect.anything()
    );
    expect(
      screen.getByText("bob", { selector: "div" })
    ).toBeInTheDocument();
  });

  it("new same-peer conversation creates a distinct conversation under the same relationship", async () => {
    mockedSearch.mockResolvedValue([bob]);
    mockedResolve.mockResolvedValue({
      relationship_id: REL_B,
      participants: [selfProfile, bob],
      peer: bob,
      created_at: "2026-08-31T12:00:00Z",
      updated_at: "2026-08-31T12:00:00Z",
    });
    const fresh = conversation("c4", REL_B, bob);
    mockedCreate.mockResolvedValue(fresh);

    render(<DirectMessageInbox />);
    await screen.findByTestId("inbox-conversation-list");
    fireEvent.click(screen.getByTestId("inbox-new-message"));
    const input = await screen.findByTestId("inbox-profile-search");
    fireEvent.change(input, { target: { value: "bob" } });
    fireEvent.click(screen.getByText("Search"));
    const result = await screen.findByTestId(`inbox-profile-result-${BOB}`);
    fireEvent.click(result);

    await waitFor(() => {
      expect(mockedCreate).toHaveBeenCalledWith(REL_B);
    });
    expect(fresh.conversation_id).not.toBe(c1.conversation_id);
    expect(fresh.conversation_id).not.toBe(c2.conversation_id);
    expect(fresh.relationship_id).toBe(REL_B);
    expect(fresh.relationship_id).toBe(c1.relationship_id);
    await waitFor(() => {
      expect(mockedFetchMessages).toHaveBeenCalledWith(
        "c4",
        expect.anything()
      );
    });
  });

  it("renders no email or internal user id anywhere", async () => {
    render(<DirectMessageInbox />);
    await screen.findByTestId("inbox-conversation-list");
    const root = screen.getByTestId("direct-message-inbox");
    expect(root.textContent).not.toContain("@");
    expect(root.textContent).not.toContain("example.com");
    expect(root.textContent).not.toContain("user_id");
  });

  it("never reconstructs hidden provenance or renders origin/placement", async () => {
    const hiddenOrigin = conversation("c5", REL_C, carol, {
      origin: {
        created_by_profile_id: SELF,
        origin_project_id: 101,
        origin_thread_id: 1001,
        created_at: "2026-08-31T12:00:00Z",
      },
      placement: { project_id: 101, created_at: "x", updated_at: "x" },
    });
    mockLoadedInbox([hiddenOrigin, c2, c1]);
    render(<DirectMessageInbox />);
    await screen.findByTestId("inbox-conversation-list");
    const root = screen.getByTestId("direct-message-inbox");
    expect(root.textContent).not.toContain("101");
    expect(root.textContent).not.toContain("1001");
    expect(root.textContent).not.toContain("project");
  });

  it("replayed send renders exactly one message", async () => {
    const existing = envelope("m1", "hello", SELF, "c1");
    mockedFetchMessages.mockResolvedValue([existing]);
    mockedSend.mockResolvedValue({ replayed: true, message: existing });

    render(<DirectMessageInbox />);
    await screen.findByTestId("inbox-conversation-list");
    fireEvent.click(screen.getByTestId("inbox-conversation-c1"));
    await screen.findByTestId("inbox-message-m1");

    const composer = screen.getByTestId("inbox-composer");
    fireEvent.change(composer, { target: { value: "hello" } });
    fireEvent.click(screen.getByTestId("inbox-send"));
    await waitFor(() => {
      expect(mockedSend).toHaveBeenCalled();
    });
    await waitFor(() => {
      const rendered = screen.getAllByTestId("inbox-message-m1");
      expect(rendered).toHaveLength(1);
    });
  });

  it("has no unread or read-state fiction", async () => {
    mockLoadedInbox([
      {
        ...c3,
        latest_message: {
          message_id: "m9",
          sender_profile_id: CAROL,
          preview: "hello preview",
          created_at: "2026-08-31T12:00:00Z",
        },
      },
      c2,
      c1,
    ]);
    render(<DirectMessageInbox />);
    await screen.findByTestId("inbox-conversation-list");
    expect(screen.queryByText(/unread/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/read receipt/i)).not.toBeInTheDocument();
    expect(screen.queryByTestId("inbox-unread-indicator")).not.toBeInTheDocument();
  });

  it("shows bounded empty states", async () => {
    mockLoadedInbox([]);
    render(<DirectMessageInbox />);
    expect(await screen.findByTestId("inbox-empty")).toBeInTheDocument();
  });

  it("shows no-match state for profile search", async () => {
    mockedSearch.mockResolvedValue([]);
    render(<DirectMessageInbox />);
    await screen.findByTestId("inbox-conversation-list");
    fireEvent.click(screen.getByTestId("inbox-new-message"));
    const input = await screen.findByTestId("inbox-profile-search");
    fireEvent.change(input, { target: { value: "nobody" } });
    fireEvent.click(screen.getByText("Search"));
    expect(await screen.findByTestId("inbox-search-empty")).toBeInTheDocument();
  });
});

describe("DirectMessagesUnavailable", () => {
  it("renders the bounded unavailable state", () => {
    render(<DirectMessagesUnavailable />);
    expect(
      screen.getByTestId("direct-messages-unavailable")
    ).toBeInTheDocument();
    expect(screen.getByText(/unavailable/i)).toBeInTheDocument();
  });
});
