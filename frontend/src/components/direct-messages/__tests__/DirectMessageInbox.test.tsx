import { fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DirectMessageInbox from "@/components/direct-messages/DirectMessageInbox";
import { useDirectMessageTranscript } from "@/features/contacts/useDirectMessageTranscript";
import type { PeopleMessagingState } from "@/features/contacts/usePeopleMessagingState";
import {
  createDirectMessageConversation,
  fetchDirectMessageConversation,
  fetchDirectMessageMessages,
  markDirectMessageConversationRead,
  sendMessageRequest,
  fetchOwnSocialIdentity,
  fetchMessageRequests,
  fetchMessageRequestHistoryPreference,
  fetchDirectMessageConversations,
  fetchProjectLabelMap,
  fetchThreadProjectScope,
  resolveDirectMessageRelationship,
  searchDirectMessageProfiles,
  type DirectMessageConversation,
  type DirectMessageEnvelope,
  type DirectMessageSocialProfile,
} from "@/lib/direct-messages";

vi.mock("@/lib/direct-messages", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/direct-messages")>();
  return {
    ...actual,
    fetchDirectMessageConversations: vi.fn(),
    fetchOwnSocialIdentity: vi.fn(),
    fetchMessageRequests: vi.fn(),
    fetchMessageRequestHistoryPreference: vi.fn(),
    fetchProjectLabelMap: vi.fn(),
    searchDirectMessageProfiles: vi.fn(),
    resolveDirectMessageRelationship: vi.fn(),
    createDirectMessageConversation: vi.fn(),
    fetchDirectMessageConversation: vi.fn(),
    fetchDirectMessageMessages: vi.fn(),
    markDirectMessageConversationRead: vi.fn(),
    sendMessageRequest: vi.fn(),
    fetchThreadProjectScope: vi.fn(),
    normalizeDirectMessageError: (error: unknown) =>
      error instanceof Error ? error : new Error("request failed"),
  };
});

vi.mock("@/features/contacts/DirectConversation", () => ({
  default: ({
    conversationId,
    onBack,
  }: {
    conversationId: string;
    onBack: () => void;
  }) => (
    <section data-testid="direct-conversation-stub">
      <span data-testid="direct-conversation-id">{conversationId}</span>
      <button type="button" onClick={onBack}>
        back
      </button>
    </section>
  ),
}));

const mockedFetchConversations = vi.mocked(fetchDirectMessageConversations);
const mockedFetchLabels = vi.mocked(fetchProjectLabelMap);
const mockedSearch = vi.mocked(searchDirectMessageProfiles);
const mockedResolve = vi.mocked(resolveDirectMessageRelationship);
const mockedCreate = vi.mocked(createDirectMessageConversation);
const mockedThreadScope = vi.mocked(fetchThreadProjectScope);

function profile(
  id: string,
  username: string,
  displayName: string,
): DirectMessageSocialProfile {
  return {
    node_id: `node-${id}`,
    profile_id: id,
    username,
    username_state: "active",
    display_name: displayName,
    avatar_url: null,
  };
}

function conversation(
  id: string,
  relationshipId: string,
  peer: DirectMessageSocialProfile,
  preview: string | null,
  unreadCount = 0,
): DirectMessageConversation {
  return {
    conversation_id: id,
    relationship_id: relationshipId,
    kind: "direct",
    created_at: "2026-09-01T00:00:00Z",
    latest_activity_at: "2026-09-01T01:00:00Z",
    participants: [profile("alice", "alice", "Alice Self"), peer],
    peer,
    origin: {
      created_by_profile_id: peer.profile_id,
      origin_project_id: null,
      origin_thread_id: null,
      created_at: "2026-09-01T00:00:00Z",
    },
    placement: { project_id: null, created_at: null, updated_at: null },
    latest_message: preview
      ? {
          message_id: `latest-${id}`,
          sender_profile_id: peer.profile_id,
          preview,
          created_at: "2026-09-01T01:00:00Z",
        }
      : null,
    unread_count: unreadCount,
  };
}

function envelope(messageId: string): DirectMessageEnvelope {
  return {
    protocol_version: "1.0",
    message_id: messageId,
    conversation_id: "c-open",
    source: { node_id: "node-alice", profile_id: "alice" },
    destination: { node_id: "node-bob", profile_id: "bob" },
    content: { type: "text/plain", body: "hello" },
    created_at: "2026-09-01T01:00:00Z",
  };
}

