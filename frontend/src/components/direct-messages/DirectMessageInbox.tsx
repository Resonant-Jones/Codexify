/**
 * General direct-message Inbox (relationship-scoped).
 *
 * Conversation-first projection over the accepted ADR-077/078 model:
 * every row is one Conversation_ID; the person filter selects a peer
 * Relationship and shows every visible Conversation under it — it never
 * collapses multiple Conversations into one canonical thread.
 *
 * Privacy posture: renders only server-returned social fields.  No
 * email, no internal user_id, no origin reconstruction, no peer
 * placement, no unread fiction, no realtime.
 */

import React from "react";

import {
  buildPeerFilterOptions,
  createGeneralDirectMessageConversation,
  directMessageErrorStatus,
  fetchDirectMessageConversations,
  fetchDirectMessageMessages,
  fetchOwnSocialIdentity,
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
  type PeerFilterOption,
  type SocialProfilePayload,
} from "@/lib/direct-messages";

const MESSAGE_PAGE_SIZE = 100;

type InboxLoadState =
  | { status: "loading" }
  | { status: "ready" }
  | { status: "error"; message: string };

type ThreadState = {
  conversationId: string;
  messages: MessageEnvelope[];
  loading: boolean;
  loadingOlder: boolean;
  exhaustedOlder: boolean;
  historyError: string | null;
};

type NewMessageState = {
  open: boolean;
  query: string;
  results: SocialProfilePayload[];
  searching: boolean;
  searchError: string | null;
  creating: boolean;
  createError: string | null;
};

type ComposerState = {
  text: string;
  sending: boolean;
  sendError: string | null;
};

