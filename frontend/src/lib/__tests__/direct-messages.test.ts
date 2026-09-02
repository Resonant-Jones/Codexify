import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import api from "@/lib/api";
import {
  buildPeerFilterOptions,
  createDirectMessageConversation,
  createGeneralDirectMessageConversation,
  fetchDirectMessageConversation,
  fetchDirectMessageConversations,
  fetchDirectMessageMessages,
  fetchDirectMessageRelationships,
  fetchRelationshipConversations,
  fetchThreadProjectScope,
  filterConversationsByRelationship,
  normalizeDirectMessageError,
  peerPresentationLabel,
  resolveDirectMessageRelationship,
  searchDirectMessageProfiles,
  sendDirectMessage,
  type DirectMessageConversation,
  type DirectMessageEnvelope,
  type DirectMessageSocialProfile,
} from "@/lib/direct-messages";

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockedGet = vi.mocked(api.get);
const mockedPost = vi.mocked(api.post);

afterEach(() => {
  vi.clearAllMocks();
});

function profile(
  id: string,
  username: string | null = null,
  displayName: string | null = null
): DirectMessageSocialProfile {
  return {
    node_id: `node-${id}`,
    profile_id: id,
    username,
    username_state: "active",
    display_name: displayName ?? (username ? `Display ${username}` : null),
    avatar_url: null,
  };
}

function conversation(
  id: string,
  relationshipId: string,
  peer: DirectMessageSocialProfile
): DirectMessageConversation {
  return {
    conversation_id: id,
    relationship_id: relationshipId,
    kind: "direct",
    created_at: "2026-09-01T00:00:00Z",
    latest_activity_at: "2026-09-01T00:00:00Z",
    participants: [profile("alice", "alice"), peer],
    peer,
    origin: {
      created_by_profile_id: peer.profile_id,
      origin_project_id: null,
      origin_thread_id: null,
      created_at: "2026-09-01T00:00:00Z",
    },
    placement: { project_id: null, created_at: null, updated_at: null },
    latest_message: null,
  };
}

function message(
  id: string,
  body: string,
  createdAt: string
): DirectMessageEnvelope {
  return {
    protocol_version: "v1",
    message_id: id,
    conversation_id: "conv-1",
    source: { node_id: "node-a", profile_id: "alice" },
    destination: { node_id: "node-b", profile_id: "bob" },
    content: { type: "text/plain", body },
    created_at: createdAt,
  };
}

describe("peerPresentationLabel", () => {
  it("falls back to a generic label for a missing profile", () => {
    expect(peerPresentationLabel(null)).toBe("Profile");
    expect(peerPresentationLabel(undefined)).toBe("Profile");
  });

  it("prefers display name over username", () => {
    expect(peerPresentationLabel(profile("bob", "bob_social", "Bob"))).toBe(
      "Bob"
    );
  });

  it("falls back to username when display name is absent", () => {
    const withoutDisplay: DirectMessageSocialProfile = {
      ...profile("bob", "bob_social"),
      display_name: null,
    };
    expect(peerPresentationLabel(withoutDisplay)).toBe("bob_social");
  });
});

describe("buildPeerFilterOptions", () => {
  it("keys options by relationship_id and dedupes by first appearance", () => {
    const bob = profile("bob", "bob");
    const carol = profile("carol", "carol");
    const conversations = [
      conversation("c1", "rel-ab", bob),
      conversation("c2", "rel-ac", carol),
      conversation("c3", "rel-ab", bob),
    ];
    const options = buildPeerFilterOptions(conversations);
    expect(options.map((option) => option.relationship_id)).toEqual([
      "rel-ab",
      "rel-ac",
    ]);
    expect(options.map((option) => option.peer_profile_id)).toEqual([
      "bob",
      "carol",
    ]);
    expect(options[0].label).toBe("Display bob");
  });

  it("skips conversations without a server-projected peer", () => {
    const conversations = [
      { ...conversation("c1", "rel-ab", profile("bob", "bob")), peer: null },
      conversation("c2", "rel-ac", profile("carol", "carol")),
    ];
    const options = buildPeerFilterOptions(conversations);
    expect(options.map((option) => option.relationship_id)).toEqual(["rel-ac"]);
  });
});