function makeState(
  overrides: Partial<PeopleMessagingState> = {},
): PeopleMessagingState {
  // The fixture mirrors the People state owner's contract: the projection
  // loader caches every projected Conversation into the shared projection,
  // and the shared read mutation posts the caller's read watermark.
  const cacheConversationMeta = vi.fn();
  return {
    peopleOpen: false,
    activeTab: "inbox",
    selectedRelationshipId: null,
    selectedConversationId: null,
    floatingConversationId: null,
    floatingMode: null,
    draftsByConversationId: {},
    messagesByConversationId: {},
    loadedByConversationId: {},
    conversationMetaById: {},
    unreadTotal: 0,
    openPeople: vi.fn(),
    closePeople: vi.fn(),
    setTab: vi.fn(),
    openRelationship: vi.fn(),
    openConversation: vi.fn(),
    closeConversation: vi.fn(),
    popOutConversation: vi.fn(() => true),
    minimizeFloating: vi.fn(),
    restoreFloating: vi.fn(),
    closeFloating: vi.fn(),
    returnFloatingToPeople: vi.fn(),
    setDraft: vi.fn(),
    cacheConversationMeta,
    replaceMessages: vi.fn(),
    appendServerMessage: vi.fn(),
    markTranscriptLoaded: vi.fn(),
    refreshUnreadProjection: vi.fn(async () => {
      const rows = await fetchDirectMessageConversations();
      rows.forEach((row) => cacheConversationMeta(row));
      return rows;
    }),
    ensureUnreadProjection: vi.fn(async () => {}),
    markConversationRead: vi.fn(
      async (conversationId: string, watermarkMessageId: string | null) => {
        try {
          await markDirectMessageConversationRead(
            conversationId,
            watermarkMessageId,
          );
          return true;
        } catch {
          return false;
        }
      },
    ),
    ...overrides,
  };
}

const bob = profile("bob", "bob", "Bob Tester");
const carol = profile("carol", "carol", "Carol Rivera");

function renderInbox(
  state: PeopleMessagingState = makeState(),
  sourceThreadId: number | null = null,
) {
  return render(
    <DirectMessageInbox
      capabilityState="available"
      sourceThreadId={sourceThreadId}
      state={state}
    />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchOwnSocialIdentity).mockResolvedValue(
    profile("alice", "alice", "Alice"),
  );
  vi.mocked(fetchMessageRequests).mockResolvedValue([]);
  vi.mocked(fetchMessageRequestHistoryPreference).mockResolvedValue(false);
  mockedFetchConversations.mockResolvedValue([]);
  mockedFetchLabels.mockResolvedValue(new Map());
  mockedSearch.mockResolvedValue([]);
  mockedThreadScope.mockResolvedValue(null);
});

describe("capability gating", () => {
  it("fails closed with the unavailable surface when not available", () => {
    render(
      <DirectMessageInbox
        capabilityState="unavailable"
        sourceThreadId={null}
        state={makeState()}
      />,
    );
    expect(screen.getByTestId("direct-messages-unavailable")).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Direct messages unavailable" }),
    ).toBeTruthy();
    expect(mockedFetchConversations).not.toHaveBeenCalled();
  });
});

describe("conversation-first rows", () => {
  it("renders every Conversation as its own row, never collapsing same-peer conversations", async () => {
    mockedFetchConversations.mockResolvedValue([
      conversation("c1", "rel-ab", bob, "first thread"),
      conversation("c2", "rel-ab", bob, "second thread"),
      conversation("c3", "rel-ac", carol, "carol thread"),
    ]);

    renderInbox();

    await waitFor(() =>
      expect(screen.getAllByTestId("conversation-row")).toHaveLength(3),
    );
    const rows = screen.getAllByTestId("conversation-row");
    expect(rows[0].textContent).toContain("first thread");
    expect(rows[1].textContent).toContain("second thread");
    expect(rows[2].textContent).toContain("carol thread");
    // Both Bob conversations remain distinct rows.
    expect(
      rows.filter((row) => row.textContent?.includes("Bob Tester")),
    ).toHaveLength(2);
  });

  it("shows a placeholder when a conversation has no messages yet", async () => {
    mockedFetchConversations.mockResolvedValue([
      conversation("c1", "rel-ab", bob, null),
    ]);

    renderInbox();

    await waitFor(() =>
      expect(screen.getAllByTestId("conversation-row")).toHaveLength(1),
    );
    expect(screen.getByText("No messages yet")).toBeTruthy();
  });
});

