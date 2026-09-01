/**
 * Relationship-scoped direct-message Inbox API client and pure helpers.
 *
 * This module is a thin projection over the accepted ADR-077/078 HTTP
 * surface.  It exposes only social profile fields (Node_ID, Profile_ID,
 * username, display name, avatar) — never email or internal user_id —
 * and keys peer filtering by `relationship_id`, never by username or
 * display strings.
 */

import api from "@/lib/api";

export type SocialProfilePayload = {
  node_id: string;
  profile_id: string;
  username: string | null;
  username_state?: string | null;
  display_name?: string | null;
  avatar_url?: string | null;
};

export type LatestMessageProjection = {
  message_id: string;
  sender_profile_id: string;
  preview: string;
  created_at: string;
};

export type ConversationOriginProjection = {
  created_by_profile_id: string | null;
  origin_project_id: number | null;
  origin_thread_id: number | null;
  created_at: string;
};

export type ConversationPlacementProjection = {
  project_id: number | null;
  created_at: string | null;
  updated_at: string | null;
};

export type ConversationProjection = {
  conversation_id: string;
  relationship_id: string;
  kind: string;
  created_at: string;
  latest_activity_at: string;
  participants: SocialProfilePayload[];
  origin: ConversationOriginProjection;
  placement: ConversationPlacementProjection;
  latest_message: LatestMessageProjection | null;
};

export type RelationshipProjection = {
  relationship_id: string;
  participants: SocialProfilePayload[];
  peer: SocialProfilePayload | null;
  created_at: string;
  updated_at: string;
};

export type MessageEnvelope = {
  protocol_version?: string;
  message_id: string;
  conversation_id: string;
  source: { node_id: string; profile_id: string };
  destination: { node_id: string; profile_id: string };
  content: { type: string; body: string };
  created_at: string;
};

export type SendMessageResult = {
  replayed: boolean;
  message: MessageEnvelope;
};

type OkEnvelope<T> = { ok: boolean } & T;

/** Bounded presentation label for a social profile. */
export function peerPresentationLabel(
  profile: SocialProfilePayload | null | undefined
): string {
  if (!profile) return "Profile";
  const username = (profile.username ?? "").trim();
  if (username) return username;
  const display = (profile.display_name ?? "").trim();
  if (display) return display;
  return "Profile";
}

/** The peer participant (the participant that is not the caller). */
export function peerForCaller(
  participants: SocialProfilePayload[],
  selfProfileId: string | null | undefined
): SocialProfilePayload | null {
  if (!selfProfileId) return null;
  return (
    participants.find((participant) => participant.profile_id !== selfProfileId) ??
    null
  );
}

export type PeerFilterOption = {
  relationship_id: string;
  peer_profile_id: string;
  label: string;
};

/**
 * Derive the relationship-backed person-filter options from the Inbox
 * conversation list.  Options follow the server activity order: the
 * first appearance of a Relationship in the list sets its position.
 * The durable key is `relationship_id`; the label is presentation only.
 */
export function buildPeerFilterOptions(
  conversations: readonly ConversationProjection[],
  selfProfileId: string | null | undefined
): PeerFilterOption[] {
  const options: PeerFilterOption[] = [];
  const seen = new Set<string>();
  for (const conversation of conversations) {
    if (seen.has(conversation.relationship_id)) continue;
    seen.add(conversation.relationship_id);
    const peer = peerForCaller(conversation.participants, selfProfileId);
    if (!peer) continue;
    options.push({
      relationship_id: conversation.relationship_id,
      peer_profile_id: peer.profile_id,
      label: peerPresentationLabel(peer),
    });
  }
  return options;
}

/**
 * Person-filtered projection.  A `null` relationship means "All".
 * Server ordering is preserved exactly; filtering never reorders or
 * collapses Conversations.
 */
export function filterConversationsByRelationship(
  conversations: readonly ConversationProjection[],
  relationshipId: string | null
): ConversationProjection[] {
  if (relationshipId === null) return [...conversations];
  return conversations.filter(
    (conversation) => conversation.relationship_id === relationshipId
  );
}

export async function fetchDirectMessageConversations(): Promise<
  ConversationProjection[]
> {
  const response = await api.get<OkEnvelope<{ conversations: ConversationProjection[] }>>(
    "/api/direct-messages/conversations"
  );
  return response.data.conversations ?? [];
}

export async function fetchDirectMessageRelationships(): Promise<
  RelationshipProjection[]
> {
  const response = await api.get<OkEnvelope<{ relationships: RelationshipProjection[] }>>(
    "/api/direct-messages/relationships"
  );
  return response.data.relationships ?? [];
}