describe("filterConversationsByRelationship", () => {
  const bob = profile("bob", "bob");
  const carol = profile("carol", "carol");
  const conversations = [
    conversation("c1", "rel-ab", bob),
    conversation("c2", "rel-ac", carol),
    conversation("c3", "rel-ab", bob),
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

describe("createDirectMessageConversation", () => {
  const bob = profile("bob", "bob");

  beforeEach(() => {
    mockedPost.mockResolvedValue({
      data: { ok: true, conversation: conversation("c-new", "rel-ab", bob) },
    } as never);
  });

  it("posts an empty body for a General-origin conversation", async () => {
    const created = await createDirectMessageConversation("rel-ab");
    expect(mockedPost).toHaveBeenCalledWith(
      "/api/direct-messages/relationships/rel-ab/conversations",
      {}
    );
    expect(created.conversation_id).toBe("c-new");
  });

  it("carries Project/Thread origin when supplied", async () => {
    await createDirectMessageConversation("rel-ab", {
      origin_project_id: 7,
      origin_thread_id: 12,
    });
    expect(mockedPost).toHaveBeenCalledWith(
      "/api/direct-messages/relationships/rel-ab/conversations",
      { origin_project_id: 7, origin_thread_id: 12 }
    );
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
  it("sends the body with a stable client message key and unwraps the result", async () => {
    const envelope = message("m1", "hello", "2026-09-01T01:00:00Z");
    mockedPost.mockResolvedValue({
      data: { ok: true, replayed: false, message: envelope },
    } as never);

    const result = await sendDirectMessage("conv-1", "hello", "attempt-1");
    expect(mockedPost).toHaveBeenCalledWith(
      "/api/direct-messages/conversations/conv-1/messages",
      { body: "hello", client_message_key: "attempt-1" }
    );
    expect(result.ok).toBe(true);
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
      { params: { limit: 200 } }
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
    const bob = profile("bob", "bob");
    mockedGet.mockResolvedValue({
      data: { ok: true, conversations: [conversation("c1", "rel-ab", bob)] },
    } as never);

    const rows = await fetchDirectMessageConversations();
    expect(rows).toHaveLength(1);
    expect(rows[0].conversation_id).toBe("c1");
    expect(mockedGet).toHaveBeenCalledWith("/api/direct-messages/conversations");
  });
});

describe("fetchDirectMessageRelationships", () => {
  it("reads the relationships envelope", async () => {
    mockedGet.mockResolvedValue({
      data: { ok: true, relationships: [] },
    } as never);

    const rows = await fetchDirectMessageRelationships();
    expect(rows).toEqual([]);
    expect(mockedGet).toHaveBeenCalledWith("/api/direct-messages/relationships");
  });
});

describe("fetchRelationshipConversations", () => {
  it("reads the relationship conversations envelope", async () => {
    mockedGet.mockResolvedValue({
      data: { ok: true, conversations: [] },
    } as never);

    const rows = await fetchRelationshipConversations("rel-ab");
    expect(rows).toEqual([]);
    expect(mockedGet).toHaveBeenCalledWith(
      "/api/direct-messages/relationships/rel-ab/conversations"
    );
  });
});

describe("fetchDirectMessageConversation", () => {
  it("reads the conversation envelope", async () => {
    const bob = profile("bob", "bob");
    mockedGet.mockResolvedValue({
      data: { ok: true, conversation: conversation("c1", "rel-ab", bob) },
    } as never);

    const row = await fetchDirectMessageConversation("c1");
    expect(row.conversation_id).toBe("c1");
    expect(mockedGet).toHaveBeenCalledWith(
      "/api/direct-messages/conversations/c1"
    );
  });
});

describe("fetchThreadProjectScope", () => {
  it("reads project scope from the mounted thread-detail route", async () => {
    mockedGet.mockResolvedValue({
      data: { thread: { project_id: 7 } },
    } as never);

    await expect(fetchThreadProjectScope(12)).resolves.toBe(7);
    expect(mockedGet).toHaveBeenCalledWith("/threads/12");
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

describe("normalizeDirectMessageError", () => {
  it("surfaces the response status and error code", () => {
    const normalized = normalizeDirectMessageError({
      response: { status: 404, data: { detail: { error: "conversation_not_found" } } },
    });
    expect(normalized.status).toBe(404);
    expect(normalized.code).toBe("conversation_not_found");
  });

  it("falls back to a generic failure for unknown shapes", () => {
    const normalized = normalizeDirectMessageError(new Error("boom"));
    expect(normalized.status).toBe(0);
    expect(normalized.code).toBeNull();
    expect(normalized.message).toBe("boom");
  });
});
