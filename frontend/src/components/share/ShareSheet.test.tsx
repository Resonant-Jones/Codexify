import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ShareSheet from "@/components/share/ShareSheet";
import type { PeopleMessagingState } from "@/features/contacts/usePeopleMessagingState";

const dm = vi.hoisted(() => ({
  searchDirectMessageProfiles: vi.fn(),
  resolveDirectMessageRelationship: vi.fn(),
  fetchRelationshipConversations: vi.fn(),
  createDirectMessageConversation: vi.fn(),
  sendDirectMessage: vi.fn(),
  fetchThreadProjectScope: vi.fn(),
  peerPresentationLabel: vi.fn(
    (p: { display_name?: string | null; username?: string | null }) =>
      p?.display_name?.trim() || p?.username || "Profile"
  ),
}));

const share = vi.hoisted(() => ({
  createShareLink: vi.fn(),
  copyTextWithFallback: vi.fn(),
}));

vi.mock("@/lib/direct-messages", () => dm);

vi.mock("@/lib/share-links", () => ({
  createShareLink: share.createShareLink,
  copyTextWithFallback: share.copyTextWithFallback,
  ShareLinkApiError: class ShareLinkApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
}));

vi.mock("@/lib/runtimeConfig", () => ({
  resolveSharePublicUrl: (url: string) => `https://public.test${url}`,
}));

const bob = {
  node_id: "node-local",
  profile_id: "profile-bob",
  username: "qualbob",
  username_state: "active" as const,
  display_name: "Bob Tester",
  avatar_url: null,
};

const relationship = {
  relationship_id: "rel-1",
  participants: [bob],
  peer: bob,
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-01T00:00:00Z",
};

function conversation(id: string) {
  return {
    conversation_id: id,
    relationship_id: "rel-1",
    kind: "direct",
    created_at: "2026-09-01T00:00:00Z",
    latest_activity_at: "2026-09-01T00:00:00Z",
    participants: [bob],
    peer: bob,
    origin: {
      created_by_profile_id: null,
      origin_project_id: null,
      origin_thread_id: null,
      created_at: "2026-09-01T00:00:00Z",
    },
    placement: { project_id: null, created_at: null, updated_at: null },
    latest_message: null,
  };
}

function makeState(overrides: Partial<PeopleMessagingState> = {}): PeopleMessagingState {
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

function renderSheet(props: Partial<ComponentProps<typeof ShareSheet>> = {}) {
  const onClose = vi.fn();
  const state = props.peopleState ?? makeState();
  const portal = document.createElement("div");
  portal.id = "cfy-portal-root";
  document.body.appendChild(portal);
  const utils = render(
    <ShareSheet
      targetType="thread"
      targetId={42}
      open
      onClose={onClose}
      capabilityState="available"
      peopleState={state}
      sourceThreadId={null}
      {...props}
    />
  );
  return { ...utils, onClose, state };
}

beforeEach(() => {
  share.createShareLink.mockResolvedValue({
    ok: true,
    token: "tok-1",
    url: "/share/tok-1",
    expires_at: null,
  });
  share.copyTextWithFallback.mockResolvedValue("clipboard");
  dm.searchDirectMessageProfiles.mockResolvedValue([bob]);
  dm.resolveDirectMessageRelationship.mockResolvedValue(relationship);
  dm.fetchRelationshipConversations.mockResolvedValue([
    conversation("c1"),
    conversation("c2"),
  ]);
  dm.createDirectMessageConversation.mockResolvedValue(conversation("c3"));
  dm.sendDirectMessage.mockResolvedValue({
    ok: true,
    replayed: false,
    message: {
      protocol_version: "1.0",
      message_id: "m1",
      conversation_id: "c1",
      source: { node_id: "n", profile_id: "a" },
      destination: { node_id: "n", profile_id: "b" },
      content: { type: "text/plain", body: "https://public.test/share/tok-1" },
      created_at: "2026-09-01T00:00:00Z",
    },
  });
  dm.fetchThreadProjectScope.mockResolvedValue(null);
});

afterEach(() => {
  document.body.innerHTML = "";
  vi.clearAllMocks();
});

async function openSendToPerson(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByTestId("share-action-send-person"));
  const input = screen.getByLabelText("Search profiles by username");
  await user.type(input, "qualbob");
  const result = await screen.findByTestId("share-person-result");
  await user.click(result);
  return result;
}

