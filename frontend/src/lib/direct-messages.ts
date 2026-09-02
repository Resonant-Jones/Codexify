/**
 * Canonical authenticated client for the direct-messaging backend surface
 * (ADR-079/080), plus pure projections for the conversation-first Inbox.
 *
 * Field names mirror the runtime contract in
 * `guardian/routes/direct_messages.py`; nothing here adds backend
 * authority semantics.  The Inbox projection keys peer filtering by
 * `relationship_id` — the Relationship is the invariant person container
 * while each row remains one Conversation_ID.
 */

import api from "@/lib/api";

export type DirectMessageSocialProfile = {
  node_id: string;
  profile_id: string;
  username: string | null;
  username_state: "unset" | "active";
  display_name: string | null;
  avatar_url: string | null;
};

export type DirectMessageRelationship = {
  relationship_id: string;
  participants: DirectMessageSocialProfile[];
  /** Caller-relative: the OTHER participant, or null (defensive). */
  peer: DirectMessageSocialProfile | null;
  created_at: string;
  updated_at: string;
};

export type DirectMessageConversationOrigin = {
  created_by_profile_id: string | null;
  origin_project_id: number | null;
  origin_thread_id: number | null;
  created_at: string;
};

export type DirectMessageConversationPlacement = {
  project_id: number | null;
  created_at: string | null;
  updated_at: string | null;
};

export type LatestMessageProjection = {
  message_id: string;
  sender_profile_id: string;
  preview: string;
  created_at: string;
};

export type DirectMessageConversation = {
  conversation_id: string;
  relationship_id: string;
  kind: string;
  created_at: string;
  latest_activity_at: string;
  participants: DirectMessageSocialProfile[];
  /** Caller-relative: the OTHER participant, or null (defensive). */
  peer: DirectMessageSocialProfile | null;
  origin: DirectMessageConversationOrigin;
  placement: DirectMessageConversationPlacement;
  /** Additive read projection: bounded latest-message preview or null. */
  latest_message: LatestMessageProjection | null;
};

export type DirectMessageEnvelope = {
  protocol_version: string;
  message_id: string;
  conversation_id: string;
  source: { node_id: string; profile_id: string };
  destination: { node_id: string; profile_id: string };
  content: { type: string; body: string };
  created_at: string;
};

export type DirectMessageSendResult = {
  ok: boolean;
  replayed: boolean;
  message: DirectMessageEnvelope;
};

export type ConversationOriginInput = {
  origin_project_id?: number | null;
  origin_thread_id?: number | null;
};

export class DirectMessageApiError extends Error {
  status: number;
  code: string | null;

  constructor(status: number, message: string, code: string | null = null) {
    super(message);
    this.name = "DirectMessageApiError";
    this.status = status;
    this.code = code;
  }
}

function errorCodeFromDetail(detail: unknown): string | null {
  if (!detail || typeof detail !== "object") return null;
  const record = detail as { error?: unknown };
  return typeof record.error === "string" ? record.error : null;
}

export function normalizeDirectMessageError(error: unknown): DirectMessageApiError {
  if (error instanceof DirectMessageApiError) return error;
  const responseStatus = (error as { response?: { status?: unknown } } | null)
    ?.response?.status;
  const status =
    typeof responseStatus === "number"
      ? responseStatus
      : typeof (error as { status?: unknown } | null)?.status === "number"
        ? ((error as { status: number }).status)
        : 0;
  const code = errorCodeFromDetail(
    (error as { response?: { data?: { detail?: unknown } } } | null)?.response
      ?.data?.detail
  );
  return new DirectMessageApiError(
    status,
    error instanceof Error ? error.message : "Direct messaging request failed",
    code
  );
}

export async function fetchOwnSocialIdentity(): Promise<DirectMessageSocialProfile> {
  const response = await api.get<{ profile: DirectMessageSocialProfile }>(
    "/api/profile/social-identity"
  );
  return response.data.profile;
}

