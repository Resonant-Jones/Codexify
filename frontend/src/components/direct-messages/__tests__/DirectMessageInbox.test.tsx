import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DirectMessageInbox from "@/components/direct-messages/DirectMessageInbox";
import type { PeopleMessagingState } from "@/features/contacts/usePeopleMessagingState";
import {
  createDirectMessageConversation,
  fetchDirectMessageConversations,
  fetchProjectLabelMap,
  fetchThreadProjectScope,
  resolveDirectMessageRelationship,
  searchDirectMessageProfiles,
  type DirectMessageConversation,
  type DirectMessageSocialProfile,
} from "@/lib/direct-messages";

vi.mock("@/lib/direct-messages", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/direct-messages")>();
  return {
    ...actual,
    fetchDirectMessageConversations: vi.fn(),
    fetchProjectLabelMap: vi.fn(),
    searchDirectMessageProfiles: vi.fn(),
    resolveDirectMessageRelationship: vi.fn(),
    createDirectMessageConversation: vi.fn(),
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
  displayName: string
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
  preview: string | null
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
  };
}

function makeState(
  overrides: Partial<PeopleMessagingState> = {}
): PeopleMessagingState {
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
    cacheConversationMeta: vi.fn(),
    replaceMessages: vi.fn(),
    appendServerMessage: vi.fn(),
    markTranscriptLoaded: vi.fn(),
    ...overrides,
  };
}

const bob = profile("bob", "bob", "Bob Tester");
const carol = profile("carol", "carol", "Carol Rivera");

function renderInbox(
  state: PeopleMessagingState = makeState(),
  sourceThreadId: number | null = null
) {
  return render(
    <DirectMessageInbox
      capabilityState="available"
      sourceThreadId={sourceThreadId}
      state={state}
    />
  );
}

beforeEach(() => {
  vi.clearAllMocks();
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
      />
    );
    expect(screen.getByTestId("direct-messages-unavailable")).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Direct messages unavailable" })
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
      expect(screen.getAllByTestId("conversation-row")).toHaveLength(3)
    );
    const rows = screen.getAllByTestId("conversation-row");
    expect(rows[0].textContent).toContain("first thread");
    expect(rows[1].textContent).toContain("second thread");
    expect(rows[2].textContent).toContain("carol thread");
    // Both Bob conversations remain distinct rows.
    expect(
      rows.filter((row) => row.textContent?.includes("Bob Tester"))
    ).toHaveLength(2);
  });

  it("shows a placeholder when a conversation has no messages yet", async () => {
    mockedFetchConversations.mockResolvedValue([
      conversation("c1", "rel-ab", bob, null),
    ]);

    renderInbox();

    await waitFor(() =>
      expect(screen.getAllByTestId("conversation-row")).toHaveLength(1)
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
      expect(screen.getAllByTestId("conversation-row")).toHaveLength(3)
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
      expect(screen.getAllByTestId("conversation-row")).toHaveLength(2)
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
      expect(screen.getAllByTestId("conversation-row")).toHaveLength(1)
    );

    fireEvent.click(screen.getByTestId("conversation-row"));
    expect(openConversation).toHaveBeenCalledWith(
      "c-target",
      expect.objectContaining({ conversation_id: "c-target" })
    );

    rerender(
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={makeState({ selectedConversationId: "c-target" })}
      />
    );

    expect(screen.getByTestId("direct-conversation-id").textContent).toBe(
      "c-target"
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
      participants: [profile("alice", "alice", "Alice Self"), bob],
      peer: bob,
      created_at: "2026-09-01T00:00:00Z",
      updated_at: "2026-09-01T00:00:00Z",
    });
    mockedCreate.mockResolvedValue(conversation("c-new", "rel-ab", bob, null));

    renderInbox(state);

    fireEvent.click(screen.getByRole("button", { name: /New Conversation/ }));
    const input = screen.getByLabelText("Search profiles by username");
    fireEvent.change(input, { target: { value: "bob" } });

    await waitFor(() =>
      expect(screen.getByTestId("profile-search-result")).toBeTruthy()
    );
    fireEvent.click(screen.getByTestId("profile-search-result"));

    await waitFor(() => expect(mockedResolve).toHaveBeenCalled());
    expect(mockedResolve).toHaveBeenCalledWith("node-bob", "bob");
    expect(mockedCreate).toHaveBeenCalledWith("rel-ab", {});
    expect(openConversation).toHaveBeenCalledWith(
      "c-new",
      expect.objectContaining({ conversation_id: "c-new" })
    );
  });

  it("captures Project/Thread origin when a source thread maps to a project", async () => {
    const openConversation = vi.fn();
    const state = makeState({ openConversation });
    mockedSearch.mockResolvedValue([bob]);
    mockedResolve.mockResolvedValue({
      relationship_id: "rel-ab",
      participants: [profile("alice", "alice", "Alice Self"), bob],
      peer: bob,
      created_at: "2026-09-01T00:00:00Z",
      updated_at: "2026-09-01T00:00:00Z",
    });
    mockedCreate.mockResolvedValue(conversation("c-new", "rel-ab", bob, null));
    mockedThreadScope.mockResolvedValue(7);

    renderInbox(state, 12);

    fireEvent.click(screen.getByRole("button", { name: /New Conversation/ }));
    fireEvent.change(screen.getByLabelText("Search profiles by username"), {
      target: { value: "bob" },
    });

    await waitFor(() =>
      expect(screen.getByTestId("profile-search-result")).toBeTruthy()
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
