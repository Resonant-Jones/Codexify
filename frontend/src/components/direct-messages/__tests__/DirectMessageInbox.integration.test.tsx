/**
 * Integration regression for the People surface's read-state wiring.
 *
 * These tests drive the **real** `usePeopleMessagingState` hook rather than
 * the test fixture's mocked state object.  The mocked state is a frozen
 * snapshot: it never replaces itself when conversation metadata is cached,
 * so it cannot reproduce a feedback loop between the state owner and a
 * component that depends on the whole state object.
 *
 * The risk under test: the Inbox's `reload` and `refreshUnread` callbacks
 * depend on the complete `state` object.  Caching conversation metadata
 * replaces that object, which recreates the callbacks, which re-runs the
 * fetch effect, which caches metadata again — a loop.
 *
 * Observed on the unfixed code: **950+ projection fetches in 400 ms**.
 * After the fix: exactly one.
 */

import { act, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DirectMessageInbox from "@/components/direct-messages/DirectMessageInbox";
import ContactsLauncher from "@/features/contacts/ContactsLauncher";
import FloatingConversation from "@/features/contacts/FloatingConversation";
import {
  usePeopleMessagingState,
  type PeopleMessagingState,
} from "@/features/contacts/usePeopleMessagingState";
import {
  fetchDirectMessageConversations,
  fetchDirectMessageMessages,
  fetchProjectLabelMap,
  markDirectMessageConversationRead,
  type DirectMessageConversation,
  type DirectMessageEnvelope,
} from "@/lib/direct-messages";

vi.mock("@/lib/direct-messages", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/direct-messages")>();
  return {
    ...actual,
    fetchDirectMessageConversations: vi.fn(),
    fetchProjectLabelMap: vi.fn(),
    fetchOwnSocialIdentity: vi.fn(),
    fetchMessageRequests: vi.fn(),
    fetchMessageRequestHistoryPreference: vi.fn(),
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
  default: () => null,
}));

vi.mock("@/components/direct-messages/MessageRequestPanel", () => ({
  default: () => null,
}));

// The launcher's badge only renders when the direct-messages route is
// available, so the runtime capability store is pinned for this file.
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

const conversation: DirectMessageConversation = {
  conversation_id: "conv-1",
  relationship_id: "rel-1",
  kind: "direct",
  created_at: "2026-09-01T00:00:00Z",
  latest_activity_at: "2026-09-01T00:00:00Z",
  participants: [],
  peer: {
    node_id: "node-local",
    profile_id: "profile-bob",
    username: "bob",
    username_state: "active",
    display_name: "Bob Tester",
    avatar_url: null,
  },
  origin: { origin_project_id: null, origin_thread_id: null },
  placement: { project_id: null, thread_id: null },
  unread_count: 2,
} as unknown as DirectMessageConversation;

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchDirectMessageConversations).mockResolvedValue([conversation]);
  vi.mocked(fetchProjectLabelMap).mockResolvedValue(new Map());
});

/**
 * Renders the Inbox against the real People state owner.
 *
 * The state object is handed to the Inbox exactly as the application hands
 * it over, so any state replacement caused by caching conversation
 * metadata reaches the Inbox's callbacks exactly as it does in production.
 */
function renderWithRealState() {
  const Harness = () => {
    const state = usePeopleMessagingState();
    return (
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={state}
      />
    );
  };
  return render(<Harness />);
}

describe("People surface read-state integration (real state owner)", () => {
  it("does not re-fetch the conversation projection in a loop", async () => {
    renderWithRealState();

    // Wait for the first load to settle and render.
    await waitFor(() => {
      expect(fetchDirectMessageConversations).toHaveBeenCalled();
    });

    const callsAfterFirstLoad =
      vi.mocked(fetchDirectMessageConversations).mock.calls.length;

    // Give the surface several polling intervals' worth of time to reveal a
    // feedback loop.  A loop re-fetches immediately and continuously; a
    // healthy surface stays at exactly one load until the Inbox is opened.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 400));
    });

    const callsAfterSettle =
      vi.mocked(fetchDirectMessageConversations).mock.calls.length;

    expect(callsAfterSettle).toBe(callsAfterFirstLoad);
    // Exactly one load, not merely "a bounded number": an unbounded loop
    // would still satisfy a loose bound.
    expect(callsAfterSettle).toBe(1);
  });

  it("renders the unread count from the server projection", async () => {
    renderWithRealState();

    await waitFor(() => {
      expect(screen.getByTestId("conversation-unread-badge")).toHaveTextContent(
        "2",
      );
    });
  });
});

