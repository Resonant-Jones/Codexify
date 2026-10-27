/**
 * Canonical direct-message Inbox: the conversation-first projection over
 * the accepted ADR-079/080 Relationship → Conversations model.
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
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import MessageRequestPanel from "./MessageRequestPanel";
import { useOnboarding } from "@/features/onboarding/OnboardingProvider";

import type { RuntimeRouteCapabilityState } from "@/contracts/supportedProfileRoutes";
import DirectConversation from "@/features/contacts/DirectConversation";
import type { PeopleMessagingState } from "@/features/contacts/usePeopleMessagingState";
import {
  buildPeerFilterOptions,
  createDirectMessageConversation,
  fetchDirectMessageConversation,
  fetchProjectLabelMap,
  fetchThreadProjectScope,
  filterConversationsByRelationship,
  normalizeDirectMessageError,
  normalizeUsernameSearchQuery,
  peerPresentationLabel,
  resolveDirectMessageRelationship,
  searchDirectMessageProfiles,
  USERNAME_SEARCH_MIN_LENGTH,
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

/** How often the open Inbox re-reads the conversation projection so a message
 *  that arrives elsewhere surfaces as unread without a manual reload. */
const UNREAD_REFRESH_INTERVAL_MS = 15_000;

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
  labels: Map<number, string>,
): string {
  if (projectId == null) return "Unscoped";
  return labels.get(projectId) ?? "Project";
}