function styles(): Record<string, React.CSSProperties> {
  return {
    root: {
      display: "flex",
      height: "100%",
      minHeight: 0,
      color: "var(--text)",
      background: "color-mix(in oklab, var(--panel-bg) 92%, transparent)",
    },
    side: {
      width: 340,
      minWidth: 260,
      maxWidth: "42%",
      borderRight: "1px solid var(--panel-border)",
      display: "flex",
      flexDirection: "column",
      minHeight: 0,
    },
    sideHeader: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "14px 16px",
      borderBottom: "1px solid var(--panel-border)",
      gap: 10,
    },
    title: { fontWeight: 700, letterSpacing: "-0.02em", fontSize: 17 },
    newButton: {
      border: "1px solid var(--panel-border)",
      background: "rgba(255,255,255,0.06)",
      color: "var(--text)",
      borderRadius: 999,
      padding: "6px 12px",
      fontSize: 13,
      cursor: "pointer",
    },
    chips: {
      display: "flex",
      gap: 8,
      padding: "10px 16px",
      overflowX: "auto",
      borderBottom: "1px solid var(--panel-border)",
      flexWrap: "nowrap",
    },
    chip: {
      border: "1px solid var(--panel-border)",
      background: "transparent",
      color: "var(--muted)",
      borderRadius: 999,
      padding: "4px 12px",
      fontSize: 12.5,
      whiteSpace: "nowrap",
      cursor: "pointer",
    },
    chipActive: {
      border: "1px solid var(--accent, #7aa2f7)",
      color: "var(--text)",
      background: "rgba(255,255,255,0.08)",
    },
    list: { flex: 1, overflowY: "auto", minHeight: 0 },
    row: {
      width: "100%",
      textAlign: "left",
      padding: "12px 16px",
      border: "none",
      borderBottom: "1px solid var(--panel-border)",
      background: "transparent",
      color: "var(--text)",
      cursor: "pointer",
    },
    rowActive: { background: "rgba(255,255,255,0.06)" },
    rowTop: {
      display: "flex",
      justifyContent: "space-between",
      gap: 10,
      alignItems: "baseline",
    },
    rowPeer: { fontWeight: 600, fontSize: 14, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
    rowTime: { fontSize: 11.5, color: "var(--muted)", flexShrink: 0 },
    rowPreview: {
      fontSize: 12.5,
      color: "var(--muted)",
      marginTop: 3,
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap",
    },
    thread: { flex: 1, display: "flex", flexDirection: "column", minWidth: 0, minHeight: 0 },
    threadHeader: {
      padding: "14px 18px",
      borderBottom: "1px solid var(--panel-border)",
      fontWeight: 700,
      letterSpacing: "-0.02em",
    },
    messages: { flex: 1, overflowY: "auto", minHeight: 0, padding: "14px 18px" },
    bubbleRow: { display: "flex", marginBottom: 10 },
    bubble: {
      maxWidth: "72%",
      borderRadius: 14,
      padding: "8px 12px",
      fontSize: 13.5,
      lineHeight: 1.45,
      border: "1px solid var(--panel-border)",
    },
    bubbleMine: { background: "rgba(122,162,247,0.16)", marginLeft: "auto" },
    bubblePeer: { background: "rgba(255,255,255,0.05)" },
    bubbleMeta: { fontSize: 10.5, color: "var(--muted)", marginTop: 4, display: "flex", gap: 8 },
    composer: {
      display: "flex",
      gap: 8,
      padding: "12px 18px",
      borderTop: "1px solid var(--panel-border)",
      alignItems: "flex-end",
    },
    composerInput: {
      flex: 1,
      background: "rgba(255,255,255,0.05)",
      border: "1px solid var(--panel-border)",
      borderRadius: 12,
      color: "var(--text)",
      padding: "10px 12px",
      fontSize: 13.5,
      resize: "none",
      minHeight: 42,
      maxHeight: 140,
    },
    sendButton: {
      border: "1px solid var(--accent, #7aa2f7)",
      background: "rgba(122,162,247,0.18)",
      color: "var(--text)",
      borderRadius: 12,
      padding: "10px 16px",
      fontSize: 13,
      cursor: "pointer",
    },
    subtle: { color: "var(--muted)", fontSize: 13 },
    centered: {
      flex: 1,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flexDirection: "column",
      gap: 10,
      padding: 24,
      textAlign: "center",
    },
    errorText: { color: "#f1a8a8", fontSize: 12.5 },
    backdrop: {
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.45)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 200,
    },
    modal: {
      width: 420,
      maxWidth: "92vw",
      borderRadius: 16,
      border: "1px solid var(--panel-border)",
      background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
      color: "var(--text)",
      padding: 18,
      boxShadow: "0 24px 80px rgba(0,0,0,0.4)",
    },
    modalTitle: { fontWeight: 700, marginBottom: 12, letterSpacing: "-0.02em" },
    modalActions: { display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 14 },
    ghostButton: {
      border: "1px solid var(--panel-border)",
      background: "transparent",
      color: "var(--muted)",
      borderRadius: 10,
      padding: "7px 14px",
      fontSize: 13,
      cursor: "pointer",
    },
    resultRow: {
      width: "100%",
      textAlign: "left",
      border: "1px solid var(--panel-border)",
      background: "rgba(255,255,255,0.04)",
      color: "var(--text)",
      borderRadius: 10,
      padding: "9px 12px",
      marginTop: 6,
      cursor: "pointer",
    },
  };
}