/**
 * The read-state invariants, exercised against the REAL state owner.
 *
 * The mocked-state fixture used by the unit suite cannot show these: it
 * never replaces itself, so it cannot express "the shared owner already
 * recorded this watermark" or "two surfaces asked at the same time".
 */
function envelope(messageId: string): DirectMessageEnvelope {
  return {
    protocol_version: "1.0",
    message_id: messageId,
    conversation_id: "conv-1",
    source: { node_id: "node-local", profile_id: "profile-alice" },
    destination: { node_id: "node-local", profile_id: "profile-bob" },
    content: { type: "text/plain", body: "hello" },
    created_at: "2026-09-01T01:00:00Z",
  };
}

/**
 * Renders the Inbox against the real People state owner with one
 * Conversation already open and its transcript already rendered.
 *
 * The transcript is seeded through the state owner's own public mutations,
 * which is exactly how the transcript hook populates it in production.
 */
function renderOpenConversation() {
  let captured: PeopleMessagingState | null = null;
  const Harness = () => {
    const state = usePeopleMessagingState();
    captured = state;
    useEffect(() => {
      state.replaceMessages("conv-1", [envelope("m-1")]);
      state.markTranscriptLoaded("conv-1");
      state.openConversation("conv-1");
      // The seeding is a one-time mount action; the state owner is stable.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    return (
      <DirectMessageInbox
        capabilityState="available"
        sourceThreadId={null}
        state={state}
      />
    );
  };
  const result = render(<Harness />);
  return { ...result, getState: () => captured };
}

describe("shared read cursor (real state owner)", () => {
  beforeEach(() => {
    vi.mocked(markDirectMessageConversationRead).mockResolvedValue({
      ...conversation,
      unread_count: 0,
    });
  });

  it("records the read once at the last rendered message", async () => {
    const { getState } = renderOpenConversation();

    await waitFor(() => {
      expect(markDirectMessageConversationRead).toHaveBeenCalledWith(
        "conv-1",
        "m-1",
      );
    });
    expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1);

    // Re-opening the same Conversation with the same transcript must not
    // post the watermark again: the shared owner already recorded it.
    await act(async () => {
      getState()?.closeConversation();
    });
    await act(async () => {
      getState()?.openConversation("conv-1");
    });

    await waitFor(() => {
      expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1);
    });
  });

  it("retries a failed read on reopen", async () => {
    vi.mocked(markDirectMessageConversationRead)
      .mockRejectedValueOnce(new Error("mark read unavailable"))
      .mockResolvedValue({ ...conversation, unread_count: 0 });

    const { getState } = renderOpenConversation();

    await waitFor(() => {
      expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1);
    });

    await act(async () => {
      getState()?.closeConversation();
    });
    await act(async () => {
      getState()?.openConversation("conv-1");
    });

    // A failed read was never recorded, so the reopen retries it.
    await waitFor(() => {
      expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(2);
    });
  });

  it("posts one watermark when the Inbox and the floating window hold one Conversation", async () => {
    let captured: PeopleMessagingState | null = null;
    const Harness = () => {
      const state = usePeopleMessagingState();
      captured = state;
      useEffect(() => {
        state.replaceMessages("conv-1", [envelope("m-1")]);
        state.markTranscriptLoaded("conv-1");
        state.openConversation("conv-1");
        state.popOutConversation("conv-1", conversation);
        // eslint-disable-next-line react-hooks/exhaustive-deps
      }, []);
      return (
        <>
          <DirectMessageInbox
            capabilityState="available"
            sourceThreadId={null}
            state={state}
          />
          <FloatingConversation state={state} />
        </>
      );
    };
    render(<Harness />);

    await waitFor(() => {
      expect(markDirectMessageConversationRead).toHaveBeenCalledWith(
        "conv-1",
        "m-1",
      );
    });
    // Two surfaces, one shared path, one watermark posted.
    expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1);
  });

  it("does not re-post a watermark the Inbox already recorded when the Conversation is popped out", async () => {
    let captured: PeopleMessagingState | null = null;
    const Harness = () => {
      const state = usePeopleMessagingState();
      captured = state;
      useEffect(() => {
        state.replaceMessages("conv-1", [envelope("m-1")]);
        state.markTranscriptLoaded("conv-1");
        state.openConversation("conv-1");
        // eslint-disable-next-line react-hooks/exhaustive-deps
      }, []);
      return (
        <>
          <DirectMessageInbox
            capabilityState="available"
            sourceThreadId={null}
            state={state}
          />
          <FloatingConversation state={state} />
        </>
      );
    };
    render(<Harness />);

    await waitFor(() => {
      expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1);
    });

    // The recipient pops the Conversation out *after* reading it in the
    // Inbox.  The shared owner already recorded that watermark, so the
    // floating window must not post it a second time.
    await act(async () => {
      captured?.popOutConversation("conv-1", conversation);
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });
    expect(markDirectMessageConversationRead).toHaveBeenCalledTimes(1);
  });
});