describe("person filter", () => {
  it("groups by Relationship without collapsing: filtering to a peer shows all their Conversations", async () => {
    mockedFetchConversations.mockResolvedValue([
      conversation("c1", "rel-ab", bob, "one"),
      conversation("c2", "rel-ab", bob, "two"),
      conversation("c3", "rel-ac", carol, "three"),
    ]);

    renderInbox();

    await waitFor(() =>
      expect(screen.getAllByTestId("conversation-row")).toHaveLength(3),
    );

    fireEvent.click(screen.getByTestId("person-filter-rel-ab"));

    const rows = screen.getAllByTestId("conversation-row");
    expect(rows).toHaveLength(2);
    expect(rows[0].textContent).toContain("one");
    expect(rows[1].textContent).toContain("two");
    expect(screen.getByText("All conversations with this person")).toBeTruthy();
  });

  it("returns to the All view and shows every conversation again", async () => {
    mockedFetchConversations.mockResolvedValue([
      conversation("c1", "rel-ab", bob, "one"),
      conversation("c2", "rel-ac", carol, "two"),
    ]);

    renderInbox();

    await waitFor(() =>
      expect(screen.getAllByTestId("conversation-row")).toHaveLength(2),
    );

    fireEvent.click(screen.getByTestId("person-filter-rel-ab"));
    expect(screen.getAllByTestId("conversation-row")).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: "All" }));
    expect(screen.getAllByTestId("conversation-row")).toHaveLength(2);
  });
});

describe("conversation selection", () => {
  it("opens the exact Conversation_ID and renders the conversation view", async () => {
    const openConversation = vi.fn();
    const state = makeState({ openConversation });
    mockedFetchConversations.mockResolvedValue([
      conversation("c-target", "rel-ab", bob, "hello"),
    ]);

    const { rerender } = renderInbox(state);

    await waitFor(() =>
      expect(screen.getAllByTestId("conversation-row")).toHaveLength(1),
    );

    fireEvent.click(screen.getByTestId("conversation-row"));
    expect(openConversation).toHaveBeenCalledWith(
      "c-target",
      expect.objectContaining({ conversation_id: "c-target" }),
    );

    rerender(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={makeState({ selectedConversationId: "c-target" })}
      />,
    );

    expect(screen.getByTestId("direct-conversation-id").textContent).toBe(
      "c-target",
    );
  });

  it("returns to the Inbox when the conversation view goes back", async () => {
    const closeConversation = vi.fn();
    const state = makeState({
      selectedConversationId: "c-target",
      closeConversation,
    });
    mockedFetchConversations.mockResolvedValue([
      conversation("c-target", "rel-ab", bob, "hello"),
    ]);

    renderInbox(state);

    fireEvent.click(screen.getByRole("button", { name: "back" }));
    expect(closeConversation).toHaveBeenCalled();
  });
});

describe("new conversation creation", () => {
  it("creates a General conversation (empty origin) when no thread scope exists", async () => {
    const openConversation = vi.fn();
    const state = makeState({ openConversation });
    mockedSearch.mockResolvedValue([bob]);
    mockedResolve.mockResolvedValue({
      relationship_id: "rel-ab",
      messaging_consent_established: true,
      participants: [profile("alice", "alice", "Alice Self"), bob],
      peer: bob,
      created_at: "2026-09-01T00:00:00Z",
      updated_at: "2026-09-01T00:00:00Z",
    });
    mockedCreate.mockResolvedValue(conversation("c-new", "rel-ab", bob, null));

    renderInbox(state);

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /Find People/ }),
      ).not.toBeDisabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: /Find People/ }));
    const input = screen.getByLabelText("Search profiles by username");
    fireEvent.change(input, { target: { value: "bob" } });

    await waitFor(() =>
      expect(screen.getByTestId("profile-search-result")).toBeTruthy(),
    );
    fireEvent.click(screen.getByTestId("profile-search-result"));

    await waitFor(() => expect(mockedResolve).toHaveBeenCalled());
    expect(mockedResolve).toHaveBeenCalledWith("node-bob", "bob");
    expect(mockedCreate).toHaveBeenCalledWith("rel-ab", {});
    expect(openConversation).toHaveBeenCalledWith(
      "c-new",
      expect.objectContaining({ conversation_id: "c-new" }),
    );
  });

  it("captures Project/Thread origin when a source thread maps to a project", async () => {
    const openConversation = vi.fn();
    const state = makeState({ openConversation });
    mockedSearch.mockResolvedValue([bob]);
    mockedResolve.mockResolvedValue({
      relationship_id: "rel-ab",
      messaging_consent_established: true,
      participants: [profile("alice", "alice", "Alice Self"), bob],
      peer: bob,
      created_at: "2026-09-01T00:00:00Z",
      updated_at: "2026-09-01T00:00:00Z",
    });
    mockedCreate.mockResolvedValue(conversation("c-new", "rel-ab", bob, null));
    mockedThreadScope.mockResolvedValue(7);

    renderInbox(state, 12);

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /Find People/ }),
      ).not.toBeDisabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: /Find People/ }));
    fireEvent.change(screen.getByLabelText("Search profiles by username"), {
      target: { value: "bob" },
    });

    await waitFor(() =>
      expect(screen.getByTestId("profile-search-result")).toBeTruthy(),
    );
    fireEvent.click(screen.getByTestId("profile-search-result"));

    await waitFor(() => expect(mockedCreate).toHaveBeenCalled());
    expect(mockedThreadScope).toHaveBeenCalledWith(12);
    expect(mockedCreate).toHaveBeenCalledWith("rel-ab", {
      origin_project_id: 7,
      origin_thread_id: 12,
    });
  });
});