function formatTimestamp(value: string | undefined | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function DirectMessageInbox() {
  const s = styles();
  const [loadState, setLoadState] = React.useState<InboxLoadState>({
    status: "loading",
  });
  const [conversations, setConversations] = React.useState<ConversationProjection[]>([]);
  const [selfProfile, setSelfProfile] = React.useState<SocialProfilePayload | null>(null);
  const [selectedRelationshipId, setSelectedRelationshipId] = React.useState<string | null>(null);
  const [activeConversationId, setActiveConversationId] = React.useState<string | null>(null);
  const [thread, setThread] = React.useState<ThreadState | null>(null);
  const [composer, setComposer] = React.useState<ComposerState>({
    text: "",
    sending: false,
    sendError: null,
  });
  const pendingSendKeyRef = React.useRef<string | null>(null);
  const [newMessage, setNewMessage] = React.useState<NewMessageState>({
    open: false,
    query: "",
    results: [],
    searching: false,
    searchError: null,
    creating: false,
    createError: null,
  });
  const listRequestRef = React.useRef(0);
  const threadRequestRef = React.useRef(0);

  const loadList = React.useCallback(async () => {
    const requestId = ++listRequestRef.current;
    setLoadState({ status: "loading" });
    try {
      const [nextConversations, ownProfile] = await Promise.all([
        fetchDirectMessageConversations(),
        fetchOwnSocialIdentity(),
      ]);
      if (requestId !== listRequestRef.current) return;
      setConversations(nextConversations);
      setSelfProfile(ownProfile);
      setLoadState({ status: "ready" });
    } catch (error) {
      if (requestId !== listRequestRef.current) return;
      setLoadState({
        status: "error",
        message:
          directMessageErrorStatus(error) === 401
            ? "Direct messages require an authenticated session."
            : "Could not load your direct messages.",
      });
    }
  }, []);

  React.useEffect(() => {
    void loadList();
  }, [loadList]);

  const openConversation = React.useCallback(
    async (conversation: ConversationProjection) => {
      const requestId = ++threadRequestRef.current;
      setActiveConversationId(conversation.conversation_id);
      setComposer((current) => ({ ...current, sendError: null }));
      setThread({
        conversationId: conversation.conversation_id,
        messages: [],
        loading: true,
        loadingOlder: false,
        exhaustedOlder: false,
        historyError: null,
      });
      try {
        const messages = await fetchDirectMessageMessages(conversation.conversation_id, {
          limit: MESSAGE_PAGE_SIZE,
        });
        if (requestId !== threadRequestRef.current) return;
        setThread((current) =>
          current && current.conversationId === conversation.conversation_id
            ? {
                ...current,
                messages,
                loading: false,
                exhaustedOlder: messages.length < MESSAGE_PAGE_SIZE,
              }
            : current
        );
      } catch {
        if (requestId !== threadRequestRef.current) return;
        setThread((current) =>
          current && current.conversationId === conversation.conversation_id
            ? {
                ...current,
                loading: false,
                historyError: "Could not load this conversation's messages.",
              }
            : current
        );
      }
    },
    []
  );

  const loadOlderMessages = React.useCallback(async () => {
    if (!thread || thread.loadingOlder || thread.exhaustedOlder) return;
    const oldest = thread.messages[0];
    if (!oldest) return;
    setThread((current) => (current ? { ...current, loadingOlder: true } : current));
    try {
      const older = await fetchDirectMessageMessages(thread.conversationId, {
        limit: MESSAGE_PAGE_SIZE,
        beforeId: oldest.message_id,
      });
      setThread((current) =>
        current && current.conversationId === thread.conversationId
          ? {
              ...current,
              messages: prependOlderMessages(current.messages, older),
              loadingOlder: false,
              exhaustedOlder: older.length < MESSAGE_PAGE_SIZE,
            }
          : current
      );
    } catch {
      setThread((current) =>
        current && current.conversationId === thread.conversationId
          ? {
              ...current,
              loadingOlder: false,
              historyError: "Could not load earlier messages.",
            }
          : current
      );
    }
  }, [thread]);

  const handleSend = React.useCallback(async () => {
    const body = composer.text.trim();
    if (!body || !thread || composer.sending) return;
    const conversationId = thread.conversationId;
    // Stable per-attempt key: retrying the same attempt replays, never duplicates.
    const clientMessageKey =
      pendingSendKeyRef.current ?? crypto.randomUUID();
    pendingSendKeyRef.current = clientMessageKey;
    setComposer((current) => ({ ...current, sending: true, sendError: null }));
    try {
      const result = await sendDirectMessage(conversationId, body, clientMessageKey);
      pendingSendKeyRef.current = null;
      setThread((current) =>
        current && current.conversationId === conversationId
          ? {
              ...current,
              messages: mergeConfirmedMessage(current.messages, result.message),
            }
          : current
      );
      setComposer({ text: "", sending: false, sendError: null });
      void loadList();
    } catch (error) {
      // Keep the key so a retry replays instead of duplicating.
      setComposer((current) => ({
        ...current,
        sending: false,
        sendError:
          directMessageErrorStatus(error) === 404
            ? "This conversation is no longer available."
            : "Message could not be sent. Try again.",
      }));
    }
  }, [composer.text, composer.sending, thread, loadList]);

  const handleSearch = React.useCallback(async () => {
    const query = newMessage.query.trim();
    if (!query) {
      setNewMessage((current) => ({ ...current, results: [], searchError: null }));
      return;
    }
    setNewMessage((current) => ({ ...current, searching: true, searchError: null }));
    try {
      const results = await searchDirectMessageProfiles(query);
      setNewMessage((current) => ({ ...current, searching: false, results }));
    } catch {
      setNewMessage((current) => ({
        ...current,
        searching: false,
        searchError: "Profile search failed. Try again.",
      }));
    }
  }, [newMessage.query]);

  const handleCreateWithPeer = React.useCallback(
    async (peer: SocialProfilePayload) => {
      setNewMessage((current) => ({ ...current, creating: true, createError: null }));
      try {
        const relationship = await resolveDirectMessageRelationship(
          peer.node_id,
          peer.profile_id
        );
        const conversation = await createGeneralDirectMessageConversation(
          relationship.relationship_id
        );
        setNewMessage({
          open: false,
          query: "",
          results: [],
          searching: false,
          searchError: null,
          creating: false,
          createError: null,
        });
        await loadList();
        await openConversation(conversation);
      } catch (error) {
        const status = directMessageErrorStatus(error);
        setNewMessage((current) => ({
          ...current,
          creating: false,
          createError:
            status === 404
              ? "That profile is not available on this node."
              : status === 400
                ? "You cannot message your own profile."
                : "Could not start the conversation. Try again.",
        }));
      }
    },
    [loadList, openConversation]
  );

  const filterOptions: PeerFilterOption[] = React.useMemo(
    () => buildPeerFilterOptions(conversations, selfProfile?.profile_id),
    [conversations, selfProfile]
  );

  const visibleConversations = React.useMemo(
    () => filterConversationsByRelationship(conversations, selectedRelationshipId),
    [conversations, selectedRelationshipId]
  );

  const activeConversation = React.useMemo(
    () =>
      conversations.find(
        (conversation) => conversation.conversation_id === activeConversationId
      ) ?? null,
    [conversations, activeConversationId]
  );

  const activePeer = React.useMemo(
    () =>
      activeConversation
        ? peerForCaller(activeConversation.participants, selfProfile?.profile_id)
        : null,
    [activeConversation, selfProfile]
  );

  const selectedPeerLabel =
    selectedRelationshipId === null
      ? null
      : (filterOptions.find(
          (option) => option.relationship_id === selectedRelationshipId
        )?.label ?? null);

  return (
    <div style={s.root} data-testid="direct-message-inbox">
      <aside style={s.side}>
        <div style={s.sideHeader}>
          <div style={s.title}>Inbox</div>
          <button
            type="button"
            style={s.newButton}
            data-testid="inbox-new-message"
            onClick={() =>
              setNewMessage((current) => ({
                ...current,
                open: true,
                results: [],
                query: "",
                searchError: null,
                createError: null,
              }))
            }
          >
            New message
          </button>
        </div>

        {loadState.status === "loading" ? (
          <div style={s.centered} data-testid="inbox-loading">
            <span style={s.subtle}>Loading your messages…</span>
          </div>
        ) : loadState.status === "error" ? (
          <div style={s.centered} data-testid="inbox-error">
            <span style={s.errorText}>{loadState.message}</span>
            <button type="button" style={s.ghostButton} onClick={() => void loadList()}>
              Retry
            </button>
          </div>
        ) : conversations.length === 0 ? (
          <div style={s.centered} data-testid="inbox-empty">
            <span style={{ fontWeight: 600 }}>No messages yet</span>
            <span style={s.subtle}>
              Start a private conversation with someone on your node.
            </span>
            <button
              type="button"
              style={s.newButton}
              onClick={() =>
                setNewMessage((current) => ({ ...current, open: true }))
              }
            >
              New message
            </button>
          </div>
        ) : (
          <>
            <div style={s.chips} data-testid="inbox-filters">
              <button
                type="button"
                data-testid="inbox-filter-all"
                style={{
                  ...s.chip,
                  ...(selectedRelationshipId === null ? s.chipActive : {}),
                }}
                onClick={() => setSelectedRelationshipId(null)}
              >
                All
              </button>
              {filterOptions.map((option) => (
                <button
                  key={option.relationship_id}
                  type="button"
                  data-testid={`inbox-filter-${option.relationship_id}`}
                  style={{
                    ...s.chip,
                    ...(selectedRelationshipId === option.relationship_id
                      ? s.chipActive
                      : {}),
                  }}
                  onClick={() => setSelectedRelationshipId(option.relationship_id)}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <div style={s.list} data-testid="inbox-conversation-list">
              {visibleConversations.length === 0 ? (
                <div style={s.centered}>
                  <span style={s.subtle}>No conversations with this person.</span>
                </div>
              ) : (
                visibleConversations.map((conversation) => {
                  const peer = peerForCaller(
                    conversation.participants,
                    selfProfile?.profile_id
                  );
                  const active = conversation.conversation_id === activeConversationId;
                  return (
                    <button
                      key={conversation.conversation_id}
                      type="button"
                      data-testid={`inbox-conversation-${conversation.conversation_id}`}
                      style={{ ...s.row, ...(active ? s.rowActive : {}) }}
                      onClick={() => void openConversation(conversation)}
                    >
                      <div style={s.rowTop}>
                        <span style={s.rowPeer}>{peerPresentationLabel(peer)}</span>
                        <span style={s.rowTime}>
                          {formatTimestamp(
                            conversation.latest_message?.created_at ??
                              conversation.latest_activity_at
                          )}
                        </span>
                      </div>
                      <div style={s.rowPreview}>
                        {conversation.latest_message
                          ? conversation.latest_message.preview
                          : "No messages yet"}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </>
        )}
      </aside>

      <section style={s.thread}>
        {thread === null ? (
          <div style={s.centered} data-testid="inbox-thread-empty">
            <span style={{ fontWeight: 600 }}>Select a conversation</span>
            <span style={s.subtle}>
              Each conversation stays a distinct thread — even with the same
              person.
            </span>
          </div>
        ) : (
          <>
            <div style={s.threadHeader}>
              {peerPresentationLabel(activePeer)}
              {selectedPeerLabel ? ` · ${selectedPeerLabel}` : ""}
            </div>
            <div style={s.messages} data-testid="inbox-message-list">
              {thread.historyError && (
                <div style={{ ...s.errorText, marginBottom: 10 }}>
                  {thread.historyError}
                </div>
              )}
              {!thread.exhaustedOlder && (
                <button
                  type="button"
                  data-testid="inbox-load-older"
                  style={s.ghostButton}
                  disabled={thread.loadingOlder}
                  onClick={() => void loadOlderMessages()}
                >
                  {thread.loadingOlder ? "Loading…" : "Load earlier"}
                </button>
              )}
              {thread.loading ? (
                <div style={{ ...s.subtle, padding: "10px 0" }}>Loading…</div>
              ) : thread.messages.length === 0 ? (
                <div style={s.centered} data-testid="inbox-thread-no-messages">
                  <span style={s.subtle}>No messages yet. Say hello.</span>
                </div>
              ) : (
                thread.messages.map((message) => {
                  const mine = message.source.profile_id === selfProfile?.profile_id;
                  return (
                    <div
                      key={message.message_id}
                      style={{
                        ...s.bubbleRow,
                        justifyContent: mine ? "flex-end" : "flex-start",
                      }}
                      data-testid={`inbox-message-${message.message_id}`}
                    >
                      <div
                        style={{
                          ...s.bubble,
                          ...(mine ? s.bubbleMine : s.bubblePeer),
                        }}
                      >
                        <div style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
                          {message.content.body}
                        </div>
                        <div style={s.bubbleMeta}>
                          <span>{mine ? "You" : peerPresentationLabel(activePeer)}</span>
                          <span>{formatTimestamp(message.created_at)}</span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
            <div style={s.composer}>
              <textarea
                style={s.composerInput}
                data-testid="inbox-composer"
                placeholder="Write a message…"
                value={composer.text}
                onChange={(event) =>
                  setComposer((current) => ({ ...current, text: event.target.value }))
                }
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void handleSend();
                  }
                }}
              />
              <button
                type="button"
                style={s.sendButton}
                data-testid="inbox-send"
                disabled={composer.sending || !composer.text.trim()}
                onClick={() => void handleSend()}
              >
                {composer.sending ? "Sending…" : "Send"}
              </button>
            </div>
            {composer.sendError && (
              <div style={{ padding: "0 18px 10px" }}>
                <span style={s.errorText}>{composer.sendError}</span>
              </div>
            )}
          </>
        )}
      </section>

      {newMessage.open && (
        <div style={s.backdrop} data-testid="inbox-new-message-modal">
          <div style={s.modal}>
            <div style={s.modalTitle}>New message</div>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                style={{ ...s.composerInput, flex: 1 }}
                data-testid="inbox-profile-search"
                placeholder="Search local profiles…"
                value={newMessage.query}
                onChange={(event) =>
                  setNewMessage((current) => ({
                    ...current,
                    query: event.target.value,
                  }))
                }
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    void handleSearch();
                  }
                }}
              />
              <button
                type="button"
                style={s.sendButton}
                disabled={newMessage.searching}
                onClick={() => void handleSearch()}
              >
                {newMessage.searching ? "Searching…" : "Search"}
              </button>
            </div>
            {newMessage.searchError && (
              <div style={{ marginTop: 8 }}>
                <span style={s.errorText}>{newMessage.searchError}</span>
              </div>
            )}
            <div style={{ marginTop: 6 }}>
              {newMessage.results.length === 0 && !newMessage.searching ? (
                <div style={{ ...s.subtle, marginTop: 8 }} data-testid="inbox-search-empty">
                  No local profiles match.
                </div>
              ) : (
                newMessage.results.map((profile) => (
                  <button
                    key={profile.profile_id}
                    type="button"
                    style={s.resultRow}
                    data-testid={`inbox-profile-result-${profile.profile_id}`}
                    disabled={newMessage.creating}
                    onClick={() => void handleCreateWithPeer(profile)}
                  >
                    {peerPresentationLabel(profile)}
                    {profile.display_name && profile.username
                      ? ` · ${profile.display_name}`
                      : ""}
                  </button>
                ))
              )}
            </div>
            {newMessage.createError && (
              <div style={{ marginTop: 8 }}>
                <span style={s.errorText}>{newMessage.createError}</span>
              </div>
            )}
            <div style={s.modalActions}>
              <button
                type="button"
                style={s.ghostButton}
                onClick={() =>
                  setNewMessage((current) => ({ ...current, open: false }))
                }
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