/**
 * The open Inbox and the floating window must show coherent caller-local
 * unread state.
 *
 * The Inbox keeps its own conversation rows, and those rows are only
 * refreshed by a projection refetch or the 15-second poll tick.  A read
 * recorded by the floating window updates the SHARED caller-local projection
 * immediately, so before this correction the launcher could show a cleared
 * count while the already-visible Inbox badge still showed the previous one.
 *
 * The correction makes the Inbox badge read the shared projection first, so
 * both surfaces render from one source.  The client cache stays a
 * non-authoritative presentation projection of the server's cursor.
 */
describe("open Inbox badge coherence with the floating window", () => {
  beforeEach(() => {
    // The floating window needs a transcript to render, and therefore a
    // read watermark to record.
    vi.mocked(fetchDirectMessageMessages).mockResolvedValue([envelope("m-1")]);
  });

  afterEach(() => {
    vi.mocked(fetchDirectMessageMessages).mockReset();
  });

  it("clears the visible badge when the floating window records the read", async () => {
    vi.mocked(markDirectMessageConversationRead).mockResolvedValue({
      ...conversation,
      unread_count: 0,
    } as unknown as DirectMessageConversation);

    let captured: PeopleMessagingState | null = null;
    const portal = document.createElement("div");
    portal.id = "cfy-portal-root";
    document.body.appendChild(portal);

    const Harness = () => {
      const state = usePeopleMessagingState();
      captured = state;
      return (
        <>
          <ContactsLauncher state={state} />
          <DirectMessageInbox
            capabilityState="available"
            sourceThreadId={null}
            state={state}
          />
          <FloatingConversation state={state} />
        </>
      );
    };
    render(<Harness />);

    // Both surfaces show the same count, read from the shared owner.
    await waitFor(() => {
      expect(screen.getByTestId("conversation-unread-badge")).toHaveTextContent(
        "2",
      );
    });
    expect(
      screen.getByTestId("contacts-launcher-unread-badge"),
    ).toHaveTextContent("2");

    const fetchesBeforeRead =
      vi.mocked(fetchDirectMessageConversations).mock.calls.length;

    // The same Conversation is opened in the floating window.
    await act(async () => {
      captured?.popOutConversation("conv-1", conversation);
    });

    // The floating window records the rendered watermark.
    await waitFor(() => {
      expect(markDirectMessageConversationRead).toHaveBeenCalledWith(
        "conv-1",
        "m-1",
      );
    });

    // The already-visible Inbox badge reflects the cleared count at once.
    await waitFor(() => {
      expect(
        screen.queryByTestId("conversation-unread-badge"),
      ).not.toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("contacts-launcher-unread-badge"),
    ).not.toBeInTheDocument();

    // No refetch and no poll tick were needed to reach that state.
    expect(
      vi.mocked(fetchDirectMessageConversations).mock.calls.length,
    ).toBe(fetchesBeforeRead);
  });
});