describe("consent integration", () => {
  it("opens an intro composer without reading Guardian/Project scope for a new pair", async () => {
    const state = makeState();
    mockedSearch.mockResolvedValue([bob]);
    mockedResolve.mockResolvedValue({
      relationship_id: "new-pair",
      messaging_consent_established: false,
      participants: [bob],
      peer: bob,
      created_at: "2026-10-02T00:00:00Z",
      updated_at: "2026-10-02T00:00:00Z",
    });
    vi.mocked(sendMessageRequest).mockResolvedValue({
      request_id: "new-request",
      relationship_id: "new-pair",
      sender_profile_id: "alice",
      recipient_profile_id: "bob",
      peer: bob,
      note: "Hi Bob",
      state: "pending",
      created_at: "2026-10-02T00:00:00Z",
      expires_at: "2026-11-01T00:00:00Z",
      transitioned_at: null,
      conversation_id: null,
      first_message_id: null,
      outgoing: true,
    });
    renderInbox(state, 12);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Find People" }),
      ).not.toBeDisabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Find People" }));
    fireEvent.change(screen.getByLabelText("Search profiles by username"), {
      target: { value: "bob" },
    });
    fireEvent.click(await screen.findByTestId("profile-search-result"));
    await screen.findByRole("form", { name: "Introductory message request" });
    expect(mockedThreadScope).not.toHaveBeenCalled();
    expect(mockedCreate).not.toHaveBeenCalled();
    expect(state.openConversation).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Introductory note"), {
      target: { value: "Hi Bob" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send request" }));
    await waitFor(() =>
      expect(sendMessageRequest).toHaveBeenCalledWith(
        bob,
        "Hi Bob",
        expect.any(String),
      ),
    );
    expect(state.openConversation).not.toHaveBeenCalled();
  });
});

describe("people search", () => {
  async function openSearch(state = makeState()) {
    renderInbox(state);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /Find People/ }),
      ).not.toBeDisabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: /Find People/ }));
    return screen.getByLabelText("Search profiles by username");
  }

  it("searches the bare handle when the @ sigil is typed", async () => {
    mockedSearch.mockResolvedValue([bob]);
    const input = await openSearch();

    fireEvent.change(input, { target: { value: "@resonant-" } });

    await waitFor(() =>
      expect(mockedSearch).toHaveBeenCalledWith("resonant-"),
    );
  });

  it("debounces rapid typing into a single request for the latest query", async () => {
    mockedSearch.mockResolvedValue([bob]);
    const input = await openSearch();

    fireEvent.change(input, { target: { value: "res" } });
    fireEvent.change(input, { target: { value: "reso" } });
    fireEvent.change(input, { target: { value: "resonant-" } });

    await waitFor(() =>
      expect(mockedSearch).toHaveBeenCalledWith("resonant-"),
    );
    expect(mockedSearch).toHaveBeenCalledTimes(1);
  });

  it("does not let a stale response replace newer results", async () => {
    let resolveStale: (profiles: DirectMessageSocialProfile[]) => void = () => {};
    mockedSearch
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveStale = resolve;
          }),
      )
      .mockResolvedValueOnce([bob]);
    const input = await openSearch();

    fireEvent.change(input, { target: { value: "old" } });
    await waitFor(() => expect(mockedSearch).toHaveBeenCalledWith("old"));

    fireEvent.change(input, { target: { value: "new" } });
    await waitFor(() => expect(mockedSearch).toHaveBeenCalledWith("new"));
    await screen.findByTestId("profile-search-result");

    resolveStale([
      {
        ...bob,
        profile_id: "profile-stale",
        username: "stale-result",
        display_name: "Stale Result",
      },
    ]);

    await waitFor(() => {
      expect(screen.queryByText("Stale Result")).not.toBeInTheDocument();
    });
    expect(screen.getByTestId("profile-search-result")).toHaveTextContent(
      "Bob Tester",
    );
  });

  it("clears results when the query is cleared", async () => {
    mockedSearch.mockResolvedValue([bob]);
    const input = await openSearch();

    fireEvent.change(input, { target: { value: "bob" } });
    await screen.findByTestId("profile-search-result");

    fireEvent.change(input, { target: { value: "" } });

    await waitFor(() => {
      expect(screen.queryByTestId("profile-search-result")).not.toBeInTheDocument();
    });
    expect(mockedSearch).toHaveBeenCalledTimes(1);
  });

  it("surfaces a failed search without breaking the surface", async () => {
    mockedSearch.mockRejectedValue(new Error("search unavailable"));
    const input = await openSearch();

    fireEvent.change(input, { target: { value: "bob" } });

    await waitFor(() =>
      expect(screen.getByText("search unavailable")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("profile-search-result")).not.toBeInTheDocument();
  });

  it("does not search below the minimum query length", async () => {
    const input = await openSearch();

    fireEvent.change(input, { target: { value: "@" } });

    await waitFor(() =>
      expect(
        screen.getByText(/Type at least 2 characters to search/),
      ).toBeInTheDocument(),
    );
    expect(mockedSearch).not.toHaveBeenCalled();
  });

  it("communicates that search is limited to this node", async () => {
    mockedSearch.mockResolvedValue([]);
    const input = await openSearch();

    expect(
      screen.getByText("Search covers people on this node only."),
    ).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "nobody" } });

    await waitFor(() =>
      expect(
        screen.getByText(/No profiles on this node match/),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByText("No profiles match that username.")).toBeNull();
  });
});