describe("ShareSheet", () => {
  it("shows Copy Link and Send to Person when messaging is available", () => {
    renderSheet();
    expect(screen.getByTestId("share-action-copy")).toBeInTheDocument();
    expect(screen.getByTestId("share-action-send-person")).toBeInTheDocument();
    // Truthful privacy copy: links are not recipient-exclusive.
    expect(screen.getByText(/not exclusive|anyone with the link/i)).toBeInTheDocument();
  });

  it("creates nothing just by opening or closing", async () => {
    const user = userEvent.setup();
    const { onClose } = renderSheet();
    expect(share.createShareLink).not.toHaveBeenCalled();
    expect(dm.resolveDirectMessageRelationship).not.toHaveBeenCalled();
    expect(dm.sendDirectMessage).not.toHaveBeenCalled();
    await user.click(screen.getByLabelText("Close Share"));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(share.createShareLink).not.toHaveBeenCalled();
    expect(dm.sendDirectMessage).not.toHaveBeenCalled();
  });

  it("copies a link with exactly one share POST", async () => {
    const user = userEvent.setup();
    renderSheet();
    await user.click(screen.getByTestId("share-action-copy"));
    await waitFor(() => {
      expect(share.createShareLink).toHaveBeenCalledTimes(1);
    });
    expect(share.createShareLink).toHaveBeenCalledWith("thread", 42);
    await waitFor(() => {
      expect(share.copyTextWithFallback).toHaveBeenCalledWith(
        "https://public.test/share/tok-1"
      );
    });
    expect(screen.getByTestId("copy-success")).toBeInTheDocument();
    expect(dm.sendDirectMessage).not.toHaveBeenCalled();
  });

  it("fails closed: Send to Person unavailable on quarantined profile with zero DM calls", async () => {
    renderSheet({ capabilityState: "unavailable" });
    expect(
      screen.getByTestId("share-action-send-person-unavailable")
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("share-action-send-person")
    ).not.toBeInTheDocument();
    expect(screen.getByText(/Direct messages are unavailable/i)).toBeInTheDocument();
    // Copy Link remains fully usable.
    expect(screen.getByTestId("share-action-copy")).toBeInTheDocument();
    expect(dm.searchDirectMessageProfiles).not.toHaveBeenCalled();
  });

  it("hides Send to Person when no People state is provided", () => {
    renderSheet({ peopleState: null });
    expect(screen.getByTestId("share-action-copy")).toBeInTheDocument();
    expect(
      screen.getByTestId("share-action-send-person-unavailable")
    ).toBeInTheDocument();
  });

  it("searches profiles by username and shows no email or user_id", async () => {
    const user = userEvent.setup();
    renderSheet();
    await user.click(screen.getByTestId("share-action-send-person"));
    const input = screen.getByLabelText("Search profiles by username");
    await user.type(input, "qualbob");
    await waitFor(() => {
      expect(dm.searchDirectMessageProfiles).toHaveBeenCalledWith("qualbob");
    });
    const result = await screen.findByTestId("share-person-result");
    expect(result).toHaveTextContent("Bob Tester");
    expect(result).toHaveTextContent("@qualbob");
    expect(screen.queryByText(/@.*\.(com|net|org)/i)).not.toBeInTheDocument();
    expect(result).not.toHaveTextContent("user_id");
  });

  it("resolves the canonical Relationship and lists every existing Conversation distinctly", async () => {
    const user = userEvent.setup();
    renderSheet();
    await openSendToPerson(user);
    await waitFor(() => {
      expect(dm.resolveDirectMessageRelationship).toHaveBeenCalledWith(
        bob.node_id,
        bob.profile_id
      );
    });
    const c1 = await screen.findByTestId("share-choice-c1");
    const c2 = screen.getByTestId("share-choice-c2");
    const newChoice = screen.getByTestId("share-choice-new");
    expect(c1).toBeInTheDocument();
    expect(c2).toBeInTheDocument();
    expect(newChoice).toBeInTheDocument();
  });

  it("sends into an existing Conversation without creating or rebinding anything", async () => {
    const user = userEvent.setup();
    const { state } = renderSheet();
    await openSendToPerson(user);
    await screen.findByTestId("share-choice-c2");
    await user.click(screen.getByTestId("share-choice-c2"));
    await user.click(screen.getByTestId("share-submit"));

    await waitFor(() => {
      expect(share.createShareLink).toHaveBeenCalledTimes(1);
      expect(dm.createDirectMessageConversation).not.toHaveBeenCalled();
      expect(dm.sendDirectMessage).toHaveBeenCalledTimes(1);
    });
    const [conversationId, body, key] = dm.sendDirectMessage.mock.calls[0];
    expect(conversationId).toBe("c2");
    expect(body).toBe("https://public.test/share/tok-1");
    expect(typeof key).toBe("string");
    expect(state.openConversation).toHaveBeenCalledWith("c2", undefined);
    expect(state.openPeople).toHaveBeenCalled();
  });

  it("creates one new Conversation with canonical Project/Thread origin and sends into it", async () => {
    const user = userEvent.setup();
    dm.fetchThreadProjectScope.mockResolvedValue(7);
    const { state } = renderSheet({ sourceThreadId: 3 });
    await openSendToPerson(user);
    await screen.findByTestId("share-choice-new");
    await user.click(screen.getByTestId("share-choice-new"));
    await user.click(screen.getByTestId("share-submit"));

    await waitFor(() => {
      expect(dm.createDirectMessageConversation).toHaveBeenCalledWith("rel-1", {
        origin_project_id: 7,
        origin_thread_id: 3,
      });
      expect(dm.sendDirectMessage).toHaveBeenCalledTimes(1);
    });
    expect(dm.sendDirectMessage.mock.calls[0][0]).toBe("c3");
    expect(state.openConversation).toHaveBeenCalledWith("c3", undefined);
  });

  it("creates a General-origin Conversation when no canonical scope exists", async () => {
    const user = userEvent.setup();
    renderSheet({ sourceThreadId: null, sourceProjectId: null });
    await openSendToPerson(user);
    await screen.findByTestId("share-choice-new");
    await user.click(screen.getByTestId("share-choice-new"));
    await user.click(screen.getByTestId("share-submit"));
    await waitFor(() => {
      expect(dm.createDirectMessageConversation).toHaveBeenCalledWith(
        "rel-1",
        {}
      );
    });
  });

  it("reuses the same URL and idempotency key when the send fails and is retried", async () => {
    const user = userEvent.setup();
    dm.sendDirectMessage
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValueOnce({
        ok: true,
        replayed: true,
        message: {
          protocol_version: "1.0",
          message_id: "m1",
          conversation_id: "c2",
          source: { node_id: "n", profile_id: "a" },
          destination: { node_id: "n", profile_id: "b" },
          content: { type: "text/plain", body: "https://public.test/share/tok-1" },
          created_at: "2026-09-01T00:00:00Z",
        },
      });
    renderSheet();
    await openSendToPerson(user);
    await screen.findByTestId("share-choice-c2");
    await user.click(screen.getByTestId("share-choice-c2"));
    await user.click(screen.getByTestId("share-submit"));

    const failure = await screen.findByText(
      /Share link created, but the message was not sent/i
    );
    expect(failure).toBeInTheDocument();
    expect(screen.getByTestId("share-created-link")).toBeInTheDocument();
    expect(share.createShareLink).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId("share-retry-send"));
    await waitFor(() => {
      expect(dm.sendDirectMessage).toHaveBeenCalledTimes(2);
    });
    // Same URL, same key, no second share link.
    expect(share.createShareLink).toHaveBeenCalledTimes(1);
    const first = dm.sendDirectMessage.mock.calls[0];
    const second = dm.sendDirectMessage.mock.calls[1];
    expect(second[0]).toBe(first[0]);
    expect(second[1]).toBe(first[1]);
    expect(second[2]).toBe(first[2]);
  });

  it("reports link failure, never sends, and retries link creation normally", async () => {
    const user = userEvent.setup();
    share.createShareLink
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce({
        ok: true,
        token: "tok-2",
        url: "/share/tok-2",
        expires_at: null,
      });
    renderSheet();
    await openSendToPerson(user);
    await screen.findByTestId("share-choice-c1");
    await user.click(screen.getByTestId("share-choice-c1"));
    await user.click(screen.getByTestId("share-submit"));

    await screen.findByText(/Share link creation failed/i);
    expect(dm.sendDirectMessage).not.toHaveBeenCalled();
    await user.click(screen.getByTestId("share-retry-link"));
    await waitFor(() => {
      expect(share.createShareLink).toHaveBeenCalledTimes(2);
      expect(dm.sendDirectMessage).toHaveBeenCalledTimes(1);
    });
  });

  it("reports conversation failure and does not fabricate atomicity", async () => {
    const user = userEvent.setup();
    dm.createDirectMessageConversation.mockRejectedValue(
      new Error("conversation boom")
    );
    renderSheet();
    await openSendToPerson(user);
    await screen.findByTestId("share-choice-new");
    await user.click(screen.getByTestId("share-choice-new"));
    await user.click(screen.getByTestId("share-submit"));

    await screen.findByText(/Conversation creation failed/i);
    // No link, no message; the failure is visible, not concealed.
    expect(share.createShareLink).not.toHaveBeenCalled();
    expect(dm.sendDirectMessage).not.toHaveBeenCalled();
  });

  it("does not create a second Conversation when link creation fails after a new Conversation succeeded", async () => {
    const user = userEvent.setup();
    share.createShareLink
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce({
        ok: true,
        token: "tok-3",
        url: "/share/tok-3",
        expires_at: null,
      });
    renderSheet();
    await openSendToPerson(user);
    await screen.findByTestId("share-choice-new");
    await user.click(screen.getByTestId("share-choice-new"));
    await user.click(screen.getByTestId("share-submit"));

    await screen.findByText(/Share link creation failed/i);
    expect(dm.createDirectMessageConversation).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId("share-retry-link"));
    await waitFor(() => {
      expect(dm.sendDirectMessage).toHaveBeenCalledTimes(1);
    });
    // Retry reused the already-created Conversation.
    expect(dm.createDirectMessageConversation).toHaveBeenCalledTimes(1);
    expect(dm.sendDirectMessage.mock.calls[0][0]).toBe("c3");
  });

  it("reuses the floating/destination Conversation state via the shared People state", async () => {
    const user = userEvent.setup();
    const state = makeState({ floatingConversationId: "c2", floatingMode: "open" });
    renderSheet({ peopleState: state });
    await openSendToPerson(user);
    await screen.findByTestId("share-choice-c2");
    await user.click(screen.getByTestId("share-choice-c2"));
    await user.click(screen.getByTestId("share-submit"));
    await waitFor(() => {
      expect(state.openConversation).toHaveBeenCalledWith("c2", undefined);
      expect(state.openPeople).toHaveBeenCalled();
    });
    // No second state owner or window manager is introduced.
    expect(state.popOutConversation).not.toHaveBeenCalled();
  });
});
