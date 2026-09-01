import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import api from "@/lib/api";
import {
  buildPeerFilterOptions,
  createGeneralDirectMessageConversation,
  fetchDirectMessageConversations,
  fetchDirectMessageMessages,
  filterConversationsByRelationship,
  mergeConfirmedMessage,
  peerForCaller,
  peerPresentationLabel,
  prependOlderMessages,
  resolveDirectMessageRelationship,
  searchDirectMessageProfiles,
  sendDirectMessage,
  type ConversationProjection,
  type MessageEnvelope,
  type SocialProfilePayload,
} from "@/lib/direct-messages";

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockedGet = vi.mocked(api.get);
const mockedPost = vi.mocked(api.post);

function profile(id: string, username: string | null = null): SocialProfilePayload {
  return {
    node_id: `node-${id}`,
    profile_id: id,
    username,
    display_name: username ? `Display ${username}` : null,
  };
}

function message(
  id: string,
  body: string,
  createdAt: string
): MessageEnvelope {
  return {
    message_id: id,
    conversation_id: "conv-1",
    source: { node_id: "node-a", profile_id: "alice" },
    destination: { node_id: "node-b", profile_id: "bob" },
    content: { type: "text", body },
    created_at: createdAt,
  };
}

function conversation(
  id: string,
  relationshipId: string,
  participants: SocialProfilePayload[]
): ConversationProjection {
  return {
    conversation_id: id,
    relationship_id: relationshipId,
    kind: "general",
    created_at: "2026-09-01T00:00:00Z",
    latest_activity_at: "2026-09-01T00:00:00Z",
    participants,
    origin: {
      created_by_profile_id: participants[0]?.profile_id ?? null,
      origin_project_id: null,
      origin_thread_id: null,
      created_at: "2026-09-01T00:00:00Z",
    },
    placement: { project_id: null, created_at: null, updated_at: null },
    latest_message: null,
  };
}

describe("peerPresentationLabel", () => {
  it("falls back to a generic label for a missing profile", () => {
    expect(peerPresentationLabel(null)).toBe("Profile");
    expect(peerPresentationLabel(undefined)).toBe("Profile");
  });

  it("prefers username over display name", () => {
    expect(peerPresentationLabel(profile("bob", "bob_social"))).toBe("bob_social");
  });

  it("falls back to display name when username is absent", () => {
    const withDisplay = { ...profile("bob", null), display_name: "Bob" };
    expect(peerPresentationLabel(withDisplay)).toBe("Bob");
  });

  it("falls back to a generic label when both are blank", () => {
    const blank = { ...profile("bob", null), display_name: "  " };
    expect(peerPresentationLabel(blank)).toBe("Profile");
  });
});

describe("peerForCaller", () => {
  it("returns the participant that is not the caller", () => {
    const participants = [profile("alice", "alice"), profile("bob", "bob")];
    expect(peerForCaller(participants, "alice")?.profile_id).toBe("bob");
  });

  it("returns null without a self profile id", () => {
    expect(peerForCaller([profile("bob", "bob")], null)).toBeNull();
  });

  it("returns null when no non-self participant exists", () => {
    expect(peerForCaller([profile("alice", "alice")], "alice")).toBeNull();
  });
});

describe("buildPeerFilterOptions", () => {
  it("dedupes by relationship and follows first-appearance order", () => {
    const alice = profile("alice", "alice");
    const bob = profile("bob", "bob");
    const carol = profile("carol", "carol");
    const conversations = [
      conversation("c1", "rel-ab", [alice, bob]),
      conversation("c2", "rel-ac", [alice, carol]),
      conversation("c3", "rel-ab", [alice, bob]),
    ];
    const options = buildPeerFilterOptions(conversations, "alice");
    expect(options.map((option) => option.relationship_id)).toEqual([
      "rel-ab",
      "rel-ac",
    ]);
    expect(options.map((option) => option.peer_profile_id)).toEqual([
      "bob",
      "carol",
    ]);
    expect(options[0].label).toBe("bob");
  });

  it("skips conversations where the peer cannot be resolved", () => {
    const alice = profile("alice", "alice");
    const conversations = [
      conversation("c1", "rel-solo", [alice]),
      conversation("c2", "rel-ab", [alice, profile("bob", "bob")]),
    ];
    const options = buildPeerFilterOptions(conversations, "alice");
    expect(options.map((option) => option.relationship_id)).toEqual(["rel-ab"]);
  });
});

describe("filterConversationsByRelationship", () => {
  const alice = profile("alice", "alice");
  const bob = profile("bob", "bob");
  const conversations = [
    conversation("c1", "rel-ab", [alice, bob]),
    conversation("c2", "rel-ac", [alice, profile("carol", "carol")]),
    conversation("c3", "rel-ab", [alice, bob]),
  ];

  it("returns everything for the All view", () => {
    expect(filterConversationsByRelationship(conversations, null)).toEqual(
      conversations
    );
  });

  it("filters by relationship without collapsing or reordering", () => {
    const filtered = filterConversationsByRelationship(conversations, "rel-ab");
    expect(filtered.map((row) => row.conversation_id)).toEqual(["c1", "c3"]);
  });
});