describe("recipient-local unread state", () => {
  it("renders an unread badge for a conversation with unread messages", async () => {
    mockedFetchConversations.mockResolvedValue([
      conversation("c-unread", "rel-ab", bob, "hello", 3),
    ]);

    renderInbox();

    await waitFor(() =>
      expect(screen.getAllByTestId("conversation-row")).toHaveLength(1),
    );
    const badge = screen.getByTestId("conversation-unread-badge");
    expect(badge.textContent).toBe("3");
    expect(badge.getAttribute("aria-label")).toBe("3 unread messages");
  });

  it("renders no badge for a conversation the reader has already read", async () => {
    mockedFetchConversations.mockResolvedValue([
      conversation("c-read", "rel-ab", bob, "hello", 0),
    ]);

    renderInbox();

    await waitFor(() =>
      expect(screen.getAllByTestId("conversation-row")).toHaveLength(1),
    );
    expect(screen.queryByTestId("conversation-unread-badge")).toBeNull();
  });

  it("caps the badge at 99+", async () => {
    mockedFetchConversations.mockResolvedValue([
      conversation("c-many", "rel-ab", bob, "hello", 250),
    ]);

    renderInbox();

    await waitFor(() =>
      expect(screen.getByTestId("conversation-unread-badge")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("conversation-unread-badge").textContent).toBe("99+");
  });

  it("recovers the unread state after a reload", async () => {
    mockedFetchConversations.mockResolvedValue([
      conversation("c-reload", "rel-ab", bob, "hello", 2),
    ]);

    const first = renderInbox();
    await waitFor(() =>
      expect(screen.getByTestId("conversation-unread-badge").textContent).toBe("2"),
    );
    first.unmount();

    // A fresh mount (the reload path) reads the same durable unread state.
    renderInbox();
    await waitFor(() =>
      expect(screen.getByTestId("conversation-unread-badge").textContent).toBe("2"),
    );
  });

  it("clears the reader's badge after the conversation is opened", async () => {
    const unread = conversation("c-open", "rel-ab", bob, "hello", 1);
    const read = conversation("c-open", "rel-ab", bob, "hello", 0);
    mockedFetchConversations
      .mockResolvedValueOnce([unread])
      .mockResolvedValue([read]);
    vi.mocked(fetchDirectMessageConversation).mockResolvedValue(read);
    vi.mocked(markDirectMessageConversationRead).mockResolvedValue(read);

    const { rerender } = renderInbox();

    await waitFor(() =>
      expect(screen.getByTestId("conversation-unread-badge")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("conversation-row"));

    // The read action fires once the transcript has actually been rendered,
    // and carries the last rendered message as the read watermark.
    rerender(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={makeState({
          selectedConversationId: "c-open",
          loadedByConversationId: { "c-open": true },
          messagesByConversationId: { "c-open": [envelope("m-1")] },
        })}
      />,
    );

    await waitFor(() =>
      expect(markDirectMessageConversationRead).toHaveBeenCalledWith(
        "c-open",
        "m-1",
      ),
    );
    // The refreshed projection no longer reports unread for this reader.
    await waitFor(() =>
      expect(screen.queryByTestId("conversation-unread-badge")).toBeNull(),
    );
  });

  it("does not mark a conversation read before its transcript is rendered", async () => {
    const unread = conversation("c-pending", "rel-ab", bob, "hello", 1);
    mockedFetchConversations.mockResolvedValue([unread]);
    vi.mocked(markDirectMessageConversationRead).mockResolvedValue(unread);

    const { rerender } = renderInbox();

    await waitFor(() =>
      expect(screen.getByTestId("conversation-unread-badge")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("conversation-row"));

    // The conversation is selected, but nothing has been rendered yet, so
    // there is no watermark to advance to and no read may happen.
    rerender(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={makeState({ selectedConversationId: "c-pending" })}
      />,
    );

    await waitFor(() =>
      expect(screen.getByTestId("direct-conversation-id")).toHaveTextContent(
        "c-pending",
      ),
    );
    expect(markDirectMessageConversationRead).not.toHaveBeenCalled();
  });

  it("never marks a conversation read by merely fetching it", async () => {
    const unread = conversation("c-fetch", "rel-ab", bob, "hello", 1);
    mockedFetchConversations.mockResolvedValue([unread]);
    vi.mocked(fetchDirectMessageConversation).mockResolvedValue(unread);

    renderInbox();

    await waitFor(() =>
      expect(screen.getByTestId("conversation-unread-badge")).toBeInTheDocument(),
    );

    // A plain fetch of the transcript is not a read action.
    await fetchDirectMessageConversation("c-fetch");

    expect(markDirectMessageConversationRead).not.toHaveBeenCalled();
    expect(screen.getByTestId("conversation-unread-badge")).toBeInTheDocument();
  });

  it("refreshes unread state while the Inbox is open", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      mockedFetchConversations
        .mockResolvedValueOnce([
          conversation("c-poll", "rel-ab", bob, "hello", 0),
        ])
        .mockResolvedValue([
          conversation("c-poll", "rel-ab", bob, "hello", 4),
        ]);

      renderInbox(makeState({ peopleOpen: true, activeTab: "inbox" }));

      await waitFor(() =>
        expect(screen.getAllByTestId("conversation-row")).toHaveLength(1),
      );
      expect(screen.queryByTestId("conversation-unread-badge")).toBeNull();

      await vi.advanceTimersByTimeAsync(15_000);

      await waitFor(() =>
        expect(screen.getByTestId("conversation-unread-badge").textContent).toBe(
          "4",
        ),
      );
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not poll while the People surface is closed", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      mockedFetchConversations.mockResolvedValue([
        conversation("c-closed", "rel-ab", bob, "hello", 0),
      ]);

      renderInbox(makeState({ peopleOpen: false, activeTab: "inbox" }));

      await waitFor(() =>
        expect(screen.getAllByTestId("conversation-row")).toHaveLength(1),
      );
      const callsAfterMount = mockedFetchConversations.mock.calls.length;

      await vi.advanceTimersByTimeAsync(45_000);

      expect(mockedFetchConversations.mock.calls.length).toBe(callsAfterMount);
    } finally {
      vi.useRealTimers();
    }
  });

  it("never advances the read cursor from the unread refresh alone", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      mockedFetchConversations.mockResolvedValue([
        conversation("c-cursor", "rel-ab", bob, "hello", 5),
      ]);

      renderInbox(makeState({ peopleOpen: true, activeTab: "inbox" }));

      await waitFor(() =>
        expect(screen.getByTestId("conversation-unread-badge")).toBeInTheDocument(),
      );

      await vi.advanceTimersByTimeAsync(15_000);
      await waitFor(() =>
        expect(mockedFetchConversations.mock.calls.length).toBeGreaterThan(1),
      );

      // Refreshing unread state must not mark anything as read.
      expect(fetchDirectMessageConversation).not.toHaveBeenCalled();
      expect(markDirectMessageConversationRead).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps the surface usable when an unread refresh fails", async () => {
    mockedFetchConversations.mockResolvedValue([
      conversation("c-error", "rel-ab", bob, "hello", 1),
    ]);

    renderInbox();

    await waitFor(() =>
      expect(screen.getByTestId("conversation-unread-badge")).toBeInTheDocument(),
    );
    expect(screen.getAllByTestId("conversation-row")).toHaveLength(1);
  });
});