export async function searchDirectMessageProfiles(
  query: string,
  limit = 20
): Promise<DirectMessageSocialProfile[]> {
  try {
    const response = await api.get<{
      ok: boolean;
      profiles: DirectMessageSocialProfile[];
    }>("/api/direct-messages/profiles", {
      params: {
        q: query.trim(),
        limit: Math.min(Math.max(limit, 1), 20),
      },
    });
    return response.data.profiles ?? [];
  } catch (error) {
    throw normalizeDirectMessageError(error);
  }
}

export async function resolveDirectMessageRelationship(
  destinationNodeId: string,
  destinationProfileId: string
): Promise<DirectMessageRelationship> {
  try {
    const response = await api.post<{
      ok: boolean;
      relationship: DirectMessageRelationship;
    }>("/api/direct-messages/relationships", {
      destination_node_id: destinationNodeId,
      destination_profile_id: destinationProfileId,
    });
    return response.data.relationship;
  } catch (error) {
    throw normalizeDirectMessageError(error);
  }
}

export async function fetchDirectMessageRelationships(): Promise<
  DirectMessageRelationship[]
> {
  try {
    const response = await api.get<{
      ok: boolean;
      relationships: DirectMessageRelationship[];
    }>("/api/direct-messages/relationships");
    return response.data.relationships ?? [];
  } catch (error) {
    throw normalizeDirectMessageError(error);
  }
}

export async function fetchDirectMessageConversations(): Promise<
  DirectMessageConversation[]
> {
  try {
    const response = await api.get<{
      ok: boolean;
      conversations: DirectMessageConversation[];
    }>("/api/direct-messages/conversations");
    return response.data.conversations ?? [];
  } catch (error) {
    throw normalizeDirectMessageError(error);
  }
}

export async function fetchRelationshipConversations(
  relationshipId: string
): Promise<DirectMessageConversation[]> {
  try {
    const response = await api.get<{
      ok: boolean;
      conversations: DirectMessageConversation[];
    }>(
      `/api/direct-messages/relationships/${encodeURIComponent(relationshipId)}/conversations`
    );
    return response.data.conversations ?? [];
  } catch (error) {
    throw normalizeDirectMessageError(error);
  }
}

/**
 * Create a new Conversation inside an existing Relationship.  Origin
 * (Project/Thread) is caller-supplied and immutable server-side; passing
 * neither creates a General-origin Conversation with null origin and
 * null placement.
 */
export async function createDirectMessageConversation(
  relationshipId: string,
  origin: ConversationOriginInput = {}
): Promise<DirectMessageConversation> {
  const body: Record<string, unknown> = {};
  if (origin.origin_project_id != null) {
    body.origin_project_id = origin.origin_project_id;
  }
  if (origin.origin_thread_id != null) {
    body.origin_thread_id = origin.origin_thread_id;
  }
  try {
    const response = await api.post<{
      ok: boolean;
      conversation: DirectMessageConversation;
    }>(
      `/api/direct-messages/relationships/${encodeURIComponent(relationshipId)}/conversations`,
      body
    );
    return response.data.conversation;
  } catch (error) {
    throw normalizeDirectMessageError(error);
  }
}

/**
 * General-origin creation: never sends Project/Thread origin.  Every call
 * returns a new Conversation_ID while the Relationship is reused.
 */
export function createGeneralDirectMessageConversation(
  relationshipId: string
): Promise<DirectMessageConversation> {
  return createDirectMessageConversation(relationshipId, {});
}

export async function fetchDirectMessageConversation(
  conversationId: string
): Promise<DirectMessageConversation> {
  try {
    const response = await api.get<{
      ok: boolean;
      conversation: DirectMessageConversation;
    }>(
      `/api/direct-messages/conversations/${encodeURIComponent(conversationId)}`
    );
    return response.data.conversation;
  } catch (error) {
    throw normalizeDirectMessageError(error);
  }
}