describe("createGeneralDirectMessageConversation", () => {
  beforeEach(() => {
    mockedPost.mockResolvedValue({
      data: { ok: true, conversation: conversation("c-new", "rel-ab", []) },
    } as never);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("posts an empty body to the relationship conversations endpoint", async () => {
    const created = await createGeneralDirectMessageConversation("rel-ab");
    expect(mockedPost).toHaveBeenCalledWith(
      "/api/direct-messages/relationships/rel-ab/conversations",
      {}
    );
    expect(created.conversation_id).toBe("c-new");
  });

  it("URL-encodes the relationship id", async () => {
    await createGeneralDirectMessageConversation("rel/a b");
    expect(mockedPost).toHaveBeenCalledWith(
      "/api/direct-messages/relationships/rel%2Fa%20b/conversations",
      {}
    );
  });
});

describe("sendDirectMessage", () => {
  it("sends the body with a stable client message key", async () => {
    const envelope = message("m1", "hello", "2026-09-01T01:00:00Z");
    mockedPost.mockResolvedValue({
      data: { ok: true, replayed: false, message: envelope },
    } as never);

    const result = await sendDirectMessage("conv-1", "hello", "attempt-1");
    expect(mockedPost).toHaveBeenCalledWith(
      "/api/direct-messages/conversations/conv-1/messages",
      { body: "hello", client_message_key: "attempt-1" }
    );
    expect(result.replayed).toBe(false);
    expect(result.message.message_id).toBe("m1");
  });
});

describe("fetchDirectMessageMessages", () => {
  it("defaults the page size and passes before_id when present", async () => {
    mockedGet.mockResolvedValue({ data: { ok: true, messages: [] } } as never);

    await fetchDirectMessageMessages("conv-1");
    expect(mockedGet).toHaveBeenLastCalledWith(
      "/api/direct-messages/conversations/conv-1/messages",
      { params: { limit: 100 } }
    );

    await fetchDirectMessageMessages("conv-1", { beforeId: "m9", limit: 10 });
    expect(mockedGet).toHaveBeenLastCalledWith(
      "/api/direct-messages/conversations/conv-1/messages",
      { params: { limit: 10, before_id: "m9" } }
    );
  });
});

describe("fetchDirectMessageConversations", () => {
  it("reads the conversations envelope", async () => {
    mockedGet.mockResolvedValue({
      data: { ok: true, conversations: [conversation("c1", "rel-ab", [])] },
    } as never);

    const rows = await fetchDirectMessageConversations();
    expect(rows).toHaveLength(1);
    expect(rows[0].conversation_id).toBe("c1");
    expect(mockedGet).toHaveBeenCalledWith("/api/direct-messages/conversations");
  });
});

describe("resolveDirectMessageRelationship", () => {
  it("posts the destination Node_ID + Profile_ID", async () => {
    mockedPost.mockResolvedValue({
      data: {
        ok: true,
        relationship: {
          relationship_id: "rel-ab",
          participants: [],
          peer: null,
          created_at: "2026-09-01T00:00:00Z",
          updated_at: "2026-09-01T00:00:00Z",
        },
      },
    } as never);

    const resolved = await resolveDirectMessageRelationship("node-b", "bob");
    expect(mockedPost).toHaveBeenCalledWith("/api/direct-messages/relationships", {
      destination_node_id: "node-b",
      destination_profile_id: "bob",
    });
    expect(resolved.relationship_id).toBe("rel-ab");
  });
});

describe("searchDirectMessageProfiles", () => {
  it("passes the query and reads the profiles envelope", async () => {
    mockedGet.mockResolvedValue({
      data: { ok: true, profiles: [profile("bob", "bob")] },
    } as never);

    const profiles = await searchDirectMessageProfiles("bo");
    expect(mockedGet).toHaveBeenCalledWith("/api/direct-messages/profiles", {
      params: { q: "bo", limit: 20 },
    });
    expect(profiles).toHaveLength(1);
  });
});

describe("mergeConfirmedMessage", () => {
  it("replaces an idempotent replay without duplicating", () => {
    const existing = message("m1", "old", "2026-09-01T01:00:00Z");
    const confirmed = message("m1", "same", "2026-09-01T01:00:00Z");
    const merged = mergeConfirmedMessage([existing], confirmed);
    expect(merged).toHaveLength(1);
    expect(merged[0].content.body).toBe("same");
  });

  it("orders by created_at then message_id", () => {
    const merged = mergeConfirmedMessage(
      [message("m2", "b", "2026-09-01T02:00:00Z")],
      message("m1", "a", "2026-09-01T01:00:00Z")
    );
    expect(merged.map((row) => row.message_id)).toEqual(["m1", "m2"]);
  });
});

describe("prependOlderMessages", () => {
  it("dedupes known messages and preserves chronological order", () => {
    const known = [
      message("m2", "two", "2026-09-01T02:00:00Z"),
      message("m3", "three", "2026-09-01T03:00:00Z"),
    ];
    const older = [
      message("m1", "one", "2026-09-01T01:00:00Z"),
      message("m2", "two", "2026-09-01T02:00:00Z"),
    ];
    const merged = prependOlderMessages(known, older);
    expect(merged.map((row) => row.message_id)).toEqual(["m1", "m2", "m3"]);
  });
});