describe("transcript refresh on reopen", () => {
  function renderTranscript(
    conversationId: string,
    loaded: boolean,
    replaceMessages: ReturnType<typeof vi.fn>,
    markTranscriptLoaded: ReturnType<typeof vi.fn>,
  ) {
    return renderHook(
      ({ id, isLoaded }: { id: string; isLoaded: boolean }) =>
        useDirectMessageTranscript(
          id,
          [],
          isLoaded,
          replaceMessages,
          markTranscriptLoaded,
        ),
      { initialProps: { id: conversationId, isLoaded: loaded } },
    );
  }

  it("refetches the transcript when a conversation is reopened", async () => {
    const first = [envelope("m-1")];
    const refreshed = [envelope("m-1"), envelope("m-2")];
    vi.mocked(fetchDirectMessageMessages)
      .mockResolvedValueOnce(first)
      .mockResolvedValueOnce(refreshed);
    const replaceMessages = vi.fn();
    const markTranscriptLoaded = vi.fn();

    // First activation.
    const firstMount = renderTranscript(
      "c-reopen",
      true,
      replaceMessages,
      markTranscriptLoaded,
    );
    await waitFor(() =>
      expect(fetchDirectMessageMessages).toHaveBeenCalledTimes(1),
    );
    await waitFor(() =>
      expect(replaceMessages).toHaveBeenCalledWith("c-reopen", first),
    );
    firstMount.unmount();

    // Reopening the same conversation refreshes even though it was loaded.
    renderTranscript("c-reopen", true, replaceMessages, markTranscriptLoaded);
    await waitFor(() =>
      expect(fetchDirectMessageMessages).toHaveBeenCalledTimes(2),
    );
    await waitFor(() =>
      expect(replaceMessages).toHaveBeenCalledWith("c-reopen", refreshed),
    );
  });

  it("shares one fetch between concurrent holders of the same conversation", async () => {
    vi.mocked(fetchDirectMessageMessages).mockResolvedValue([envelope("m-1")]);
    const replaceMessages = vi.fn();
    const markTranscriptLoaded = vi.fn();

    // The People modal and the floating window can hold one conversation.
    renderTranscript("c-shared", true, replaceMessages, markTranscriptLoaded);
    renderTranscript("c-shared", true, replaceMessages, markTranscriptLoaded);

    await waitFor(() =>
      expect(replaceMessages).toHaveBeenCalledWith(
        "c-shared",
        [envelope("m-1")],
      ),
    );
    expect(fetchDirectMessageMessages).toHaveBeenCalledTimes(1);
  });

  it("does not fetch for an empty conversation", async () => {
    const replaceMessages = vi.fn();
    const markTranscriptLoaded = vi.fn();

    renderTranscript("", true, replaceMessages, markTranscriptLoaded);

    await waitFor(() => expect(markTranscriptLoaded).not.toHaveBeenCalled());
    expect(fetchDirectMessageMessages).not.toHaveBeenCalled();
  });

  it("keeps the previous transcript and does not mark loaded when a refresh fails", async () => {
    vi.mocked(fetchDirectMessageMessages).mockRejectedValue(
      new Error("transcript unavailable"),
    );
    const replaceMessages = vi.fn();
    const markTranscriptLoaded = vi.fn();

    const { result } = renderTranscript(
      "c-failed",
      true,
      replaceMessages,
      markTranscriptLoaded,
    );

    await waitFor(() =>
      expect(result.current.error).toBe("transcript unavailable"),
    );
    // The cached transcript is preserved and nothing is marked read.
    expect(replaceMessages).not.toHaveBeenCalled();
    expect(markTranscriptLoaded).not.toHaveBeenCalled();
  });

  it("does not refetch in a loop once a conversation is loaded", async () => {
    vi.mocked(fetchDirectMessageMessages).mockResolvedValue([envelope("m-1")]);
    const replaceMessages = vi.fn();
    const markTranscriptLoaded = vi.fn();

    const { rerender } = renderTranscript(
      "c-loop",
      false,
      replaceMessages,
      markTranscriptLoaded,
    );
    await waitFor(() =>
      expect(fetchDirectMessageMessages).toHaveBeenCalledTimes(1),
    );

    // The shared cache becoming loaded re-runs the effect; it must not
    // start another fetch.
    rerender({ id: "c-loop", isLoaded: true });
    await waitFor(() =>
      expect(markTranscriptLoaded).toHaveBeenCalledWith("c-loop"),
    );
    expect(fetchDirectMessageMessages).toHaveBeenCalledTimes(1);
  });
});