export async function fetchDirectMessageMessages(
  conversationId: string,
  options: { limit?: number; beforeId?: string | null } = {}
): Promise<DirectMessageEnvelope[]> {
  try {
    const response = await api.get<{
      ok: boolean;
      messages: DirectMessageEnvelope[];
    }>(
      `/api/direct-messages/conversations/${encodeURIComponent(conversationId)}/messages`,
      {
        params: {
          limit: Math.min(Math.max(options.limit ?? 200, 1), 200),
          ...(options.beforeId ? { before_id: options.beforeId } : {}),
        },
      }
    );
    return response.data.messages ?? [];
  } catch (error) {
    throw normalizeDirectMessageError(error);
  }
}

/**
 * Durably send one message.  The client message key is stable per attempt
 * so retries replay the original message instead of duplicating.
 */
export async function sendDirectMessage(
  conversationId: string,
  body: string,
  clientMessageKey?: string
): Promise<DirectMessageSendResult> {
  const payloadBody: Record<string, unknown> = { body };
  if (clientMessageKey) payloadBody.client_message_key = clientMessageKey;
  try {
    const response = await api.post<DirectMessageSendResult>(
      `/api/direct-messages/conversations/${encodeURIComponent(conversationId)}/messages`,
      payloadBody
    );
    return response.data;
  } catch (error) {
    throw normalizeDirectMessageError(error);
  }
}

/**
 * Canonical project scope for a thread the caller currently occupies.
 *
 * The backend owns thread→project truth; this returns `project_id` only
 * when the authenticated thread read succeeds and carries one.  Any
 * failure (or a thread with no project) fails closed to `null` — origin
 * is never guessed from local UI assumptions.
 */
export async function fetchThreadProjectScope(
  threadId: number
): Promise<number | null> {
  try {
    const response = await api.get<{
      thread?: { project_id?: unknown } | null;
    }>(`/threads/${encodeURIComponent(String(threadId))}`);
    const raw = response.data?.thread?.project_id;
    const parsed = typeof raw === "number" ? raw : Number(raw);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  } catch {
    return null;
  }
}

/**
 * Caller-visible project label map (id → name) from the caller's own
 * project listing.  Used only to label the caller's OWN placement/origin
 * ids; peer-private identifiers never appear in the DM payloads.
 */
export async function fetchProjectLabelMap(): Promise<Map<number, string>> {
  const labels = new Map<number, string>();
  try {
    const response = await api.get<Array<{ id?: unknown; name?: unknown }>>(
      "/api/projects"
    );
    for (const entry of Array.isArray(response.data) ? response.data : []) {
      const id = typeof entry.id === "number" ? entry.id : Number(entry.id);
      if (Number.isFinite(id) && typeof entry.name === "string") {
        labels.set(id, entry.name);
      }
    }
  } catch {
    // Labels are presentation-only; failure means generic labels.
  }
  return labels;
}

/** Bounded presentation label for a social profile. */
export function peerPresentationLabel(
  profile: DirectMessageSocialProfile | null | undefined
): string {
  if (!profile) return "Profile";
  const display = (profile.display_name ?? "").trim();
  if (display) return display;
  const username = (profile.username ?? "").trim();
  if (username) return username;
  return "Profile";
}

export type PeerFilterOption = {
  relationship_id: string;
  peer_profile_id: string;
  label: string;
};

/**
 * Relationship-backed person-filter options derived from the Inbox
 * conversation list.  The Relationship is the invariant container: the
 * durable key is `relationship_id` and a username change can never change
 * which Conversations belong to a selected peer.  Options follow the
 * server activity order (first appearance of a Relationship sets its
 * position).
 */
export function buildPeerFilterOptions(
  conversations: readonly DirectMessageConversation[]
): PeerFilterOption[] {
  const options: PeerFilterOption[] = [];
  const seen = new Set<string>();
  for (const conversation of conversations) {
    if (seen.has(conversation.relationship_id)) continue;
    seen.add(conversation.relationship_id);
    const peer = conversation.peer;
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
  conversations: readonly DirectMessageConversation[],
  relationshipId: string | null
): DirectMessageConversation[] {
  if (relationshipId === null) return [...conversations];
  return conversations.filter(
    (conversation) => conversation.relationship_id === relationshipId
  );
}
