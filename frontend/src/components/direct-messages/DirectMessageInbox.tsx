/**
 * Canonical direct-message Inbox: the conversation-first projection over
 * the accepted ADR-077/078 Relationship → Conversations model.
 *
 * - Every row is exactly one Conversation_ID.  Multiple Conversations
 *   with the same peer remain distinct rows; they are never collapsed.
 * - The person filter is Relationship-backed: options are keyed by
 *   `relationship_id` (the invariant person container) and selecting a
 *   peer shows every caller-visible Conversation under that
 *   Relationship — a username change can never change what a filter
 *   shows.
 * - New-conversation creation captures a Project/Thread origin only when
 *   a source thread is supplied; otherwise the creation is General
 *   (null origin, null placement), per the backend contract.
 * - Opening a row opens that exact Conversation_ID in the shared People
 *   conversation view; the portable floating window and drafts live in
 *   the People state owner.
 *
 * The surface fails closed when the accepted `direct_messages` runtime
 * route capability is not `available`.
 */
import { MessageSquarePlus, Search, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { RuntimeRouteCapabilityState } from "@/contracts/supportedProfileRoutes";
import DirectConversation from "@/features/contacts/DirectConversation";
import type { PeopleMessagingState } from "@/features/contacts/usePeopleMessagingState";
import {
  buildPeerFilterOptions,
  createDirectMessageConversation,
  fetchDirectMessageConversations,
  fetchProjectLabelMap,
  fetchThreadProjectScope,
  filterConversationsByRelationship,
  normalizeDirectMessageError,
  peerPresentationLabel,
  resolveDirectMessageRelationship,
  searchDirectMessageProfiles,
  type ConversationOriginInput,
  type DirectMessageConversation,
  type DirectMessageSocialProfile,
} from "@/lib/direct-messages";

type DirectMessageInboxProps = {
  capabilityState: RuntimeRouteCapabilityState;
  /** Canonical route-derived thread scope; only used to capture
   *  Conversation origin at creation time (never to rebind existing
   *  Conversations). */
  sourceThreadId: number | null;
  state: PeopleMessagingState;
};

function profileSubtitle(profile: DirectMessageSocialProfile | null): string {
  if (!profile) return "";
  return profile.username ? `@${profile.username}` : "";
}

function avatarInitials(label: string): string {
  return (
    label
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join("")
      .toUpperCase() || "?"
  );
}

function formatActivity(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function projectLabel(
  projectId: number | null,
  labels: Map<number, string>
): string {
  if (projectId == null) return "Unscoped";
  return labels.get(projectId) ?? "Project";
}

function originLabel(
  conversation: DirectMessageConversation,
  labels: Map<number, string>
): string {
  const originProject = conversation.origin.origin_project_id;
  const originThread = conversation.origin.origin_thread_id;
  if (originProject == null && originThread == null) return "General";
  const project = projectLabel(originProject, labels);
  if (originThread == null) return project;
  return `${project} · Thread ${originThread}`;
}

export default function DirectMessageInbox({
  capabilityState,
  sourceThreadId,
  state,
}: DirectMessageInboxProps) {
  const [conversations, setConversations] = useState<DirectMessageConversation[]>(
    []
  );
  const [projectLabels, setProjectLabels] = useState<Map<number, string>>(
    () => new Map()
  );
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [filterRelationshipId, setFilterRelationshipId] = useState<
    string | null
  >(null);

  const [newConversationOpen, setNewConversationOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<DirectMessageSocialProfile[]>(
    []
  );
  const [searching, setSearching] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const messagingEnabled = capabilityState === "available";

  const reload = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [conversationRows, labels] = await Promise.all([
        fetchDirectMessageConversations(),
        fetchProjectLabelMap(),
      ]);
      setConversations(conversationRows);
      setProjectLabels(labels);
      conversationRows.forEach((conversation) =>
        state.cacheConversationMeta(conversation)
      );
    } catch (error) {
      const normalized = normalizeDirectMessageError(error);
      setLoadError(
        normalized.status === 404
          ? "Direct messaging is unavailable in this profile."
          : normalized.message
      );
    } finally {
      setLoading(false);
    }
  }, [state]);

  useEffect(() => {
    if (!messagingEnabled) return;
    void reload();
  }, [messagingEnabled, reload]);

  const filterOptions = useMemo(
    () => buildPeerFilterOptions(conversations),
    [conversations]
  );

  const visibleConversations = useMemo(
    () => filterConversationsByRelationship(conversations, filterRelationshipId),
    [conversations, filterRelationshipId]
  );

  const filteredPeer = useMemo(() => {
    if (filterRelationshipId === null) return null;
    return visibleConversations[0]?.peer ?? null;
  }, [filterRelationshipId, visibleConversations]);

  const runSearch = useCallback(async (query: string) => {
    const trimmed = query.trim();
    if (trimmed.length === 0) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    setCreateError(null);
    try {
      setSearchResults(await searchDirectMessageProfiles(trimmed));
    } catch (error) {
      setCreateError(normalizeDirectMessageError(error).message);
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  const computeOrigin = useCallback(async (): Promise<ConversationOriginInput> => {
    if (sourceThreadId == null) return {};
    const projectId = await fetchThreadProjectScope(sourceThreadId);
    if (projectId == null) return {};
    return {
      origin_project_id: projectId,
      origin_thread_id: sourceThreadId,
    };
  }, [sourceThreadId]);

  const startConversationWith = useCallback(
    async (profile: DirectMessageSocialProfile): Promise<void> => {
      setCreating(true);
      setCreateError(null);
      try {
        const relationship = await resolveDirectMessageRelationship(
          profile.node_id,
          profile.profile_id
        );
        const origin = await computeOrigin();
        const conversation = await createDirectMessageConversation(
          relationship.relationship_id,
          origin
        );
        state.cacheConversationMeta(conversation);
        setNewConversationOpen(false);
        setSearchQuery("");
        setSearchResults([]);
        await reload();
        state.openConversation(conversation.conversation_id, conversation);
      } catch (error) {
        setCreateError(normalizeDirectMessageError(error).message);
      } finally {
        setCreating(false);
      }
    },
    [computeOrigin, reload, state]
  );

  if (!messagingEnabled) {
    return (
      <main
        className="flex min-h-full items-center justify-center p-6"
        data-testid="direct-messages-unavailable"
      >
        <section
          aria-labelledby="direct-messages-unavailable-heading"
          className="w-full max-w-md rounded-[var(--radius-tile,19px)] border border-[var(--panel-border)] bg-[var(--panel-bg)]/95 p-8 text-[var(--text)] shadow-2xl backdrop-blur-xl"
        >
          <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-subtle)]">
            Codexify
          </p>
          <h1
            className="mt-3 text-2xl font-semibold tracking-[-0.03em]"
            id="direct-messages-unavailable-heading"
          >
            Direct messages unavailable
          </h1>
          <p className="mt-3 text-sm leading-6 text-[var(--text-subtle)]">
            This runtime profile does not provide the direct-messaging Inbox.
            Direct messages remain private-profile functionality and have not
            been widened to other postures.
          </p>
        </section>
      </main>
    );
  }

  if (state.selectedConversationId) {
    return (
      <DirectConversation
        conversationId={state.selectedConversationId}
        state={state}
        projectLabels={projectLabels}
        onBack={state.closeConversation}
      />
    );
  }

  return (
    <section className="flex h-full min-h-0 flex-col" aria-label="Inbox">
      <div className="flex items-center justify-between gap-3 px-4 pb-2 pt-3">
        <div>
          <p className="text-xs uppercase tracking-wider text-[var(--text-subtle)]">
            Direct conversations
          </p>
          <h3 className="text-base font-semibold tracking-[-0.02em] text-[var(--text)]">
            Your conversations
          </h3>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--panel-border)] bg-[var(--panel-bg)] px-3 py-1.5 text-xs font-medium text-[var(--text)] transition-colors hover:bg-[var(--panel-bg-hover,var(--panel-bg))]"
          aria-expanded={newConversationOpen}
          onClick={() => setNewConversationOpen((current) => !current)}
        >
          <MessageSquarePlus size={14} aria-hidden="true" />
          New Conversation
        </button>
      </div>

      {newConversationOpen ? (
        <div className="mx-4 mb-3 rounded-xl border border-[var(--panel-border)] bg-[var(--panel-bg)] p-3" aria-label="New Conversation">
          <div className="flex items-center gap-2 rounded-lg border border-[var(--panel-border)] bg-[var(--background,transparent)] px-2.5 py-1.5">
            <Search size={13} aria-hidden="true" className="text-[var(--text-subtle)]" />
            <input
              type="search"
              className="min-w-0 flex-1 bg-transparent text-sm text-[var(--text)] outline-none placeholder:text-[var(--text-subtle)]"
              value={searchQuery}
              placeholder="Search by Codexify username"
              aria-label="Search profiles by username"
              onChange={(event) => {
                setSearchQuery(event.target.value);
                void runSearch(event.target.value);
              }}
            />
            <button
              type="button"
              aria-label="Close new conversation search"
              className="text-[var(--text-subtle)] hover:text-[var(--text)]"
              onClick={() => {
                setNewConversationOpen(false);
                setSearchQuery("");
                setSearchResults([]);
                setCreateError(null);
              }}
            >
              <X size={13} aria-hidden="true" />
            </button>
          </div>
          {createError ? (
            <p className="mt-2 text-xs text-[var(--text-subtle)]">{createError}</p>
          ) : null}
          {searching ? (
            <p className="mt-2 text-xs text-[var(--text-subtle)]">Searching…</p>
          ) : searchQuery.trim() && searchResults.length === 0 ? (
            <p className="mt-2 text-xs text-[var(--text-subtle)]">
              No profiles match that username.
            </p>
          ) : (
            <div className="mt-2 space-y-1" role="list">
              {searchResults.map((profile) => (
                <button
                  key={`${profile.node_id}:${profile.profile_id}`}
                  type="button"
                  className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left text-sm text-[var(--text)] transition-colors hover:bg-[var(--panel-bg-hover,var(--panel-bg))]"
                  data-testid="profile-search-result"
                  disabled={creating}
                  onClick={() => void startConversationWith(profile)}
                >
                  <span>{peerPresentationLabel(profile)}</span>
                  {profile.username ? (
                    <span className="text-xs text-[var(--text-subtle)]">
                      @{profile.username}
                    </span>
                  ) : null}
                </button>
              ))}
            </div>
          )}
        </div>
      ) : null}

      <div
        className="mx-4 mb-2 flex flex-wrap items-center gap-1.5"
        role="group"
        aria-label="Person filter"
      >
        <button
          type="button"
          className={
            filterRelationshipId === null
              ? "rounded-full bg-[var(--accent)] px-3 py-1 text-xs font-medium text-[var(--accent-foreground,var(--background))]"
              : "rounded-full border border-[var(--panel-border)] px-3 py-1 text-xs text-[var(--text-subtle)] transition-colors hover:text-[var(--text)]"
          }
          onClick={() => setFilterRelationshipId(null)}
        >
          All
        </button>
        {filterOptions.map((option) => (
          <button
            key={option.relationship_id}
            type="button"
            data-testid={`person-filter-${option.relationship_id}`}
            className={
              filterRelationshipId === option.relationship_id
                ? "rounded-full bg-[var(--accent)] px-3 py-1 text-xs font-medium text-[var(--accent-foreground,var(--background))]"
                : "rounded-full border border-[var(--panel-border)] px-3 py-1 text-xs text-[var(--text-subtle)] transition-colors hover:text-[var(--text)]"
            }
            onClick={() => setFilterRelationshipId(option.relationship_id)}
          >
            {option.label}
          </button>
        ))}
      </div>

      {loading && conversations.length === 0 ? (
        <p className="px-4 py-6 text-center text-sm text-[var(--text-subtle)]">
          Loading your conversations…
        </p>
      ) : loadError && conversations.length === 0 ? (
        <div className="px-4 py-6 text-center">
          <p className="text-sm text-[var(--text-subtle)]">{loadError}</p>
          <button
            type="button"
            className="mt-2 rounded-lg border border-[var(--panel-border)] px-3 py-1.5 text-xs text-[var(--text)]"
            onClick={() => void reload()}
          >
            Retry
          </button>
        </div>
      ) : conversations.length === 0 ? (
        <p className="px-4 py-6 text-center text-sm text-[var(--text-subtle)]">
          No conversations yet. Start one by searching a Codexify username.
        </p>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2" role="list">
          {filteredPeer && filterRelationshipId !== null ? (
            <div className="mb-2 mt-1 flex items-center gap-2 rounded-xl border border-[var(--panel-border)] bg-[var(--panel-bg)] px-3 py-2">
              <span
                className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent)]/15 text-xs font-semibold text-[var(--accent)]"
                aria-hidden="true"
              >
                {avatarInitials(peerPresentationLabel(filteredPeer))}
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-[var(--text)]">
                  {peerPresentationLabel(filteredPeer)}
                </p>
                <p className="text-xs text-[var(--text-subtle)]">
                  All conversations with this person
                </p>
              </div>
            </div>
          ) : null}
          {visibleConversations.map((conversation) => {
            const peer = conversation.peer;
            const peerLabel = peerPresentationLabel(peer);
            return (
              <button
                key={conversation.conversation_id}
                type="button"
                data-testid="conversation-row"
                className="mb-1 flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left transition-colors hover:bg-[var(--panel-bg-hover,var(--panel-bg))]"
                onClick={() =>
                  state.openConversation(
                    conversation.conversation_id,
                    conversation
                  )
                }
              >
                <span
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--accent)]/15 text-xs font-semibold text-[var(--accent)]"
                  aria-hidden="true"
                >
                  {avatarInitials(peerLabel)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="truncate text-sm font-medium text-[var(--text)]">
                      {peerLabel}
                    </span>
                    <span className="shrink-0 text-[11px] text-[var(--text-subtle)]">
                      {formatActivity(conversation.latest_activity_at)}
                    </span>
                  </span>
                  {profileSubtitle(peer) ? (
                    <span className="block truncate text-xs text-[var(--text-subtle)]">
                      {profileSubtitle(peer)}
                    </span>
                  ) : null}
                  <span className="mt-0.5 block truncate text-xs text-[var(--text-subtle)]">
                    {conversation.latest_message
                      ? conversation.latest_message.preview
                      : "No messages yet"}
                  </span>
                  <span className="block truncate text-[11px] text-[var(--text-subtle)]/80">
                    ↳ {originLabel(conversation, projectLabels)} · placed in{" "}
                    {projectLabel(conversation.placement.project_id, projectLabels)}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