describe("reopen and refreshed watermark", () => {
  it("posts the refreshed watermark once the refreshed transcript renders", async () => {
    vi.mocked(markDirectMessageConversationRead).mockResolvedValue(
      conversation("c-refresh", "rel-ab", bob, "hello", 0),
    );

    const { rerender } = render(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={makeState({
          selectedConversationId: "c-refresh",
          loadedByConversationId: { "c-refresh": true },
          messagesByConversationId: { "c-refresh": [envelope("m-1")] },
        })}
      />,
    );

    await waitFor(() =>
      expect(markDirectMessageConversationRead).toHaveBeenCalledWith(
        "c-refresh",
        "m-1",
      ),
    );

    // The transcript refreshes and a newer message renders.
    rerender(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={makeState({
          selectedConversationId: "c-refresh",
          loadedByConversationId: { "c-refresh": true },
          messagesByConversationId: {
            "c-refresh": [envelope("m-1"), envelope("m-2")],
          },
        })}
      />,
    );

    await waitFor(() =>
      expect(markDirectMessageConversationRead).toHaveBeenCalledWith(
        "c-refresh",
        "m-2",
      ),
    );
  });

  it("does not re-post an unchanged watermark when the conversation is reopened", async () => {
    vi.mocked(markDirectMessageConversationRead).mockResolvedValue(
      conversation("c-same", "rel-ab", bob, "hello", 0),
    );

    const state = makeState({
      selectedConversationId: "c-same",
      loadedByConversationId: { "c-same": true },
      messagesByConversationId: { "c-same": [envelope("m-1")] },
    });

    const { rerender } = render(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={state}
      />,
    );

    await waitFor(() =>
      expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1),
    );

    // The recipient leaves and comes back before the transcript has changed.
    rerender(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={makeState()}
      />,
    );
    rerender(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={makeState({
          selectedConversationId: "c-same",
          loadedByConversationId: { "c-same": true },
          messagesByConversationId: { "c-same": [envelope("m-1")] },
        })}
      />,
    );

    await waitFor(() =>
      expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1),
    );
  });
});