export async function fetchOwnSocialIdentity(): Promise<SocialProfilePayload> {
  const response = await api.get<OkEnvelope<{ profile: SocialProfilePayload }>>(
    "/api/profile/social-identity"
  );
  return response.data.profile;
}

export async function searchDirectMessageProfiles(
  query: string
): Promise<SocialProfilePayload[]> {
  const response = await api.get<OkEnvelope<{ profiles: SocialProfilePayload[] }>>(
    "/api/direct-messages/profiles",
    { params: { q: query, limit: 20 } }
  );
  return response.data.profiles ?? [];
}

export async function resolveDirectMessageRelationship(
  destinationNodeId: string,
  destinationProfileId: string
): Promise<RelationshipProjection> {
  const response = await api.post<OkEnvelope<{ relationship: RelationshipProjection }>>(
    "/api/direct-messages/relationships",
    {
      destination_node_id: destinationNodeId,
      destination_profile_id: destinationProfileId,
    }
  );
  return response.data.relationship;
}

/**
 * Create a new General-origin Conversation inside an existing
 * Relationship.  No Project/Thread origin and no placement are ever
 * sent for the General Inbox path; every call creates a new
 * Conversation_ID while the Relationship is reused.
 */
export async function createGeneralDirectMessageConversation(
  relationshipId: string
): Promise<ConversationProjection> {
  const response = await api.post<
    OkEnvelope<{ conversation: ConversationProjection }>
  >(
    `/api/direct-messages/relationships/${encodeURIComponent(relationshipId)}/conversations`,
    {}
  );
  return response.data.conversation;
}

export async function fetchDirectMessageConversation(
  conversationId: string
): Promise<ConversationProjection> {
  const response = await api.get<OkEnvelope<{ conversation: ConversationProjection }>>(
    `/api/direct-messages/conversations/${encodeURIComponent(conversationId)}`
  );
  return response.data.conversation;
}

export async function fetchDirectMessageMessages(
  conversationId: string,
  options: { limit?: number; beforeId?: string } = {}
): Promise<MessageEnvelope[]> {
  const response = await api.get<OkEnvelope<{ messages: MessageEnvelope[] }>>(
    `/api/direct-messages/conversations/${encodeURIComponent(conversationId)}/messages`,
    {
      params: {
        limit: options.limit ?? 100,
        ...(options.beforeId ? { before_id: options.beforeId } : {}),
      },
    }
  );
  return response.data.messages ?? [];
}

/**
 * Durably send one message.  The `clientMessageKey` must be stable per
 * attempt so retries replay the original message instead of duplicating.
 */
export async function sendDirectMessage(
  conversationId: string,
  body: string,
  clientMessageKey: string
): Promise<SendMessageResult> {
  const response = await api.post<OkEnvelope<SendMessageResult>>(
    `/api/direct-messages/conversations/${encodeURIComponent(conversationId)}/messages`,
    {
      body,
      client_message_key: clientMessageKey,
    }
  );
  return {
    replayed: response.data.replayed,
    message: response.data.message,
  };
}

export function directMessageErrorStatus(error: unknown): number | null {
  const status = (error as { response?: { status?: unknown } } | null)?.response
    ?.status;
  return typeof status === "number" ? status : null;
}

/**
 * Merge one server-confirmed message into a chronological message list.
 * Idempotent replays (same message_id) never produce duplicates and are
 * ordered by (created_at, message_id) like the server readback.
 */
export function mergeConfirmedMessage(
  messages: readonly MessageEnvelope[],
  confirmed: MessageEnvelope
): MessageEnvelope[] {
  const next = messages.filter(
    (message) => message.message_id !== confirmed.message_id
  );
  next.push(confirmed);
  return next.sort((left, right) => {
    if (left.created_at !== right.created_at) {
      return left.created_at < right.created_at ? -1 : 1;
    }
    return left.message_id < right.message_id ? -1 : 1;
  });
}

/** Prepend an older page while preserving deterministic ordering. */
export function prependOlderMessages(
  messages: readonly MessageEnvelope[],
  older: readonly MessageEnvelope[]
): MessageEnvelope[] {
  const known = new Set(messages.map((message) => message.message_id));
  const fresh = older.filter((message) => !known.has(message.message_id));
  return mergeList([...fresh, ...messages]);
}

function mergeList(messages: MessageEnvelope[]): MessageEnvelope[] {
  return messages.sort((left, right) => {
    if (left.created_at !== right.created_at) {
      return left.created_at < right.created_at ? -1 : 1;
    }
    return left.message_id < right.message_id ? -1 : 1;
  });
}