function originLabel(
  conversation: DirectMessageConversation,
  labels: Map<number, string>,
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
  const onboarding = useOnboarding();
  const [conversations, setConversations] = useState<
    DirectMessageConversation[]
  >([]);
  const [projectLabels, setProjectLabels] = useState<Map<number, string>>(
    () => new Map(),
  );
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [filterRelationshipId, setFilterRelationshipId] = useState<
    string | null
  >(null);

  const [newConversationOpen, setNewConversationOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<
    DirectMessageSocialProfile[]
  >([]);
  const [searching, setSearching] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [ownProfile, setOwnProfile] =
    useState<DirectMessageSocialProfile | null>(null);
  const [introPeer, setIntroPeer] = useState<DirectMessageSocialProfile | null>(
    null,
  );

  const messagingEnabled = capabilityState === "available";
  const syncIdentity = useCallback(
    (profile: DirectMessageSocialProfile) => {
      setOwnProfile(profile);
      onboarding?.setProfile(profile);
    },
    [onboarding?.setProfile],
  );

  // Depend on the specific stable callbacks, never on the whole `state`
  // object.  The People state owner replaces its state object whenever
  // conversation metadata is cached; a callback that depended on the whole
  // object would be recreated by that replacement, re-running the fetch
  // effect, which would fetch, cache, replace, and fetch again.
  const { cacheConversationMeta, refreshUnreadProjection } = state;

  const reload = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [conversationRows, labels] = await Promise.all([
        refreshUnreadProjection(),
        fetchProjectLabelMap(),
      ]);
      setConversations(conversationRows);
      setProjectLabels(labels);
    } catch (error) {
      const normalized = normalizeDirectMessageError(error);
      setLoadError(
        normalized.status === 404
          ? "Direct messaging is unavailable in this profile."
          : normalized.message,
      );
    } finally {
      setLoading(false);
    }
  }, [refreshUnreadProjection]);

  /**
   * Refresh only the conversation projection so recipient-local unread
   * counts stay current while the Inbox is open.  It never advances a read
   * cursor: only opening a conversation does that, server-side.
   */
  const refreshUnread = useCallback(async () => {
    try {
      const conversationRows = await refreshUnreadProjection();
      setConversations(conversationRows);
    } catch {
      // A failed unread refresh must never disturb the visible Inbox.
    }
  }, [refreshUnreadProjection]);

  /**
   * Marking a conversation read is the reader's own explicit action: it
   * advances the caller's recipient-local cursor through the ONE shared path
   * in the People state owner — the same path the floating window uses — and
   * the projection is then re-read so the caller's own unread badge clears.
   * Fetching a conversation is read-only and never marks anything read.  The
   * peer can never observe this.
   *
   * The cursor advances to the caller's **read watermark** — the last message
   * they actually saw — and never past it, so a message that arrived after
   * their transcript was fetched is not marked read without having been shown.
   *
   * Resolves to whether the read is recorded.  A failed read is left
   * *retryable*: the watermark is remembered only once the mutation has
   * actually succeeded, so reopening the conversation retries it.
   */
  const markConversationRead = useCallback(
    async (conversationId: string, watermarkMessageId: string | null) => {
      const recorded = await state.markConversationRead(
        conversationId,
        watermarkMessageId,
      );
      if (recorded) await refreshUnread();
      return recorded;
    },
    [refreshUnread, state.markConversationRead],
  );

  const openAcceptedConversation = useCallback(
    async (conversationId: string) => {
      const conversation = await fetchDirectMessageConversation(conversationId);
      cacheConversationMeta(conversation);
      state.openConversation(conversationId, conversation);
    },
    [cacheConversationMeta, state.openConversation],
  );

  useEffect(() => {
    if (!messagingEnabled) return;
    void reload();
  }, [messagingEnabled, reload]);

  // Mark the opened conversation read once its transcript has actually been
  // rendered, using the last rendered message as the read watermark.  Waiting
  // for the transcript is what keeps the watermark honest: a message that
  // arrived after the transcript was fetched is not marked read.
  //
  // The watermark is remembered per conversation, so reopening a conversation
  // whose transcript has not changed yet does not re-post a stale watermark;
  // the refreshed transcript posts its own once it renders.
  //
  // This is surface-local bookkeeping: it keeps THIS surface from re-posting
  // and re-refreshing for a watermark it already handled.  The People state
  // owner holds the *shared* guard, so the Inbox and the floating window
  // never post the same watermark twice.
  //
  // A watermark is remembered only once the mutation has actually SUCCEEDED.
  // The mutation is idempotent, so a failed read stays retryable: the next
  // reopen posts it again instead of leaving the badge stuck.
  const markedWatermarks = useRef<Map<string, string>>(new Map());
  const pendingWatermarks = useRef<Set<string>>(new Set());
  useEffect(() => {
    const conversationId = state.selectedConversationId;
    if (!conversationId) return;
    if (!state.loadedByConversationId[conversationId]) return;
    const rendered = state.messagesByConversationId[conversationId] ?? [];
    const watermark = rendered.length > 0 ? rendered[rendered.length - 1].message_id : null;
    if (watermark === null) return;
    if (markedWatermarks.current.get(conversationId) === watermark) return;
    const attemptKey = `${conversationId}:${watermark}`;
    if (pendingWatermarks.current.has(attemptKey)) return;
    pendingWatermarks.current.add(attemptKey);
    void markConversationRead(conversationId, watermark).then((recorded) => {
      pendingWatermarks.current.delete(attemptKey);
      if (recorded) {
        markedWatermarks.current.set(conversationId, watermark);
      }
    });
  }, [
    markConversationRead,
    state.loadedByConversationId,
    state.messagesByConversationId,
    state.selectedConversationId,
  ]);

  // Poll the conversation projection while the Inbox is visible so a message
  // that arrives in another session surfaces as unread without a manual
  // reload.  The poll is inert once the surface is closed.
  useEffect(() => {
    if (!messagingEnabled) return;
    if (!state.peopleOpen || state.activeTab !== "inbox") return;
    const timer = window.setInterval(() => {
      void refreshUnread();
    }, UNREAD_REFRESH_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [
    messagingEnabled,
    refreshUnread,
    state.peopleOpen,
    state.activeTab,
  ]);

  const filterOptions = useMemo(
    () => buildPeerFilterOptions(conversations),
    [conversations],
  );

  const visibleConversations = useMemo(
    () =>
      filterConversationsByRelationship(conversations, filterRelationshipId),
    [conversations, filterRelationshipId],
  );

  const filteredPeer = useMemo(() => {
    if (filterRelationshipId === null) return null;
    return visibleConversations[0]?.peer ?? null;
  }, [filterRelationshipId, visibleConversations]);

  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchRequestSequence = useRef(0);

  const runSearch = useCallback(
    async (query: string, requestSequence: number) => {
      const normalized = normalizeUsernameSearchQuery(query);
      if (normalized.length < USERNAME_SEARCH_MIN_LENGTH) {
        if (requestSequence === searchRequestSequence.current) {
          setSearchResults([]);
          setSearching(false);
        }
        return;
      }
      setSearching(true);
      setCreateError(null);
      try {
        const results = await searchDirectMessageProfiles(normalized);
        // A slower earlier response must never replace a newer query's
        // results.
        if (requestSequence === searchRequestSequence.current) {
          setSearchResults(results);
        }
      } catch (error) {
        if (requestSequence === searchRequestSequence.current) {
          setCreateError(normalizeDirectMessageError(error).message);
          setSearchResults([]);
        }
      } finally {
        if (requestSequence === searchRequestSequence.current) {
          setSearching(false);
        }
      }
    },
    [],
  );

  const handleSearchQueryChange = useCallback(
    (value: string) => {
      const requestSequence = searchRequestSequence.current + 1;
      searchRequestSequence.current = requestSequence;
      setSearchQuery(value);
      if (searchTimer.current) window.clearTimeout(searchTimer.current);
      if (normalizeUsernameSearchQuery(value).length < USERNAME_SEARCH_MIN_LENGTH) {
        setSearchResults([]);
        setSearching(false);
        return;
      }
      searchTimer.current = window.setTimeout(() => {
        void runSearch(value, requestSequence);
      }, 250);
    },
    [runSearch],
  );

  const closeSearch = useCallback(() => {
    // Invalidate any in-flight search so a late response cannot repopulate a
    // surface the user already closed.
    searchRequestSequence.current += 1;
    if (searchTimer.current) {
      window.clearTimeout(searchTimer.current);
      searchTimer.current = null;
    }
    setNewConversationOpen(false);
    setSearchQuery("");
    setSearchResults([]);
    setSearching(false);
    setCreateError(null);
  }, []);

  useEffect(
    () => () => {
      if (searchTimer.current) window.clearTimeout(searchTimer.current);
    },
    [],
  );

  const normalizedSearchQuery = useMemo(
    () => normalizeUsernameSearchQuery(searchQuery),
    [searchQuery],
  );

  const computeOrigin =
    useCallback(async (): Promise<ConversationOriginInput> => {
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
          profile.profile_id,
        );
        if (!relationship.messaging_consent_established) {
          setIntroPeer(profile);
          setNewConversationOpen(false);
          setSearchQuery("");
          setSearchResults([]);
          return;
        }
        const origin = await computeOrigin();
        const conversation = await createDirectMessageConversation(
          relationship.relationship_id,
          origin,
        );
        state.cacheConversationMeta(conversation);
        setNewConversationOpen(false);
        setSearchQuery("");
        setSearchResults([]);
        await reload();
        state.openConversation(conversation.conversation_id, conversation);
      } catch (error) {
        const normalized = normalizeDirectMessageError(error);
        if (normalized.code === "messaging_consent_required") {
          setIntroPeer(profile);
          setNewConversationOpen(false);
          setSearchQuery("");
          setSearchResults([]);
        } else {
          setCreateError(normalized.message);
        }
      } finally {
        setCreating(false);
      }
    },
    [computeOrigin, reload, state],
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
          disabled={ownProfile?.username_state !== "active"}
          onClick={() => setNewConversationOpen((current) => !current)}
        >
          <MessageSquarePlus size={14} aria-hidden="true" />
          Find People
        </button>
      </div>

      <MessageRequestPanel
        introPeer={introPeer}
        onIntroClose={() => setIntroPeer(null)}
        onIdentity={syncIdentity}
        onAccepted={openAcceptedConversation}
      />

      {newConversationOpen ? (
        <div
          className="mx-4 mb-3 rounded-xl border border-[var(--panel-border)] bg-[var(--panel-bg)] p-3"
          aria-label="Find People"
        >
          <div className="flex items-center gap-2 rounded-lg border border-[var(--panel-border)] bg-[var(--background,transparent)] px-2.5 py-1.5">
            <Search
              size={13}
              aria-hidden="true"
              className="text-[var(--text-subtle)]"
            />
            <input
              type="search"
              className="min-w-0 flex-1 bg-transparent text-sm text-[var(--text)] outline-none placeholder:text-[var(--text-subtle)]"
              value={searchQuery}
              placeholder="Search by Codexify username"
              aria-label="Search profiles by username"
              onChange={(event) => {
                handleSearchQueryChange(event.target.value);
              }}
            />
            <button
              type="button"
              aria-label="Close new conversation search"
              className="text-[var(--text-subtle)] hover:text-[var(--text)]"
              onClick={closeSearch}
            >
              <X size={13} aria-hidden="true" />
            </button>
          </div>
          <p className="mt-1 text-[11px] text-[var(--text-subtle)]">
            Search covers people on this node only.
          </p>
          {createError ? (
            <p className="mt-2 text-xs text-[var(--text-subtle)]">
              {createError}
            </p>
          ) : null}
          {searching ? (
            <p className="mt-2 text-xs text-[var(--text-subtle)]">Searching…</p>
          ) : searchQuery.trim() &&
            normalizedSearchQuery.length < USERNAME_SEARCH_MIN_LENGTH ? (
              <p className="mt-2 text-xs text-[var(--text-subtle)]">
                Type at least {USERNAME_SEARCH_MIN_LENGTH} characters to search.
              </p>
            ) : normalizedSearchQuery.length >= USERNAME_SEARCH_MIN_LENGTH &&
              searchResults.length === 0 ? (
              <p className="mt-2 text-xs text-[var(--text-subtle)]">
                No profiles on this node match “{normalizedSearchQuery}”.
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
            // The badge reads the SHARED caller-local projection first.
            //
            // A read recorded by another surface — the floating window —
            // updates that shared projection immediately, while this
            // Inbox's own conversation rows are only refreshed by a
            // refetch or the poll tick.  Preferring the shared entry keeps
            // an already-visible badge honest without adding a second
            // counter, a second store, or another request; the shared
            // projection is a presentation copy of the same caller-local
            // read state, never an authority.
            //
            // The Inbox's own row remains the fallback for a Conversation
            // the shared projection does not carry yet.
            const sharedConversation =
              state.conversationMetaById[conversation.conversation_id];
            const unreadCount = Math.max(
              0,
              Number(
                sharedConversation?.unread_count ??
                  conversation.unread_count ??
                  0,
              ) || 0,
            );
            return (
              <button
                key={conversation.conversation_id}
                type="button"
                data-testid="conversation-row"
                className="mb-1 flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left transition-colors hover:bg-[var(--panel-bg-hover,var(--panel-bg))]"
                onClick={() =>
                  state.openConversation(
                    conversation.conversation_id,
                    conversation,
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
                    <span className="flex shrink-0 items-center gap-2">
                      {unreadCount > 0 ? (
                        <span
                          data-testid="conversation-unread-badge"
                          aria-label={`${unreadCount} unread message${
                            unreadCount === 1 ? "" : "s"
                          }`}
                          className="inline-flex min-w-4 items-center justify-center rounded-full bg-[var(--accent)] px-1.5 py-0.5 text-[10px] font-semibold leading-none text-[var(--accent-contrast,#fff)]"
                        >
                          {unreadCount > 99 ? "99+" : unreadCount}
                        </span>
                      ) : null}
                      <span className="text-[11px] text-[var(--text-subtle)]">
                        {formatActivity(conversation.latest_activity_at)}
                      </span>
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
                    {projectLabel(
                      conversation.placement.project_id,
                      projectLabels,
                    )}
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