describe("failed read stays retryable", () => {
  it("retries the read on reopen when the first mutation failed", async () => {
    vi.mocked(markDirectMessageConversationRead)
      .mockRejectedValueOnce(new Error("mark read unavailable"))
      .mockResolvedValue(
        conversation("c-retry", "rel-ab", bob, "hello", 0),
      );

    const state = makeState({
      selectedConversationId: "c-retry",
      loadedByConversationId: { "c-retry": true },
      messagesByConversationId: { "c-retry": [envelope("m-1")] },
    });

    const { rerender } = render(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={state}
      />,
    );

    // The first mutation fails and must not be remembered as recorded.
    await waitFor(() =>
      expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1),
    );
    await waitFor(() =>
      expect(markDirectMessageConversationRead).toHaveBeenCalledWith(
        "c-retry",
        "m-1",
      ),
    );

    // Reopening the same conversation with the same transcript retries.
    rerender(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={makeState()}
      />,
    );
    rerender(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={state}
      />,
    );

    await waitFor(() =>
      expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(2),
    );
    expect(markDirectMessageConversationRead).toHaveBeenLastCalledWith(
      "c-retry",
      "m-1",
    );
  });

  it("does not re-post a watermark that was recorded successfully", async () => {
    vi.mocked(markDirectMessageConversationRead).mockResolvedValue(
      conversation("c-once", "rel-ab", bob, "hello", 0),
    );

    const state = makeState({
      selectedConversationId: "c-once",
      loadedByConversationId: { "c-once": true },
      messagesByConversationId: { "c-once": [envelope("m-1")] },
    });

    const { rerender } = render(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={state}
      />,
    );

    await waitFor(() =>
      expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1),
    );

    rerender(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={makeState()}
      />,
    );
    rerender(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={state}
      />,
    );

    await waitFor(() =>
      expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1),
    );
  });

  it("does not issue concurrent duplicate mutations for one watermark", async () => {
    let resolvePost: (value: unknown) => void = () => {};
    vi.mocked(markDirectMessageConversationRead).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePost = resolve;
        }),
    );

    const state = makeState({
      selectedConversationId: "c-once",
      loadedByConversationId: { "c-once": true },
      messagesByConversationId: { "c-once": [envelope("m-1")] },
    });

    const { rerender } = render(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={state}
      />,
    );

    await waitFor(() =>
      expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1),
    );

    // Re-render while the first mutation is still in flight.
    rerender(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={makeState({
          selectedConversationId: "c-once",
          loadedByConversationId: { "c-once": true },
          messagesByConversationId: { "c-once": [envelope("m-1")] },
        })}
      />,
    );

    expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1);
    resolvePost(conversation("c-once", "rel-ab", bob, "hello", 0));
    await waitFor(() =>
      expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1),
    );
  });
});
